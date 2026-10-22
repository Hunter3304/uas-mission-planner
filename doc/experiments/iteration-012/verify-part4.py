"""Run isolated real-stack Part 4 acceptance; keep sources and existing caches intact.

Requires the installed backend environment, built frontend, Playwright and Chrome.
Use a NEW output directory. No acquisition or external network is required.
"""

import argparse
import ctypes
import json
import os
import platform
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def descendants(pid):
    """Include the real interpreter behind Windows venv's redirector executable."""
    if os.name != "nt":
        return [pid]
    from ctypes import wintypes

    class Entry(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("usage", wintypes.DWORD),
            ("pid", wintypes.DWORD),
            ("heap", ctypes.c_size_t),
            ("module", wintypes.DWORD),
            ("threads", wintypes.DWORD),
            ("parent", wintypes.DWORD),
            ("priority", wintypes.LONG),
            ("flags", wintypes.DWORD),
            ("exe", wintypes.WCHAR * 260),
        ]

    kernel = ctypes.windll.kernel32
    kernel.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = (wintypes.HANDLE, ctypes.POINTER(Entry))
    kernel.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(Entry))
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    parents = {}
    try:
        entry = Entry()
        entry.size = ctypes.sizeof(entry)
        more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            parents[entry.pid] = entry.parent
            more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    found = {pid}
    while True:
        added = {child for child, parent in parents.items() if parent in found} - found
        if not added:
            return sorted(found)
        found.update(added)


def memory(pid):
    if sys.platform != "win32":
        return {"available": False, "reason": "Windows process counters required"}
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "peak_working_set",
                "working_set",
                "peak_paged",
                "paged",
                "peak_nonpaged",
                "nonpaged",
                "pagefile",
                "peak_pagefile",
                "private",
            )
        ]

    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x410, False, pid)
    if not handle:
        return {"available": False, "reason": "Cannot open process"}
    try:
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        fn = ctypes.windll.psapi.GetProcessMemoryInfo
        fn.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
        if not fn(handle, ctypes.byref(counters), counters.cb):
            return {"available": False, "reason": "Counter query failed"}
        return {
            "available": True,
            **{
                name: getattr(counters, name)
                for name in ("working_set", "peak_working_set", "private")
            },
        }
    finally:
        kernel.CloseHandle(handle)


