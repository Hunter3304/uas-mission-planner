# Iteration 016 — Prepare the Hannover–Lehrte pedestrian layer

Use the saved `data/hannover-part1-v4` regional study from the existing dataset
setup. The added preparation is an offline job once the two public input files
are saved. It uses the walking profiles pinned in
[mid_profiles.py](../../backend/src/uas_planner/core/mid_profiles.py). See
the [source inventory](../data-sources/07-mid-2023.md) for definitions, the
MiT extraction recipe and citations.

Save the workbook and the WFS response from the repository root. Keep the
files in the local ignored `data` directory with the study assets.

```powershell
New-Item -ItemType Directory -Force data/.pedestrian-inputs | Out-Null
$workbook = 'https://www.mobilitaet-in-deutschland.de/pdf/MiD23_SAE_Regionalisierung-von-MiD-Ergebnissen_Gemeindedaten.xlsx'
$boundaries = 'https://sgx.geodatenzentrum.de/wfs_vg250?service=WFS&version=2.0.0&request=GetFeature&typeNames=vg250_gem&srsName=EPSG%3A25832&bbox=544207.161%2C5796876.656%2C572850.415%2C5811664.217%2CEPSG%3A25832'
Invoke-WebRequest -Uri $workbook -OutFile data/.pedestrian-inputs/MiD23_SAE_Gemeindedaten.xlsx
Invoke-WebRequest -Uri $boundaries -OutFile data/.pedestrian-inputs/vg250-hannover.gml
```

Keep the 18 November 2026 BKG response to reproduce the exact validation run.
The WFS response includes a request timestamp, so future downloads can have a
different checksum even when the geometries match. Record the provider release
and the new source checksum when updating an input.

```powershell
uv run --project backend --locked uas-planner study-pedestrian-prepare `
  data/hannover-part1-v4 `
  --mid-workbook data/.pedestrian-inputs/MiD23_SAE_Gemeindedaten.xlsx `
  --boundaries data/.pedestrian-inputs/vg250-hannover.gml `
  --boundary-release 'VG250, 2025-01-01 (BKG catalogue)'
```

The command prints coverage, allocation and sensitivity diagnostics and replaces
`data/.pedestrian-exposure/hannover-part1-v4.json` atomically after validation.
Use that file to keep the full input receipts, geographic grid, seven windows
and ledgers. Run the command again when study assets or input sources change.

## Inspect the result

Start the backend and frontend as described in the [README](../../README.md).
Select `hannover-part1-v4`, expand **Outdoor pedestrians** and select **Show
outdoor pedestrian estimates**. Choose any of the seven Europe/Berlin windows.
Click a cell for its average count, density, window and coverage. The windows
share the same colour scale. The palest colour represents modelled zero and grey
indicates unavailable estimates. The profile represents all survey days pooled.

The endpoint is
`GET /api/datasets/hannover-part1-v4/study/pedestrian-exposure?scenario=08-10`.
The seven IDs are `05-08`, `08-10`, `10-13`, `13-16`, `16-19`, `19-22`, and
`22-05`. The API loads the saved product and checks its study-manifest hash.
The request does not rebuild the walking graph. In the route panel, choose
**Outdoor pedestrian exposure** in the **Routing mode** dropdown. Select the
saved endpoints and a Europe/Berlin departure time. The map follows the selected
departure window. Choose **Existing planning** for the original controls.
See the [Phase 2 acceptance report](../iteration/iteration-016/phase-2.md) for
runtime defaults, route scoring and the verified site pair.

## Read the ledger

Each window tracks the full estimated walking minutes and parcels them into
outdoor in-area, covered, outside the area, and unallocated. Covered minutes
include known shelter along selected paths. Unallocated includes unconnected
origins, origins with no reachable destination, uncertain shelter and outdoor
minutes crossing a cell labelled unavailable. A cell with usable source
coverage and no allocated path gets the modelled zero. The source graph uses
foot access and shelter tags, with untagged shelter treated as outdoors.

Walking budgets use reachable tagged destinations within 2.5 km of the origin
snap point, with up to six candidates and a 150 m maximum snap distance. The
distance weight is `1 / (1 + distance_m / 500)^2`, multiplied by the count of
mapped destination-use tags at the vertex. The sensitivity calculation changes
the decay denominator to 750 m. The spatial rule remains constant across
windows. The estimated intensity changes across the day while the relative
geographic pattern stays fixed. This is a model of residents' walking and a
transferred state timing profile. Local street counts, stationary crowds and
weekend-specific timing lie outside the output's coverage.
