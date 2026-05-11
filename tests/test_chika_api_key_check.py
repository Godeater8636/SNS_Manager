"""APIキー未設定時に分かりやすい例外で停止することを確認."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.fetchers.chika_fetcher import ChikaFetcher


def test_missing_api_key_raises_clear_error() -> None:
    fetcher = ChikaFetcher(
        config={"enabled": True, "endpoint": "http://example", "year": 2025},
        http=MagicMock(),
        api_key=None,
    )
    with pytest.raises(RuntimeError) as exc:
        fetcher.fetch()
    msg = str(exc.value)
    assert "REINFOLIB_API_KEY" in msg
    assert "--demo" in msg


def test_with_api_key_attempts_http(monkeypatch) -> None:
    http = MagicMock()
    http.get.return_value.json.return_value = {"data": []}
    fetcher = ChikaFetcher(
        config={
            "enabled": True,
            "endpoint": "http://example",
            "year": 2025,
            "prefecture_codes": ["13"],
        },
        http=http,
        api_key="dummy-key",
    )
    result = fetcher.fetch()
    assert http.get.called
    assert result.is_empty()
