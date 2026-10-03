# Pinned native Windows OMPL build

`ompl-2.0.1+uas.1-cp313-cp313-win_amd64.whl` is a locally patched build of
official OMPL 2.0.1 for Windows x64 CPython 3.13. It is optional, installed by
`uv sync --project backend --locked --extra ompl-windows`. No compiler is needed
to install it. Its Boost serialization DLL is included; Windows MSVC runtime
libraries must be available. It is not a stock upstream/PyPI binary.

[build-info.json](build-info.json) records the artifact and patch SHA-256,
upstream/submodule/vcpkg commits and tool/dependency versions. `backend/uv.lock`
also pins the artifact hash. Licenses accompany the wheel and are included inside
it. No upstream C++ planning algorithm was rewritten.

The [complete patch](../../doc/iteration/iteration-006/windows-probe/ompl-2.0.1-uas.1.patch)
adds ABITstar registration, repairs conservative last-valid outputs, enables
Python cost-to-go conversion and fixes MSVC portability and runtime packaging.
It assigns local version `2.0.1+uas.1`, omits the unused static `.lib` from the
wheel and includes licenses. The wheel is about 4.7 MB; build headers/static
archives remain in the isolated build, not in this runtime package.

To reproduce, follow the [verified source/tool preparation](../../doc/iteration/iteration-006/part2-windows-verification.md),
apply this complete patch to the pinned checkout with `git apply`, copy the saved
`build.py` and `wheel.py` into the prepared probe root, then run
`.venv/Scripts/python.exe -X utf8 build.py wheel`. Configure the vcvars path in
`build.py` for the host. The official pinned Nanobind submodule supplies the C++
binding headers. Build timestamps can change the resulting zip hash; a rebuilt
artifact requires explicit hash review and lock regeneration.

Validated on the development Windows host, including a new virtual environment;
a separate clean Windows host and Linux ABIT* runtime remain unverified. CI is
configured to install this extra on Windows, retain graph tests on Linux and
run actual native planner tests when the extension is present.
