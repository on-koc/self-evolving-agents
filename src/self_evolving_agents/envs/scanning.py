"""Shared definition of the nadir-scanning task family.

Two environments implement this task: ``bsk-scan`` (the real one, on Basilisk via
BSK-RL) and ``toy-scan`` (a small analytic surrogate used by tests and offline
demos). They share the action vocabulary, the feature names, the operating
conditions and the text shown to the agent, so that policies, prompts and claims
written against one run unchanged against the other.
"""

from __future__ import annotations

from typing import Any

from ..types import Task
from .base import EnvSpec

SCAN, CHARGE, DOWNLINK, DESAT = "scan", "charge", "downlink", "desat"
ACTIONS = [SCAN, CHARGE, DOWNLINK, DESAT]
ACTION_ALIASES = {
    "nadir_scan": SCAN,
    "image": SCAN,
    "sun_point": CHARGE,
    "recharge": CHARGE,
    "down_link": DOWNLINK,
    "transmit": DOWNLINK,
    "desaturate": DESAT,
    "momentum_dump": DESAT,
}

#: Sentinel for "not within the look-ahead horizon" in time-to-event features.
FAR = 1.0e6

FEATURE_DOCS: dict[str, str] = {
    "battery": "battery state of charge, 0..1",
    "storage": "data buffer fill level, 0..1",
    "wheel_speed": "fastest reaction wheel as a fraction of its speed limit, 0..1",
    "in_eclipse": "1 if currently in Earth's shadow, else 0",
    "eclipse_start_s": "seconds until the next eclipse entry",
    "eclipse_end_s": "seconds until the next eclipse exit",
    "gs_in_view": "1 if a ground-station pass is open now, else 0",
    "gs_open_s": "seconds until the next pass opens (0 while one is open)",
    "gs_close_s": "seconds until that pass closes",
    "time_frac": "elapsed fraction of the episode, 0..1",
    "time_left_s": "seconds remaining in the episode",
    "last_reward": "reward earned by the previous step",
    "prev_scan": "1 if the previous action was scan, else 0",
    "prev_charge": "1 if the previous action was charge, else 0",
    "prev_downlink": "1 if the previous action was downlink, else 0",
    "prev_desat": "1 if the previous action was desat, else 0",
}
FEATURES = list(FEATURE_DOCS)

#: Operating conditions of the reference spacecraft (the BSK-RL nadir-scanning
#: configuration from Stephenson & Schaub's RLlib example).
DEFAULT_CONDITIONS: dict[str, float] = {
    "battery_capacity_wh": 200.0,
    "panel_area_m2": 0.25,
    "panel_efficiency": 0.20,
    "base_power_w": 10.0,
    "instrument_power_w": 30.0,
    "transmitter_power_w": 25.0,
    "thruster_power_w": 80.0,
    "storage_capacity_mb": 5000.0,
    "instrument_rate_mb_s": 0.5,
    "downlink_rate_mb_s": 50.0,
    "disturbance_torque_nm": 1.0e-4,
    "max_wheel_speed_rpm": 6000.0,
}

#: Episode construction parameters (not part of the operating regime).
DEFAULT_PARAMS: dict[str, float] = {
    "duration_s": 17100.0,  # about three orbits
    "scan_s": 180.0,
    "charge_s": 120.0,
    "downlink_s": 60.0,
    "desat_s": 60.0,
    "init_battery_min": 0.3,
    "init_battery_max": 1.0,
    "init_storage_min": 0.0,
    "init_storage_max": 0.8,
    "init_wheel_frac": 0.5,
    # Ground-truth success: survived, and recorded data for at least this fraction
    # of the episode. Used for reporting and by the environment judge only.
    "success_score": 0.2,
}

