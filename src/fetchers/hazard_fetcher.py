"""② ハザードマップデータ取得モジュール.

国土数値情報 (https://nlftp.mlit.go.jp/ksj/) や自治体オープンデータから
ZIP / GeoJSON / Shapefile を取得する。

サポート形式 (config.yaml の ``format``):
  - ``geojson``        : 単一 GeoJSON ファイル
  - ``geojson_zip``    : GeoJSON を含む ZIP
  - ``shapefile_zip``  : Shapefile (.shp + .dbf + 任意 .prj) を含む ZIP
  - ``auto_zip``       : ZIP 内の中身を自動判定 (.geojson 優先 → .shp フォールバック)

国土数値情報の ``*_GML.zip`` は多くの場合中身が Shapefile なので、
auto_zip にしておけば追加設定なく取り込める。
"""

from __future__ import annotations

import io
import json
import logging
import tempfile
import zipfile
from pathlib import Path
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
        fmt: str = layer.get("format", "auto_zip")
        style_id = _style_id(layer["name"])
        name = layer["name"]

        response = self.http.get(url, stream=True)
        content = response.content

        if fmt == "geojson":
            geojson = json.loads(content.decode("utf-8"))
            return _geojson_to_polygons(geojson, name, style_id)

        if fmt == "geojson_zip":
            geojson = _extract_geojson_from_zip(content)
            return _geojson_to_polygons(geojson, name, style_id)

        if fmt == "shapefile_zip":
            return _read_shapefile_zip(content, name, style_id, self.logger)

        if fmt == "auto_zip":
            geojson = _try_extract_geojson_from_zip(content)
            if geojson is not None:
                return _geojson_to_polygons(geojson, name, style_id)
            self.logger.info(
                "ZIP内にGeoJSON無し → Shapefile として読込: %s", name
            )
            return _read_shapefile_zip(content, name, style_id, self.logger)

        raise ValueError(f"未対応のフォーマット: {fmt}")


def _style_id(layer_name: str) -> str:
    return "style-" + "".join(c for c in layer_name if c.isalnum())[:24].lower()


def _extract_geojson_from_zip(content: bytes) -> dict[str, Any]:
    result = _try_extract_geojson_from_zip(content)
    if result is None:
        raise ValueError("ZIP内にGeoJSONが見つかりません")
    return result


def _try_extract_geojson_from_zip(content: bytes) -> dict[str, Any] | None:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        candidates = [
            n for n in zf.namelist() if n.lower().endswith((".geojson", ".json"))
        ]
        if not candidates:
            return None
        with zf.open(candidates[0]) as fh:
            return json.loads(fh.read().decode("utf-8"))


def _read_shapefile_zip(
    content: bytes,
    layer_name: str,
    style_id: str,
    logger: logging.Logger,
) -> list[PolygonFeature]:
    """Shapefile を含む ZIP を一時展開して PolygonFeature 列を返す.

    依存: ``pyshp`` (shapefile モジュール)
    座標系はファイル付属 .prj を見ず WGS84 経緯度を想定する。
    国土数値情報は EPSG:6668 (JGD2011) で配布されているが、
    JGD2011 と WGS84 の差はメートル単位で目視判別できないため
    本ツールでは変換せずそのまま扱う。
    """
    try:
        import shapefile  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "Shapefile 読込には pyshp が必要です。\n"
            "  pip install pyshp\n"
            "もしくは requirements.txt から再インストールしてください。"
        ) from exc

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            zf.extractall(tmp_path)

        shp_files = list(tmp_path.rglob("*.shp"))
        if not shp_files:
            raise ValueError("ZIP内にShapefile (.shp) が見つかりません")

        polygons: list[PolygonFeature] = []
        for shp in shp_files:
            logger.info("Shapefile 読込: %s", shp.name)
            polygons.extend(
                _shapefile_to_polygons(shp, layer_name, style_id)
            )
        return polygons


def _shapefile_to_polygons(
    shp_path: Path, layer_name: str, style_id: str
) -> list[PolygonFeature]:
    import shapefile  # type: ignore[import-untyped]

    reader = shapefile.Reader(str(shp_path), encoding="cp932")
    try:
        # 属性カラム名 (.dbf) を取得 (先頭の DeletionFlag は除く)
        field_names = [f[0] for f in reader.fields[1:]]
        out: list[PolygonFeature] = []

        for shape_rec in reader.iterShapeRecords():
            shape = shape_rec.shape
            record = shape_rec.record
            if shape.shapeType not in (
                shapefile.POLYGON,
                shapefile.POLYGONZ,
                shapefile.POLYGONM,
            ):
                continue

            rings = _shape_parts_to_rings(shape)
            if not rings:
                continue

            props = {k: v for k, v in zip(field_names, list(record))}
            desc = _props_to_html(props)
            out.append(
                PolygonFeature(
                    rings=rings,
                    name=layer_name,
                    description_html=desc,
                    style_id=style_id,
                )
            )
        return out
    finally:
        reader.close()


def _shape_parts_to_rings(shape: Any) -> list[list[LatLon]]:
    """pyshp Shape の parts 配列を ring 列に分割する."""
    points = shape.points
    if not points:
        return []
    parts = list(shape.parts) + [len(points)]
    rings: list[list[LatLon]] = []
    for i in range(len(parts) - 1):
        slice_pts = points[parts[i] : parts[i + 1]]
        latlons = [LatLon(lat=pt[1], lon=pt[0]) for pt in slice_pts if len(pt) >= 2]
        if len(latlons) >= 3:
            rings.append(latlons)
    return rings


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
