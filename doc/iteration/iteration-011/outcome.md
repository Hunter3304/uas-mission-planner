# Iteration 011 - Independent OFM visualization

Approved 2026-10-16. Milestone 10; planning Issue #98 / PR #99 and implementation
Issue #100; integration branch `iteration/011`; feature `feature/100-ofm-visualization`.

The planning baseline passed Linux/Windows/frontend run `38889659526` and merged
through #99 at `fcae27c`. Its previously published documentation branch was removed
locally/remotely, followed by fetch/prune and local/remote branch verification.

Feature PR #101 passed Linux/Windows/frontend run `38891678564` on `7c172ed`
and merged at `4338849`. Issues #98/#100 are closed and merged-feature cleanup
is verified locally/remotely. Main integration retains an independent CI gate.

## Result

Independent OFM snapshot acquisition/import/rebuild/inspection, regional display
layers, a read-only API and standalone preview are implemented. The backend serves
`/ofm`; a downloadable single-file HTML version works without any HTTP requests.
No frontend main-map or planner integration is included. See the
[operation guide and API contract](../../experiments/iteration-011.md).

Default extent is the existing `hannover-lehrte-5km` study. All eight reference
sites remain within the saved boundary; the four observed OFM aerodromes/helipads
are styled and queried separately from project hospital/laboratory reference sites.
National inventory and selected regional records are distinguished.

## Real retained acceptance (2026-10-16)

A new bounded official ED 2610 acquisition is retained at
`data/.ofm/hannover-2610-v2`. The ZIP is 7,709,535 bytes and has SHA-256
`e87c100883ea10dd196fb5a8ce200d8dbf6644ec5857f57f310ce57dd40280e1`.
Index and ZIP receipts/response headers, original bytes and all derivative hashes
are preserved locally. Offline rebuild under `.cache/iteration011-real-rebuild`
produces identical checksums for all seven source/derivative files.

- Source inventory: 1,056 Ase records, 1,048 Abd records and 1,360 Ahp records.
- Selected regional layer: five drawable airspaces and five invalid-shape
  bounding-box candidates with null geometry; four drawable OFM aerodrome points.
- Diagnostics: five invalid regional candidates and 17 unsupported records with
  unknown region relation. Unknown records are not silently asserted outside the
  study and remain available via the diagnostic/detail APIs.
- Nine repeated semantic-ID groups exist in the source; one has conflicting
  semantic values. Conflicting variants and multiple geometry parts are quarantined
  and inspectable, rather than choosing a variant or inventing multipart semantics.
- The Hannover CTR retains HEI 0 FT / ALT 2500 FT (762 m in the MSL reference).
  FL values remain flight levels; no flight applicability is inferred.
- Desktop and 390 px mobile real-data preview inspection: eight reference sites,
  selectable CTR attributes, no page errors and no horizontal page overflow.
  Local screenshots: `.cache/iteration011-desktop.png` / `iteration011-mobile.png`;
  offline preview: `.cache/iteration011-real-preview-v3.html`.

The data is effective on 2026-10-12; its AIRAC interval is 2026-10-01 to 2026-10-29.
This does not reconstruct the project's historical 2026-10-07 scenario. Acquisition
and integrity verification do not certify freshness, legal clearance or completeness.

## Validation

Full local backend: **274 passed / one existing Windows permission skip** (101.36 s).
The 13 OFM tests cover region selection, original height references/FL, invalid and
conflicting semantics, linked data, deterministic offline rebuilding, corruption,
file-inventory containment, malformed/entity XML, schema rejection, download size/
redirect restrictions, empty aerodromes, read-only API and escaped offline export.

Ruff lint/format, frontend lint/TypeScript/production build pass. An offline Python
wheel build succeeds and includes the preview HTML and default-region resource. All **14 mocked
browser** and **14 real-stack smoke** tests pass with clean exits. New browser tests
check references, original text/XSS handling, filters, layer switches, zoom/fit,
source-provenance export, mobile layout and offline HTML with no HTTP requests.

Application code does not stop/reuse user-owned services. Test servers are isolated
and stopped by their own runners. Original regional data and private profiles remain.
Feature publication has passed its CI gate and cleanup is verified above. Main
integration retains an independent gate; verified final facts follow afterwards.

## Limits retained

Provider shape-extension geometries are display derivatives. Unsupported raw
arcs/frontiers/multiple parts, derived geometry and conflicting metadata retain
diagnostics. No complete raw OFMX/XSD/geodesic validation is claimed. Runway/service
attributes use supported direct associations; navigation-aid drawing is deferred.
Source ZIP/readme attribution is retained, but complete license archival and public
data redistribution review remain outstanding. No real raw/derived source data are
published by the code PR. Existing main-map, routing/legal/NOTAM and performance
follow-up scopes are unchanged.
