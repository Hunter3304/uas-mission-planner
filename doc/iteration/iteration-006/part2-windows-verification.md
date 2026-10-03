# Part 2 — Official OMPL native Windows verification

Date: 2026-10-01 (Europe/Berlin).
Status: native Windows dependency gate passed. MSVC/SDK and dependencies built;
official C++ core and patched Python extension compiled; local wheel installed
offline in a new environment and actual ABIT* callback/path probes passed.
This document records the dependency gate. The subsequently implemented adapter
and local Part 2 acceptance are recorded in [Part 2 feedback](part2.md);
publication/integration remain pending.

## Current decision

User explicitly deferred native Python ABIT* reimplementation and requested:
revise the plan, then verify official OMPL on Windows. No Linux/WSL/Docker
runtime is selected. Keep Python 3.13 and existing Part 1 costs/constraints.
The Python survey and prior Linux proposal are historical evidence only.

## Isolated preparation

Probe root: `D:/Aostfalia/tmp/ompl-windows-probe`.
No project dependency or backend virtual environment was changed.

- Official OMPL tag `2.0.1`, commit
  `c509861210a63ec962bbec72c52823abc16b102e`.
- Nanobind source submodule:
  `c5a3a378aa61d104c82ca053cb1e367782cd3618`.
- Its robin-map submodule:
  `4ec1bf19c6a96125ea22062f38c2cf5b958e448e`.
- Probe interpreter: Windows x64 CPython 3.13.13. Existing interpreter includes
  `include/Python.h` and `libs/python313.lib`.
- Probe-only build helpers installed: CMake 4.4.3, Ninja 1.13.2,
  scikit-build-core 1.1.0, nanobind 3.1.0, packaging 26.3, pathspec 1.1.1.
  CMake uses the pinned Nanobind source submodule, not necessarily the helper
  package version. uv cache resides under the probe root.
- VAMP disabled for this initial baseline; no robotics acceleration dependency
  is needed for the shared Shapely geometry callbacks.

## Actual preflight results

No MSVC/clang-cl/GCC, CMake/Ninja/vcpkg were found initially in PATH; no Visual
Studio installation or Windows SDK entry was found in the checked standard
locations/registry. Then isolated CMake/Ninja were installed and executed.

### Visual Studio generator

```powershell
& 'D:\Aostfalia\tmp\ompl-windows-probe\.venv\Scripts\cmake.exe' -S D:\Aostfalia\tmp\ompl-windows-probe\source -B D:\Aostfalia\tmp\ompl-windows-probe\build-msvc -G 'Visual Studio 17 2022' -A x64 -DOMPL_BUILD_VAMP=OFF -DOMPL_BUILD_PYTHON_BINDINGS=ON -DOMPL_BUILD_DEMOS=OFF -DOMPL_BUILD_TESTS=OFF '-DPython_EXECUTABLE=D:/Aostfalia/tmp/ompl-windows-probe/.venv/Scripts/python.exe'
```

Exit 1: `could not find any instance of Visual Studio`.
Full log: `D:/Aostfalia/tmp/ompl-windows-probe/configure-msvc.log`.

### Ninja generator

```powershell
& 'D:\Aostfalia\tmp\ompl-windows-probe\.venv\Scripts\cmake.exe' -S D:\Aostfalia\tmp\ompl-windows-probe\source -B D:\Aostfalia\tmp\ompl-windows-probe\build-ninja -G Ninja '-DCMAKE_MAKE_PROGRAM=D:/Aostfalia/tmp/ompl-windows-probe/.venv/Scripts/ninja.exe' -DOMPL_BUILD_VAMP=OFF -DOMPL_BUILD_PYTHON_BINDINGS=ON -DOMPL_BUILD_DEMOS=OFF -DOMPL_BUILD_TESTS=OFF '-DPython_EXECUTABLE=D:/Aostfalia/tmp/ompl-windows-probe/.venv/Scripts/python.exe'
```

Exit 1: `No CMAKE_CXX_COMPILER could be found`.
Full log: `D:/Aostfalia/tmp/ompl-windows-probe/configure-ninja.log`.
These are missing prerequisites, not evidence that OMPL cannot compile on Windows.

## Binding audit before compilation

The pinned official source contains
`src/ompl/geometric/planners/informedtrees/ABITstar.h` and its C++ implementation.
However, `py-bindings/geometric/init.h`, `py-bindings/python.cpp`, and the planner
binding sources register BITstar but not ABITstar. The checked official main
tree (`5b209a03fe48c41f7a2f364382c2e425bf1c7c1c`) likewise has no separate ABITstar
binding file; the release source is the authoritative audit target here.

