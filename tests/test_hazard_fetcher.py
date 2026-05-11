"""HazardFetcher の GeoJSON → PolygonFeature 変換テスト."""

from __future__ import annotations

from src.fetchers.hazard_fetcher import _geojson_to_polygons


def test_polygon_extraction() -> None:
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"想定浸水深": "3.0m"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [139.0, 35.0],
                            [139.1, 35.0],
                            [139.1, 35.1],
                            [139.0, 35.1],
                            [139.0, 35.0],
                        ]
                    ],
                },
            }
        ],
    }
    polys = _geojson_to_polygons(geojson, "洪水浸水想定区域", "style-flood")
    assert len(polys) == 1
    assert polys[0].name == "洪水浸水想定区域"
    assert "想定浸水深" in polys[0].description_html
    assert len(polys[0].rings) == 1


def test_multipolygon_extraction() -> None:
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [[[139.0, 35.0], [139.1, 35.0], [139.05, 35.1], [139.0, 35.0]]],
                        [[[140.0, 36.0], [140.1, 36.0], [140.05, 36.1], [140.0, 36.0]]],
                    ],
                },
            }
        ],
    }
    polys = _geojson_to_polygons(geojson, "土砂", "style-rock")
    assert len(polys) == 2
