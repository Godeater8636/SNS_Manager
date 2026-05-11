"""ChikaFetcher の応答パースを検証 (ネットワークアクセスなし)."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.fetchers.chika_fetcher import ChikaFetcher


def test_parse_response_extracts_valid_points() -> None:
    fetcher = ChikaFetcher(
        config={"enabled": True, "endpoint": "http://example", "year": 2025},
        http=MagicMock(),
    )
    payload = {
        "status": "OK",
        "data": [
            {
                "lat": 35.681,
                "lon": 139.767,
                "address": "東京都千代田区丸の内1-1",
                "price_per_sqm": 1500000,
                "use_category": "商業地",
                "year": 2025,
            },
            # 日本外 → 除外される想定
            {"lat": 0.0, "lon": 0.0, "address": "海上"},
            # 緯度欠落 → 除外
            {"lon": 139.0, "address": "不正"},
        ],
    }
    points = fetcher._parse_response(payload)
    assert len(points) == 1
    assert "丸の内" in points[0].name
    assert "1,500,000" in points[0].description_html


def test_fetch_disabled_returns_empty() -> None:
    fetcher = ChikaFetcher(
        config={"enabled": False, "endpoint": "http://example"},
        http=MagicMock(),
    )
    result = fetcher.fetch()
    assert result.is_empty()
