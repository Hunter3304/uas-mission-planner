"""Isolated real API for Playwright; invoked only by the smoke-test configuration."""

from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

from uas_planner.api.app import create_app
from uas_planner.cli import main

if __name__ == "__main__":
    cache = Path(__file__).resolve().parents[2] / ".cache"
    cache.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="smoke-", dir=cache) as directory:
        root = Path(directory)
        if main(["sample", "--output", str(root / "offline-sample")]) != 0:
            raise SystemExit("Could not prepare the smoke sample")
        uvicorn.run(create_app(root), host="127.0.0.1", port=8011)
