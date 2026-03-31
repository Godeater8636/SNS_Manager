from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "sns_manager",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.worker.post_tasks",
        "app.worker.auto_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tokyo",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    # Beat schedule
    beat_schedule={
        # Check scheduled posts every minute
        "dispatch-scheduled-posts": {
            "task": "app.worker.post_tasks.dispatch_scheduled_posts",
            "schedule": 60.0,  # every 60 seconds
        },
        # Check enabled auto tasks every minute
        "dispatch-auto-tasks": {
            "task": "app.worker.auto_tasks.dispatch_auto_tasks",
            "schedule": 60.0,
        },
        # Reset daily counters at midnight JST (15:00 UTC)
        "reset-daily-counters": {
            "task": "app.worker.auto_tasks.reset_daily_counters",
            "schedule": crontab(hour=15, minute=0),
        },
    },
)
