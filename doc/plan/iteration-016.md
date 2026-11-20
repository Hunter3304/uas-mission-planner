# Iteration 016 — Time-dependent outdoor pedestrian exposure

Approved for Phase 1 implementation on 18 November 2026. The behavioural inputs are public MiD 2023 aggregates. The project transfers the Niedersachsen departure and duration patterns to the existing Hannover–Lehrte study area and estimates where residents walk using GHSL and OpenStreetMap. [Preparation guide](../experiments/iteration-016.md)

## Scope and delivery

Add an **Outdoor pedestrian exposure** mode alongside **Existing planning**. Keep Existing planning as the default and preserve its objectives, controls and API behaviour. Both modes use the current map, study boundary, eight saved facilities and existing feasibility checks. In the new mode, building use can help identify plausible walking destinations. Building geometry continues to serve the existing feasibility checks. Building risk grades do not enter the new objective.

- **Phase 1 — Public inputs and exposure map.** Verify the inputs first, then produce an average-day pedestrian layer for each published time window on the existing map. Phase 1 ends with data and map validation.
- **Phase 2 — Route planning and mode selector.** Use the accepted Phase 1 surfaces in an objective that combines route distance and pedestrian exposure at the selected departure time. Add the mode dropdown and its input panel on the existing page.

The output is the modelled mean number of residents walking on unsheltered routes during a time window. Its scope excludes stationary people outdoors, cycling, walking stages of trips assigned to another main mode, and visitor flows outside the resident-origin model. The published profile pools all survey days. Local date and time select the model window and continue to drive the existing flight checks. The pedestrian estimate has no separate weekday, weekend, holiday or live profile.

## Inputs and provenance

