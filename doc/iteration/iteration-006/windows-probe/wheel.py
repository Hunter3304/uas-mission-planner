"""Build a CPython 3.13 Windows wheel from the pinned, patched official source."""
import os
from pathlib import Path
from scikit_build_core.build import build_wheel

root = Path(__file__).resolve().parent
os.chdir(root / "source/py-bindings")
definitions = {
    "OMPL_BUILD_VAMP": "OFF", "OMPL_BUILD_PYTHON_BINDINGS": "ON",
    "OMPL_BUILD_DEMOS": "OFF", "OMPL_BUILD_TESTS": "OFF",
    "VCPKG_TARGET_TRIPLET": "x64-windows", "VCPKG_MANIFEST_MODE": "OFF",
    "VCPKG_MANIFEST_INSTALL": "OFF", "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
    "CMAKE_TOOLCHAIN_FILE": str(root / "vcpkg/scripts/buildsystems/vcpkg.cmake"),
    "VCPKG_INSTALLED_DIR": str(root / "dependencies"),
    "CMAKE_MAKE_PROGRAM": str(root / ".venv/Scripts/ninja.exe"),
}
settings = {"build-dir": str(root / "build-msvc-release"), "build.tool-args": "-j4"}
settings.update({f"cmake.define.{key}": value for key, value in definitions.items()})
print(build_wheel(str(root / "wheels"), config_settings=settings))
