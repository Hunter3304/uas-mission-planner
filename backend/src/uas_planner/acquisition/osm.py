"""OSMnx adapter. Preserve complete source geometries intersecting the query area."""

from pathlib import Path
from threading import Lock

import geopandas as gpd
import osmnx as ox
from osmnx._errors import InsufficientResponseError
from requests.exceptions import RequestException

from uas_planner.core.area import BoundingBox

TAGS = {"building": True, "highway": True, "landuse": True, "natural": True}
_SETTINGS_LOCK = Lock()


class AcquisitionError(RuntimeError):
    """The external data source could not provide a usable response."""


def acquire(area: BoundingBox, cache_dir: Path) -> gpd.GeoDataFrame:
    """Fetch tagged features with cache enabled and bounded HTTP request timeouts.

    OSMnx owns service backoff; this is not a total wall-clock deadline. The lock
    protects its process-global settings. Empty matches are a valid result;
    service and malformed-response errors remain failures.
    """
    with _SETTINGS_LOCK:
        original = (ox.settings.cache_folder, ox.settings.use_cache, ox.settings.requests_timeout)
        try:
            ox.settings.cache_folder = str(cache_dir)
            ox.settings.use_cache = True
            ox.settings.requests_timeout = 60
            try:
                frame = ox.features_from_bbox(area.as_tuple(), tags=TAGS.copy())
            except InsufficientResponseError as exc:
                if "No matching features" not in str(exc):
                    raise AcquisitionError(f"OSM response could not be parsed: {exc}") from exc
                return gpd.GeoDataFrame(
                    {"element_type": [], "osm_id": []}, geometry=[], crs="EPSG:4326"
                )
            except (RequestException, ValueError) as exc:
                raise AcquisitionError(f"OSM acquisition failed: {exc}") from exc
        finally:
            ox.settings.cache_folder, ox.settings.use_cache, ox.settings.requests_timeout = original
    frame = frame.reset_index().rename(columns={"osmid": "osm_id"})
    if not {"element_type", "osm_id"}.issubset(frame.columns):
        raise AcquisitionError("OSM response lacks element identity.")
    return frame.to_crs("EPSG:4326")
