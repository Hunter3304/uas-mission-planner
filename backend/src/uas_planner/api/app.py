"""Read-only dataset explorer API for local demonstrations."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response

from uas_planner import __version__
from uas_planner.core.area import BoundingBox
from uas_planner.core.costs import analyze_all_layers, analyze_collection
from uas_planner.core.experiment import (
    checksum,
    inspect_location,
    load_experiment,
    population_layer,
    read_json,
    safe_file,
    zone_layer,
)
from uas_planner.storage.dataset import load_dataset

LAYER_NAMES = ("building", "highway", "landuse", "natural")
DATASET_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}\Z")
logger = logging.getLogger(__name__)


def create_app(data_dir: Path | None = None) -> FastAPI:
    default = Path(__file__).resolve().parents[4] / "data"
    root = Path(data_dir or os.environ.get("UAS_DATA_DIR", default)).resolve()
    api = FastAPI(title="UAS Mission Planner", version=__version__)

    def dataset_path(dataset_id: str) -> Path:
        if not DATASET_ID.fullmatch(dataset_id):
            raise HTTPException(404, "Dataset not found.")
        path = (root / dataset_id).resolve()
        if not path.is_relative_to(root) or path == root or not path.is_dir():
            raise HTTPException(404, "Dataset not found.")
        for filename in ("features.gpkg", "metadata.json"):
            if not (path / filename).resolve().is_relative_to(path):
                raise HTTPException(404, "Dataset not found.")
        return path

    def verified(dataset_id: str, *, compact: bool = False):
        path = dataset_path(dataset_id)
        if (path / "osm").is_dir():
            osm = (path / "osm").resolve()
            if not osm.is_relative_to(path):
                raise HTTPException(404, "Dataset not found.")
            path = osm
            if any(
                not (path / name).resolve().is_relative_to(path)
                for name in ("features.gpkg", "metadata.json")
            ):
                raise HTTPException(404, "Dataset not found.")
        try:
            frame, metadata = load_dataset(path, compact=compact)
            BoundingBox(**metadata["query_bounds"])
            return path, frame, metadata
        except Exception as exc:
            logger.warning("Cannot verify dataset %s: %s", dataset_id, type(exc).__name__)
            raise HTTPException(
                422, "Dataset cannot be verified. Check its files and metadata."
            ) from exc

    def summary(dataset_id, frame, metadata):
        return {
            "id": dataset_id,
            "synthetic": metadata.get("synthetic", False),
            "source": metadata.get("source", "OpenStreetMap via OSMnx/Overpass"),
            "feature_count": len(frame),
            "crs": frame.crs.to_string(),
            "geometry_counts": {
                key: int(value) for key, value in frame.geom_type.value_counts().items()
            },
            "layer_counts": {
                key: int(frame[key].notna().sum()) if key in frame else 0 for key in LAYER_NAMES
            },
            "query_bounds": metadata["query_bounds"],
            "feature_bounds": frame.total_bounds.tolist() if len(frame) else None,
            "query_area_km2": metadata.get("query_area_km2"),
            "saved_at_utc": metadata.get("saved_at_utc"),
            "acquisition_finished_at_utc": metadata.get("acquisition_finished_at_utc"),
            "invalid_geometry_count": metadata.get("invalid_geometry_count", 0),
            "sha256": metadata["sha256"],
            "verified": True,
            "has_experiment": (dataset_path(dataset_id) / "experiment.json").is_file(),
        }

    def external(dataset_id):
        path = dataset_path(dataset_id)
        if not (path / "experiment.json").is_file():
            raise HTTPException(404, "No external experiment saved for this dataset.")
        try:
            manifest = load_experiment(path)
            osm_path = path / "osm" if (path / "osm").is_dir() else path
            osm_metadata = read_json(
                safe_file(path, str((osm_path / "metadata.json").relative_to(path)))
            )
            osm_file = safe_file(path, str((osm_path / "features.gpkg").relative_to(path)))
            if checksum(osm_file) != osm_metadata["sha256"]:
                raise ValueError("OSM snapshot checksum mismatch.")
            if manifest["config"]["bounds"] != osm_metadata["query_bounds"]:
                raise ValueError("OSM and external experiment bounds do not match.")
            return path, manifest
        except Exception as exc:
            logger.warning("Cannot verify experiment %s: %s", dataset_id, type(exc).__name__)
            raise HTTPException(
                422, "External experiment cannot be verified. Check payloads and bounds."
            ) from exc

    @api.get("/api/datasets/{dataset_id}/experiment")
    def experiment(dataset_id: str):
        _, manifest = external(dataset_id)
        return manifest

    @api.get("/api/datasets/{dataset_id}/experiment/layers/{layer}")
    def experiment_layer(dataset_id: str, layer: Literal["population", "zones"]):
        path, manifest = external(dataset_id)
        try:
            return (
                population_layer(path, manifest)
                if layer == "population"
                else zone_layer(path, manifest)
            )
        except (ValueError, KeyError, OSError) as exc:
            raise HTTPException(422, "Cannot inspect external layer.") from exc

    @api.get("/api/datasets/{dataset_id}/experiment/inspect")
    def experiment_point(dataset_id: str, longitude: float, latitude: float):
        path, manifest = external(dataset_id)
        try:
            return inspect_location(path, manifest, longitude, latitude)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @api.get("/api/health")
    def health():
        return {"status": "ok"}

    @api.get("/api/datasets")
    def datasets():
        items = []
        if root.is_dir():
            for entry in sorted(root.iterdir(), key=lambda value: value.name.lower()):
                if not entry.is_dir() or not DATASET_ID.fullmatch(entry.name):
                    continue
                try:
                    _, frame, metadata = verified(entry.name, compact=True)
                    items.append(summary(entry.name, frame, metadata))
                except HTTPException as exc:
                    if exc.status_code == 422:
                        items.append({"id": entry.name, "verified": False, "error": exc.detail})
        return {"datasets": items}

    @api.get("/api/datasets/{dataset_id}")
    def details(dataset_id: str):
        _, frame, metadata = verified(dataset_id, compact=True)
        return summary(dataset_id, frame, metadata)

    @api.get("/api/datasets/{dataset_id}/features")
    def features(dataset_id: str, analysis: Literal["building-costs", "tag-costs"] | None = None):
        _, frame, metadata = verified(dataset_id, compact=True)
        # Large experiment snapshots contain many sparse OSM tag columns. Omit
        # absent tags only in their display response; source downloads stay intact.
        na = "drop" if (dataset_path(dataset_id) / "experiment.json").is_file() else "null"
        collection = json.loads(frame.to_json(drop_id=True, na=na))
        for feature, tags in zip(collection["features"], frame.attrs["source_tags"], strict=True):
            if na == "null":
                feature["properties"].update(
                    {key: tags.get(key) for key in metadata["tag_columns"]}
                )
            else:
                feature["properties"].update(tags)
        if analysis == "tag-costs":
            return analyze_all_layers(collection)
        return analyze_collection(collection) if analysis else collection

    @api.get("/api/datasets/{dataset_id}/download/{format_name}")
    def download(dataset_id: str, format_name: Literal["geojson", "gpkg", "metadata"]):
        path, frame, _ = verified(dataset_id)
        if format_name == "geojson":
            return Response(
                frame.to_json(drop_id=True, na="null"),
                media_type="application/geo+json",
                headers={"Content-Disposition": f'attachment; filename="{dataset_id}.geojson"'},
            )
        filename, media = (
            ("features.gpkg", "application/geopackage+sqlite3")
            if format_name == "gpkg"
            else ("metadata.json", "application/json")
        )
        return FileResponse(path / filename, media_type=media, filename=f"{dataset_id}-{filename}")

    return api


app = create_app()
