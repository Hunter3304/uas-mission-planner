"""Weighted public MiT 2023 walking profiles for Niedersachsen."""

from datetime import datetime
from math import fsum, isclose
from zoneinfo import ZoneInfo

DAY_MINUTES = 24 * 60
WINDOWS = {
    "05-08": (5 * 60, 8 * 60),
    "08-10": (8 * 60, 10 * 60),
    "10-13": (10 * 60, 13 * 60),
    "13-16": (13 * 60, 16 * 60),
    "16-19": (16 * 60, 19 * 60),
    "19-22": (19 * 60, 22 * 60),
    "22-05": (22 * 60, 29 * 60),
}
START_PERCENTS = (
    8.6620797989413,
    12.115587459590369,
    21.192338613823697,
    25.08827336296236,
    22.947590279365986,
    8.210269718715525,
    1.783860766600763,
)
DURATION_BINS = (
    (0, 5, 2.4914916433589083),
    (5, 10, 18.95833493345174),
    (10, 15, 17.242717204763295),
    (15, 20, 14.350053233927628),
    (20, 30, 11.061654305681442),
    (30, 45, 14.83420359279707),
    (45, 60, 6.1369967705668715),
    (60, None, 14.924548315453054),
)
BASE_TAIL_MINUTES = 90
TAIL_SENSITIVITY_MINUTES = (60, 120)
START_WEIGHTED_BASE = 19774
DURATION_WEIGHTED_BASE = 20080


def source_metadata():
    return {
        "title": "Mobilität in Tabellen (MiT 2023)",
        "url": "https://mobilitaet-in-tabellen-2023.bast.de/",
        "retrieved_on": "2026-11-18",
        "land": "Niedersachsen",
        "day_type": "All survey days pooled",
        "query": {
            "dataset": "Wege (w)",
            "start_row": "Startzeit des Weges gruppiert (sz_gr2)",
            "duration_row": "Wegedauer [min] (ohne rbW) in Gruppen (wegmin_imp2_gr)",
            "column": "Hauptverkehrsmittel (fehlende Angaben wurden aufgefüllt) (hvm_imp)",
            "mode": "zu Fuß",
            "breakdown": "Bundesland (BLAND)",
            "aggregation": "Weighted column percentages (W_GEW)",
        },
        "start_weighted_base": START_WEIGHTED_BASE,
        "start_unweighted_base": 18339,
        "duration_weighted_base": DURATION_WEIGHTED_BASE,
        "duration_unweighted_base": 18591,
        "start_percentages": dict(zip(WINDOWS, START_PERCENTS, strict=True)),
        "duration_bins": [
            {"lower_minutes": lower, "upper_minutes": upper, "percentage": percent}
            for lower, upper, percent in DURATION_BINS
        ],
        "municipal_transfer": "Apply both state profiles to the municipal daily walking budget",
        "within_start_window": "Uniform local clock minutes on a repeating 24-hour day",
        "start_duration_relationship": "Independent state-level marginal distributions",
        "representative_duration_rule": "Finite-bin midpoints and a fixed open-bin value",
        "open_duration_bin_minutes": BASE_TAIL_MINUTES,
    }


def window_metadata(key):
    start, end = WINDOWS[key]
    first, last = start // 60, end // 60 % 24
    overnight = end > DAY_MINUTES
    return {
        "id": key,
        "label": f"{first:02d}:00–{last:02d}:00" + (" (next day)" if overnight else ""),
        "start_hour": first,
        "end_hour": last,
        "overnight": overnight,
        "minutes": end - start,
        "timezone": "Europe/Berlin",
    }


def departure_window(timestamp):
    """Select the public half-open window on the Europe/Berlin clock."""
    instant = datetime.fromisoformat(timestamp)
    if instant.utcoffset() is None:
        raise ValueError("Pedestrian scoring requires an offset-aware departure time.")
    local = instant.astimezone(ZoneInfo("Europe/Berlin"))
    minutes = local.hour * 60 + local.minute
    if minutes < WINDOWS["05-08"][0]:
        minutes += DAY_MINUTES
    return next(key for key, (start, end) in WINDOWS.items() if start <= minutes < end)


def mean_interval_overlap(start, end, duration, lower, upper):
    """Mean overlap of a fixed-duration trip uniformly started in [start, end)."""

    def overlap(s):
        return max(0.0, min(s + duration, upper) - max(s, lower))

    # The overlap is piecewise linear. Integrate each piece by its endpoints.
    breaks = sorted(
        {
            start,
            end,
            *(x for x in (lower - duration, upper - duration, lower, upper) if start < x < end),
        }
    )
    return fsum((b - a) * (overlap(a) + overlap(b)) / 2 for a, b in zip(breaks, breaks[1:])) / (
        end - start
    )


def expected_minutes(tail_minutes=BASE_TAIL_MINUTES):
    """Walking minutes in each target window per expected daily walking departure."""
    if not 60 <= tail_minutes < DAY_MINUTES:
        raise ValueError("The open duration bin must represent 60 to under 1440 minutes.")
    if not isclose(fsum(START_PERCENTS), 100) or not isclose(
        fsum(value for _, _, value in DURATION_BINS), 100
    ):
        raise ValueError("MiT walking profile shares do not sum to 100 percent.")

    durations = [
        (tail_minutes if upper is None else (lower + upper) / 2, percent / 100)
        for lower, upper, percent in DURATION_BINS
    ]
    windows = {
        key: fsum(
            start_percent
            * duration_fraction
            / 100
            * mean_interval_overlap(start, end, duration, lower + shift, upper + shift)
            for (start, end), start_percent in zip(WINDOWS.values(), START_PERCENTS, strict=True)
            for duration, duration_fraction in durations
            for shift in (-DAY_MINUTES, 0, DAY_MINUTES)
        )
        for key, (lower, upper) in WINDOWS.items()
    }
    if not isclose(fsum(windows.values()), fsum(d * fraction for d, fraction in durations)):
        raise ValueError("Time-window walking minutes do not reconcile to trip duration.")
    return windows