def launch(command, log, env=None):
    return subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=log,
        stderr=subprocess.STDOUT,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def stop(process):
    if process and process.poll() is None:
        # Stop only descendants of this harness-owned process, including venv redirectors.
        if os.name == "nt":
            from ctypes import wintypes

            kernel = ctypes.windll.kernel32
            kernel.OpenProcess.argtypes = (
                wintypes.DWORD,
                wintypes.BOOL,
                wintypes.DWORD,
            )
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
            kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
            for pid in reversed(descendants(process.pid)):
                if pid == process.pid:
                    continue
                handle = kernel.OpenProcess(1, False, pid)
                if handle:
                    try:
                        kernel.TerminateProcess(handle, 0)
                    finally:
                        kernel.CloseHandle(handle)
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def ready(url, process):
    until = time.monotonic() + 40
    while time.monotonic() < until:
        if process.poll() is not None:
            raise RuntimeError(f"Server exited: {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError(f"Server did not become ready: {url}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api-port", type=int, default=8016)
    parser.add_argument("--ui-port", type=int, default=5186)
    parser.add_argument("--skip-prepare", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    for port in (args.api_port, args.ui_port):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))
    env = {**os.environ, "PYTHONUTF8": "1"}
    node = "node"
    processes, samples = {}, []
    done = threading.Event()

    def monitor():
        while not done.wait(0.1):
            for name, process in list(processes.items()):
                if process.poll() is None:
                    counters = [
                        {"pid": pid, **memory(pid)} for pid in descendants(process.pid)
                    ]
                    available = [c for c in counters if c.get("available")]
                    samples.append(
                        {
                            "utc": datetime.now(timezone.utc).isoformat(),
                            "phase": name,
                            "pid": process.pid,
                            "processes": counters,
                            "available": bool(available),
                            **{
                                key: sum(c[key] for c in available)
                                for key in (
                                    "working_set",
                                    "peak_working_set",
                                    "private",
                                )
                            },
                        }
                    )

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    started = time.monotonic()
    logs = []
    try:
        if not args.skip_prepare:
            log = (output / "prepare.log").open("w", encoding="utf-8")
            logs.append(log)
            command = [
                sys.executable,
                "-m",
                "uas_planner.cli",
                "study-osm-prepare",
                "data/hannover-part1-v4",
                "--cache-root",
                str(output / "fresh-display-cache"),
            ]
            prepare = launch(command, log, env)
            processes["preparation"] = prepare
            t = time.monotonic()
            if prepare.wait(timeout=600) != 0:
                raise RuntimeError("Preparation failed; see prepare.log")
            preparation = {
                "wall_s": time.monotonic() - t,
                "command": command,
                "cache": "New derived generation; shared serving cache untouched",
            }
            del processes["preparation"]
        else:
            preparation = {"skipped": True}
        for name, command in (
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
            ),
            (
                "frontend",
                [
                    node,
                    "frontend/node_modules/vite/bin/vite.js",
                    "preview",
                    "frontend",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.ui_port),
                ],
            ),
        ):
            log = (output / f"{name}.log").open("w", encoding="utf-8")
            logs.append(log)
            service_env = {**env, "UAS_API_URL": f"http://127.0.0.1:{args.api_port}"}
            processes[name] = launch(command, log, service_env)
        ready(f"http://127.0.0.1:{args.api_port}/api/health", processes["backend"])
        ready(f"http://127.0.0.1:{args.ui_port}", processes["frontend"])
        log = (output / "browser.log").open("w", encoding="utf-8")
        logs.append(log)
        browser_env = {
            **env,
            "UAS_API_URL": f"http://127.0.0.1:{args.api_port}",
            "UAS_UI_URL": f"http://127.0.0.1:{args.ui_port}",
        }
        processes["browser_driver"] = launch(
            [node, "doc/experiments/iteration-012/verify-part4.mjs", str(output)],
            log,
            browser_env,
        )
        if processes["browser_driver"].wait(timeout=1800) != 0:
            raise RuntimeError(
                "Browser acceptance failed; see browser.log and partial evidence"
            )
    finally:
        done.set()
        thread.join(timeout=2)
        for process in processes.values():
            stop(process)
        for log in logs:
            log.close()
        peaks = {}
        for phase in {sample["phase"] for sample in samples}:
            rows = [s for s in samples if s["phase"] == phase and s.get("available")]
            peaks[phase] = {
                "samples": len(rows),
                **{
                    key: max((r[key] for r in rows), default=None)
                    for key in ("working_set", "peak_working_set", "private")
                },
            }
        result = {
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
            "python": platform.python_version(),
            "wall_s": time.monotonic() - started,
            "preparation": locals().get("preparation"),
            "memory_peaks": peaks,
            "sampling_interval_s": 0.1,
            "limitations": "Private memory is sampled; working-set peak is an OS counter. "
            "Browser JS heap/DOM are measured separately through Chrome DevTools. "
            "New processes and new preparation cache; OS disk cache is not flushed.",
        }
        browser_path = output / "browser-evidence.json"
        if browser_path.is_file():
            browser_evidence = json.loads(browser_path.read_text(encoding="utf-8"))
            result["browser_passed"] = browser_evidence.get("passed", False)
            markers = browser_evidence.get("phase_times", [])
            by_phase = {}
            for first, last in pairwise(markers):
                first_time = datetime.fromisoformat(first["utc"].replace("Z", "+00:00"))
                last_time = datetime.fromisoformat(last["utc"].replace("Z", "+00:00"))
                by_phase[first["name"]] = {}
                for process_name in ("backend", "browser_driver"):
                    rows = [
                        s
                        for s in samples
                        if s["phase"] == process_name
                        and s.get("available")
                        and first_time <= datetime.fromisoformat(s["utc"]) < last_time
                    ]
                    by_phase[first["name"]][process_name] = {
                        "samples": len(rows),
                        **{
                            key: max((s[key] for s in rows), default=None)
                            for key in ("working_set", "private")
                        },
                    }
            result["sampled_memory_by_browser_phase"] = by_phase
        (output / "process-evidence.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        (output / "memory-samples.json").write_text(
            json.dumps(samples), encoding="utf-8"
        )
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