The minimal expected remedy is a Nanobind class wrapper deriving from the
already registered BITstar, exposing the official ABITstar constructor and
inflation/truncation settings, and registering it after BITstar. This exposes
the official C++ algorithm; it does not reimplement its search in Python.
The patches described below have now been compiled and runtime-tested.

Also, `py-bindings/base/MotionValidator.cpp` forwards the three-argument
last-valid overload to the two-argument callback without populating lastValid.
The overload contract must be verified/repaired before claiming full callback
compatibility. Successful import alone cannot satisfy this gate.

Official references:
[build configuration](https://github.com/ompl/ompl/blob/2.0.1/CMakeLists.txt),
[dependencies](https://github.com/ompl/ompl/blob/2.0.1/CMakeModules/OMPLDependencies.cmake),
[Python package build](https://github.com/ompl/ompl/blob/2.0.1/py-bindings/pyproject.toml),
[binding regression report](https://github.com/ompl/ompl/issues/1419).

## Concrete compiler prerequisite

Microsoft's Visual Studio 2022 Build Tools installer was downloaded from
`https://aka.ms/vs/17/release/vs_BuildTools.exe` to
`D:/Aostfalia/tmp/ompl-windows-probe/vs_BuildTools.exe`.
Authenticode: Valid, signer Microsoft Corporation.
SHA-256: `985969f472caad75d993a5cb4c35a6a4271460cc12b343e2433b994d173aa990`.

Current execution token is not an administrator. The user explicitly approved
installation of compiler tools and continuation. Launched the verified installer
with UAC elevation; it returned exit code 0. No automatic reboot occurred.
Installed VS Build Tools 2022 version 17.14.37710.0 (17.14.41), MSVC
14.44.35207, and Windows SDK 10.0.26100.0. vcpkg detects the x64 compiler.

Installed components, without the full Visual Studio IDE:

- `Microsoft.VisualStudio.Workload.VCTools` (required workload components).
- `Microsoft.VisualStudio.Component.VC.Tools.x86.x64`.
- `Microsoft.VisualStudio.Component.Windows11SDK.26100`.

Installation command (already executed after explicit approval, with RunAs
elevation on Start-Process):

```powershell
$installArgs = @('--quiet', '--wait', '--norestart', '--nocache', '--installPath', 'D:\Aostfalia\app\VSBuildTools2022', '--add', 'Microsoft.VisualStudio.Workload.VCTools', '--add', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '--add', 'Microsoft.VisualStudio.Component.Windows11SDK.26100')
$installProcess = Start-Process -FilePath 'D:\Aostfalia\tmp\ompl-windows-probe\vs_BuildTools.exe' -ArgumentList $installArgs -Verb RunAs -WindowStyle Hidden -Wait -PassThru
$installProcess.ExitCode
```

This is a system-level installation, even with the main installation directory
on D:. Shared installer/SDK components may reside on C:. It requires network
downloads and several GB of storage; the measured free space was 43.3 GB on C:
and 339.2 GB on D:. `--norestart` prevents an automatic reboot; handle any returned
restart-required status explicitly. Recheck the executable signature immediately
before launch.

Microsoft references:
[command-line tools](https://learn.microsoft.com/en-us/cpp/build/building-on-the-command-line?view=msvc-170),
[component identifiers](https://learn.microsoft.com/en-us/visualstudio/install/workload-component-id-vs-build-tools?view=vs-2022).

## Verified build and runtime result

The CMake configure and build now succeed with Ninja/MSVC, Release, Windows
x64 CPython 3.13.13, static OMPL, VAMP/demos/tests disabled. vcpkg is pinned to
`eb2d3a3279fd019cb7733072d86900d0ad2a1aef`; dependencies are installed under
the isolated probe's `dependencies/x64-windows`: Boost 1.92.0 and Eigen 5.0.1.
Boost math, graph and odeint were added after the first compile identified the
missing `boost/math/special_functions/prime.hpp`. Boost serialization and
program-options alone were insufficient.

The [recorded patch](windows-probe/ompl-2.0.1-windows-abit.patch) makes these
changes to official 2.0.1, without changing the C++ search algorithm:

- Register ABITstar after BITstar and expose its inflation/truncation settings.
- Repair the motion-validator overload conservatively: failure reports the
  valid start at fraction zero; success leaves last-valid output unchanged.
  Add a callable overload probe, including null output.
- Restrict `-Wno-unused-parameter` to non-MSVC compilers; include `<string>` for
  `std::to_string`; use Nanobind's portable `nb::ssize_t` for slices.
- Include Nanobind's function converter so `setCostToGoHeuristic` accepts a
  Python callback. Its absence caused an actual TypeError before the fix.
- Install runtime DLL dependencies into the wheel. Initial wheel omitted the
  Boost serialization DLL; final wheel includes it.

Normalize Windows environment-variable names before calling vcvars64.bat;
otherwise inherited `Path` can overwrite its uppercase `PATH`. Disable vcpkg
manifest installation and explicitly point to existing dependencies/downloads
and Ninja. The source manifest initially triggered a second network download.
The Nanobind `STABLE_ABI` option was left unchanged; the actual Windows artifact
is CPython-specific `cp313-cp313-win_amd64`, not an abi3 wheel.

Saved scripts: [build](windows-probe/build.py), [wheel](windows-probe/wheel.py),
[runtime probe](windows-probe/probe.py), [result](windows-probe/probe-result.json),
and [artifact location / SHA256](windows-probe/wheel-artifact.json).
Scripts expect to reside in the probe root alongside `source`, `.venv`,
`vcpkg` and `dependencies`; the vcvars path is this machine's installation.
Reproduction requires the recorded source/submodule pins and patch, not a
stock PyPI package or unpatched OMPL checkout.

Executed from `D:/Aostfalia/tmp/ompl-windows-probe` after dependency preparation:

```powershell
uv pip install --python .venv/Scripts/python.exe --cache-dir uv-cache cmake==4.4.3 ninja==1.13.2 scikit-build-core==1.1.0 nanobind==3.1.0 packaging==26.3 pathspec==1.1.1
$env:VCPKG_DOWNLOADS = "$PWD/downloads"
$env:VCPKG_DISABLE_METRICS = '1'
./vcpkg/vcpkg.exe install boost-serialization:x64-windows boost-program-options:x64-windows boost-math:x64-windows boost-graph:x64-windows boost-odeint:x64-windows eigen3:x64-windows --x-install-root="$PWD/dependencies" --disable-metrics
./.venv/Scripts/python.exe -X utf8 build.py configure
./.venv/Scripts/python.exe -X utf8 build.py compile
./.venv/Scripts/python.exe -X utf8 build.py wheel
uv venv wheel-test --python 'D:/Aostfalia/app/Python 3.13/python.exe' --cache-dir uv-cache
uv pip install --python wheel-test/Scripts/python.exe --offline --no-deps --cache-dir uv-cache wheels/ompl-2.0.1-cp313-cp313-win_amd64.whl
$env:PYTHONPATH = 'D:/Aostfalia/develop/uas-mission-planner/backend/src;D:/Aostfalia/develop/uas-mission-planner/backend/.venv/Lib/site-packages'
./wheel-test/Scripts/python.exe -X utf8 probe.py
```

The last command uses the installed wheel and existing backend geospatial
dependencies, without modifying that backend environment. Exit code 0.
Build logs remain under the probe root: `build-configure.log`,
`build-compile.log`, `build-wheel.log`, `dependencies.log`,
`dependencies-extra.log`, `wheel-probe.log`.

Final installed-wheel fixture: 3.000334 s deadline-limited solve returned
`Exact solution` through `kABITstar` (official default k-nearest naming).
121.853865 m path, independently recomputed objective 12.18538648; all segments
passed shared and independent Shapely checks with 1 m clearance. The planner
avoided the scored building, so the final path's risk contribution is zero.
The separate analytical segment test verifies nonzero risk: 20 m at score 4
plus 100 m length gives `0.9 * 80 + 0.1 * 100 = 82`; heuristic is 10.
State, motion, cost, motion heuristic, cost-to-go and termination callbacks
were executed. Last-valid failure/success/null cases passed. Immediate
cancellation returned no exact path in 0.000084 s; OMPL labels it `Timeout`,
so the future application adapter must distinguish cancellation itself.
Timing-based sampling can vary between runs; these figures do not establish
optimality or reproduce all results of the thesis.

The wheel includes Boost's serialization runtime DLL. This was tested in a
fresh virtual environment on the same Windows host; a separate clean Windows
machine and Linux runtime have not been tested. The wheel is a local patched
build, not an unmodified official binary or published release.

## Remaining acceptance

Native Windows compilation, wheel installation and controlled runtime probes
are complete. Integrate the adapter, pin the patched dependency, distinguish
application outcomes and exercise concurrent independent tasks before claiming
Part 2 delivery. README includes the verified additional dependencies.

Application-level regression coverage remains required; the isolated probe
does not establish application integration or production cancellation behavior.

Application implementation, Part 2 acceptance and publication remain outstanding.
No WSL/Docker setup, real-data acquisition, native Python algorithm or Part 3
controls were introduced. Existing unrelated HANDOFF edits are preserved.
