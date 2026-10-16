"""Bounded official OFM files; immutable snapshots are rebuilt offline."""

import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from uas_planner.core.ofm import import_snapshot, load_snapshot, publication


def official_url(url):
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "snapshots.openflightmaps.org"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        raise ValueError("OFM downloads require the official HTTPS snapshots host.")
    return url


def download(url, target, limit):
    started = time.monotonic()
    requested = official_url(url)
    for _ in range(4):
        with requests.get(
            official_url(url),
            stream=True,
            timeout=(10, 30),
            allow_redirects=False,
            headers={"User-Agent": "UAS-Mission-Planner/OFM-research"},
        ) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["Location"])
                continue
            response.raise_for_status()
            size = 0
            with Path(target).open("xb") as stream:
                for block in response.iter_content(65536):
                    size += len(block)
                    if size > limit or time.monotonic() - started > 120:
                        raise ValueError("OFM download exceeds byte/time limit.")
                    stream.write(block)
            return {
                "request_url": requested,
                "response_url": url,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "bytes": size,
                "headers": {
                    k: response.headers.get(k) for k in ("Content-Type", "Last-Modified", "ETag")
                },
            }
    raise ValueError("Too many OFM redirects.")


def acquire_ofm(cycle, output, *, region=None):
    if Path(output).exists():
        raise FileExistsError("Choose a new OFM snapshot output.")
    # Validate before constructing a provider URL.
    if len(cycle) != 4 or not cycle.isascii() or not cycle.isdigit():
        raise ValueError("AIRAC must contain four ASCII digits.")
    url = f"https://snapshots.openflightmaps.org/publicationServices/ED_{cycle}.xml"
    with tempfile.TemporaryDirectory(prefix="uas-ofm-") as temporary:
        root = Path(temporary)
        index = root / "publication.xml"
        index_receipt = download(url, index, 2 * 1024 * 1024)
        catalog = publication(index.read_bytes(), cycle)
        archive = root / "source.zip"
        archive_receipt = download(catalog["product"]["URL"], archive, 30 * 1024 * 1024)
        return import_snapshot(
            archive,
            index,
            output,
            cycle=cycle,
            region=region,
            receipts={"publication": index_receipt, "archive": archive_receipt},
        )


def rebuild_ofm(directory, output):
    manifest = load_snapshot(directory)
    directory = Path(directory)
    return import_snapshot(
        directory / "source.zip",
        directory / "publication.xml",
        output,
        cycle=manifest["publication"]["cycle"],
        region=manifest["region"],
        receipts={"method": "offline rebuild", "original_receipts": manifest["receipts"]},
    )
