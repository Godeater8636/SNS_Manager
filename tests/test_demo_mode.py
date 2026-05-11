"""--demo モードと demo データの整合性テスト."""

from __future__ import annotations

from pathlib import Path

from src.converters.kml_builder import KmlBuilder
from src.demo_data import make_demo_chika, make_demo_hazard


def test_demo_chika_has_points() -> None:
    result = make_demo_chika()
    assert not result.is_empty()
    assert len(result.points) >= 5
    for pt in result.points:
        assert pt.point.is_in_japan()


def test_demo_hazard_has_polygons() -> None:
    result = make_demo_hazard()
    assert not result.is_empty()
    assert len(result.polygons) >= 2
    for poly in result.polygons:
        assert poly.rings and len(poly.rings[0]) >= 3


def test_demo_data_serializes_to_kml(tmp_path: Path) -> None:
    builder = KmlBuilder(document_name="DEMO")
    builder.add_result(make_demo_chika())
    builder.add_result(make_demo_hazard())
    out = builder.save(tmp_path / "demo.kml", fmt="kml")
    text = out.read_text(encoding="utf-8")
    assert "東京駅前" in text
    assert "洪水浸水想定区域 (DEMO)" in text
