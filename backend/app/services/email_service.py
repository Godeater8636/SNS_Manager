"""
Email service — SendGrid or コンソール出力（ローカル開発用）。

環境変数 SENDGRID_API_KEY が未設定の場合は標準出力にメール内容を表示する。
"""

import logging
from app.config import settings

logger = logging.getLogger(__name__)


def _is_sendgrid_configured() -> bool:
    return bool(settings.SENDGRID_API_KEY)


async def send_email(to: str, subject: str, body_html: str, body_text: str | None = None) -> bool:
    """
    メールを送信する。
    SendGrid 未設定時はコンソールに出力して True を返す（ローカル開発用）。
    """
    if _is_sendgrid_configured():
        return await _send_via_sendgrid(to, subject, body_html, body_text)
    else:
        _log_to_console(to, subject, body_html, body_text)
        return True


async def _send_via_sendgrid(to: str, subject: str, body_html: str, body_text: str | None) -> bool:
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email=settings.FROM_EMAIL,
            to_emails=to,
            subject=subject,
            html_content=body_html,
            plain_text_content=body_text,
        )
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sg.send(message)
        logger.info("Email sent via SendGrid to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("SendGrid send failed to %s: %s", to, e)
        return False


def _log_to_console(to: str, subject: str, body_html: str, body_text: str | None):
    """ローカル開発用: メール内容をコンソールに出力する。"""
    separator = "=" * 60
    print(f"\n{separator}")
    print(f"📧  [DEV EMAIL — 実際には送信されません]")
    print(f"  To      : {to}")
    print(f"  From    : {settings.FROM_EMAIL}")
    print(f"  Subject : {subject}")
    print(f"{'-' * 60}")
    print(body_text or body_html)
    print(f"{separator}\n")


# ── 共通メールテンプレート ────────────────────────────────────────────────────

async def send_password_reset_email(to: str, otp: str) -> bool:
    subject = "【SNS Manager】パスワードリセット"
    body_text = f"""
パスワードリセットのリクエストを受け付けました。

リセットコード: {otp}

このコードは30分間有効です。
身に覚えがない場合は無視してください。
"""
    body_html = f"<p>リセットコード: <strong>{otp}</strong></p><p>30分間有効です。</p>"
    return await send_email(to, subject, body_html, body_text)


async def send_post_failed_email(to: str, post_content: str, error: str) -> bool:
    subject = "【SNS Manager】投稿に失敗しました"
    body_text = f"""
予約投稿の実行に失敗しました。

投稿内容: {post_content[:100]}...
エラー: {error}

ダッシュボードから再投稿を行ってください。
"""
    body_html = f"<p>投稿が失敗しました。</p><p>エラー: {error}</p>"
    return await send_email(to, subject, body_html, body_text)
