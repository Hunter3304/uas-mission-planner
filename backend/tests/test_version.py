import json
import tomllib
from pathlib import Path

from uas_planner import __version__
from uas_planner.api.app import create_app


def test_release_versions_agree():
    root = Path(__file__).resolve().parents[2]
    backend = tomllib.loads((root / "backend/pyproject.toml").read_text())
    frontend = json.loads((root / "frontend/package.json").read_text())
    lock = json.loads((root / "frontend/package-lock.json").read_text())
    assert backend["project"]["version"] == frontend["version"] == __version__
    assert lock["version"] == lock["packages"][""]["version"] == __version__
    assert create_app().openapi()["info"]["version"] == __version__
