"""エラー通知モジュール.

設計図 ③ の「エラー監視 (サイト仕様変更対応、エラー通知)」を担う。
SMTP 設定が無い・通知が無効化されている場合はログのみ。
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any

from src.utils.config import env_or_none


class Notifier:
    def __init__(
        self, config: dict[str, Any], logger: logging.Logger | None = None
    ) -> None:
        self.config = config or {}
        self.logger = logger or logging.getLogger(__name__)

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled"))

    def notify_error(self, subject: str, body: str) -> None:
        """エラーメッセージを送信する. 失敗してもアプリは止めない."""
        self.logger.error("[NOTIFY] %s\n%s", subject, body)
        if not self.enabled:
            return
        try:
            self._send_email(subject, body)
        except Exception:  # noqa: BLE001
            self.logger.exception("通知メール送信に失敗")

    def _send_email(self, subject: str, body: str) -> None:
        email_cfg = self.config.get("email") or {}
        host = env_or_none(email_cfg.get("smtp_host_env"))
        port = env_or_none(email_cfg.get("smtp_port_env"))
        user = env_or_none(email_cfg.get("smtp_user_env"))
        password = env_or_none(email_cfg.get("smtp_password_env"))
        from_addr = email_cfg.get("from_addr")
        to_addrs = email_cfg.get("to_addrs") or []

        if not host or not from_addr or not to_addrs:
            self.logger.warning("通知有効だがSMTP設定が不足。スキップ")
            return

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_addrs)
        msg.set_content(body)

        port_int = int(port) if port else 587
        with smtplib.SMTP(host, port_int, timeout=30) as smtp:
            smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
