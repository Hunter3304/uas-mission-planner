"""Bounded, offline regional OSM display access; never used by the route planner.

Preparation is an explicit CLI operation. HTTP reads can verify an existing
snapshot once per process, but cannot start a display build. Source and derived
files stay immutable while queries use short-lived read-only SQLite connections.
"""

import hashlib
import json
import math
import os
import re
import sqlite3
import struct
import threading
import uuid
from collections import Counter, OrderedDict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic

from shapely import from_wkb, get_num_coordinates, to_wkb
from shapely.geometry import box, mapping

from uas_planner.core.area import dataset_area
from uas_planner.core.costs import RULES, analyze_feature, classify_layer
from uas_planner.storage.dataset import _validate_metadata, checksum

CATEGORIES = ("building", "highway", "landuse", "natural")
SCHEMA = 2
GRID_SIDE = 40
MAX_FEATURES = 5000
MAX_BYTES = 5 * 1024 * 1024
MAX_COORDINATES = 100_000
MAX_CANDIDATES = 10_000
MAX_SOURCE_GEOMETRY_BYTES = 16 * 1024 * 1024
MAX_TAG_BYTES = 1024 * 1024
MAX_DETAIL_TAGS = 512
MAX_DETAIL_TOKENS = 4096
SCORE_FIELDS = ("cost", "status", "has_default", "obstruction")
QUERY_SECONDS = 2.0
ELEMENT = re.compile(r"(?:node|way|relation)\Z")


class DisplayUnavailable(ValueError):
    """An explicit preparation, verification or concurrency state."""

    def __init__(self, state, message):
        super().__init__(message)
        self.state = state


class DisplayNotFound(LookupError):
    """A valid OSM identity is absent from this verified snapshot."""


class DisplayLimit(ValueError):
    """An individual object's details exceed a bounded response/analysis budget."""


def parse_identity(element_type, osm_id):
    value = str(osm_id)
    if (
        not ELEMENT.fullmatch(element_type or "")
        or not re.fullmatch(r"0|[1-9][0-9]{0,18}", value)
        or int(value) > 2**63 - 1
    ):
        raise ValueError("A canonical node/way/relation and nonnegative int64 OSM ID are required.")
    return element_type, int(value)


def validate_style(style, cost_category, names):
    if style not in ("category", "cost"):
        raise ValueError("style must be category or cost.")
    if style == "cost" and cost_category not in names:
        raise ValueError("Cost style requires cost_category among the selected categories.")
    if style == "category" and cost_category is not None:
        raise ValueError("cost_category is only valid with style=cost.")


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def token(path):
    stat = path.stat()
    # On Windows st_ctime is creation time, not metadata-change time. Include
    # NTFS ChangeTime so a same-size edit with restored mtime still invalidates
    # the in-process checksum verification. These tokens detect changes; only
    # the subsequent complete checksums establish integrity.
    change_time = windows_change_time(path) if os.name == "nt" else stat.st_ctime_ns
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, change_time)


def windows_change_time(path):
    import ctypes
    from ctypes import wintypes

    class BasicInfo(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_int64) for name in ("creation", "access", "write", "change")
        ] + [("attributes", wintypes.DWORD)]

    kernel = ctypes.windll.kernel32
    create = kernel.CreateFileW
    create.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create.restype = wintypes.HANDLE
    info = kernel.GetFileInformationByHandleEx
    info.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    close = kernel.CloseHandle
    close.argtypes = (wintypes.HANDLE,)
    handle = create(str(path.resolve()), 0, 7, None, 3, 0, None)
    if handle == wintypes.HANDLE(-1).value:
        raise OSError("Cannot inspect source/cache change time.")
    try:
        result = BasicInfo()
        if not info(handle, 0, ctypes.byref(result), ctypes.sizeof(result)):
            raise OSError("Cannot inspect source/cache change time.")
        return result.change
    finally:
        close(handle)


def read_object(path, limit=4 * 1024 * 1024):
    if path.stat().st_size > limit:
        raise ValueError("Display metadata exceeds its size limit.")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Display metadata must be a JSON object.")
    return value


