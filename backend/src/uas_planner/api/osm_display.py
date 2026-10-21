"""Read-only bounded regional OSM display API; preparation is CLI-only."""

import sqlite3
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from uas_planner.core.osm_display import DisplayUnavailable, encode, parse_bbox, parse_categories


def router(store, dataset_path):
    api = APIRouter()

    def read(operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except DisplayUnavailable as exc:
            raise HTTPException(
                409 if exc.state in ("not_prepared", "stale") else 503,
                {"state": exc.state, "message": str(exc)},
                headers={"Retry-After": "2"},
            ) from exc
        except sqlite3.OperationalError as exc:
            raise HTTPException(503, "OSM display query failed or reached its time limit.") from exc
        except (ValueError, OSError, KeyError, TypeError, sqlite3.DatabaseError) as exc:
            raise HTTPException(
                422, "OSM display cannot be verified; inspect/prepare it explicitly."
            ) from exc

    @api.get("/api/datasets/{dataset_id}/study/osm/summary")
    def summary(dataset_id: str):
        return read(store.status, dataset_path(dataset_id))

    def selection(bbox, categories):
        try:
            return parse_bbox(bbox), parse_categories(categories)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @api.get("/api/datasets/{dataset_id}/study/osm/features")
    def features(
        dataset_id: str,
        bbox: str = Query(max_length=200),
        zoom: int = Query(default=16, ge=0, le=22),
        categories: str = Query(default="building,highway,landuse,natural", max_length=100),
        style: Literal["category"] = "category",
    ):
        bounds, names = selection(bbox, categories)
        result = read(store.features, dataset_path(dataset_id), bounds, categories=names, zoom=zoom)
        return Response(encode(result), media_type="application/geo+json")

    @api.get("/api/datasets/{dataset_id}/study/osm/overview")
    def overview(
        dataset_id: str,
        bbox: str = Query(max_length=200),
        categories: str = Query(default="building,highway,landuse,natural", max_length=100),
    ):
        bounds, names = selection(bbox, categories)
        result = read(store.overview, dataset_path(dataset_id), bounds, categories=names)
        return Response(encode(result), media_type="application/geo+json")

    return api
