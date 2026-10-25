"""Run Part 3 against isolated real-data services; never reuse user service ports."""

import argparse
import json
import os
import runpy
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--api-port", type=int, default=8022)
    parser.add_argument("--ui-port", type=int, default=5192)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    for port in (args.api_port, args.ui_port):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))
    # Reuse the established hidden-launch/owned-tree-cleanup helpers only.
    helpers = runpy.run_path(
        str(ROOT / "doc/experiments/iteration-012/verify-part4.py")
    )
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "UAS_API_URL": f"http://127.0.0.1:{args.api_port}",
        "UAS_UI_URL": f"http://127.0.0.1:{args.ui_port}",
    }
    processes, logs = [], []
    try:
        for name, command, url in (
            (
                "backend",
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "uas_planner.api.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.api_port),
                ],
                env["UAS_API_URL"] + "/api/health",
            ),
            (
                "frontend",
                [
                    "node",
                    "frontend/node_modules/vite/bin/vite.js",
                    "preview",
                    "frontend",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.ui_port),
                ],
                env["UAS_UI_URL"],
            ),
        ):
            log = (output / f"{name}.log").open("w", encoding="utf-8")
            logs.append(log)
            process = helpers["launch"](command, log, env)
            processes.append(process)
            helpers["ready"](url, process)
        browser = helpers["launch"](
            ["node", "doc/experiments/iteration-013/verify-part3.mjs", str(output)],
            sys.stdout,
            env,
        )
        processes.append(browser)
        if browser.wait(timeout=900) != 0:
            raise RuntimeError("Real browser acceptance failed; see local evidence.")
    finally:
        for process in reversed(processes):
            helpers["stop"](process)
        for log in logs:
            log.close()
        (output / "services.json").write_text(
            json.dumps(
                {"owned_services_stopped": all(p.poll() is not None for p in processes)}
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
