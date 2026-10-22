"""Automatic loading bounds actual preparation, not only browser HTTP consumers."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace

from fastapi.testclient import TestClient

from uas_planner.api.app import create_app
from uas_planner.core import regional


def test_parallel_scenario_preparation_is_rejected_and_slot_reopens(tmp_path, monkeypatch):
    (tmp_path / "study").mkdir()
    entered, finish = Event(), Event()
    calls, closed = [], []

    def model(*args, **kwargs):
        calls.append(args)
        entered.set()
        assert finish.wait(10)
        return SimpleNamespace(terrain=SimpleNamespace(close=lambda: closed.append(True)))

    monkeypatch.setattr(regional, "RegionalConstraints", model)
    monkeypatch.setattr(regional, "constraint_layers", lambda *args: {"verified_fixture": True})
    with TestClient(create_app(tmp_path)) as client, ThreadPoolExecutor() as pool:
        body = {"scenario": {}, "planning_mode": "conservative"}
        first = pool.submit(client.post, "/api/datasets/study/study/layers/constraints", json=body)
        try:
            assert entered.wait(10)
            rejected = client.post("/api/datasets/study/study/layers/constraints", json=body)
            assert rejected.status_code == 503
            assert "already preparing" in rejected.json()["detail"]
            assert len(calls) == 1
        finally:
            finish.set()
        assert first.result(timeout=10).status_code == 200
        assert (
            client.post("/api/datasets/study/study/layers/constraints", json=body).status_code
            == 200
        )
        assert len(calls) == len(closed) == 2


def test_failed_scenario_preparation_releases_slot(tmp_path, monkeypatch):
    (tmp_path / "study").mkdir()
    closed = []
    monkeypatch.setattr(
        regional,
        "RegionalConstraints",
        lambda *args, **kwargs: SimpleNamespace(
            terrain=SimpleNamespace(close=lambda: closed.append(True))
        ),
    )

    def invalid(*args):
        raise ValueError("Cannot prepare this scenario")

    monkeypatch.setattr(regional, "constraint_layers", invalid)
    with TestClient(create_app(tmp_path)) as client:
        url = "/api/datasets/study/study/layers/constraints"
        assert client.post(url, json={"scenario": {}}).status_code == 422
        monkeypatch.setattr(regional, "constraint_layers", lambda *args: {})
        assert client.post(url, json={"scenario": {}}).status_code == 200
        assert len(closed) == 2
        assert client.post(url, json={"scenario": {}, "unexpected": 1}).status_code == 422
        assert client.post(url, json={"scenario": {}}).status_code == 200
