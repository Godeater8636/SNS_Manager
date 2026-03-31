import stripe
from fastapi import APIRouter, Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.plan import Plan
from app.models.payment import Payment
from app.schemas.payment import (
    PlanResponse, SubscribeRequest, SubscribeResponse,
    ChangePlanRequest, CancelResponse, PaymentResponse,
)
from app.schemas.common import SuccessResponse, PaginatedData
from app.core.exceptions import NotFoundException, ValidationException
from app.config import settings

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/plans")
async def list_plans(db: AsyncSession = Depends(get_db)) -> SuccessResponse[list[PlanResponse]]:
    result = await db.execute(select(Plan).order_by(Plan.price_jpy))
    plans = result.scalars().all()
    return SuccessResponse(data=[PlanResponse.model_validate(p) for p in plans])


@router.post("/subscribe")
async def subscribe(
    body: SubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[SubscribeResponse]:
    plan_result = await db.execute(select(Plan).where(Plan.name == body.plan_name))
    plan = plan_result.scalar_one_or_none()
    if not plan or not plan.stripe_price_id:
        raise NotFoundException("プラン")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Create or retrieve Stripe customer
    if not current_user.stripe_customer_id:
        customer = stripe.Customer.create(email=current_user.email)
        current_user.stripe_customer_id = customer.id

    # Attach payment method
    stripe.PaymentMethod.attach(body.payment_method_id, customer=current_user.stripe_customer_id)
    stripe.Customer.modify(
        current_user.stripe_customer_id,
        invoice_settings={"default_payment_method": body.payment_method_id},
    )

    # Create subscription
    subscription = stripe.Subscription.create(
        customer=current_user.stripe_customer_id,
        items=[{"price": plan.stripe_price_id}],
        expand=["latest_invoice.payment_intent"],
    )

    current_user.stripe_sub_id = subscription.id
    current_user.plan_id = plan.id

    client_secret = None
    if subscription.latest_invoice and subscription.latest_invoice.payment_intent:
        pi = subscription.latest_invoice.payment_intent
        if pi.status == "requires_action":
            client_secret = pi.client_secret

    from datetime import datetime, timezone
    period_end = datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc)
    current_user.plan_expires_at = period_end

    return SuccessResponse(data=SubscribeResponse(
        subscription_id=subscription.id,
        status=subscription.status,
        current_period_end=period_end,
        client_secret=client_secret,
    ))


@router.post("/change-plan")
async def change_plan(
    body: ChangePlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[dict]:
    plan_result = await db.execute(select(Plan).where(Plan.name == body.new_plan_name))
    plan = plan_result.scalar_one_or_none()
    if not plan or not plan.stripe_price_id:
        raise NotFoundException("プラン")

    if not current_user.stripe_sub_id:
        raise ValidationException("アクティブなサブスクリプションがありません")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    subscription = stripe.Subscription.retrieve(current_user.stripe_sub_id)
    stripe.Subscription.modify(
        current_user.stripe_sub_id,
        items=[{"id": subscription["items"]["data"][0]["id"], "price": plan.stripe_price_id}],
        proration_behavior="immediate_with_invoice",
    )
    current_user.plan_id = plan.id
    return SuccessResponse(data={"message": f"プランを{plan.display_name}に変更しました"})


@router.post("/cancel")
async def cancel(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[CancelResponse]:
    if not current_user.stripe_sub_id:
        raise ValidationException("アクティブなサブスクリプションがありません")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    subscription = stripe.Subscription.modify(
        current_user.stripe_sub_id,
        cancel_at_period_end=True,
    )

    from datetime import datetime, timezone
    cancel_at = datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc)
    return SuccessResponse(data=CancelResponse(
        cancel_at=cancel_at,
        message="次回更新日までサービスをご利用いただけます",
    ))


@router.get("/history")
async def payment_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[PaginatedData[PaymentResponse]]:
    result = await db.execute(
        select(Payment).where(Payment.user_id == current_user.id).order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()
    return SuccessResponse(data=PaginatedData(
        items=[PaymentResponse.model_validate(p) for p in payments],
        total=len(payments), page=1, per_page=len(payments) or 1, pages=1,
    ))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET)
    except (stripe.error.SignatureVerificationError, ValueError):
        raise ValidationException("Webhook署名が無効です")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "invoice.payment_succeeded":
        await _handle_payment_succeeded(data, db)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data, db)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data, db)

    return {"received": True}


async def _handle_payment_succeeded(invoice: dict, db: AsyncSession):
    from datetime import datetime, timezone
    customer_id = invoice.get("customer")
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    plan_result = await db.execute(select(Plan).where(Plan.stripe_price_id != None))
    # Find plan by price ID from line items
    for item in invoice.get("lines", {}).get("data", []):
        price_id = item.get("price", {}).get("id")
        if price_id:
            plan_r = await db.execute(select(Plan).where(Plan.stripe_price_id == price_id))
            plan = plan_r.scalar_one_or_none()
            if plan:
                payment = Payment(
                    user_id=user.id,
                    plan_id=plan.id,
                    stripe_invoice_id=invoice.get("id"),
                    amount_jpy=invoice.get("amount_paid", 0),
                    status="succeeded",
                    paid_at=datetime.now(timezone.utc),
                    period_start=datetime.fromtimestamp(item["period"]["start"], tz=timezone.utc) if item.get("period") else None,
                    period_end=datetime.fromtimestamp(item["period"]["end"], tz=timezone.utc) if item.get("period") else None,
                )
                db.add(payment)
                user.plan_id = plan.id
                user.is_active = True
                break

    await db.flush()


async def _handle_payment_failed(invoice: dict, db: AsyncSession):
    customer_id = invoice.get("customer")
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if user:
        # TODO: send failure notification email
        pass


async def _handle_subscription_deleted(subscription: dict, db: AsyncSession):
    customer_id = subscription.get("customer")
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if user:
        starter_result = await db.execute(select(Plan).where(Plan.name == "starter"))
        starter = starter_result.scalar_one_or_none()
        if starter:
            user.plan_id = starter.id
        user.stripe_sub_id = None
    await db.flush()
