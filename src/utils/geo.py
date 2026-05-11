"""座標系・地理ユーティリティ.

Google Earth は WGS84 経緯度 (EPSG:4326) を使う。
入力データが日本測地系 (Tokyo Datum, EPSG:4301) のみだった場合は
近似変換が必要だが、現代のほとんどの公開データは既に世界測地系のため
本モジュールでは妥当性チェックと小数桁丸めのみ行う。
"""

from __future__ import annotations

from dataclasses import dataclass


# 日本国内のおおよその経緯度範囲
JP_LAT_MIN, JP_LAT_MAX = 20.0, 46.0
JP_LON_MIN, JP_LON_MAX = 122.0, 154.0


@dataclass(frozen=True)
class LatLon:
    """WGS84 緯度経度のペア."""

    lat: float
    lon: float

    def is_in_japan(self) -> bool:
        return (
            JP_LAT_MIN <= self.lat <= JP_LAT_MAX
            and JP_LON_MIN <= self.lon <= JP_LON_MAX
        )

    def as_kml(self) -> tuple[float, float]:
        """KMLは (lon, lat) の順なので注意."""
        return (round(self.lon, 6), round(self.lat, 6))
