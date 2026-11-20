"""Reconcile the public municipal MiD inputs with the native GHSL count raster."""

from collections import defaultdict
from math import fsum, isclose, isfinite

import pyogrio
import rasterio
from pyproj import Transformer
from shapely import STRtree, segmentize, union_all
from shapely.geometry import shape
from shapely.ops import transform

from uas_planner.core.experiment import checksum
from uas_planner.core.population_costs import aggregate_native

SAE_SHEET = "SAE-Ergebnisse-Gem. > 10.000 EW"
SAE_FIELDS = ("GKZ", "SAE\nAnzahl Wege", "SAE\nAnteil Fuß-Wege\n(in %)")
SAE_URL = (
    "https://www.mobilitaet-in-deutschland.de/pdf/"
    "MiD23_SAE_Regionalisierung-von-MiD-Ergebnissen_Gemeindedaten.xlsx"
)
BKG_WFS = "https://sgx.geodatenzentrum.de/wfs_vg250"
BKG_ATTRIBUTION = "© BKG, dl-de/by-2-0"
AREA_TOLERANCE_M2 = 0.1


def municipal_rates(path, expected_codes):
    """Read only the required municipal walking rates from the published workbook."""
    frame = pyogrio.read_dataframe(path, layer=SAE_SHEET, columns=SAE_FIELDS, read_geometry=False)
    rates = {}
    for code, trips, walking_pct in frame.loc[:, list(SAE_FIELDS)].itertuples(
        index=False, name=None
    ):
        code = str(code).zfill(8)
        if code not in expected_codes:
            continue
        trips, walking_pct = float(trips), float(walking_pct)
        if code in rates or not isfinite(trips) or trips < 0 or not 0 <= walking_pct <= 100:
            raise ValueError(f"Invalid or duplicate MiD municipal rates for AGS {code}.")
        rates[code] = trips * walking_pct / 100
    if missing := expected_codes - rates.keys():
        raise ValueError(
            f"MiD municipal walking estimates missing for AGS {', '.join(sorted(missing))}."
        )
    return rates


def municipal_boundaries(path, study_boundary):
    frame = pyogrio.read_dataframe(path, columns=["ags", "gen"])
    if frame.crs is None:
        raise ValueError("Municipal boundaries need a declared coordinate system.")
    geometries = defaultdict(list)
    names = {}
    for code, name, geom in (
        frame.to_crs(25832).loc[:, ["ags", "gen", "geometry"]].itertuples(index=False, name=None)
    ):
        code = str(code).zfill(8)
        if geom is None or geom.is_empty:
            continue
        if not geom.is_valid or geom.geom_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError(f"Invalid BKG municipality geometry for AGS {code}.")
        clipped = geom.intersection(study_boundary)
        if clipped.area > 0:
            geometries[code].append(clipped)
            names[code] = str(name)
    if not geometries:
        raise ValueError("Municipal boundaries do not intersect the saved study area.")
    boundaries = {code: union_all(geometries[code]) for code in sorted(geometries)}
    covered = union_all(list(boundaries.values())).area
    gap = max(0, study_boundary.area - covered)
    overlap = max(0, fsum(g.area for g in boundaries.values()) - covered)
    if max(gap, overlap) > AREA_TOLERANCE_M2:
        raise ValueError(
            f"Municipal geometry leaves {gap:.2f} m² uncovered and {overlap:.2f} m² overlapping."
        )
    return boundaries, names, gap, overlap


def estimate_departures(population, raster, workbook, boundaries_path, boundary_release):
    """Multiply count-conserving residents by municipality-specific walking rates."""
    cells = population.metric_population_cells
    study_boundary = shape(population.metadata["study_boundary_metric"])
    workbook_hash, boundary_hash = checksum(workbook), checksum(boundaries_path)
    boundaries, names, gap, overlap = municipal_boundaries(boundaries_path, study_boundary)
    rates = municipal_rates(workbook, set(boundaries))
    codes = list(boundaries)
    tree = STRtree(list(boundaries.values()))
    project_native = Transformer.from_crs(25832, "ESRI:54009", always_xy=True).transform
    population_by_code = defaultdict(float)
    metric_known_area = partition_adjustment = 0.0
    split_cells = 0
    departures = []

    with rasterio.open(raster) as src:
        for polygon, _, residents in cells:
            parts = []
            for index in sorted(tree.query(polygon, predicate="intersects")):
                part = polygon.intersection(tree.geometries[index])
                if part.area > 0:
                    parts.append((codes[index], part))
            if not parts:
                raise ValueError("A study cell has no municipal coverage.")
            if residents is None:
                native = transform(project_native, segmentize(polygon, 25))
                aggregate = aggregate_native(src, native, vectorized=True)
                residents = aggregate["observed_estimated_people"]
                metric_known_area += polygon.area * aggregate["known_area_m2"] / native.area
            else:
                metric_known_area += polygon.area

            if len(parts) == 1 or residents == 0:
                shares = {parts[0][0]: residents}
            else:
                split_cells += 1
                shares = {
                    code: aggregate_native(
                        src, transform(project_native, segmentize(part, 25)), vectorized=True
                    )["observed_estimated_people"]
                    for code, part in parts
                }
                subtotal = fsum(shares.values())
                if subtotal <= 0 or not isclose(subtotal, residents, rel_tol=1e-5, abs_tol=0.005):
                    raise ValueError("GHSL municipality split does not conserve the cell count.")
                partition_adjustment += abs(residents - subtotal)
                shares = {code: residents * value / subtotal for code, value in shares.items()}

            for code, count in shares.items():
                population_by_code[code] += count
            departures.append(fsum(count * rates[code] for code, count in shares.items()))

    observed = population.metadata["observed_estimated_people"]
    if not isclose(fsum(population_by_code.values()), observed, abs_tol=1e-6):
        raise ValueError("GHSL population does not reconcile across municipalities.")
    if checksum(workbook) != workbook_hash or checksum(boundaries_path) != boundary_hash:
        raise ValueError("Municipal inputs changed during preparation.")
    return departures, {
        "municipalities": [
            {"ags": code, "name": names[code], "area_m2": boundaries[code].area} for code in codes
        ],
        "study_area_m2": study_boundary.area,
        "municipality_uncovered_area_m2": gap,
        "municipality_overlap_area_m2": overlap,
        "ghsl_known_area_m2": min(metric_known_area, study_boundary.area),
        "ghsl_residents_reconciled": observed,
        "populated_cells_split_by_municipal_boundary": split_cells,
        "native_intersection_residual_residents_before_normalization": partition_adjustment,
        "sae": {
            "title": "MiD 2023 municipal small-area estimates, November 2025",
            "url": SAE_URL,
            "file": workbook.name,
            "sha256": workbook_hash,
            "table": SAE_SHEET,
            "fields": [" ".join(field.split()) for field in SAE_FIELDS],
        },
        "boundaries": {
            "title": "VG250 (municipalities)",
            "release": boundary_release,
            "url": BKG_WFS,
            "file": boundaries_path.name,
            "sha256": boundary_hash,
            "attribution": BKG_ATTRIBUTION,
        },
    }