#: Named single-factor departures from the reference spacecraft.
REGIMES: dict[str, dict[str, float]] = {
    "nominal": {},
    "small_battery": {"battery_capacity_wh": 50.0},
    "tiny_battery": {"battery_capacity_wh": 25.0},
    "big_battery": {"battery_capacity_wh": 400.0},
    "small_panel": {"panel_area_m2": 0.10},
    "power_hungry": {"instrument_power_w": 90.0},
    "high_disturbance": {"disturbance_torque_nm": 2.0e-3},
    "weak_wheels": {"max_wheel_speed_rpm": 1500.0},
    "data_heavy": {"instrument_rate_mb_s": 2.0},
    "slow_downlink": {"downlink_rate_mb_s": 5.0},
}

SOLAR_FLUX_W_M2 = 1361.0


def scan_task(
    env_id: str = "bsk-scan",
    regime: str = "nominal",
    seed: int = 0,
    conditions: dict[str, float] | None = None,
    **params: float,
) -> Task:
    """Build a scanning task. ``conditions`` override the named regime."""
    if regime not in REGIMES:
        raise KeyError(f"unknown regime {regime!r}; known: {', '.join(REGIMES)}")
    merged = {**DEFAULT_CONDITIONS, **REGIMES[regime], **(conditions or {})}
    unknown = set(merged) - set(DEFAULT_CONDITIONS)
    if unknown:
        raise KeyError(f"unknown condition(s): {', '.join(sorted(unknown))}")
    unknown = set(params) - set(DEFAULT_PARAMS)
    if unknown:
        raise KeyError(f"unknown parameter(s): {', '.join(sorted(unknown))}")
    name = regime if not conditions else f"{regime}+custom"
    return Task(env_id=env_id, name=name, seed=seed, conditions=merged, params=dict(params))


def resolve(task: Task) -> tuple[dict[str, float], dict[str, float]]:
    """Fill in defaults, returning ``(conditions, params)`` as floats."""
    conditions = {**DEFAULT_CONDITIONS, **{k: float(v) for k, v in task.conditions.items()}}
    params = {**DEFAULT_PARAMS, **{k: float(v) for k, v in task.params.items()}}
    return conditions, params


def panel_power_w(conditions: dict[str, float]) -> float:
    """Electrical power from the solar array when pointed straight at the Sun."""
    return SOLAR_FLUX_W_M2 * conditions["panel_area_m2"] * conditions["panel_efficiency"]


def data_sheet(conditions: dict[str, float]) -> str:
    c = conditions
    return (
        "Spacecraft data sheet:\n"
        f"- Battery: {c['battery_capacity_wh']:g} Wh\n"
        f"- Solar array: {c['panel_area_m2']:g} m2 at {c['panel_efficiency'] * 100:g}% efficiency "
        f"(about {panel_power_w(c):.0f} W when pointed at the Sun)\n"
        f"- Power draw: {c['base_power_w']:g} W always on; instrument {c['instrument_power_w']:g} W; "
        f"transmitter {c['transmitter_power_w']:g} W; desaturation thrusters {c['thruster_power_w']:g} W\n"
        f"- Data: buffer {c['storage_capacity_mb']:g} MB; instrument writes {c['instrument_rate_mb_s']:g} MB/s; "
        f"downlink sends {c['downlink_rate_mb_s']:g} MB/s\n"
        f"- Reaction wheels: speed limit {c['max_wheel_speed_rpm']:g} rpm; "
        f"external disturbance torque about {c['disturbance_torque_nm']:g} N m"
    )


def scan_query(conditions: dict[str, float], params: dict[str, float]) -> str:
    orbits = params["duration_s"] / 5700.0
    return (
        f"Operate an Earth-observation satellite for {params['duration_s']:g} s "
        f"(about {orbits:.1f} orbits). Maximise the total time spent recording nadir-scan data "
        "without losing the spacecraft.\n\n" + data_sheet(conditions)
    )


