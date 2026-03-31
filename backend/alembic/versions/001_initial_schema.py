"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-31
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # plans
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("price_jpy", sa.Integer(), nullable=False),
        sa.Column("max_accounts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_posts_month", sa.Integer(), nullable=True),
        sa.Column("can_automate", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("stripe_price_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("plan_started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("plan_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("trial_ends_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("stripe_customer_id", sa.String(100), nullable=True),
        sa.Column("stripe_sub_id", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("totp_secret", sa.String(100), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Tokyo"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("stripe_customer_id"),
        sa.UniqueConstraint("stripe_sub_id"),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_stripe_customer_id", "users", ["stripe_customer_id"])

    # social_accounts
    op.create_table(
        "social_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False, server_default="x"),
        sa.Column("x_username", sa.String(50), nullable=False),
        sa.Column("x_display_name", sa.String(100), nullable=True),
        sa.Column("encrypted_password", sa.Text(), nullable=False),
        sa.Column("encrypted_cookies", sa.Text(), nullable=True),
        sa.Column("encryption_key_id", sa.String(50), nullable=False),
        sa.Column("daily_like_limit", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("daily_follow_limit", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("action_min_interval_sec", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("action_max_interval_sec", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("active_hours_start", sa.SmallInteger(), nullable=False, server_default="7"),
        sa.Column("active_hours_end", sa.SmallInteger(), nullable=False, server_default="23"),
        sa.Column("burst_size", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("burst_rest_sec", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("session_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("daily_likes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("daily_follows_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("daily_reset_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "x_username", name="uq_social_accounts_user_username"),
    )
    op.create_index("idx_social_accounts_user_id", "social_accounts", ["user_id"])

    # posts
    op.create_table(
        "posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("social_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_post_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("thread_order", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("media_urls", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("posted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("x_tweet_id", sa.String(50), nullable=True),
        sa.Column("retry_count", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("is_template", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["social_account_id"], ["social_accounts.id"]),
        sa.ForeignKeyConstraint(["parent_post_id"], ["posts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('draft','scheduled','posting','posted','failed','cancelled')", name="ck_posts_status"),
    )
    op.create_index("idx_posts_user_id", "posts", ["user_id"])
    op.create_index("idx_posts_social_account_id", "posts", ["social_account_id"])
    op.create_index("idx_posts_status_scheduled_at", "posts", ["status", "scheduled_at"],
                    postgresql_where=sa.text("status = 'scheduled'"))

    # post_analytics
    op.create_table(
        "post_analytics",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fetched_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retweets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("replies", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quotes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bookmarks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("link_clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("engagement_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_post_analytics_post_id", "post_analytics", ["post_id"])
    op.create_index("idx_post_analytics_fetched_at", "post_analytics", ["fetched_at"])

    # affiliate_links
    op.create_table(
        "affiliate_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("destination_url", sa.Text(), nullable=False),
        sa.Column("slug", sa.String(20), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("total_clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("redirect_on_expire", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("idx_affiliate_links_user_id", "affiliate_links", ["user_id"])
    op.create_index("idx_affiliate_links_slug", "affiliate_links", ["slug"])
    op.create_index("idx_affiliate_links_tags", "affiliate_links", ["tags"], postgresql_using="gin")

    # link_clicks
    op.create_table(
        "link_clicks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("affiliate_link_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("clicked_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("user_agent_hash", sa.String(64), nullable=True),
        sa.Column("referer", sa.Text(), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.ForeignKeyConstraint(["affiliate_link_id"], ["affiliate_links.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_link_clicks_affiliate_link_id", "link_clicks", ["affiliate_link_id"])
    op.create_index("idx_link_clicks_clicked_at", "link_clicks", ["clicked_at"])
    op.create_index("idx_link_clicks_post_id", "link_clicks", ["post_id"])

    # tasks
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("social_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_type", sa.String(30), nullable=False),
        sa.Column("search_keyword", sa.String(500), nullable=True),
        sa.Column("target_username", sa.String(50), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("cron_expression", sa.String(100), nullable=False, server_default="*/30 * * * *"),
        sa.Column("total_executed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_success", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_executed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("next_execute_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["social_account_id"], ["social_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("task_type IN ('auto_like','auto_follow','auto_unfollow')", name="ck_tasks_task_type"),
    )
    op.create_index("idx_tasks_user_id", "tasks", ["user_id"])
    op.create_index("idx_tasks_social_account_id", "tasks", ["social_account_id"])
    op.create_index("idx_tasks_enabled_next", "tasks", ["is_enabled", "next_execute_at"],
                    postgresql_where=sa.text("is_enabled = true"))

    # task_logs
    op.create_table(
        "task_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("executed_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("target_x_user_id", sa.String(50), nullable=True),
        sa.Column("target_tweet_id", sa.String(50), nullable=True),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_task_logs_task_id", "task_logs", ["task_id"])
    op.create_index("idx_task_logs_executed_at", "task_logs", ["executed_at"])

    # payments
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("stripe_payment_intent_id", sa.String(100), nullable=True),
        sa.Column("stripe_invoice_id", sa.String(100), nullable=True),
        sa.Column("amount_jpy", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="JPY"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("paid_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("period_start", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("period_end", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_payment_intent_id"),
        sa.UniqueConstraint("stripe_invoice_id"),
        sa.CheckConstraint("status IN ('pending','succeeded','failed','refunded')", name="ck_payments_status"),
    )
    op.create_index("idx_payments_user_id", "payments", ["user_id"])
    op.create_index("idx_payments_stripe_invoice_id", "payments", ["stripe_invoice_id"])

    # Seed plans
    op.execute("""
        INSERT INTO plans (name, display_name, price_jpy, max_accounts, max_posts_month, can_automate)
        VALUES
            ('starter',  'Starter',  2980,  1,    100,  false),
            ('pro',      'Pro',      7980,  5,    1000, true),
            ('business', 'Business', 19800, 20,   NULL, true)
    """)


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("task_logs")
    op.drop_table("tasks")
    op.drop_table("link_clicks")
    op.drop_table("affiliate_links")
    op.drop_table("post_analytics")
    op.drop_table("posts")
    op.drop_table("social_accounts")
    op.drop_table("users")
    op.drop_table("plans")
