"""Hand-checkable Part 2 preparation behavior."""

import pytest
from experiment_fixture import create_experiment_fixture

from uas_planner.core.grid import _zone_state, build_grid, validate_cell_size


def test_grid_validation_and_rebuild(tmp_path):
    manifest = create_experiment_fixture(tmp_path / "experiment")
    directory = tmp_path / "experiment"
    coarse = build_grid(directory, manifest, 100)
    fine = build_grid(directory, manifest, 50)
    assert fine["cell_count"] > coarse["cell_count"]
    assert all(cell["state"] == "unresolved" for cell in fine["cells"])
    assert len(fine["connectors"]) == 2
    assert {item["endpoint"] for item in fine["connectors"]} == {"start", "end"}
    assert all(item["length_m"] >= 0 for item in fine["connectors"])
    assert all(item["state"] != "permitted" for item in fine["edges"])
    assert any(cell["population"]["unknown_area_m2"] > 0 for cell in fine["cells"])
    assert any(cell["population"]["estimated_people"] == 0 for cell in fine["cells"])
    # Center elevation cannot prove MSL clearance across a cell or connection.
    assert any(
        "test-zone.42" in reason["source"] for cell in fine["cells"] for reason in cell["reasons"]
    )


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True])
def test_bad_size(value):
    with pytest.raises(ValueError):
        validate_cell_size(value)


def test_vertical_applicability_is_conditional():
    properties = {
        "lower_limit_altitude": 500,
        "lower_limit_unit": "ft",
        "lower_limit_alt_ref": "MSL",
    }
    assert _zone_state(properties, 60, 80)[0] == "permitted"
    assert _zone_state(properties, 100, 80)[0] == "unresolved"
    assert _zone_state(properties, 60, None)[0] == "unresolved"