def scan_spec(params: dict[str, float]) -> EnvSpec:
    p = params
    return EnvSpec(
        domain="spacecraft operations and satellite tasking",
        role=(
            "You are the onboard tasking agent of a low-Earth-orbit Earth-observation satellite. "
            "At every decision step you choose one operating mode. The flight software then slews "
            "the spacecraft as needed and runs that mode for a fixed time before asking you again."
        ),
        actions_doc=(
            f"- `{SCAN}` ({p['scan_s']:g} s): point the instrument at nadir and record data into the "
            "onboard buffer.\n"
            f"- `{CHARGE}` ({p['charge_s']:g} s): point the solar array at the Sun; instrument off.\n"
            f"- `{DOWNLINK}` ({p['downlink_s']:g} s): transmit buffered data to a ground station.\n"
            f"- `{DESAT}` ({p['desat_s']:g} s): fire thrusters to unload reaction-wheel momentum."
        ),
        observation_doc=(
            "- battery: state of charge as a percentage of capacity.\n"
            "- data buffer: how full the onboard storage is.\n"
            "- wheels: speed of the fastest reaction wheel as a percentage of its limit.\n"
            "- eclipse: whether the spacecraft is in sunlight or in Earth's shadow, and the time to "
            "the next transition.\n"
            "- ground station: whether a station is in view, and when the current or next pass "
            "opens and closes.\n"
            "- time: elapsed fraction of the episode.\n"
            "- last reward: what the previous step earned."
        ),
        rules_doc=(
            "- Reward for a step is the number of seconds of data actually recorded during it, "
            "divided by the episode length. The best possible total is 1.\n"
            "- The episode ends immediately, with a reward of -1, if the battery is fully depleted "
            "or if any reaction wheel exceeds its speed limit.\n"
            "- Otherwise the episode ends when the time limit is reached."
        ),
        action_format=f"exactly one of: {', '.join(ACTIONS)}",
        success_doc=(
            "The episode is a success if the spacecraft survives to the time limit and a "
            "substantial share of the episode was spent recording data. Losing the spacecraft, "
            "or spending most of the episode without recording, is a failure."
        ),
        action_names=list(ACTIONS),
        feature_docs=dict(FEATURE_DOCS),
    )


def _duration(seconds: float) -> str:
    if seconds >= FAR:
        return "none expected"
    if seconds < 120:
        return f"{seconds:.0f} s"
    return f"{seconds / 60:.0f} min"


def render_observation(f: dict[str, float], sim_time_s: float, last_action: str | None) -> str:
    """Human-readable status report built from the feature dictionary."""
    lines = [
        f"Time {sim_time_s:.0f} s ({f['time_frac'] * 100:.0f}% of episode, "
        f"{_duration(f['time_left_s'])} left)",
        f"Battery {f['battery'] * 100:.0f}% | data buffer {f['storage'] * 100:.0f}% full | "
        f"wheels at {f['wheel_speed'] * 100:.0f}% of limit",
    ]
    if f["in_eclipse"]:
        lines.append(
            f"In eclipse; sunlight returns in {_duration(f['eclipse_end_s'])}, "
            f"next eclipse after that begins in {_duration(f['eclipse_start_s'])}"
        )
    elif f["eclipse_start_s"] >= FAR:
        lines.append("In sunlight; no eclipse expected")
    else:
        lines.append(
            f"In sunlight; eclipse begins in {_duration(f['eclipse_start_s'])} "
            f"and ends in {_duration(f['eclipse_end_s'])}"
        )
    if f["gs_in_view"]:
        lines.append(f"Ground station in view for another {_duration(f['gs_close_s'])}")
    elif f["gs_open_s"] >= FAR:
        lines.append("No ground station pass expected")
    else:
        lines.append(
            f"No ground station in view; next pass opens in {_duration(f['gs_open_s'])} "
            f"and closes in {_duration(f['gs_close_s'])}"
        )
    if last_action is not None:
        lines.append(f"Last action: {last_action}, reward {f['last_reward']:+.4f}")
    return "\n".join(lines)