| Input | Use and status |
| --- | --- |
| Existing Hannover–Lehrte study | Reuse the current footprint and eight facilities, `data/hannover-part1-v4/study.json`, and the 150 m EPSG:25832 analysis grid. Use the current raster, API and map conventions. |
| GHSL GHS-POP R2023A V1.0 | Reuse the 2020 residential population estimate at `data/hannover-part1-v4/population.tif` (native 100 m). Aggregate counts with mass conservation and track NoData. [JRC product](https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php) · [Dataset DOI](https://doi.org/10.2905/2FF68A52-5B5F-4A22-8F40-C41DA8332CFE) |
| OpenStreetMap via Geofabrik | Reuse the local Niedersachsen PBF and `osm/features.gpkg`. Read any required standalone destinations and pedestrian tags from the same PBF when the existing GeoPackage filters omit them. Record the snapshot and attribution. [Niedersachsen extract](https://download.geofabrik.de/europe/germany/niedersachsen.html) · [OSM attribution](https://www.openstreetmap.org/copyright) |
| MiD 2023 municipal small-area estimates | Use `SAE Anzahl Wege` for average daily trips per resident and `SAE Anteil Fuß-Wege (%)` for walking share by trip count. All ten municipalities intersecting the study area have a workbook entry. These municipality figures are published statistical estimates of resident behaviour. [Workbook](https://www.mobilitaet-in-deutschland.de/pdf/MiD23_SAE_Regionalisierung-von-MiD-Ergebnissen_Gemeindedaten.xlsx) · [Methods report](https://www.mobilitaet-in-deutschland.de/pdf/MiD2023_SAE-Bericht.pdf) |
| MiT 2023 public Niedersachsen profiles | In `Wege`, use `Startzeit des Weges gruppiert` for starts and `Wegedauer [min] (ohne rbW) in Gruppen` for duration. For both tables, use `Hauptverkehrsmittel (fehlende Angaben wurden aufgefüllt)` as columns, `Bundesland` as breakdown and `Spalten %` as weighted percentages. Keep the Niedersachsen `zu Fuß` column. Both cross-tabulations were reproduced in the public tool. [Public MiT tool](https://mobilitaet-in-tabellen-2023.bast.de/) · [MiD supporting documentation](https://www.mobilitaet-in-deutschland.de/pdf/infas_Erg%C3%A4nzendeStudienunterlagen_MiD2023_7555.pdf) |
| BKG VG250 municipal boundaries | Auxiliary geometry for joining GHSL origins to the municipal MiD estimates by AGS. The union of the ten intersecting municipalities covers the study polygon. Use a pinned boundary release and retain the join and area check. [BKG open WFS](https://gdz.bkg.bund.de/index.php/default/open-data/wfs-verwaltungsgebiete-1-250-000-stand-01-01-wfs-vg250.html) |

The ten municipalities are Hannover (`03241001`), Burgdorf (`03241003`), Hemmingen (`03241007`), Isernhagen (`03241008`), Laatzen (`03241009`), Langenhagen (`03241010`), Lehrte (`03241011`), Ronnenberg (`03241014`), Seelze (`03241015`) and Sehnde (`03241016`). Municipal coverage establishes that each part of the study area has a municipal input. The model will assess raster and path coverage separately.

| Local start window | Niedersachsen share of walking starts, rounded for display |
| --- | ---: |
| 05:00–08:00 | 8.66% |
| 08:00–10:00 | 12.12% |
| 10:00–13:00 | 21.19% |
| 13:00–16:00 | 25.09% |
| 16:00–19:00 | 22.95% |
| 19:00–22:00 | 8.21% |
| 22:00–05:00 the next day | 1.78% |

| Trip duration | Niedersachsen share of walking durations, rounded for display |
| --- | ---: |
| Under 5 min | 2.49% |
| 5 to under 10 min | 18.96% |
| 10 to under 15 min | 17.24% |
| 15 to under 20 min | 14.35% |
| 20 to under 30 min | 11.06% |
| 30 to under 45 min | 14.83% |
| 45 to under 60 min | 6.14% |
| 60 min and over | 14.92% |

The start table provides shares of **trip starts**. The duration table provides a separate marginal distribution, so the first model applies the same duration distribution to all start windows. Use the unrounded weighted percentages returned by the public tool and validate each total. Store the aggregate values and query recipe locally. The input checks use the public products, and the planner reads the precomputed local output.

## Phase 1 — Data and map

### Verify the inputs before building the population layer

Reproduce the full-footprint municipal join and both Niedersachsen queries from public sources. Check that the municipal trip rate and walking share refer to the same denominator. Compare the weighting and exclusions across sources. The public grouped duration excludes regularly recurring work trips and includes imputed durations. The observed walking bases differ between the start and the duration query, with 19,774 and 20,080 weighted trips respectively. These are survey bases. Document how this difference and the treatment of recurring trips affect the transfer to the municipal walking total. If a compatible timed-trip coverage adjustment can be calculated, retain it in the input ledger. Otherwise apply the public profiles as an approximation to the overall municipal walking budget and record this assumption and its sensitivity.

Complete the initial check by pinning both profiles, validating the municipal join and documenting the transfer before generating estimated counts. The grouped walking durations supply the observed duration information. The within-group duration assumptions and their effect on estimates must be explicit. Test fixtures may verify the implementation. Acceptance requires published survey inputs and reconciled coverage.

### Calculate and distribute walking time

1. **Estimate walking departures.** For origin `i` in municipality `m`, multiply its GHSL resident mass `P_i` by municipal daily trips per resident `T_m` and the municipal walking fraction `F_m`. Multiply this walking-trip budget by the verified share `p_j` for start window `j`. The calculation `P_i × T_m × F_m × p_j` gives expected walking departures on a representative day. Use the residential cell as the spatial origin proxy for that budget. Apply any verified timed-trip coverage adjustment established by the input check. Allocate mixed boundary cells by intersection and preserve the total resident mass.
2. **Convert departures to walking person-minutes.** Distribute starts uniformly within each source window. Use the published duration shares, finite-bin midpoints and a representative duration for the open-ended bin. Start with 90 minutes for the `60 min and over` group and repeat the calculation at 60 and 120 minutes as sensitivity scenarios. These values are model parameters. For a start `s`, representative duration `d` and target interval `[a,b)`, credit `max(0, min(s+d,b) - max(s,a))` minutes. Average over start times and weight by the duration shares. Account for trips spanning windows or midnight on a repeating representative day.
3. **Allocate those minutes spatially.** Build a time-invariant allocation for each origin from reachable OSM walking routes. Use mapped pedestrian access, reachability and walking distance. Use building or destination types as static indicators of potential destinations where supported by the mapping. Assign minutes in proportion to time along the candidate routes. Inspect covered paths, tunnels, bridges and crossings before classifying outdoor segments. Retain the existing study boundary and account for minutes assigned outside it where the source graph permits. Record minutes for missing connections, uncertain classifications and other unresolved allocations.
4. **Serve the precomputed layer.** For each target window, divide the outdoor person-minutes in a cell by the window length in minutes to obtain mean concurrent pedestrians. Divide by the covered cell area in km² to obtain density. Save count, area, density, window, source and model versions, and coverage status. Publish all seven windows through the existing local dataset and React/Leaflet map patterns. Use a common colour scale and show the number, density and source window on inspection. Visually distinguish modelled zero from unavailable coverage. Reuse the surface across requests without rebuilding the pedestrian graph at runtime.

The statewide timing factor, shared duration assumption and fixed spatial allocation scale the same spatial pattern across windows. High and low periods change total exposure. The inputs do not identify which particular street becomes busier at a different time. Sensitivity checks should vary the duration and the spatial allocation separately and report their effects on estimated counts and route comparisons.

### Phase 1 acceptance

- Record the ten-municipality join, footprint coverage, GHSL valid area, OSM graph and exposure coverage, source versions, and any residual unknown cells. Quantify unresolved minutes and reject unexplained data loss. The original study boundary remains the delivery footprint.
- Generate every time window from the accepted public inputs. Verify the GHSL population transfer, the sums of departures, unequal window lengths, cross-window and midnight overlap, and deterministic output. Reconcile the full daily person-minute budget with outdoor in-area minutes, covered minutes, outside-area minutes and unresolved minutes using mutually exclusive categories.
- In the existing map, switch among all seven windows, inspect a cell and see the same-scale legend, local window, mean count and coverage status. Label the map as a resident-walking estimate from an all-days state profile.
- Record a reproducible import and generation procedure, an input inventory and known limitations in `doc/data-sources/`, plus the Phase 1 outcome. Save public aggregate values, extraction dates, queries, source vintage, boundary release, licences and attribution. Include the resulting estimate and uncertainty in the acceptance evidence before starting Phase 2.

## Phase 2 — Routing and mode selector

Approved for implementation on 19 November 2026. [Phase 2 outcome](../iteration/iteration-016/phase-2.md)

Use the departure's Europe/Berlin clock time to select a half-open published window. The initial planner evaluates each flight against the departure window throughout the route and discloses when estimated arrival is in another window. The selected date and time stay in use for the full existing flight-interval checks. Handle midnight and daylight-saving time via the existing local-date and timezone rules. Exposure-layer availability must be explicit. A candidate with unavailable required exposure data cannot be reported as a fully scored pedestrian-exposure route.

For horizontal route length `L`, length `l_g` in cell `g`, and pedestrian density `rho_g` in its selected window, use the existing regional grid integration pattern with a fixed positive `rho_ref` across windows for a study and model version:

```text
E = sum_g(l_g * rho_g / rho_ref)
J = L + lambda * E
```

`E` is an exposure-weighted length in metres. `lambda` is a dimensionless distance/exposure trade-off stored in configuration initially. Document how `rho_ref` and `lambda` were chosen, and use the same settings for search and independent scoring. Report `L`, `E`, `J`, the window and the model version. The score supports a comparative planning experiment. With a common temporal multiplier, the distance/exposure trade-off may lead to a different route, while the underlying relative density ranking stays fixed.

Start with the existing cross-platform A* integration. Reuse the existing terrain, obstacles, airspace and flight-interval feasibility checks. Add **Existing planning / Outdoor pedestrian exposure** to the existing page, share the map and map controls, and synchronise the selected time, overlay and route result. In the new mode show origin, destination, local departure date/time and the altitude, speed or other inputs needed by the existing feasibility checks. Apply documented defaults for planner settings. Hide the legacy objective picker, background and population weights, and other legacy-only route controls while the new mode is selected.

### Phase 2 acceptance

- Plan a route between existing sites, initially MHH to MVZ Labor Limbach Lehrte, on the real-input exposure surfaces. Compare two or more published windows at the same flight constraints and verify `L`, `E` and `J` independently. A controlled two-route case verifies that changing the distance/exposure trade-off can change the selected route. Real-case comparisons report the result even if the chosen geometry is identical.
- Verify the dropdown and mode-specific panel, local-time boundaries, missing coverage, and the map and result's shared time window. Run regressions for the existing distance and fused-risk objectives, default API behaviour, shared map layers and legacy controls after switching modes.
- Record both phase outcomes, scenario and test evidence in `doc/iteration/iteration-016/`. Follow the handoff's milestone, issue, branch, integration and review workflow after plan approval.

## References for the internship report

- **Bäumer, M., & Pfeiffer, M. (2025).** *Mobilitätskennzahlen für Deutschland in kleinräumiger Gliederung auf der Basis von modellgestützten Small Area-Schätzungen*. Cite for the municipal trip rates and mode shares, including the model-based geographic transfer. [Methods report](https://www.mobilitaet-in-deutschland.de/pdf/MiD2023_SAE-Bericht.pdf)
- **Tun, E., Nishikiori, T., Varghese, V., Chikaraishi, M., Seike, M., & Fujiwara, A. (2024).** *Emergency shelter location–allocation analysis with time–varying demand*. Cite for estimating time-dependent presence from travel diaries and population. This plan applies the time-interval concept to public aggregates. [DOI](https://doi.org/10.1016/j.eastsj.2024.100152)
- **Crols, T., & Malleson, N. (2019).** *Quantifying the ambient population using hourly population footfall data and an agent-based model of daily mobility*. Cite for destination assignment and the distinction between modelled presence and validation against observed counts. [DOI](https://doi.org/10.1007/s10707-019-00346-1)
- **Pilko, A., Sóbester, A., Scanlan, J. P., & Ferraro, M. (2023).** *Spatiotemporal ground risk mapping for uncrewed aircraft systems operations*. Cite for the use of time-varying population estimates in UAS ground-risk research. The route objective here is specific to this project. [DOI](https://doi.org/10.2514/1.I011113)
- **Schiavina, M., Freire, S., Carioli, A., & MacManus, K. (2023).** *GHS-POP R2023A – GHS population grid multitemporal (1975–2030)*. Cite for the residential population grid. [Dataset DOI](https://doi.org/10.2905/2FF68A52-5B5F-4A22-8F40-C41DA8332CFE)

## Existing project entry points

Reuse the population aggregation and map display patterns in [population_costs.py](../../backend/src/uas_planner/core/population_costs.py), [app.py](../../backend/src/uas_planner/api/app.py), [RegionalMap.tsx](../../frontend/src/RegionalMap.tsx) and [PopulationCostOverlay.tsx](../../frontend/src/PopulationCostOverlay.tsx). Phase 2 connects through [regional_routing.py](../../backend/src/uas_planner/core/regional_routing.py) and [RegionalRouting.tsx](../../frontend/src/RegionalRouting.tsx). [Iteration 015](iteration-015.md) documents the existing routing baseline.
