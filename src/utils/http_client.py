"""指数バックオフ付き HTTP クライアント.

サイト側の一時的な不調・レート制限・ネットワーク断に強くするため、
全ての外部HTTP呼び出しはこのモジュールを通す。
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from requests import Response


class HttpError(RuntimeError):
    """リトライ後も成功しなかった HTTP 呼び出しを表す例外."""


class HttpClient:
    """単純な GET ヘルパ. 設定からタイムアウト・リトライ回数を受け取る."""

    def __init__(
        self,
        timeout: int = 60,
        retry_count: int = 4,
        backoff_seconds: float = 2.0,
        user_agent: str = "SNS-Manager-AutoMapper/1.0",
        logger: logging.Logger | None = None,
    ) -> None:
        self.timeout = timeout
        self.retry_count = max(retry_count, 1)
        self.backoff_seconds = backoff_seconds
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self.logger = logger or logging.getLogger(__name__)

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        stream: bool = False,
    ) -> Response:
        last_exc: Exception | None = None
        for attempt in range(self.retry_count):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    stream=stream,
                )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_exc = exc
                wait = self.backoff_seconds * (2**attempt)
                self.logger.warning(
                    "HTTP取得失敗 (試行 %d/%d) url=%s 待機 %.1fs: %s",
                    attempt + 1,
                    self.retry_count,
                    url,
                    wait,
                    exc,
                )
                if attempt + 1 < self.retry_count:
                    time.sleep(wait)
        raise HttpError(f"GET 失敗: {url}") from last_exc