def contained(parent, child):
    path = parent / child
    if path.is_symlink() or not path.resolve().is_relative_to(parent.resolve()):
        raise ValueError("Display path leaves its dataset/cache directory.")
    return path


def context(directory):
    directory = Path(directory).resolve()
    study_path = contained(directory, "study.json")
    study = read_object(study_path)
    if study.get("schema_version") != 1 or study.get("kind") != "regional-source-study":
        raise ValueError("A version 1 regional study is required.")
    osm = contained(directory, "osm") if (directory / "osm").is_dir() else directory
    metadata_path = contained(osm, "metadata.json")
    source = contained(osm, "features.gpkg")
    metadata = read_object(metadata_path)
    _validate_metadata(metadata)
    bounds = dataset_area(metadata).as_tuple()
    if (
        not isinstance(study.get("config"), dict)
        or study["config"].get("bounds") != metadata["query_bounds"]
    ):
        raise ValueError("Study and OSM coverage do not match.")
    identity = {
        "schema_version": SCHEMA,
        "source_sha256": metadata["sha256"],
        "metadata_sha256": digest(metadata),
        "study_sha256": digest(study),
        "rule_sha256": digest(RULES),
        "rule_version": RULES["version"],
        "grid_side": GRID_SIDE,
        "simplification_tolerance_m": 0,
    }
    return {
        "directory": directory,
        "source": source,
        "metadata_path": metadata_path,
        "study_path": study_path,
        "metadata": metadata,
        "identity": identity,
        "key": digest(identity),
        "bounds": bounds,
        "source_token": token(source),
    }


def source_unchanged(ctx):
    current = context(ctx["directory"])
    if current["identity"] != ctx["identity"] or current["source_token"] != ctx["source_token"]:
        raise DisplayUnavailable(
            "stale", "Source changed; explicitly prepare/reverify OSM display."
        )


@contextmanager
def read_database(path):
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        yield connection
    finally:
        connection.close()


def gpkg_wkb(blob):
    """Decode the standard GeoPackageBinary header; no GDAL extension is loaded."""
    if not blob or len(blob) < 8 or blob[:3] != b"GP\x00":
        raise ValueError("Unsupported GeoPackage geometry header.")
    flags = blob[3]
    envelope = (flags >> 1) & 7
    if envelope > 4 or flags & 0b11100000:
        raise ValueError("Unsupported extended/reserved GeoPackage geometry.")
    order = "<" if flags & 1 else ">"
    if struct.unpack(order + "i", blob[4:8])[0] != 4326:
        raise ValueError("Geometry SRS must be EPSG:4326.")
    offset = 8 + (0, 32, 48, 48, 64)[envelope]
    return blob[offset:]


def validate_source_db(connection, metadata):
    geometry = connection.execute("SELECT * FROM gpkg_geometry_columns").fetchall()
    if len(geometry) != 1 or geometry[0][:2] != ("features", "geom") or geometry[0][3] != 4326:
        raise ValueError("Unsupported source geometry layer/CRS.")
    if (
        connection.execute("SELECT count(*) FROM features").fetchone()[0]
        != metadata["feature_count"]
    ):
        raise ValueError("Source feature count does not match metadata.")
    indexed = connection.execute("SELECT count(*) FROM rtree_features_geom").fetchone()[0]
    return {"source_index_entries": indexed, "source_spatial_index": "rtree_features_geom"}


def parse_bbox(value):
    try:
        values = (
            tuple(float(v) for v in value.split(",")) if isinstance(value, str) else tuple(value)
        )
        if len(values) != 4 or not all(math.isfinite(v) for v in values):
            raise ValueError
        west, south, east, north = values
        if not (-180 <= west < east <= 180 and -85 <= south < north <= 85):
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("bbox requires finite west,south,east,north WGS84 bounds.") from None
    return values


def parse_categories(value):
    names = value.split(",") if isinstance(value, str) else list(value)
    if not names or len(names) != len(set(names)) or any(n not in CATEGORIES for n in names):
        raise ValueError("categories must be distinct building,highway,landuse,natural names.")
    return tuple(n for n in CATEGORIES if n in names)


def intersect_bounds(requested, coverage):
    west, south = max(requested[0], coverage[0]), max(requested[1], coverage[1])
    east, north = min(requested[2], coverage[2]), min(requested[3], coverage[3])
    return (west, south, east, north) if west < east and south < north else None


