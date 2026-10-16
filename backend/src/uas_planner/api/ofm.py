"""Read-only independent OFM API and standalone preview."""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from uas_planner.core.ofm import ID, load_snapshot, read


def router(root):
    api = APIRouter()
    collection = Path(root) / ".ofm"

    def snapshot(ident):
        if not ID.fullmatch(ident):
            raise HTTPException(404, "OFM snapshot not found.")
        path = collection / ident
        if (
            collection.is_symlink()
            or path.is_symlink()
            or not collection.resolve().is_relative_to(Path(root).resolve())
            or not path.resolve().is_relative_to(collection.resolve())
            or not path.is_dir()
        ):
            raise HTTPException(404, "OFM snapshot not found.")
        try:
            return path, load_snapshot(path)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            raise HTTPException(422, "OFM snapshot cannot be verified.") from exc

    @api.get("/ofm")
    def preview():
        return FileResponse(
            Path(__file__).with_name("ofm_preview.html"),
            media_type="text/html",
            headers={
                "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
            },
        )

    @api.get("/api/ofm/snapshots")
    def snapshots():
        items = []
        if collection.is_dir() and not collection.is_symlink():
            for entry in sorted(collection.iterdir()):
                if not entry.is_dir() or not ID.fullmatch(entry.name) or entry.is_symlink():
                    continue
                try:
                    _, manifest = snapshot(entry.name)
                    items.append({"id": entry.name, "verified": True, **manifest})
                except HTTPException:
                    items.append(
                        {
                            "id": entry.name,
                            "verified": False,
                            "error": "Snapshot verification failed.",
                        }
                    )
        return {"snapshots": items}

    @api.get("/api/ofm/snapshots/{ident}")
    def metadata(ident: str):
        _, manifest = snapshot(ident)
        return {"id": ident, **manifest}

    @api.get("/api/ofm/snapshots/{ident}/features")
    def features(ident: str, layer: Literal["airspaces", "aerodromes"] = "airspaces"):
        path, manifest = snapshot(ident)
        return {
            **read(path / f"{layer}.geojson"),
            "provenance": {
                "snapshot_id": ident,
                "source": "OpenFlightMaps",
                "source_sha256": manifest["files"]["source.zip"],
                "publication": manifest["publication"],
                "source_xml": manifest["source_xml"],
                "region_id": manifest["region"]["region_id"],
                "license": manifest["license"],
                "geometry_policy": manifest["geometry_policy"],
            },
        }

    @api.get("/api/ofm/snapshots/{ident}/features/{feature_id}")
    def detail(ident: str, feature_id: str):
        path, _ = snapshot(ident)
        item = read(path / "details.json").get(feature_id)
        if item is None:
            raise HTTPException(404, "OFM feature not found.")
        return item

    @api.get("/api/ofm/snapshots/{ident}/diagnostics")
    def diagnostics(ident: str):
        path, manifest = snapshot(ident)
        return {"coverage": manifest["coverage"], "diagnostics": read(path / "diagnostics.json")}

    @api.get("/api/ofm/snapshots/{ident}/preview")
    def offline_preview(ident: str):
        from uas_planner.core.ofm_preview import preview_html

        path, _ = snapshot(ident)
        return HTMLResponse(
            preview_html(path),
            headers={"Content-Disposition": f'attachment; filename="{ident}-preview.html"'},
        )

    return api