def brief_observation(f: dict[str, float], sim_time_s: float) -> str:
    """One-line status for step histories."""
    sun = (
        f"eclipse, sun in {_duration(f['eclipse_end_s'])}"
        if f["in_eclipse"]
        else f"sunlit, eclipse in {_duration(f['eclipse_start_s'])}"
    )
    station = (
        f"station in view {_duration(f['gs_close_s'])}"
        if f["gs_in_view"]
        else f"next pass in {_duration(f['gs_open_s'])}"
    )
    return (
        f"t={sim_time_s:.0f}s battery {f['battery'] * 100:.0f}% buffer {f['storage'] * 100:.0f}% "
        f"wheels {f['wheel_speed'] * 100:.0f}% | {sun} | {station}"
    )


def step_summary(before: dict[str, float], after: dict[str, float], reward: float) -> str:
    """One-line account of what a step changed."""
    return (
        f"reward {reward:+.4f}; battery {before['battery'] * 100:.0f}%->{after['battery'] * 100:.0f}%, "
        f"buffer {before['storage'] * 100:.0f}%->{after['storage'] * 100:.0f}%, "
        f"wheels {before['wheel_speed'] * 100:.0f}%->{after['wheel_speed'] * 100:.0f}%"
    )


def end_event(alive: bool, failure: str | None, timed_out: bool) -> str:
    if not alive:
        cause = {
            "battery": "the battery was fully depleted",
            "wheels": "a reaction wheel exceeded its speed limit",
        }.get(failure or "", "a failure condition was met")
        return f"Episode over: spacecraft lost because {cause}."
    if timed_out:
        return "Episode over: time limit reached with the spacecraft alive."
    return ""


def previous_action_features(last_action: str | None) -> dict[str, float]:
    return {f"prev_{name}": 1.0 if last_action == name else 0.0 for name in ACTIONS}


def summarise_episode(
    steps: list[dict[str, Any]], alive: bool, failure: str | None, params: dict[str, float]
) -> dict[str, Any]:
    """Outcome metrics shared by both scanning environments.

    ``steps`` holds one dict per step with the action taken, the reward, the step
    duration and the features observed *after* the step. Besides the headline numbers
    this collects the mediator variables used to test explanations: how low the
    battery got, how fast the wheels spun, how much time was spent in each mode, how
    much scan time recorded nothing, and how much charging happened in the dark.
    """
    per_action = {name: 0.0 for name in ACTIONS}
    wasted_scan_s = 0.0
    dark_charge_s = 0.0
    switches = 0
    previous = None
    min_battery, max_wheel = 1.0, 0.0
    scan_fraction = 0.0
    for s in steps:
        action, dt = s["action"], s["dt"]
        per_action[action] += dt
        if previous is not None and action != previous:
            switches += 1
        previous = action
        if action == SCAN:
            recorded = max(s["reward"], 0.0) * params["duration_s"]
            scan_fraction += recorded / params["duration_s"]
            wasted_scan_s += max(dt - recorded, 0.0)
        if action == CHARGE and s["in_eclipse_before"]:
            dark_charge_s += dt
        min_battery = min(min_battery, s["battery"])
        max_wheel = max(max_wheel, s["wheel_speed"])
    elapsed = sum(s["dt"] for s in steps)
    return {
        "alive": alive,
        "failure": failure,
        "scan_fraction": round(scan_fraction, 6),
        "elapsed_s": elapsed,
        "n_steps": len(steps),
        "min_battery": round(min_battery, 4),
        "max_wheel_speed": round(max_wheel, 4),
        "mode_switches": switches,
        "wasted_scan_s": round(wasted_scan_s, 1),
        "dark_charge_s": round(dark_charge_s, 1),
        **{f"time_{name}_s": round(v, 1) for name, v in per_action.items()},
    }
