# Iteration 002: Demonstrable dataset explorer

## Agreement and scope

The user requested the second work block: **display layers, statistics, and downloadable results**. This iteration adds a separately running FastAPI backend and React frontend over the existing dataset round trip. It reuses locally saved datasets; acquiring a new area remains available through the existing CLI.

## Deliverables and acceptance criteria

1. List saved datasets from the configured data directory, without exposing arbitrary filesystem paths.
2. Verify datasets through the existing storage core before returning their contents. Missing and invalid datasets have explicit API/UI error states.
3. Display the selected dataset on a Leaflet map with building, highway, landuse, and natural layer switches, source query bounds, fit-to-data, and safe feature property inspection.
4. Show total unique feature count, geometry counts, layer counts, CRS, and acquisition/storage information. Explain overlapping semantic layers rather than implying layer counts sum to unique features.
5. Download GeoJSON, the original GeoPackage, and JSON metadata. Exports refer to the complete verified dataset, independently of display filtering.
6. Support loading, empty, no-dataset, server-error, and unavailable-basemap states. Saved vector layers and downloads do not require a basemap service.
7. Use English UI text, keyboard-accessible controls, and a responsive layout suitable for a local demonstration.
8. Verify API behavior with offline tests, frontend type/lint/build checks, browser interaction tests, and a visual check using the real Braunschweig sample.
9. Update README, HANDOFF, and iteration feedback. Merge tested features into `iteration/002`, then the sprint into `main`; close Issues/Milestone and verify local/remote feature-branch deletion.

## Planned Issues

- Dataset explorer API: listing, details/GeoJSON, verified downloads, restricted paths, tests.
- React dataset explorer: map, layer controls, statistics, feature inspection, downloads, responsive states.
- Demonstration verification and documentation: browser checks, CI integration, startup instructions, retrospective.

Each Issue belongs to the Iteration 002 Milestone and is created before its feature branch.

## Architecture

- FastAPI adapts the framework-independent Python storage core.
- React calls relative `/api` URLs through Vite's local development proxy. Backend and frontend are separate processes.
- Bind local servers to loopback. The dataset root defaults to the repository's `data/` directory and can be set with `UAS_DATA_DIR`.
- Use Leaflet directly from a React map component. Basemap attribution remains visible.
- No runtime network requests occur for reading saved vector data; optional background tiles require internet.

## Deferred

Browser-triggered acquisition, background download queues, risk maps, path planning, user accounts, and public deployment are not required for this work block. Do not start another sprint without discussion.