class DisplayStore:
    """At most eight verified snapshots and two simultaneous read queries per app."""

    def __init__(self, cache_root):
        self.cache_root = Path(cache_root).absolute()
        self._verified = OrderedDict()
        self._memo_lock = threading.Lock()
        self._verify_lock = threading.Lock()
        self._queries = threading.BoundedSemaphore(2)

    def _folder(self, ctx):
        if self.cache_root.is_symlink():
            raise ValueError("Display cache root cannot be a symlink.")
        return contained(self.cache_root, ctx["key"])

    def prepare(self, directory, *, refresh=False, progress=None):
        """Explicit, batch-committed build. Completed manifests are published last."""
        ctx = context(directory)
        folder = self._folder(ctx)
        folder.mkdir(parents=True, exist_ok=True)
        lock = contained(folder, "prepare.lock")
        try:
            lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise DisplayUnavailable("preparing", "OSM preparation is already locked.") from None
        try:
            os.close(lock_fd)
            if not refresh and (folder / "manifest.json").is_file():
                return self.summary(directory)
            started = monotonic()
            if checksum(ctx["source"]) != ctx["metadata"]["sha256"]:
                raise ValueError("OSM source checksum mismatch.")
            generation = uuid.uuid4().hex
            db_path = contained(folder, f"display-{generation}.sqlite")
            result = self._build(ctx, db_path, progress)
            source_unchanged(ctx)
            manifest = {
                **result,
                "identity": ctx["identity"],
                "database": db_path.name,
                "database_sha256": checksum(db_path),
                "prepared_at": datetime.now(timezone.utc).isoformat(),
                "preparation_s": round(monotonic() - started, 3),
            }
            pending = contained(folder, f"manifest-{generation}.json")
            pending.write_text(encode(manifest), encoding="utf-8")
            pending.replace(contained(folder, "manifest.json"))
            with self._memo_lock:
                self._verified.pop(str(ctx["directory"]), None)
            return self.summary(directory)
        except sqlite3.Error as exc:
            raise ValueError(
                "Cannot prepare OSM display database; inspect retained source/cache files."
            ) from exc
        finally:
            lock.unlink(missing_ok=True)

    def _build(self, ctx, db_path, progress):
        counts, geometry_counts, reasons = Counter(), Counter(), Counter()
        samples, seen, drawable = [], 0, 0
        feature_bounds = None
        coverage = box(*ctx["bounds"])
        declared_tags = set(ctx["metadata"]["tag_columns"])
        west, south, east, north = ctx["bounds"]
        with read_database(ctx["source"]) as source, sqlite3.connect(db_path) as output:
            index_info = validate_source_db(source, ctx["metadata"])
            output.executescript(
                "CREATE TABLE objects (id INTEGER PRIMARY KEY, element_type TEXT NOT NULL, "
                "osm_id INTEGER NOT NULL, mask INTEGER NOT NULL, geometry BLOB, coordinates INTEGER, "
                "geometry_bytes INTEGER, diagnostic TEXT, UNIQUE(element_type,osm_id));"
                "CREATE TABLE costs (object_id INTEGER, category TEXT, cost INTEGER, status TEXT, "
                "has_default INTEGER, obstruction INTEGER, PRIMARY KEY(object_id,category)) WITHOUT ROWID;"
                "CREATE VIRTUAL TABLE spatial USING rtree(id,minx,maxx,miny,maxy);"
                "CREATE TABLE overview (cell INTEGER PRIMARY KEY, total INTEGER NOT NULL, "
                "building INTEGER, highway INTEGER, landuse INTEGER, natural INTEGER);"
            )
            cells = {}
            rows = source.execute(
                "SELECT fid,element_type,osm_id,length(geom),length(CAST(tags_json AS BLOB)),"
                "CASE WHEN length(geom)<=? THEN geom END,"
                "CASE WHEN length(CAST(tags_json AS BLOB))<=? THEN tags_json END FROM features",
                (MAX_SOURCE_GEOMETRY_BYTES, MAX_TAG_BYTES),
            )
            for fid, element_type, osm_id, geometry_size, tag_size, blob, raw_tags in rows:
                if (
                    not ELEMENT.fullmatch(element_type or "")
                    or type(osm_id) is not int
                    or osm_id < 0
                ):
                    raise ValueError("Source contains invalid OSM identity.")
                if raw_tags is None:
                    raise ValueError("Source tags exceed the per-object preparation limit.")
                tags = json.loads(raw_tags)
                if not isinstance(tags, dict) or not set(tags).issubset(declared_tags):
                    raise ValueError("Source tags do not match the declared schema.")
                mask = sum(
                    1 << i for i, name in enumerate(CATEGORIES) if tags.get(name) is not None
                )
                for i, name in enumerate(CATEGORIES):
                    counts[name] += bool(mask & (1 << i))
                diagnostic, wkb, coordinates, extent = None, None, 0, None
                if geometry_size is None or geometry_size > MAX_SOURCE_GEOMETRY_BYTES:
                    diagnostic = "missing_or_oversized_geometry"
                else:
                    try:
                        geometry = from_wkb(gpkg_wkb(blob))
                        geometry_counts[geometry.geom_type] += 1
                        extent = geometry.bounds
                        if (
                            geometry.is_empty
                            or len(extent) != 4
                            or not all(map(math.isfinite, extent))
                        ):
                            diagnostic = "empty_or_nonfinite_geometry"
                        elif not geometry.is_valid:
                            diagnostic = "invalid_source_geometry"
                        elif geometry.geom_type not in (
                            "Point",
                            "MultiPoint",
                            "LineString",
                            "MultiLineString",
                            "Polygon",
                            "MultiPolygon",
                        ):
                            diagnostic = "unsupported_geometry_type"
                        elif not geometry.intersects(coverage):
                            diagnostic = "outside_study_geometry"
                        else:
                            coordinates = int(get_num_coordinates(geometry))
                            wkb = to_wkb(geometry)
                            point = geometry.intersection(coverage).representative_point()
                            col = min(
                                GRID_SIDE - 1,
                                max(0, int((point.x - west) / (east - west) * GRID_SIDE)),
                            )
                            row = min(
                                GRID_SIDE - 1,
                                max(0, int((point.y - south) / (north - south) * GRID_SIDE)),
                            )
                            cell = cells.setdefault(row * GRID_SIDE + col, [0] * 5)
                            cell[0] += 1
                            for i in range(4):
                                cell[i + 1] += bool(mask & (1 << i))
                    except (ValueError, TypeError, struct.error) as exc:
                        raise ValueError("Cannot decode source geometry.") from exc
                if extent and len(extent) == 4 and all(map(math.isfinite, extent)):
                    if feature_bounds is None:
                        feature_bounds = list(extent)
                    else:
                        feature_bounds = [
                            min(feature_bounds[0], extent[0]),
                            min(feature_bounds[1], extent[1]),
                            max(feature_bounds[2], extent[2]),
                            max(feature_bounds[3], extent[3]),
                        ]
                output.execute(
                    "INSERT INTO objects VALUES (?,?,?,?,?,?,?,?)",
                    (
                        fid,
                        element_type,
                        osm_id,
                        mask,
                        wkb,
                        coordinates,
                        len(wkb) if wkb else 0,
                        diagnostic,
                    ),
                )
                # Only primary-category scores are prepared. Explanations and original
                # sparse tags are read for a single selected object, never on pan.
                for name in CATEGORIES:
                    score = classify_layer(tags, name)
                    if score is not None:
                        output.execute(
                            "INSERT INTO costs VALUES (?,?,?,?,?,?)",
                            (fid, name, *(score[field] for field in SCORE_FIELDS)),
                        )
                # Explicit columns avoid accidental dependence on the source schema.
                if wkb is not None:
                    output.execute(
                        "INSERT INTO spatial VALUES (?,?,?,?,?)",
                        (fid, extent[0], extent[2], extent[1], extent[3]),
                    )
                    drawable += 1
                if diagnostic:
                    reasons[diagnostic] += 1
                    if len(samples) < 30:
                        samples.append(
                            {"element_type": element_type, "osm_id": osm_id, "reason": diagnostic}
                        )
                seen += 1
                if seen % 1000 == 0:
                    output.commit()
                    if progress and seen % 10_000 == 0:
                        progress(
                            {
                                "state": "preparing",
                                "processed": seen,
                                "total": ctx["metadata"]["feature_count"],
                            }
                        )
            output.executemany(
                "INSERT INTO overview VALUES (?,?,?,?,?,?)",
                ((key, *values) for key, values in sorted(cells.items())),
            )
            output.commit()
            if seen != ctx["metadata"]["feature_count"]:
                raise ValueError("Prepared count does not match source metadata.")
        return {
            "feature_count": seen,
            "drawable_count": drawable,
            "layer_counts": {name: counts[name] for name in CATEGORIES},
            "geometry_counts": dict(geometry_counts),
            "feature_bounds": feature_bounds,
            "diagnostics": {
                "counts": dict(reasons),
                "samples": samples,
                "samples_complete": sum(reasons.values()) <= len(samples),
            },
            "overview_assignment": "One representative point of each valid object's intersection with the study; categories may overlap.",
            "category_precedence": list(CATEGORIES),
            **index_info,
        }

    def _snapshot(self, directory):
        ctx = context(directory)
        folder = self._folder(ctx)
        manifest_path = contained(folder, "manifest.json")
        if not manifest_path.is_file():
            state = "preparing" if (folder / "prepare.lock").exists() else "not_prepared"
            raise DisplayUnavailable(
                state, "Run study-osm-prepare explicitly before reading OSM display."
            )
        manifest = read_object(manifest_path)
        name = manifest.get("database", "")
        if not re.fullmatch(r"display-[a-f0-9]{32}\.sqlite", name):
            raise ValueError("Invalid display database name.")
        database = contained(folder, name)
        fingerprint = (ctx["key"], ctx["source_token"], token(manifest_path), token(database))
        cache_key = str(ctx["directory"])
        with self._memo_lock:
            cached = self._verified.get(cache_key)
            if cached and cached[0] == fingerprint:
                self._verified.move_to_end(cache_key)
                return ctx, manifest, database, fingerprint
        if not self._verify_lock.acquire(blocking=False):
            raise DisplayUnavailable(
                "verifying", "Another display snapshot is being verified; retry shortly."
            )
        try:
            if manifest.get("identity") != ctx["identity"]:
                raise ValueError("Display identity mismatch; prepare again.")
            if checksum(ctx["source"]) != ctx["metadata"]["sha256"]:
                raise ValueError(
                    "OSM source checksum mismatch; prepare again after restoring sources."
                )
            if checksum(database) != manifest.get("database_sha256"):
                raise ValueError(
                    "Display cache checksum mismatch; explicitly rebuild with --refresh."
                )
            with read_database(database) as connection:
                if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("Display database integrity failure.")
                count = connection.execute("SELECT count(*) FROM objects").fetchone()[0]
                if count != ctx["metadata"]["feature_count"] or count != manifest.get(
                    "feature_count"
                ):
                    raise ValueError("Display cache count mismatch.")
            source_unchanged(ctx)
            if fingerprint[2:] != (token(manifest_path), token(database)):
                raise ValueError("Display cache changed during verification.")
            with self._memo_lock:
                self._verified[cache_key] = (fingerprint,)
                self._verified.move_to_end(cache_key)
                while len(self._verified) > 8:
                    self._verified.popitem(last=False)
            return ctx, manifest, database, fingerprint
        finally:
            self._verify_lock.release()

    def summary(self, directory):
        ctx, manifest, _, _ = self._snapshot(directory)
        source_unchanged(ctx)
        return {
            "state": "ready",
            "verified": True,
            "identity": ctx["identity"],
            "coverage_bounds": ctx["bounds"],
            "limits": self.limits(),
            **manifest,
        }

    def status(self, directory):
        try:
            return self.summary(directory)
        except DisplayUnavailable as exc:
            return {"state": exc.state, "verified": False, "message": str(exc)}
        except sqlite3.DatabaseError as exc:
            raise ValueError("Display database verification failed; explicitly rebuild.") from exc

    @staticmethod
    def limits():
        return {
            "features": MAX_FEATURES,
            "response_bytes": MAX_BYTES,
            "coordinates": MAX_COORDINATES,
            "candidates": MAX_CANDIDATES,
            "query_seconds": QUERY_SECONDS,
            "overview_cells": GRID_SIDE**2,
            "detail_tags": MAX_DETAIL_TAGS,
            "detail_tokens": MAX_DETAIL_TOKENS,
        }

    def catalog(self, directory):
        ctx = context(directory)
        status = self.status(directory)
        metadata = ctx["metadata"]
        return {
            "id": ctx["directory"].name,
            "synthetic": metadata.get("synthetic", False),
            "source": metadata.get("source"),
            "feature_count": metadata["feature_count"],
            "crs": metadata["crs"],
            "geometry_counts": status.get("geometry_counts", {}),
            "layer_counts": status.get("layer_counts", {}),
            "query_bounds": metadata["query_bounds"],
            "feature_bounds": status.get("feature_bounds"),
            "query_area_km2": metadata.get("query_area_km2"),
            "saved_at_utc": metadata.get("saved_at_utc"),
            "acquisition_finished_at_utc": metadata.get("acquisition_finished_at_utc"),
            "invalid_geometry_count": metadata.get("invalid_geometry_count", 0),
            "sha256": metadata["sha256"],
            "verified": status["verified"],
            "has_study": True,
            "has_experiment": (ctx["directory"] / "experiment.json").is_file(),
            "display_state": status["state"],
            "verification": "Prepared OSM source verified"
            if status["verified"]
            else "Metadata only; display preparation required",
        }

    @contextmanager
    def _query(self, directory):
        if not self._queries.acquire(blocking=False):
            raise DisplayUnavailable("busy", "Display query capacity reached; retry shortly.")
        try:
            ctx, manifest, database, fingerprint = self._snapshot(directory)
            with read_database(database) as connection:
                deadline = monotonic() + QUERY_SECONDS
                connection.set_progress_handler(lambda: int(monotonic() >= deadline), 1000)
                yield ctx, manifest, connection, deadline
            source_unchanged(ctx)
            folder = self._folder(ctx)
            if fingerprint[2:] != (token(folder / "manifest.json"), token(database)):
                raise DisplayUnavailable(
                    "stale", "Display changed during query; retry with current snapshot."
                )
        finally:
            self._queries.release()

    def features(
        self,
        directory,
        bbox,
        *,
        categories=CATEGORIES,
        zoom=16,
        style="category",
        cost_category=None,
    ):
        requested = parse_bbox(bbox)
        names = parse_categories(categories)
        validate_style(style, cost_category, names)
        if type(zoom) is not int or not 0 <= zoom <= 22:
            raise ValueError("zoom must be an integer from 0 to 22.")
        with self._query(directory) as (ctx, manifest, connection, deadline):
            effective = intersect_bounds(requested, ctx["bounds"])
            result = self._collection(ctx, requested, effective, "detail")
            result["display"].update(
                categories=names,
                zoom=zoom,
                simplification_tolerance_m=0,
                geometry_policy="Original complete geometry; selection uses effective viewport intersection.",
                style=style,
                cost_category=cost_category,
            )
            if effective is None:
                return result
            mask = sum(1 << CATEGORIES.index(n) for n in names)
            shape = box(*effective)
            coords, used, examined, reason = 0, 8192, 0, None
            cost_join = (
                "JOIN costs c ON c.object_id=o.id AND c.category=? " if style == "cost" else ""
            )
            rows = connection.execute(
                "SELECT o.id,o.element_type,o.osm_id,o.mask,o.coordinates,o.geometry_bytes "
                "FROM spatial s JOIN objects o ON o.id=s.id "
                + cost_join
                + "WHERE s.maxx>=? AND s.minx<=? AND s.maxy>=? AND s.miny<=? "
                "AND (o.mask & ?)!=0 LIMIT ?",
                (
                    *((cost_category,) if style == "cost" else ()),
                    effective[0],
                    effective[2],
                    effective[1],
                    effective[3],
                    mask,
                    MAX_CANDIDATES + 1,
                ),
            )
            for fid, element, osm_id, membership, count, size in rows:
                examined += 1
                if examined > MAX_CANDIDATES or monotonic() >= deadline:
                    reason = "candidate_or_time_limit"
                    break
                if count > MAX_COORDINATES - coords or size > MAX_BYTES - used:
                    reason = "geometry_budget"
                    break
                blob = connection.execute(
                    "SELECT geometry FROM objects WHERE id=?", (fid,)
                ).fetchone()[0]
                geometry = from_wkb(blob)
                if not geometry.intersects(shape):
                    continue
                if len(result["features"]) >= MAX_FEATURES:
                    reason = "feature_limit"
                    break
                feature = {
                    "type": "Feature",
                    "id": f"{element}/{osm_id}",
                    "geometry": mapping(geometry),
                    "properties": {
                        "element_type": element,
                        "osm_id": osm_id,
                        "categories": [
                            n for i, n in enumerate(CATEGORIES) if membership & (1 << i)
                        ],
                    },
                }
                if style == "cost":
                    score = connection.execute(
                        "SELECT cost,status,has_default,obstruction FROM costs "
                        "WHERE object_id=? AND category=?",
                        (fid, cost_category),
                    ).fetchone()
                    feature["cost_analysis"] = dict(zip(SCORE_FIELDS, score, strict=True))
                    for field in ("has_default", "obstruction"):
                        feature["cost_analysis"][field] = bool(feature["cost_analysis"][field])
                feature_bytes = len(encode(feature).encode()) + 1
                if used + feature_bytes > MAX_BYTES:
                    reason = "response_byte_limit"
                    break
                used += feature_bytes
                coords += count
                result["features"].append(feature)
            result["display"].update(
                returned_count=len(result["features"]),
                coordinates=coords,
                examined_candidates=min(examined, MAX_CANDIDATES),
                complete=reason is None,
                limit_reason=reason,
                overview_recommended=reason is not None,
            )
            result["display"]["diagnostic_counts"] = manifest["diagnostics"]["counts"]
            return result

    def detail(self, directory, element_type, osm_id):
        element, osm_id = parse_identity(element_type, osm_id)
        with self._query(directory) as (ctx, _, connection, deadline):
            row = connection.execute(
                "SELECT id,mask,diagnostic FROM objects WHERE element_type=? AND osm_id=?",
                (element, osm_id),
            ).fetchone()
            if row is None:
                raise DisplayNotFound("OSM object is absent from this saved study.")
            fid, mask, diagnostic = row
            # The source fid is retained at preparation. Read by primary key; never
            # reconstruct a GeoDataFrame or scan all source tags for a click.
            with read_database(ctx["source"]) as source:
                source.set_progress_handler(lambda: int(monotonic() >= deadline), 1000)
                record = source.execute(
                    "SELECT element_type,osm_id,length(geom),"
                    "CASE WHEN length(geom)<=? THEN geom END,"
                    "CASE WHEN length(CAST(tags_json AS BLOB))<=? THEN tags_json END "
                    "FROM features WHERE fid=?",
                    (MAX_SOURCE_GEOMETRY_BYTES, MAX_TAG_BYTES, fid),
                ).fetchone()
            if record is None or record[:2] != (element, osm_id):
                raise ValueError("Source/cache object identity mismatch.")
            _, _, size, blob, raw_tags = record
            if raw_tags is None:
                raise DisplayLimit("Original tags exceed the detail budget; use source export.")
            tags = json.loads(raw_tags)
            # Full explanations repeat original values for each independent layer.
            # Check their work budget before allocating those copies/matches.
            if len(tags) > MAX_DETAIL_TAGS or detail_tokens(tags) > MAX_DETAIL_TOKENS:
                raise DisplayLimit("Full explanations exceed the detail budget; use source export.")
            geometry, geometry_type, count = None, None, 0
            omitted = None
            if blob is None:
                omitted = (
                    "missing_source_geometry" if size is None else "source_geometry_byte_limit"
                )
            if blob is not None:
                original = from_wkb(gpkg_wkb(blob))
                geometry_type = original.geom_type
                count = int(get_num_coordinates(original))
                if count > MAX_COORDINATES:
                    omitted = "coordinate_limit"
                else:
                    candidate = mapping(original)
                    try:
                        if len(encode(candidate).encode()) <= MAX_BYTES // 2:
                            geometry = candidate
                        else:
                            omitted = "geometry_response_byte_limit"
                    except ValueError:
                        omitted = "nonfinite_source_geometry"
            result = {
                "type": "Feature",
                "id": f"{element}/{osm_id}",
                "geometry": geometry,
                "properties": {**tags, "element_type": element, "osm_id": osm_id},
                "layer_analyses": {name: analyze_feature(tags, name) for name in CATEGORIES},
                "display": {
                    "identity": ctx["identity"],
                    "representation": "object_detail",
                    "categories": [n for i, n in enumerate(CATEGORIES) if mask & (1 << i)],
                    "coverage_bounds": ctx["bounds"],
                    "diagnostic": diagnostic,
                    "drawable": diagnostic is None,
                    "geometry_type": geometry_type,
                    "coordinates": count,
                    "geometry_omitted": omitted,
                    "geometry_policy": "Original source geometry; no clipping, simplification or repair.",
                    "simplification_tolerance_m": 0,
                    "tags_complete": True,
                    "classification_complete": True,
                    "geometry_complete": geometry is not None,
                    "limits": self.limits(),
                },
            }
            if len(encode(result).encode()) > MAX_BYTES:
                result["geometry"] = None
                result["display"].update(
                    geometry_omitted="detail_response_byte_limit", geometry_complete=False
                )
                if len(encode(result).encode()) > MAX_BYTES:
                    raise DisplayLimit(
                        "Full details exceed the response budget; use source export."
                    )
            if monotonic() >= deadline:
                raise DisplayUnavailable("busy", "Detail query reached its time budget; retry.")
            return result

    def overview(self, directory, bbox, *, categories=CATEGORIES):
        requested, names = parse_bbox(bbox), parse_categories(categories)
        with self._query(directory) as (ctx, manifest, connection, deadline):
            effective = intersect_bounds(requested, ctx["bounds"])
            result = self._collection(ctx, requested, effective, "aggregate_overview")
            result["display"].update(
                assignment=manifest["overview_assignment"],
                counts_scope="Whole cells intersecting the effective viewport; not exact viewport object counts.",
                categories=names,
                grid_side=GRID_SIDE,
            )
            if effective is None:
                return result
            west, south, east, north = ctx["bounds"]
            dx, dy = (east - west) / GRID_SIDE, (north - south) / GRID_SIDE
            for cell, total, *counts in connection.execute("SELECT * FROM overview ORDER BY cell"):
                row, col = divmod(cell, GRID_SIDE)
                bounds = (
                    west + col * dx,
                    south + row * dy,
                    west + (col + 1) * dx,
                    south + (row + 1) * dy,
                )
                if intersect_bounds(bounds, effective) is None:
                    continue
                selected = {n: counts[CATEGORIES.index(n)] for n in names}
                if not any(selected.values()):
                    continue
                result["features"].append(
                    {
                        "type": "Feature",
                        "id": f"cell/{cell}",
                        "geometry": mapping(box(*bounds)),
                        "properties": {"objects": total, "category_counts": selected},
                    }
                )
            result["display"]["returned_count"] = len(result["features"])
            result["display"]["diagnostic_counts"] = manifest["diagnostics"]["counts"]
            return result

    def _collection(self, ctx, requested, effective, representation):
        return {
            "type": "FeatureCollection",
            "features": [],
            "display": {
                "identity": ctx["identity"],
                "requested_bounds": requested,
                "effective_bounds": effective,
                "coverage_bounds": ctx["bounds"],
                "representation": representation,
                "returned_count": 0,
                "complete": True,
                "outside_coverage": effective is None,
                "limits": self.limits(),
                "style": "category",
                "category_precedence": list(CATEGORIES),
                "classification_details": "On demand: /study/osm/features/{element_type}/{osm_id}",
            },
        }


def detail_tokens(tags):
    """Bound explanation expansion, including semicolon and list-valued source tags."""
    pending, total = list(tags.values()), 0
    while pending:
        value = pending.pop()
        if isinstance(value, list):
            pending.extend(value)
        else:
            total += value.count(";") + 1 if isinstance(value, str) else 1
        if total > MAX_DETAIL_TOKENS:
            break
    return total
