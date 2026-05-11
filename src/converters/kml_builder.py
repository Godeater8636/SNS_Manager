"""KML/KMZ 生成モジュール.

依存ライブラリ ``simplekml`` の薄いラッパ。Google Earth Pro が読める形式
(KML 2.2) に正確な経緯度・吹き出し付きで書き出す。
"""

from __future__ import annotations

import logging
from pathlib import Path

import simplekml

from src.fetchers.base import FetchResult, PointFeature, PolygonFeature


class KmlBuilder:
    """単一の FetchResult を1ファイルにまとめて書き出す."""

    def __init__(self, document_name: str, logger: logging.Logger | None = None) -> None:
        self.kml = simplekml.Kml(name=document_name)
        self.kml.document.name = document_name
        self.logger = logger or logging.getLogger(__name__)
        self._styles: dict[str, simplekml.Style] = {}

    # -- 外部公開 API ----------------------------------------------------------

    def add_result(self, result: FetchResult) -> None:
        if result.is_empty():
            self.logger.warning("空のフェッチ結果のためスキップ: %s", result.source)
            return

        folder = self.kml.newfolder(name=result.source)

        if result.points:
            point_folder = folder.newfolder(name=f"{result.source} (ポイント)")
            for pt in result.points:
                self._add_point(point_folder, pt)

        if result.polygons:
            poly_folder = folder.newfolder(name=f"{result.source} (エリア)")
            for poly in result.polygons:
                self._add_polygon(poly_folder, poly)

    def save(self, output_path: str | Path, fmt: str = "kml") -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt.lower() == "kmz":
            target = path.with_suffix(".kmz")
            self.kml.savekmz(str(target))
        else:
            target = path.with_suffix(".kml")
            self.kml.save(str(target))
        self.logger.info("KML保存: %s", target)
        return target

    # -- 内部実装 --------------------------------------------------------------

    def _add_point(self, folder: simplekml.Folder, feature: PointFeature) -> None:
        placemark = folder.newpoint(name=feature.name)
        placemark.coords = [feature.point.as_kml()]
        placemark.description = feature.description_html
        placemark.style.iconstyle.icon.href = (
            "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"
        )
        placemark.style.iconstyle.scale = 0.9

    def _add_polygon(
        self, folder: simplekml.Folder, feature: PolygonFeature
    ) -> None:
        if not feature.rings:
            return
        outer, *inners = feature.rings
        placemark = folder.newpolygon(
            name=feature.name,
            outerboundaryis=[ll.as_kml() for ll in outer],
            innerboundaryis=[[ll.as_kml() for ll in ring] for ring in inners],
        )
        placemark.description = feature.description_html
        placemark.style = self._get_or_make_style(feature.style_id)

    def _get_or_make_style(self, style_id: str) -> simplekml.Style:
        if style_id in self._styles:
            return self._styles[style_id]
        style = simplekml.Style()
        # スタイルIDから簡易にカラーを派生させる。本番では config から流したい。
        color_hex = _hash_to_kml_color(style_id)
        style.linestyle.color = color_hex
        style.linestyle.width = 1
        style.polystyle.color = color_hex
        style.polystyle.fill = 1
        style.polystyle.outline = 1
        self._styles[style_id] = style
        return style


def _hash_to_kml_color(seed: str) -> str:
    """KML は AABBGGRR (リトルエンディアン) 形式. 半透明 (AA=80) で固定."""
    h = abs(hash(seed)) & 0xFFFFFF
    r = (h >> 16) & 0xFF
    g = (h >> 8) & 0xFF
    b = h & 0xFF
    return f"80{b:02x}{g:02x}{r:02x}"
