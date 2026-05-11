"""フェッチャ共通の基底クラス・データモデル."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.utils.geo import LatLon


@dataclass
class PointFeature:
    """1点1値の地物 (地価ポイントなど).

    KMLの ``<Placemark>`` 1つに対応する。
    """

    point: LatLon
    name: str
    description_html: str
    # KMLに乗せるカスタム属性 (吹き出しテンプレで使う)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolygonFeature:
    """面情報 (ハザードマップの浸水域など)."""

    rings: list[list[LatLon]]
    name: str
    description_html: str
    style_id: str


@dataclass
class FetchResult:
    """フェッチ結果のコンテナ.

    points と polygons は併存可能 (混合データソース対応)。
    """

    source: str
    points: list[PointFeature] = field(default_factory=list)
    polygons: list[PolygonFeature] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.points and not self.polygons
