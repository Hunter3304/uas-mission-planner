"""Bounded official temporary-layer snapshot and original notice receipts."""

import json
from pathlib import Path
from urllib.parse import urlparse

from uas_planner.acquisition.study import PayloadStore, fetch_dipul
from uas_planner.core.area import StudyRegion
from uas_planner.core.experiment import read_json
from uas_planner.core.restrictions import OFFICIAL_HOSTS


def acquire_restrictions(bounds, output, notice_urls=()):
    if len(notice_urls) > 10:
        raise ValueError("At most ten official notice URLs per snapshot.")
    for url in notice_urls:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS or parsed.username:
            raise ValueError("Only official HTTPS notice URLs are accepted.")
    area = StudyRegion(*bounds)
    config = {
        "dipul_url": "https://uas-betrieb.de/geoservices/dipul/ows",
        "dipul_layers": ["dipul:temporaere_betriebseinschraenkungen"],
        "bounds": dict(zip(("west", "south", "east", "north"), bounds)),
        "notice_urls": list(notice_urls),
    }
    store = PayloadStore(output, config)
    sources = fetch_dipul(store, area)
    for index, url in enumerate(notice_urls):
        store.fetch(f"official-notice-{index:03d}.html", url)
    result = {
        "schema_version": 1,
        "kind": "temporary-restriction-snapshot",
        "config": config,
        "sources": sources,
        "files": store.files,
        "coverage": "unverified; empty WFS results do not establish NOTAM completeness",
    }
    with (Path(output) / "restrictions.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    notices = []
    for response in sources["responses"]:
        for page in response["pages"]:
            for feature in read_json(Path(output) / page)["features"]:
                receipt = next(item for item in store.files if item["path"] == page)
                notices.append(
                    {
                        "id": f"wfs-{len(notices)}",
                        "reviewed": False,
                        "state": "unresolved",
                        "official_url": config["dipul_url"],
                        "evidence": "",
                        "checked_at": receipt["retrieved_at_utc"],
                        "geometry": feature["geometry"],
                        "properties": feature["properties"],
                        "original_feature_id": feature["id"],
                    }
                )
    template = {
        "schema_version": 1,
        "name": "Review temporary restrictions before use",
        "zone_assessments": {},
        "notices": notices,
        "source_snapshot": result,
    }
    with (Path(output) / "profile-template.json").open("x", encoding="utf-8") as stream:
        json.dump(template, stream, indent=2, allow_nan=False)
    return result
