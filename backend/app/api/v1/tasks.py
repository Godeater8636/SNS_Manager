import csv
import io
import uuid
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.task import Task, TaskLog
from app.models.social_account import SocialAccount
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskLogResponse
from app.schemas.common import SuccessResponse, PaginatedData
from app.core.exceptions import NotFoundException, ForbiddenException

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _to_response(task: Task) -> TaskResponse:
    return TaskResponse.model_validate(task)


@router.get("")
async def list_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[PaginatedData[TaskResponse]]:
    result = await db.execute(
        select(Task).where(Task.user_id == current_user.id).order_by(Task.created_at.desc())
    )
    tasks = result.scalars().all()
    return SuccessResponse(data=PaginatedData(
        items=[_to_response(t) for t in tasks],
        total=len(tasks), page=1, per_page=len(tasks) or 1, pages=1,
    ))


@router.post("", status_code=201)
async def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TaskResponse]:
    # Plan check for automation
    if not current_user.plan or not current_user.plan.can_automate:
        raise ForbiddenException("自動化機能はPro以上のプランで利用できます")

    acc_result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == body.social_account_id,
            SocialAccount.user_id == current_user.id,
        )
    )
    if not acc_result.scalar_one_or_none():
        raise NotFoundException("Xアカウント")

    task = Task(
        user_id=current_user.id,
        social_account_id=body.social_account_id,
        task_type=body.task_type,
        search_keyword=body.search_keyword,
        target_username=body.target_username,
        is_enabled=body.is_enabled,
        cron_expression=body.cron_expression,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return SuccessResponse(data=_to_response(task))


@router.patch("/{task_id}")
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TaskResponse]:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundException("タスク")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(task, field, value)

    return SuccessResponse(data=_to_response(task))


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundException("タスク")
    await db.delete(task)


@router.get("/{task_id}/logs")
async def get_task_logs(
    task_id: uuid.UUID,
    action: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[PaginatedData[TaskLogResponse]]:
    task_result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    if not task_result.scalar_one_or_none():
        raise NotFoundException("タスク")

    conditions = [TaskLog.task_id == task_id]
    if action:
        conditions.append(TaskLog.action == action)

    result = await db.execute(
        select(TaskLog).where(and_(*conditions))
        .order_by(TaskLog.executed_at.desc())
        .offset((page - 1) * per_page).limit(per_page)
    )
    logs = result.scalars().all()
    count_result = await db.execute(select(TaskLog).where(and_(*conditions)))
    total = len(count_result.scalars().all())

    return SuccessResponse(data=PaginatedData(
        items=[TaskLogResponse.model_validate(l) for l in logs],
        total=total, page=page, per_page=per_page,
        pages=(total + per_page - 1) // per_page or 1,
    ))


@router.get("/logs/export-csv")
async def export_task_logs_csv(
    task_id: uuid.UUID | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if task_id:
        task_result = await db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
        )
        if not task_result.scalar_one_or_none():
            raise NotFoundException("タスク")
        conditions.append(TaskLog.task_id == task_id)
    else:
        user_tasks = await db.execute(select(Task.id).where(Task.user_id == current_user.id))
        task_ids = [r for r in user_tasks.scalars().all()]
        if task_ids:
            conditions.append(TaskLog.task_id.in_(task_ids))

    result = await db.execute(
        select(TaskLog).where(and_(*conditions) if conditions else True)
        .order_by(TaskLog.executed_at.desc())
    )
    logs = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "task_id", "executed_at", "target_tweet_id", "target_x_user_id", "action", "response_time_ms", "error_message"])
    for log in logs:
        writer.writerow([str(log.id), str(log.task_id), log.executed_at, log.target_tweet_id,
                         log.target_x_user_id, log.action, log.response_time_ms, log.error_message])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=task_logs.csv"},
    )
