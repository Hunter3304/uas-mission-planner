"""Build only in the isolated probe; import MSVC's process-local environment."""

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VCVARS = Path(r"D:\Aostfalia\app\VSBuildTools2022\VC\Auxiliary\Build\vcvars64.bat")
result = subprocess.run(
    f'cmd.exe /d /s /c "call "{VCVARS}" >nul && set"',
    capture_output=True, text=True, check=True,
    env={key.upper(): value for key, value in os.environ.items()},
)
environment = {key.upper(): value for key, value in os.environ.items()}
for line in result.stdout.splitlines():
    key, separator, value = line.partition("=")
    if separator and key and not key.startswith("="):
        environment[key.upper()] = value
environment["PATH"] = str(ROOT / ".venv" / "Scripts") + os.pathsep + environment["PATH"]
environment["VCPKG_DOWNLOADS"] = str(ROOT / "downloads")
environment["VSLANG"] = "1033"
cmake = ROOT / ".venv" / "Scripts" / "cmake.exe"
build = ROOT / "build-msvc-release"
if len(sys.argv) == 1 or sys.argv[1] == "configure":
    command = [str(cmake), "-S", str(ROOT / "source"), "-B", str(build), "-G", "Ninja",
               "-DCMAKE_BUILD_TYPE=Release", "-DOMPL_BUILD_VAMP=OFF",
               "-DOMPL_BUILD_PYTHON_BINDINGS=ON", "-DOMPL_BUILD_DEMOS=OFF",
               "-DOMPL_BUILD_TESTS=OFF", "-DVCPKG_TARGET_TRIPLET=x64-windows",
               "-DVCPKG_MANIFEST_MODE=OFF", "-DVCPKG_MANIFEST_INSTALL=OFF",
               f"-DCMAKE_MAKE_PROGRAM={ROOT / '.venv/Scripts/ninja.exe'}",
               "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
               f"-DCMAKE_TOOLCHAIN_FILE={ROOT / 'vcpkg/scripts/buildsystems/vcpkg.cmake'}",
               f"-DVCPKG_INSTALLED_DIR={ROOT / 'dependencies'}",
               f"-DPython_EXECUTABLE={ROOT / '.venv/Scripts/python.exe'}",
               f"-DCMAKE_INSTALL_PREFIX={ROOT / '.venv/Lib/site-packages'}",
               "-DOMPL_PYTHON_INSTALL_PREFIX=."]
elif sys.argv[1] == "compile":
    command = [str(cmake), "--build", str(build), "--target", "_ompl", "--parallel", "4"]
elif sys.argv[1] == "install":
    command = [str(cmake), "--install", str(build)]
elif sys.argv[1] == "wheel":
    command = [str(ROOT / '.venv/Scripts/python.exe'), str(ROOT / 'wheel.py')]
else:
    raise SystemExit("Expected configure, compile, install or wheel")
with (ROOT / f"build-{sys.argv[1] if len(sys.argv) > 1 else 'configure'}.log").open("w", encoding="utf-8") as log:
    process = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, errors="replace")
    for line in process.stdout:
        if "including file:" not in line and "包含文件:" not in line:
            print(line, end="", flush=True)
        log.write(line)
    raise SystemExit(process.wait())
