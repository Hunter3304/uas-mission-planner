"""Official OMPL continuous ABIT* with task-local state and cooperative limits."""

from copy import deepcopy
from math import hypot, isclose, isfinite
from time import perf_counter
from weakref import proxy

from pyproj import Transformer

from uas_planner.core.risk import nonnegative
from uas_planner.core.routing import constraint_checker


class _Stopped(Exception):
    pass


def _load_ompl():
    # Optional dependency: graph routing remains usable without the native extension.
    from ompl import base, geometric

    if not hasattr(geometric, "ABITstar"):
        raise ImportError("OMPL lacks ABITstar; install the documented patched build.")
    return base, geometric


class AbitPlanner:
    """One search per instance. Do not mutate the supplied risk model during a run.

    Budgets include preparation when started_at is supplied by the saved-data
    entry point. Native callbacks and setup are cooperative, not forcibly killed.
    Final validation always runs before releasing an exact route.
    """

    def __init__(
        self,
        grid,
        risk_model,
        endpoints,
        *,
        time_budget_s=3,
        cancel=None,
        started_at=None,
        samples_per_batch=100,
    ):
        self.started = perf_counter() if started_at is None else started_at
        self.budget = nonnegative(time_budget_s, "Planning time budget")
        self.deadline = self.started + self.budget
        if cancel is not None and not callable(cancel):
            raise ValueError("Cancellation must be a callable returning a boolean.")
        if (
            isinstance(samples_per_batch, bool)
            or not isinstance(samples_per_batch, int)
            or samples_per_batch < 1
        ):
            raise ValueError("Samples per batch must be a positive integer.")
        self.cancel = cancel
        self.batch = samples_per_batch
        self.grid = deepcopy(grid)
        self.model = risk_model
        self.endpoints = deepcopy(endpoints)
        if risk_model.crs.to_string() != grid["analysis_crs"]:
            raise ValueError("Risk model CRS must match continuous planning CRS.")
        for name in ("start", "end"):
            coordinate = self.endpoints[name]
            if len(coordinate) != 2 or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v)
                for v in coordinate
            ):
                raise ValueError("Endpoints must contain finite longitude/latitude pairs.")
            if not -180 <= coordinate[0] <= 180 or not -90 <= coordinate[1] <= 90:
                raise ValueError("Endpoints must be longitude/latitude in EPSG:4326.")
        self.check = constraint_checker(self.grid, self.model.safety_distance_m)
        self.forward = Transformer.from_crs(4326, risk_model.crs, always_xy=True).transform
        self.reverse = Transformer.from_crs(risk_model.crs, 4326, always_xy=True).transform
        self.stop_reason = None
        self.unknown_seen = False
        self.simple_setup = None
        self.setup_ms = 0.0
        self.used = False
        self.counters = dict.fromkeys(("state", "motion", "cost", "heuristic", "cost_to_go"), 0)

    def _terminated(self):
        if self.cancel is not None and self.cancel():
            self.stop_reason = "cancelled"
        elif self.stop_reason is None and perf_counter() >= self.deadline:
            self.stop_reason = "time_budget"
        return self.stop_reason is not None

    def _allowed(self, points):
        geographic = [self.reverse(*p) for p in points]
        state = self.check(geographic)
        assessment = self.model.evaluate(points, input_crs=self.model.crs.to_string())
        unknown = state == "unresolved" or assessment["assessment"] != "assessed"
        self.unknown_seen |= unknown
        return state == "permitted" and not unknown

    def initialize(self):
        """Retain Python callback objects while C++ owns references to them."""
        setup_started = perf_counter()
        if self.simple_setup is not None:
            raise RuntimeError("Planner already initialized.")
        ob, og = _load_ompl()
        if self._terminated():
            raise _Stopped
        # C++ owns callbacks; callbacks must not retain the planner/SpaceInformation
        # that owns them. Nanobind cannot collect these cross-language cycles.
        owner = proxy(self)
        space = ob.RealVectorStateSpace(2)
        bounds = ob.RealVectorBounds(2)
        minx, miny, maxx, maxy = self.model.boundary.bounds
        for axis, low, high in ((0, minx, maxx), (1, miny, maxy)):
            bounds.setLow(axis, low)
            bounds.setHigh(axis, high)
        space.setBounds(bounds)
        self.simple_setup = og.SimpleSetup(space)
        si = self.simple_setup.getSpaceInformation()

        def point(state):
            return (state[0], state[1])

        class StateValidator(ob.StateValidityChecker):
            def isValid(self, state):
                owner.counters["state"] += 1
                return not owner._terminated() and owner._allowed([point(state)])

        class MotionValidator(ob.MotionValidator):
            def checkMotion(self, start, end):
                owner.counters["motion"] += 1
                return not owner._terminated() and owner._allowed([point(start), point(end)])

        class Objective(ob.OptimizationObjective):
            def stateCost(self, state):
                return ob.Cost(0)

            def motionCost(self, start, end):
                owner.counters["cost"] += 1
                value = owner.model.evaluate(
                    [point(start), point(end)], input_crs=owner.model.crs.to_string()
                )
                if value["assessment"] != "assessed":
                    owner.unknown_seen = True
                    return ob.Cost(float("inf"))
                return ob.Cost(value["objective_cost"])

            def motionCostHeuristic(self, start, end):
                owner.counters["heuristic"] += 1
                return ob.Cost(
                    owner.model.distance_weight
                    * owner.simple_setup.getSpaceInformation().distance(start, end)
                )

        self.state_validator = StateValidator(si)
        self.motion_validator = MotionValidator(si)
        self.objective = Objective(si)

        def cost_to_go(state, goal):
            owner.counters["cost_to_go"] += 1
            return ob.Cost(
                owner.model.distance_weight * max(0, goal.distanceGoal(state) - goal.getThreshold())
            )

        self.cost_to_go = cost_to_go
        self.objective.setCostToGoHeuristic(cost_to_go)
        self.simple_setup.setStateValidityChecker(self.state_validator)
        si.setMotionValidator(self.motion_validator)
        self.simple_setup.setOptimizationObjective(self.objective)
        self.planner = og.ABITstar(si)
        self.planner.setSamplesPerBatch(self.batch)
        self.simple_setup.setPlanner(self.planner)
        self.states = []
        for name in ("start", "end"):
            state = si.allocState()
            state[0], state[1] = self.forward(*self.endpoints[name])
            self.states.append(state)
        self.simple_setup.setStartAndGoalStates(*self.states, 1e-7)
        self.simple_setup.setup()
        self.ob = ob
        self.setup_ms = (perf_counter() - setup_started) * 1000

    def _result(self, status, **values):
        return {
            "algorithm": "abitstar",
            "rules_version": self.model.provenance["rules_version"],
            "status": status,
            "exact": False,
            "solution_kind": "none",
            "geometry": None,
            "length_m": None,
            "risk_length_cost": None,
            "objective_cost": None,
            "start": self.endpoints["start"],
            "end": self.endpoints["end"],
            "analysis_crs": self.model.crs.to_string(),
            "objective": "risk",
            "safety_distance_m": self.model.safety_distance_m,
            "risk_model": deepcopy(self.model.provenance),
            "policy": self.grid["policy"],
            "assumptions": deepcopy(self.grid["assumptions"]),
            "time_budget_s": self.budget,
            "stop_reason": self.stop_reason,
            "runtime_ms": (perf_counter() - self.started) * 1000,
            "callbacks": dict(self.counters),
            "optimality": "Finite-budget continuous-space result; no finite-run optimality guarantee.",
            **values,
        }

    def _validate_path(self, path, exact):
        metric = [(path.getState(i)[0], path.getState(i)[1]) for i in range(path.getStateCount())]
        if not metric or any(not all(isfinite(v) for v in p) for p in metric):
            raise ValueError("Planner returned empty or nonfinite path.")
        coordinates = [list(self.reverse(*p)) for p in metric]
        targets = [self.forward(*self.endpoints[name]) for name in ("start", "end")]
        if hypot(metric[0][0] - targets[0][0], metric[0][1] - targets[0][1]) > 1e-6:
            raise ValueError("Path does not preserve the exact start.")
        coordinates[0] = list(self.endpoints["start"])
        if exact:
            if hypot(metric[-1][0] - targets[1][0], metric[-1][1] - targets[1][1]) > 1e-6:
                raise ValueError("Exact path does not reach the exact goal.")
            coordinates[-1] = list(self.endpoints["end"])
        segments = list(zip(coordinates, coordinates[1:])) or [(coordinates[0], coordinates[0])]
        assessments = []
        for a, b in segments:
            if self.check([a, b]) != "permitted":
                raise ValueError("Final path failed full constraint validation.")
            cost = self.model.evaluate([a, b])
            if cost["assessment"] != "assessed":
                raise ValueError("Final path risk support is unresolved.")
            assessments.append(cost)
        totals = {
            name: sum(a[name] for a in assessments)
            for name in ("length_m", "risk_length_cost", "objective_cost")
        }
        if not all(isfinite(v) for v in totals.values()) or not isclose(
            totals["objective_cost"], path.cost(self.objective).value(), rel_tol=1e-7, abs_tol=1e-5
        ):
            raise ValueError("Final objective differs from the planner's cost.")
        return {
            **totals,
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates if len(coordinates) > 1 else coordinates * 2,
            },
            "assessment_flags": {
                "has_default": any(a["has_default"] for a in assessments),
                "background_assumed": any(a["background_assumed"] for a in assessments),
                "source_ids": sorted({i for a in assessments for i in a["source_ids"]}),
            },
        }

    def run(self):
        if self.used:
            raise RuntimeError("Create a new planner instance for each task.")
        self.used = True
        try:
            if self._terminated():
                return self._result("cancelled" if self.stop_reason == "cancelled" else "timeout")
            endpoint_states = [self.check([self.endpoints[n]]) for n in ("start", "end")]
            if "blocked" in endpoint_states:
                return self._result("invalid_endpoint")
            if "unresolved" in endpoint_states or any(
                self.model.evaluate([self.endpoints[n]])["assessment"] != "assessed"
                for n in ("start", "end")
            ):
                return self._result("unresolved_input")
            try:
                if self.simple_setup is None:
                    self.initialize()
            except (ImportError, OSError) as error:
                return self._result("planner_unavailable", message=str(error))
            setup_ms = self.setup_ms
            if self._terminated():
                raise _Stopped
            native_status = self.simple_setup.solve(
                self.ob.PlannerTerminationCondition(self._terminated)
            )
            problem = self.simple_setup.getProblemDefinition()
            if self.cancel is not None and self.cancel():
                self.stop_reason = "cancelled"
            if self.stop_reason == "cancelled":
                return self._result(
                    "cancelled", native_status=str(native_status), setup_ms=setup_ms
                )
            exact = problem.hasExactSolution()
            if problem.hasSolution():
                validation_start = perf_counter()
                validated = self._validate_path(self.simple_setup.getSolutionPath(), exact)
                if self.cancel is not None and self.cancel():
                    self.stop_reason = "cancelled"
                    return self._result("cancelled")
                if exact:
                    return self._result(
                        "success",
                        exact=True,
                        solution_kind="exact",
                        native_status=str(native_status),
                        setup_ms=setup_ms,
                        validation_ms=(perf_counter() - validation_start) * 1000,
                        **validated,
                    )
                # Partial candidates are diagnostics, never exported as successful routes.
                return self._result(
                    "approximate_solution",
                    solution_kind="approximate",
                    candidate=validated,
                    native_status=str(native_status),
                    setup_ms=setup_ms,
                )
            return self._result(
                "unresolved_input" if self.unknown_seen else "timeout",
                native_status=str(native_status),
                setup_ms=setup_ms,
                message="No validated exact path; continuous-space feasibility is unknown.",
            )
        except _Stopped:
            return self._result("cancelled" if self.stop_reason == "cancelled" else "timeout")
        except Exception as error:
            return self._result("computational_failure", message=f"{type(error).__name__}: {error}")


def plan_abitstar(grid, risk_model, endpoints, **options):
    """Return a structured result; never persist global path/graph files."""
    return AbitPlanner(grid, risk_model, endpoints, **options).run()
