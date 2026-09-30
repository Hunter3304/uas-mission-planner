# External data and methodology assessment

Assessment date: **2026-09-29**. Scope: the six sources requested by Yao,
evaluated against the existing UAS Mission Planner at local commit `84cf8a3`.
This is a documentation assessment, not an implemented integration or an approved sprint.

## Reading order

| Source | Access and format | Update frequency | Spatial resolution | Automation assessment |
| --- | --- | --- | --- | --- |
| [Droniq / TraX](01-droniq-trax.md) | App/web application; commercial external traffic interface exists, protocol/schema unconfirmed | Marketed as live; numerical latency/update guarantees unconfirmed | Aircraft tracks; accuracy/coverage unconfirmed, no raster cell size | Conditional on provider access, documentation and data rights |
| [OpenFlightMaps](02-openflightmaps.md) | Regional downloads; OFMX, with other exports described by provider | AIRAC, nominally 28 days; inspect actual package validity | Vector objects; no universal metre resolution; chart scale is separate | Feasible candidate after current German package and parser validation |
| [GHSL](03-ghsl.md) | Anonymous HTTP download; GHS-POP ZIP/TIFF raster | Irregular releases; five-year epochs are not update frequency | Selected GHS-POP: 100 m / 1 km Mollweide, or 3 / 30 arcseconds WGS84 | Strong first candidate for reproducible offline processing |
| [DIPUL](04-dipul.md) | WFS/GML, WMS images, GeoJSON/ED-318 downloads; registered ED-318 API | Static downloads: 28-day AIRAC; live-service cadence unconfirmed | Vector geometries, heterogeneous sources; no universal metre accuracy | Strong candidate via static files or WFS; preserve conditions and validity |
| [SORA 2.5](05-sora-2.5.md) | JARUS PDFs; EASA online rules, PDF and machine-readable XML | Document revisions | Not a spatial dataset | Selected rules can be encoded; substantial mission inputs and review remain |
| [EGRED 2](06-egred-2.md) | BBK guidance publication, PDF | Revisions; no fixed interval confirmed | Not a spatial dataset | Selected checks can be encoded after defining the BOS scenario |

Official evidence links and qualifications are in each source note. “Feasible”
means a reasoned engineering assessment, not a successful end-to-end test.
See [integration recommendation](integration-recommendation.md) for priorities,
project-specific gaps and a proposed first experiment.

## Main conclusions

1. Start technical validation with **GHSL and DIPUL**; retain the four existing
   independent OSM cost layers as the baseline.
2. Use **OpenFlightMaps** as supplementary aviation context after verifying its
   current regional distribution and preserving altitude/time semantics.
3. Keep **Droniq** as a conditional dynamic-traffic workstream. App access does
   not prove permission or technical access to the external feed.
4. Treat **SORA and EGRED** as methodological inputs. They cannot be downloaded
   as ready-made risk-map layers.
5. The missing link in this project is a spatial cost/constraint model followed
   by a route planner. Additional map overlays alone do not complete the task.

## Evidence and verification limits

- Primary provider/authority web material was reviewed on the assessment date.
  A dated release is distinguished from a website crawl or download date.
- GHSL's public file index was readable. Its raster tiles were not downloaded
  or inspected, and the specific tile covering the experiment is not selected.
- DIPUL's current documentation explicitly lists vector access. WFS/WMS
  GetCapabilities requests through the research browser returned fetch errors;
  no capabilities, schema or feature-response validation is claimed.
- Mobilithek's listing requires JavaScript in the available browser. Static
  package access requirements and payload were not independently validated.
- OpenFlightMaps' German regional page was found; its current downloadable
  payload was not inspected. The older `/ed-germany/` address returned 404.
- BBK's short landing address failed in the research browser and the publication
  HTML returned 403. Official indexed publication text identifies June 2024;
  this is the edition located, not proof that no later revision exists.
- Local HTTP probes were blocked by the environment's network proxy. These
  failures are not evidence that the providers' services are unavailable.
- No accounts were created, subscriptions purchased, providers contacted,
  datasets acquired, rules implemented or routing experiments run.

## Maintaining this assessment

Update the relevant source note when a real payload is inspected. Record request
URL, access date, product/version, validity or epoch, CRS, units, coverage,
license, checksum, parser result and remaining limitations. Keep licensed/raw
datasets outside this documentation folder; store assessment results here.
