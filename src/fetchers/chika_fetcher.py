"""① 国土交通省 地価公示データ取得モジュール.

不動産情報ライブラリ API (https://www.reinfolib.mlit.go.jp/help/apiManual/)
の XIT001 (地価公示・地価調査ポイント) を呼び出す想定。

サイト仕様変更で API の URL や応答 JSON 構造が変わった場合は、
``_parse_response`` を修正することで対応する。
"""

from __future__ import annotations

import logging
from typing import Any

from src.fetchers.base import FetchResult, PointFeature
from src.utils.geo import LatLon
from src.utils.http_client import HttpClient


class ChikaFetcher:
    """地価公示データを取得するフェッチャ."""

    SOURCE_NAME = "MLIT 地価公示"

    def __init__(
        self,
        config: dict[str, Any],
        http: HttpClient,
        api_key: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.config = config
        self.http = http
        self.api_key = api_key
        self.logger = logger or logging.getLogger(__name__)

    def fetch(self) -> FetchResult:
        if not self.config.get("enabled", True):
            self.logger.info("地価フェッチ: 無効化されているためスキップ")
            return FetchResult(source=self.SOURCE_NAME)

        if not self.api_key:
            # APIキー無しのまま叩くと 401 で4回リトライして時間を浪費する。
            # 早期に分かりやすい例外で停止し、対処方法を案内する。
            raise RuntimeError(
                "不動産情報ライブラリ API キーが未設定です。\n"
                "1) https://www.reinfolib.mlit.go.jp/help/apiManual/ で API キーを取得\n"
                "2) 環境変数 REINFOLIB_API_KEY=<取得したキー> を設定して再実行\n"
                "   (動作確認だけなら --demo オプションで API 不要のサンプルが作れます)"
            )

        endpoint: str = self.config["endpoint"]
        year = self.config.get("year")
        prefectures: list[str] = self.config.get("prefecture_codes") or [""]

        result = FetchResult(source=self.SOURCE_NAME)
        for pref in prefectures:
            params: dict[str, Any] = {}
            if year:
                params["year"] = year
            if pref:
                params["area"] = pref
            headers: dict[str, str] = {}
            if self.api_key:
                # 不動産情報ライブラリ API は Ocp-Apim-Subscription-Key を使う
                headers["Ocp-Apim-Subscription-Key"] = self.api_key

            self.logger.info(
                "地価データ取得: pref=%s year=%s endpoint=%s",
                pref or "ALL",
                year,
                endpoint,
            )
            response = self.http.get(endpoint, params=params, headers=headers)
            payload = response.json()
            result.points.extend(self._parse_response(payload))

        self.logger.info("地価ポイント取得件数: %d", len(result.points))
        return result

    def _parse_response(self, payload: dict[str, Any]) -> list[PointFeature]:
        """API応答を PointFeature の列に正規化する.

        想定構造 (不動産情報ライブラリ V4):
            {
              "status": "OK",
              "data": [
                 {
                    "point_id": "...",
                    "lat": 35.681236,
                    "lon": 139.767125,
                    "address": "東京都千代田区...",
                    "price_per_sqm": 1200000,
                    "use_category": "商業地",
                    "year": 2025
                 }, ...
              ]
            }

        構造が変わった場合はここを修正する。
        """
        rows = payload.get("data") or payload.get("results") or []
        points: list[PointFeature] = []
        for row in rows:
            lat = _to_float(row.get("lat") or row.get("latitude"))
            lon = _to_float(row.get("lon") or row.get("longitude"))
            if lat is None or lon is None:
                continue
            ll = LatLon(lat=lat, lon=lon)
            if not ll.is_in_japan():
                continue

            address = row.get("address") or row.get("住所") or "(住所不明)"
            price = row.get("price_per_sqm") or row.get("u_current_year_price")
            use = row.get("use_category") or row.get("地目") or ""
            year = row.get("year") or row.get("u_target_year_name_ja") or ""

            description_html = _build_balloon_html(address, price, use, year)
            points.append(
                PointFeature(
                    point=ll,
                    name=f"{address} ({use})" if use else address,
                    description_html=description_html,
                    attributes={
                        "address": address,
                        "price_per_sqm": price,
                        "use_category": use,
                        "year": year,
                    },
                )
            )
        return points


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_balloon_html(address: str, price: Any, use: str, year: Any) -> str:
    price_str = (
        f"{int(price):,} 円/㎡" if isinstance(price, (int, float)) and price else "—"
    )
    return (
        "<table style=\"font-family:sans-serif;font-size:12px\">"
        f"<tr><th align='left'>住所</th><td>{_h(address)}</td></tr>"
        f"<tr><th align='left'>用途</th><td>{_h(use) or '—'}</td></tr>"
        f"<tr><th align='left'>公示価格</th><td>{price_str}</td></tr>"
        f"<tr><th align='left'>基準年</th><td>{_h(str(year)) or '—'}</td></tr>"
        "</table>"
    )


def _h(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
