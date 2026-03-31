"""
Celery tasks for auto-like / auto-follow execution with BAN avoidance.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.worker.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.task import Task, TaskLog
from app.models.social_account import SocialAccount
from app.services.twikit_service import TwikitService
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.worker.auto_tasks.dispatch_auto_tasks")
def dispatch_auto_tasks():
    """Scan enabled tasks whose next_execute_at has passed and dispatch them."""
    _run_async(_async_dispatch_auto_tasks())


async def _async_dispatch_auto_tasks():
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Task).where(
                and_(
                    Task.is_enabled.is_(True),
                    Task.next_execute_at <= now,
                )
            ).limit(100)
        )
        tasks = result.scalars().all()

    for task in tasks:
        run_auto_task.delay(str(task.id))
        logger.info("Dispatched auto task %s (type=%s)", task.id, task.task_type)


@celery_app.task(name="app.worker.auto_tasks.run_auto_task", bind=True)
def run_auto_task(self, task_id: str):
    _run_async(_async_run_auto_task(task_id))


async def _async_run_auto_task(task_id: str):
    async with AsyncSessionLocal() as db:
        task_result = await db.execute(select(Task).where(Task.id == uuid.UUID(task_id)))
        task = task_result.scalar_one_or_none()
        if not task or not task.is_enabled:
            return

        acc_result = await db.execute(
            select(SocialAccount).where(SocialAccount.id == task.social_account_id)
        )
        account = acc_result.scalar_one_or_none()
        if not account or not account.is_active:
            logger.warning("Account not found or inactive for task %s", task_id)
            return

        # Check active hours
        service = TwikitService(
            x_username=account.x_username,
            encrypted_password=account.encrypted_password,
            encrypted_cookies=account.encrypted_cookies,
        )
        if not service._is_active_hours(account.active_hours_start, account.active_hours_end):
            logger.debug("Outside active hours for account %s. Skipping.", account.x_username)
            _update_next_execute(task)
            await db.commit()
            return

        # Daily limit check
        if task.task_type == "auto_like" and account.daily_likes_count >= account.daily_like_limit:
            logger.info("Daily like limit reached for account %s", account.x_username)
            _update_next_execute(task)
            await db.commit()
            return
        if task.task_type == "auto_follow" and account.daily_follows_count >= account.daily_follow_limit:
            logger.info("Daily follow limit reached for account %s", account.x_username)
            _update_next_execute(task)
            await db.commit()
            return

        # Calculate max actions remaining
        if task.task_type == "auto_like":
            max_actions = min(
                account.burst_size,
                account.daily_like_limit - account.daily_likes_count,
            )
        else:
            max_actions = min(
                account.burst_size,
                account.daily_follow_limit - account.daily_follows_count,
            )

        logs: list[dict] = []
        try:
            if task.task_type == "auto_like" and task.search_keyword:
                logs = await service.search_and_like(
                    keyword=task.search_keyword,
                    max_count=max_actions,
                    min_interval_sec=account.action_min_interval_sec,
                    max_interval_sec=account.action_max_interval_sec,
                    burst_size=account.burst_size,
                    burst_rest_sec=account.burst_rest_sec,
                )
            elif task.task_type == "auto_follow" and task.target_username:
                logs = await service.follow_user_followers(
                    target_username=task.target_username,
                    max_count=max_actions,
                    min_interval_sec=account.action_min_interval_sec,
                    max_interval_sec=account.action_max_interval_sec,
                    burst_size=account.burst_size,
                    burst_rest_sec=account.burst_rest_sec,
                )
        except Exception as e:
            logger.error("Auto task %s execution error: %s", task_id, e)
            logs = [{"action": "error", "error_message": str(e), "target_tweet_id": None,
                     "target_x_user_id": None, "response_time_ms": None}]

        # Persist logs and update counters
        success_count = sum(1 for l in logs if l["action"] in ("liked", "followed"))
        failed_count = sum(1 for l in logs if l["action"] == "error")

        for log_data in logs:
            log = TaskLog(
                task_id=task.id,
                target_tweet_id=log_data.get("target_tweet_id"),
                target_x_user_id=log_data.get("target_x_user_id"),
                action=log_data["action"],
                error_message=log_data.get("error_message"),
                response_time_ms=log_data.get("response_time_ms"),
            )
            db.add(log)

        task.total_executed += len(logs)
        task.total_success += success_count
        task.total_failed += failed_count
        task.last_executed_at = datetime.now(timezone.utc)
        _update_next_execute(task)

        if task.task_type == "auto_like":
            account.daily_likes_count += success_count
        elif task.task_type == "auto_follow":
            account.daily_follows_count += success_count

        # Update cookies if refreshed
        if service._encrypted_cookies and service._encrypted_cookies != account.encrypted_cookies:
            account.encrypted_cookies = service._encrypted_cookies

        await db.commit()
        logger.info("Auto task %s completed: %d success, %d failed", task_id, success_count, failed_count)


def _update_next_execute(task: Task):
    """Calculate next execution time from cron expression."""
    from croniter import croniter
    cron = croniter(task.cron_expression, datetime.now(timezone.utc))
    task.next_execute_at = cron.get_next(datetime)


@celery_app.task(name="app.worker.auto_tasks.reset_daily_counters")
def reset_daily_counters():
    """Reset daily action counters for all social accounts at midnight JST."""
    _run_async(_async_reset_daily_counters())


async def _async_reset_daily_counters():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SocialAccount))
        accounts = result.scalars().all()
        now = datetime.now(timezone.utc)
        for account in accounts:
            account.daily_likes_count = 0
            account.daily_follows_count = 0
            account.daily_reset_at = now
        await db.commit()
        logger.info("Reset daily counters for %d accounts", len(accounts))
