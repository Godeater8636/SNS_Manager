"""② ハザードマップデータ取得モジュール.

国土数値情報 (https://nlftp.mlit.go.jp/ksj/) の ZIP/GeoJSON や、
自治体オープンデータの GeoJSON エンドポイントを取得する。

サポート形式:
  - ``geojson``      : 単一 GeoJSON ファイル
  - ``geojson_zip``  : GeoJSON を含む ZIP
  - ``kml``          : 既に KML の場合 (placeholder)
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from typing import Any

from src.fetchers.base import FetchResult, PolygonFeature
from src.utils.geo import LatLon
from src.utils.http_client import HttpClient


class HazardFetcher:
    """ハザード情報を複数レイヤー分まとめて取得する."""

    SOURCE_NAME = "MLIT ハザードマップ"

    def __init__(
        self,
        config: dict[str, Any],
        http: HttpClient,
        logger: logging.Logger | None = None,
    ) -> None:
        self.config = config
        self.http = http
        self.logger = logger or logging.getLogger(__name__)

    def fetch(self) -> FetchResult:
        if not self.config.get("enabled", True):
            self.logger.info("ハザードフェッチ: 無効化されているためスキップ")
            return FetchResult(source=self.SOURCE_NAME)

        layers = self.config.get("layers") or []
        result = FetchResult(source=self.SOURCE_NAME)

        for layer in layers:
            try:
                polygons = self._fetch_layer(layer)
                result.polygons.extend(polygons)
                self.logger.info(
                    "ハザードレイヤー取得: %s 件数=%d",
                    layer.get("name"),
                    len(polygons),
                )
            except Exception:  # noqa: BLE001 - 1レイヤー失敗で全体を止めない
                self.logger.exception(
                    "ハザードレイヤー取得失敗: %s", layer.get("name")
                )
        return result

    def _fetch_layer(self, layer: dict[str, Any]) -> list[PolygonFeature]:
        url: str = layer["url"]
        fmt: str = layer.get("format", "geojson")
        style_id = _style_id(layer["name"])

        response = self.http.get(url, stream=True)
        content = response.content

        if fmt == "geojson":
            geojson = json.loads(content.decode("utf-8"))
        elif fmt == "geojson_zip":
            geojson = _extract_geojson_from_zip(content)
        else:
            raise ValueError(f"未対応のフォーマット: {fmt}")

        return _geojson_to_polygons(geojson, layer["name"], style_id)


def _style_id(layer_name: str) -> str:
    return "style-" + "".join(c for c in layer_name if c.isalnum())[:24].lower()


def _extract_geojson_from_zip(content: bytes) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        # ZIP 内の最初の .geojson / .json を採用
        candidates = [
            n for n in zf.namelist() if n.lower().endswith((".geojson", ".json"))
        ]
        if not candidates:
            raise ValueError("ZIP内にGeoJSONが見つかりません")
        with zf.open(candidates[0]) as fh:
            return json.loads(fh.read().decode("utf-8"))


def _geojson_to_polygons(
    geojson: dict[str, Any], layer_name: str, style_id: str
) -> list[PolygonFeature]:
    """GeoJSON FeatureCollection を PolygonFeature の列に変換する."""
    features = geojson.get("features", [])
    out: list[PolygonFeature] = []
    for feat in features:
        geom = feat.get("geometry") or {}
        gtype = geom.get("type")
        coords = geom.get("coordinates")
        if not gtype or not coords:
            continue

        rings_groups: list[list[list[LatLon]]] = []
        if gtype == "Polygon":
            rings_groups.append(_polygon_to_rings(coords))
        elif gtype == "MultiPolygon":
            for poly in coords:
                rings_groups.append(_polygon_to_rings(poly))
        else:
            continue

        props = feat.get("properties") or {}
        desc = _props_to_html(props)
        for rings in rings_groups:
            if not rings:
                continue
            out.append(
                PolygonFeature(
                    rings=rings,
                    name=layer_name,
                    description_html=desc,
                    style_id=style_id,
                )
            )
    return out


def _polygon_to_rings(polygon_coords: list[list[list[float]]]) -> list[list[LatLon]]:
    rings: list[list[LatLon]] = []
    for ring in polygon_coords:
        latlons = [LatLon(lat=pt[1], lon=pt[0]) for pt in ring if len(pt) >= 2]
        if len(latlons) >= 3:
            rings.append(latlons)
    return rings


def _props_to_html(props: dict[str, Any]) -> str:
    if not props:
        return ""
    rows = "".join(
        f"<tr><th align='left'>{_h(str(k))}</th><td>{_h(str(v))}</td></tr>"
        for k, v in props.items()
    )
    return f"<table style='font-family:sans-serif;font-size:12px'>{rows}</table>"


def _h(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
