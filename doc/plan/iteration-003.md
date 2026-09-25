# Iteration 003: Stable prototype delivery

## Agreement

The user requested error handling, small-example tests, README improvements, and a stage version. Deliver these as v0.3.0, a local research prototype release. Preserve separate Python and React processes and the independent research core.

## Issues and acceptance

1. Harden failure handling: malformed manifests and stored tags fail predictably; the CLI exits cleanly; unavailable APIs, HTML responses, and failed downloads have actionable English messages and regression coverage.
2. Add a reproducible offline sample: a CLI command creates a small synthetic point/line/polygon dataset using the existing storage pipeline, without overwriting data or calling the network. Mark synthetic provenance explicitly. Verify CLI -> storage -> actual API -> browser -> download using the sample, including in CI.
3. Prepare stage delivery: synchronize package/API versions, update lockfiles, provide a README quick start and port/URL troubleshooting, changelog and feedback; validate, merge, tag the tested main commit, and publish GitHub Release v0.3.0.

## Workflow and validation

- Create Milestone Iteration 003 and its Issues before feature branches.
- Merge each verified feature PR into iteration/003; close its Issue and delete local/remote feature branches immediately.
- Run Python tests and Ruff, frontend ESLint/type/build checks, mocked UI regressions, and the real-stack offline sample test. CI validates Windows/Linux Python and Linux browser behavior.
- Merge iteration/003 into main, retain the iteration reference, close the Milestone, and publish the release against a verified commit. Record final facts in HANDOFF and feedback using the agreed post-merge documentation workflow.
- Do not stop user-owned services. Test servers use separate ports and stop after tests. Do not leave additional demonstration servers running.

## Boundaries

No new planning algorithms, browser acquisition, public hosting, large-area optimization, or dependency upgrades beyond what this delivery requires. Existing small-area and in-memory limits remain documented. The stage version denotes a reproducible prototype, not production or aviation certification.
