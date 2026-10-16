"""Single-file offline preview from verified OFM display derivatives."""

import json
from pathlib import Path

from uas_planner.core.ofm import load_snapshot, read


def preview_html(directory):
    directory = Path(directory)
    manifest = load_snapshot(directory)
    payload = {
        "metadata": {"id": directory.name, **manifest},
        "layers": {
            name: read(directory / f"{name}.geojson") for name in ("airspaces", "aerodromes")
        },
        "diagnostics": read(directory / "diagnostics.json"),
        "details": read(directory / "details.json"),
    }
    # Escaping '<' prevents source text from terminating the inline script element.
    encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
    template = Path(__file__).parents[1] / "api" / "ofm_preview.html"
    return template.read_text(encoding="utf-8").replace("/*OFM_EMBEDDED*/null", encoded)


def export_preview(directory, output):
    text = preview_html(directory)
    with Path(output).open("x", encoding="utf-8") as stream:
        stream.write(text)
