"""デモ用サンプルデータ.

API キー未取得・ネットワーク制限環境でもパイプライン全体の動作確認が
できるよう、東京駅周辺の架空地価ポイントと簡易ハザード矩形を内蔵する。

実データではなく**動作確認用のダミー**である点に注意。
"""

from __future__ import annotations

from src.fetchers.base import FetchResult, PointFeature, PolygonFeature
from src.utils.geo import LatLon


def make_demo_chika() -> FetchResult:
    samples = [
        ("東京駅前", 35.681236, 139.767125, 8500000, "商業地"),
        ("新宿駅西口", 35.689634, 139.700566, 6200000, "商業地"),
        ("渋谷スクランブル", 35.659518, 139.700473, 5800000, "商業地"),
        ("品川駅前", 35.628471, 139.738760, 3900000, "商業地"),
        ("丸の内一丁目", 35.681000, 139.767000, 9200000, "商業地"),
        ("世田谷区桜新町", 35.628120, 139.638160, 850000, "住宅地"),
        ("杉並区荻窪", 35.704660, 139.620080, 720000, "住宅地"),
    ]
    result = FetchResult(source="MLIT 地価公示 (DEMO)")
    for name, lat, lon, price, use in samples:
        html = (
            "<table style='font-family:sans-serif;font-size:12px'>"
            f"<tr><th align='left'>住所</th><td>{name}</td></tr>"
            f"<tr><th align='left'>用途</th><td>{use}</td></tr>"
            f"<tr><th align='left'>公示価格</th><td>{price:,} 円/㎡</td></tr>"
            "<tr><th align='left'>備考</th><td>※ DEMOデータ</td></tr>"
            "</table>"
        )
        result.points.append(
            PointFeature(
                point=LatLon(lat=lat, lon=lon),
                name=f"{name} ({use})",
                description_html=html,
                attributes={"price_per_sqm": price, "use_category": use},
            )
        )
    return result


def make_demo_hazard() -> FetchResult:
    """江東区・墨田区付近の浸水想定エリアをイメージした矩形 (架空)."""
    result = FetchResult(source="MLIT ハザードマップ (DEMO)")
    flood_ring = [
        LatLon(35.690, 139.800),
        LatLon(35.690, 139.830),
        LatLon(35.665, 139.830),
        LatLon(35.665, 139.800),
        LatLon(35.690, 139.800),
    ]
    landslide_ring = [
        LatLon(35.610, 139.580),
        LatLon(35.610, 139.605),
        LatLon(35.595, 139.605),
        LatLon(35.595, 139.580),
        LatLon(35.610, 139.580),
    ]
    result.polygons.append(
        PolygonFeature(
            rings=[flood_ring],
            name="洪水浸水想定区域 (DEMO)",
            description_html="想定浸水深: 3.0m 〜 5.0m (DEMO)",
            style_id="style-flood",
        )
    )
    result.polygons.append(
        PolygonFeature(
            rings=[landslide_ring],
            name="土砂災害警戒区域 (DEMO)",
            description_html="区分: イエローゾーン (DEMO)",
            style_id="style-landslide",
        )
    )
    return result
