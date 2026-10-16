# Independent OpenFlightMaps layers - operation guide

Approved scope: [Iteration 011](../plan/iteration-011.md). The independent preview
is served by the backend and requires no frontend development server or online
basemap. The existing main explorer and route controls are separate.

## Acquire a new revision

From the repository root, using the locked environment:

```powershell
uv run --project backend --locked uas-planner ofm-fetch --cycle 2610 --output data/.ofm/hannover-2610-new
uv run --project backend --locked uas-planner ofm-inspect data/.ofm/hannover-2610-new
```

Choose a new output name for every acquisition. `2610` is the inspected example,
not an automatically current cycle. Select the intended cycle and inspect its
published validity and XML effective time. A cycle can contain multiple revisions;
the ZIP checksum identifies the exact received version. Retrieval does not establish
flight applicability, freshness or complete coverage.

The acquisition command resolves the official ED publication XML, follows its
OFMX product link and bounds the index/ZIP download sizes and time. Source files,
HTTP receipts/headers and SHA-256 values are retained. The importer supports the
inspected isolated Germany OFMX 0.1 product. Other schema versions fail explicitly.
The completion marker `ofm.json` is written last; a partial directory cannot pass
inspection. Original/private data outside the new output remain untouched.

Default selection uses `hannover-lehrte-5km`, the saved eight-site region and its
5 km margin. Exact WGS84 west/south/east/north bounds:
`9.650495867959657, 52.32042221571155, 10.068841103123809, 52.45032927853548`.
The packaged region is checked against the versioned study configuration.
`--region path/to/region.json` explicitly selects another validated region; its
reference sites must lie within its declared bounds. Download extent and selected
display extent remain distinct.

## Offline import and rebuild

```powershell
uv run --project backend --locked uas-planner ofm-import --cycle 2610 --archive path/to/ofmx_ed.zip --publication path/to/ED_2610.xml --output data/.ofm/imported-new
uv run --project backend --locked uas-planner ofm-rebuild data/.ofm/imported-new --output data/.ofm/rebuilt-new
```

Import/rebuild require no network. Rebuild first verifies originals and derived
files, then produces new deterministic layer/detail/diagnostic files. Existing
outputs are refused. Integrity checks detect accidental changes; unsigned local
checksums do not authenticate independently modified source/manifest pairs.

Snapshots live under `data/.ofm/{id}` by default, separately from the existing OSM
dataset schema. Every snapshot includes source ZIP/publication, region, airspace
and aerodrome GeoJSON, object details, diagnostics and a checksummed manifest.
Runways, services/frequencies and other related XML are retained in selected-object
details where direct associations are supported. National source-category counts
remain in the inventory; navigation-aid drawing is outside this delivery.

## View and export

Start or restart the backend in its own terminal to load the merged code:

```powershell
uv run --project backend --locked uvicorn uas_planner.api.app:app --host 127.0.0.1 --port 8000
```

Open [the independent preview](http://127.0.0.1:8000/ofm). `UAS_DATA_DIR`, when set,
selects the data root; its OFM collection remains `{data_root}/.ofm`. There is no
menu/map change in the main frontend. Do not stop an unidentified process merely
to free the port; reuse/restart the confirmed project backend through its terminal.

- Select a verified snapshot. Failed verification is shown explicitly and clears
  previous source geometry; there is no automatic acquisition in the browser.
- Toggle airspaces, aerodromes and project reference sites independently. Search
  and type filters change the view; they do not change saved source data.
- Select a list entry or shape for original type/class, lower/upper values,
  references, units, schedules, remarks, related XML and quality diagnostics.
- Pan/zoom and **Fit region** inspect the saved boundary without source requests
  or extent expansion. The reference-site list can focus an individual site.
- **Export airspaces/aerodromes** saves the complete selected-region sublayer,
  including null-geometry candidates, with source/region/revision/license provenance.
  Search filters do not remove records from that source-layer export.
- **Export metadata** saves snapshot identity/inventory/receipts. **Download offline
  preview** saves one self-contained HTML file with details and diagnostics; open
  it locally without a server. The offline file contains retained source information,
  so keep it local unless redistribution rights have been reviewed.

The same offline file can be generated through the CLI. The output parent
directory must exist, and the file itself must be new:

```powershell
New-Item -ItemType Directory -Force .cache | Out-Null
uv run --project backend --locked uas-planner ofm-preview data/.ofm/hannover-2610-new --output .cache/ofm-preview-new.html
```

## Read-only API

| Method/path | Purpose |
|---|---|
| `GET /api/ofm/snapshots` | Local snapshot listing and verification state |
| `GET /api/ofm/snapshots/{id}` | Metadata, region, inventory, receipts and quality counts |
| `GET /api/ofm/snapshots/{id}/features?layer=airspaces` | Selected regional airspaces and export provenance |
| `GET /api/ofm/snapshots/{id}/features?layer=aerodromes` | Selected regional aerodromes; an empty layer is valid |
| `GET /api/ofm/snapshots/{id}/features/{feature_id}` | Object attributes, supported relationships and source variants |
| `GET /api/ofm/snapshots/{id}/diagnostics` | Invalid/unsupported records with candidate/unknown region relation |
| `GET /api/ofm/snapshots/{id}/preview` | Downloadable self-contained HTML preview |

Unknown IDs return 404, invalid layer parameters return 422, and snapshot corruption
returns 422. Reads verify the fixed file inventory and checksums. The API does not
accept arbitrary source filenames or acquire provider data.

## Interpretation and quality

HEI, ALT and STD retain their ground/MSL/standard-atmosphere references. Feet-to-metre
arithmetic is shown in the **same** reference; FL is preserved without a metre/MSL
conversion. Missing schedules/values never assert unrestricted operation.

Provider shape extensions are display derivatives. Unsupported/multiple parts,
conflicting semantic records, missing derived boundaries and invalid geometry are
reported, not silently repaired or interpreted as prohibitions. Valid full source
extents are retained and clipped only by the viewport. Raw straight-vertex fallback
is labelled a display approximation; raw arcs/frontiers without supported shapes
remain unresolved. The preview is an approximate geographic visualization, not a
navigation chart or metric measurement tool.

Five invalid source-shape bounding boxes overlap the inspected region. Their
null-geometry candidates and other unknown-extent diagnostics remain queryable;
these do not establish five exact intersections or complete coverage. Detailed
source variants are available when a repeated mid has conflicting attributes.

OFMA attribution and the bundled-readme hash are preserved. Full license text
has not been archived and redistribution is not reviewed; raw/derived real data
remain local and outside Git. OFM does not add NOTAM completeness or permission
evidence. This delivery does not change the current three planners, risk weights,
DIPUL decisions or main-map behavior.
