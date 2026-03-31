"""
Celery tasks for scheduled post execution and Twikit session management.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta

from celery import shared_task
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.worker.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.post import Post, PostAnalytics
from app.models.social_account import SocialAccount
from app.services.twikit_service import TwikitService

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _run_async(coro):
    """Run async coroutine in sync Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.worker.post_tasks.dispatch_scheduled_posts")
def dispatch_scheduled_posts():
    """Scan for posts due for publishing and enqueue them."""
    _run_async(_async_dispatch_scheduled_posts())


async def _async_dispatch_scheduled_posts():
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Post).where(
                and_(
                    Post.status == "scheduled",
                    Post.scheduled_at <= now,
                    Post.parent_post_id.is_(None),  # Only dispatch root posts
                )
            ).limit(50)
        )
        posts = result.scalars().all()
        for post in posts:
            post.status = "posting"
        await db.commit()

    for post in posts:
        execute_post.delay(str(post.id))
        logger.info("Enqueued post %s for execution", post.id)


@celery_app.task(
    name="app.worker.post_tasks.execute_post",
    bind=True,
    max_retries=MAX_RETRIES,
    default_retry_delay=60,
)
def execute_post(self, post_id: str):
    _run_async(_async_execute_post(self, post_id))


async def _async_execute_post(task, post_id: str):
    async with AsyncSessionLocal() as db:
        # Load root post and all thread children
        root_result = await db.execute(
            select(Post).where(Post.id == uuid.UUID(post_id))
        )
        root_post = root_result.scalar_one_or_none()
        if not root_post:
            logger.error("Post %s not found", post_id)
            return

        # Gather full thread in order
        thread: list[Post] = [root_post]
        if root_post.id:
            children_result = await db.execute(
                select(Post).where(Post.parent_post_id == root_post.id)
                .order_by(Post.thread_order)
            )
            thread.extend(children_result.scalars().all())

        # Load social account
        acc_result = await db.execute(
            select(SocialAccount).where(SocialAccount.id == root_post.social_account_id)
        )
        account = acc_result.scalar_one_or_none()
        if not account:
            logger.error("SocialAccount not found for post %s", post_id)
            await _mark_failed(db, root_post, "SocialAccount not found")
            return

        service = TwikitService(
            x_username=account.x_username,
            encrypted_password=account.encrypted_password,
            encrypted_cookies=account.encrypted_cookies,
        )

        try:
            prev_tweet_id = None
            for i, post in enumerate(thread):
                tweet_id = await service.post_tweet(
                    content=post.content,
                    media_ids=None,  # TODO: upload media to Twikit
                    reply_to_tweet_id=prev_tweet_id,
                )
                post.x_tweet_id = tweet_id
                post.status = "posted"
                post.posted_at = datetime.now(timezone.utc)
                prev_tweet_id = tweet_id

                # Create initial analytics record
                analytics = PostAnalytics(post_id=post.id)
                db.add(analytics)

                # Intra-thread delay (3 ± 0.5s)
                if i < len(thread) - 1:
                    import random
                    await asyncio.sleep(max(1.0, random.gauss(3, 0.5)))

            # Update cookies if re-login occurred
            if service._encrypted_cookies and service._encrypted_cookies != account.encrypted_cookies:
                account.encrypted_cookies = service._encrypted_cookies
                account.last_login_at = datetime.now(timezone.utc)
                account.session_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

            await db.commit()
            logger.info("Successfully posted thread starting at post %s", post_id)

        except Exception as e:
            await db.rollback()
            logger.error("Post execution failed for %s: %s", post_id, e)

            async with AsyncSessionLocal() as db2:
                root_result2 = await db2.execute(select(Post).where(Post.id == uuid.UUID(post_id)))
                root_post2 = root_result2.scalar_one_or_none()
                if root_post2:
                    root_post2.retry_count += 1
                    if root_post2.retry_count >= MAX_RETRIES:
                        await _mark_failed(db2, root_post2, str(e))
                    else:
                        root_post2.status = "scheduled"
                        backoff = 2 ** root_post2.retry_count * 60
                        task.retry(countdown=backoff, exc=e)
                    await db2.commit()


async def _mark_failed(db: AsyncSession, post: Post, error: str):
    post.status = "failed"
    post.last_error = error[:500]
    await db.commit()
    logger.error("Post %s permanently failed: %s", post.id, error)
    # TODO: send email notification to user


@celery_app.task(name="app.worker.post_tasks.twikit_login_task")
def twikit_login_task(account_id: str):
    """Perform initial Twikit login and store cookies."""
    _run_async(_async_twikit_login(account_id))


async def _async_twikit_login(account_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SocialAccount).where(SocialAccount.id == uuid.UUID(account_id))
        )
        account = result.scalar_one_or_none()
        if not account:
            logger.error("Account %s not found for Twikit login", account_id)
            return

        service = TwikitService(
            x_username=account.x_username,
            encrypted_password=account.encrypted_password,
        )
        try:
            encrypted_cookies = await service.login()
            account.encrypted_cookies = encrypted_cookies
            account.last_login_at = datetime.now(timezone.utc)
            account.session_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            await db.commit()
            logger.info("Twikit login completed for account %s (%s)", account_id, account.x_username)
        except Exception as e:
            logger.error("Twikit login failed for account %s: %s", account_id, e)
