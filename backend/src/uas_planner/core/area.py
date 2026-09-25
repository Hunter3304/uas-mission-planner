"""Explicit geographic bounds for small-area prototype queries."""

from dataclasses import dataclass
from math import isfinite

from pyproj import Geod

MAX_AREA_KM2 = 25.0


@dataclass(frozen=True)
class BoundingBox:
    """EPSG:4326 bounds; dateline crossing and polar queries are out of scope."""

    west: float
    south: float
    east: float
    north: float

    def __post_init__(self):
        if not all(isfinite(v) for v in self.as_tuple()):
            raise ValueError("Bounds must be finite numbers.")
        if not -180 <= self.west < self.east <= 180:
            raise ValueError("Require -180 <= west < east <= 180; no dateline crossing.")
        if not -85 <= self.south < self.north <= 85:
            raise ValueError("Require -85 <= south < north <= 85.")
        if self.east - self.west > 1 or self.north - self.south > 1:
            raise ValueError("Each bounding-box span must be at most one degree.")
        if self.area_km2 > MAX_AREA_KM2:
            raise ValueError(f"Prototype query area must not exceed {MAX_AREA_KM2:g} km2.")

    def as_tuple(self):
        """OSMnx order: left, bottom, right, top."""
        return (self.west, self.south, self.east, self.north)

    @property
    def area_km2(self):
        area, _ = Geod(ellps="WGS84").polygon_area_perimeter(
            [self.west, self.east, self.east, self.west],
            [self.south, self.south, self.north, self.north],
        )
        return abs(area) / 1_000_000
