# Iteration 006 Part 2 — OMPL runtime dependency gate

Date: 2026-10-01 (Europe/Berlin).
Status: implementation authorized; native Windows dependency gate failed.
Part 2 is not complete. Runtime proposal below requires review before installation.

## Verified repository and environment

- Part 1 is on local main at `e54e245` (merge of PR #58).
- Python: CPython 3.13.13, MSC v.1944, 64-bit Windows.
- Project supports Python >=3.13,<3.14 and Windows/Linux regression coverage.
- `importlib.util.find_spec('ompl')` returns None in `backend/.venv`.
- No Docker executable was found. WSL executable exists, but `wsl --list --quiet`
  reports that Windows Subsystem for Linux is not installed. No Linux runtime
  or distribution was installed by this session.
- The existing unrelated HANDOFF changes were preserved.

## Reproducible package-resolution checks

Run from the repository root with network access:

```powershell
uv pip install --python backend\.venv\Scripts\python.exe --dry-run --only-binary :all: --no-cache ompl==2.0.1
```

Exit code 1:

```text
Because ompl==2.0.1 has no wheels with a matching platform tag
(e.g., win_amd64) ... requirements are unsatisfiable.
```

The corresponding cross-platform resolution check:

```powershell
uv pip install --python backend\.venv\Scripts\python.exe --dry-run --only-binary :all: --no-cache --python-platform x86_64-unknown-linux-gnu ompl==2.0.1
```

Exit code 0: resolved one package; would download/install `ompl==2.0.1`.
Neither command installs a package or changes project dependencies/lockfiles.
Initial sandbox network denial was retried with approved network access; the
Windows result above is a package compatibility failure, not that network error.

[PyPI release files](https://pypi.org/project/ompl/2.0.1/) list CPython 3.13
Linux x86-64/ARM64 and macOS wheels, with no Windows wheel or source distribution
for this release. The CPython 3.13 Linux x86-64 wheel SHA-256 is
`a740777f1959f3ae858d397ed1557b5a01729219f8261b0455654664f9161cd8`.
[Official installation documentation](https://ompl.kavrakilab.org/core/installation.html)
states that its recommended Windows vcpkg installation does not include Python
bindings. That page's older Python-wheel version list is superseded for package
availability by the actual release files.

This establishes failure of the binary-package installation route on the
current Windows baseline. It does not establish that a custom source build is
impossible. A supported/reproducible Windows source-build route has not been
verified. Linux package resolution succeeds, but actual imports, ABITstar,
custom objectives, motion-validator overloads and solving remain untested.

## Proposed isolated runtime for review

Recommended: WSL 2 with an Ubuntu 24.04 x86-64 distribution and a separate Linux
checkout. Keep CPython 3.13.13 and pin OMPL 2.0.1. Run the complete research
backend in Linux; keep the existing Windows frontend and use its existing HTTP
connection to the backend. This avoids introducing a new remote worker protocol.
The Part 2 Python core remains independent of HTTP; CLI/API/UI ABIT* selectors
remain Part 3 scope.

Installing/enabling WSL may require administrator access, virtualization support,
a reboot and distribution download. Those host changes have not been authorized
as part of this proposal. Do not copy or reuse the Windows `.venv` in Linux.
Use a separate checkout/venv, leave saved source snapshots unchanged, and use
task-specific result directories. Check localhost connectivity when running
the API later; no public listener is required.

After approval:

1. Enable/install WSL 2 and Ubuntu 24.04 if available on this host. If host
   capabilities prevent that, report the failure and review another runtime;
   do not silently switch deployment architecture.
2. Install a pinned Linux uv toolchain and CPython 3.13.13 in that distribution,
   create an isolated checkout, and install the existing locked backend.
3. Use a disposable Linux probe environment to install `ompl==2.0.1`. Verify
   `ompl.base`, `ompl.geometric` and `geometric.ABITstar`; execute real custom
   objective and both motion-validation callback forms before adding the
   dependency to the project. An import-only probe is insufficient.
4. Add a pinned optional ABIT* extra and regenerate the lockfile only after
   callback validation succeeds. Existing Windows distance/weighted graph
   planners retain their current environment. Selecting unavailable ABIT*
   returns an explicit diagnostic; it never substitutes another algorithm.
5. Create and assign the Part 2 issue to Milestone 6 before creating its feature
   branch from synchronized `iteration/006`. No feature branch was created
   during this dependency-gate investigation.
6. Implement the adapter with independent task instances, shared metric risk and
   full-motion checks, conservative admissible cost-to-go, bounded planning,
   cooperative cancellation, structured outcomes and final revalidation.
7. Run actual ABIT* tests in Linux CI with the optional extra; retain the existing
   Windows/Linux baseline tests. Test unavailable-planner behavior on Windows.

## Required evidence before Part 2 acceptance

- Real callback execution, including last-valid motion-validator overload;
  callbacks must use Part 1 metric costs and complete buffered geometry checks.
- Fully checked exact routes on controlled open/detour fixtures; independent
  recomputation of physical length, risk cost and weighted objective.
- Approximate, timeout, invalid endpoints, unresolved input, cancellation and
  computation-failure outcomes; timeout is not proof of infeasibility.
- Total planning budget, measured setup/solve durations and documented
  cooperative cancellation granularity. No claim of a hard process deadline.
- Concurrent task isolation and optional task-specific diagnostics; no required
  graph_tool, global path.txt or graph.graphml.

No adapter, OMPL dependency, custom runtime installation, new acquisition or
Part 3 controls have been implemented. The next decision is approval of the
isolated Linux runtime, followed by actual callback validation.
