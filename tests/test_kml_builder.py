"""KmlBuilder の基本動作テスト."""

from __future__ import annotations

from pathlib import Path

from src.converters.kml_builder import KmlBuilder
from src.fetchers.base import FetchResult, PointFeature, PolygonFeature
from src.utils.geo import LatLon


def test_save_kml_creates_file(tmp_path: Path) -> None:
    result = FetchResult(source="テストソース")
    result.points.append(
        PointFeature(
            point=LatLon(lat=35.681236, lon=139.767125),
            name="東京駅",
            description_html="<b>サンプル</b>",
            attributes={"price_per_sqm": 1_000_000},
        )
    )
    result.polygons.append(
        PolygonFeature(
            rings=[
                [
                    LatLon(35.0, 139.0),
                    LatLon(35.0, 140.0),
                    LatLon(36.0, 140.0),
                    LatLon(36.0, 139.0),
                    LatLon(35.0, 139.0),
                ]
            ],
            name="テスト浸水域",
            description_html="サンプルエリア",
            style_id="style-flood",
        )
    )

    builder = KmlBuilder(document_name="テスト")
    builder.add_result(result)
    out = builder.save(tmp_path / "test.kml", fmt="kml")

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "東京駅" in text
    assert "テスト浸水域" in text
    # KML は (lon, lat) の順
    assert "139.767125,35.681236" in text


def test_kmz_output(tmp_path: Path) -> None:
    result = FetchResult(source="ソース")
    result.points.append(
        PointFeature(
            point=LatLon(lat=34.7, lon=135.5),
            name="大阪",
            description_html="",
        )
    )
    builder = KmlBuilder(document_name="KMZテスト")
    builder.add_result(result)
    out = builder.save(tmp_path / "test", fmt="kmz")
    assert out.suffix == ".kmz"
    assert out.exists()
