"""
Twikit service wrapper.

Handles:
- Login and session management
- Cookie persistence (encrypted in DB)
- Rate-limit aware posting
- Auto-like and auto-follow with BAN avoidance logic
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timezone, timedelta

import twikit
from twikit import Client, TooManyRequests

from app.core.security import encrypt, decrypt
from app.config import settings

logger = logging.getLogger(__name__)

# Twikit rate-limit backoff: 15 minutes
RATE_LIMIT_WAIT_SEC = 60 * 15


class TwikitService:
    def __init__(self, x_username: str, encrypted_password: str, encrypted_cookies: str | None = None):
        self.x_username = x_username
        self._encrypted_password = encrypted_password
        self._encrypted_cookies = encrypted_cookies
        self.client = Client(language="ja")

    async def login(self) -> str:
        """Log in with username/password. Returns encrypted cookies JSON."""
        password = decrypt(self._encrypted_password)
        await self.client.login(
            auth_info_1=self.x_username,
            password=password,
        )
        cookies = self.client.get_cookies()
        cookies_json = json.dumps(cookies)
        encrypted = encrypt(cookies_json)
        logger.info("Twikit login succeeded for %s", self.x_username)
        return encrypted

    async def _ensure_session(self):
        """Restore session from cookies, or re-login if expired."""
        if self._encrypted_cookies:
            try:
                cookies_json = decrypt(self._encrypted_cookies)
                self.client.set_cookies(json.loads(cookies_json))
                return
            except Exception as e:
                logger.warning("Cookie restore failed for %s: %s. Re-logging in.", self.x_username, e)

        # Re-login
        new_encrypted = await self.login()
        self._encrypted_cookies = new_encrypted

    async def post_tweet(self, content: str, media_ids: list[str] | None = None, reply_to_tweet_id: str | None = None) -> str:
        """Post a tweet. Returns tweet ID."""
        await self._ensure_session()
        try:
            tweet = await self.client.create_tweet(
                text=content,
                media_ids=media_ids,
                reply_to=reply_to_tweet_id,
            )
            return tweet.id
        except TooManyRequests:
            logger.warning("Rate limited while posting for %s. Waiting %ds.", self.x_username, RATE_LIMIT_WAIT_SEC)
            await asyncio.sleep(RATE_LIMIT_WAIT_SEC)
            raise

    async def search_and_like(
        self,
        keyword: str,
        max_count: int,
        min_interval_sec: int,
        max_interval_sec: int,
        burst_size: int,
        burst_rest_sec: int,
    ) -> list[dict]:
        """Search tweets and like them with BAN-avoidance delays. Returns action logs."""
        await self._ensure_session()
        logs: list[dict] = []
        liked_count = 0

        try:
            tweets = await self.client.search_tweet(keyword, product="Latest", count=min(max_count * 2, 100))
        except TooManyRequests:
            logger.warning("Rate limited on search for %s. Waiting.", self.x_username)
            await asyncio.sleep(RATE_LIMIT_WAIT_SEC)
            return logs

        for i, tweet in enumerate(tweets):
            if liked_count >= max_count:
                break

            start_time = time.time()
            action = "skipped"
            error_msg = None

            try:
                await tweet.favorite()
                action = "liked"
                liked_count += 1
                logger.debug("Liked tweet %s by %s", tweet.id, self.x_username)
            except TooManyRequests:
                logger.warning("Rate limited on like for %s. Waiting %ds.", self.x_username, RATE_LIMIT_WAIT_SEC)
                await asyncio.sleep(RATE_LIMIT_WAIT_SEC)
                action = "error"
                error_msg = "rate_limit"
            except Exception as e:
                action = "error"
                error_msg = str(e)
                logger.error("Like failed for tweet %s: %s", tweet.id, e)

            elapsed_ms = int((time.time() - start_time) * 1000)
            logs.append({
                "target_tweet_id": tweet.id,
                "target_x_user_id": tweet.user.id if tweet.user else None,
                "action": action,
                "error_message": error_msg,
                "response_time_ms": elapsed_ms,
            })

            # Burst control
            if liked_count > 0 and liked_count % burst_size == 0:
                logger.debug("Burst rest %ds for %s", burst_rest_sec, self.x_username)
                await asyncio.sleep(burst_rest_sec)
            else:
                # Gaussian random delay between actions
                mean = (min_interval_sec + max_interval_sec) / 2
                std = (max_interval_sec - min_interval_sec) / 6
                delay = max(min_interval_sec, min(max_interval_sec, random.gauss(mean, std)))
                await asyncio.sleep(delay)

        return logs

    async def follow_user_followers(
        self,
        target_username: str,
        max_count: int,
        min_interval_sec: int,
        max_interval_sec: int,
        burst_size: int,
        burst_rest_sec: int,
    ) -> list[dict]:
        """Follow followers of a target user with BAN-avoidance delays."""
        await self._ensure_session()
        logs: list[dict] = []
        followed_count = 0

        try:
            target_user = await self.client.get_user_by_screen_name(target_username)
            followers = await target_user.get_followers(count=min(max_count * 2, 200))
        except TooManyRequests:
            await asyncio.sleep(RATE_LIMIT_WAIT_SEC)
            return logs
        except Exception as e:
            logger.error("Failed to get followers of %s: %s", target_username, e)
            return logs

        for follower in followers:
            if followed_count >= max_count:
                break

            start_time = time.time()
            action = "skipped"
            error_msg = None

            try:
                await follower.follow()
                action = "followed"
                followed_count += 1
            except TooManyRequests:
                await asyncio.sleep(RATE_LIMIT_WAIT_SEC)
                action = "error"
                error_msg = "rate_limit"
            except Exception as e:
                action = "error"
                error_msg = str(e)

            elapsed_ms = int((time.time() - start_time) * 1000)
            logs.append({
                "target_x_user_id": follower.id,
                "target_tweet_id": None,
                "action": action,
                "error_message": error_msg,
                "response_time_ms": elapsed_ms,
            })

            if followed_count > 0 and followed_count % burst_size == 0:
                await asyncio.sleep(burst_rest_sec)
            else:
                mean = (min_interval_sec + max_interval_sec) / 2
                std = (max_interval_sec - min_interval_sec) / 6
                delay = max(min_interval_sec, min(max_interval_sec, random.gauss(mean, std)))
                await asyncio.sleep(delay)

        return logs

    def _is_active_hours(self, active_start: int, active_end: int) -> bool:
        now_jst_hour = datetime.now(timezone.utc).hour + 9  # rough JST offset
        now_jst_hour = now_jst_hour % 24
        return active_start <= now_jst_hour <= active_end
