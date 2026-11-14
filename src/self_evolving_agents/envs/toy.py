"""``toy-scan``: a small analytic stand-in for the Basilisk scanning task.

It exists so that tests and offline demos run in milliseconds without Basilisk. It
has the same actions, features and operating conditions as ``bsk-scan`` and a
qualitatively similar energy / data / momentum budget, but it is a bookkeeping
model, not a physics simulation. Nothing measured on it should be read as a
statement about the real simulator.
"""

from __future__ import annotations

import numpy as np

from ..types import Action, Observation, Outcome, Task
from . import scanning as sc
from .base import ActionParseError, EnvSpec, StepResult, TextEnv, match_action_name, register

ORBIT_S = 5700.0
ECLIPSE_FRACTION = 0.35
GS_PERIOD_S = 2900.0
GS_WINDOW_S = 330.0
SETTLE_S = 60.0  # scan time lost after switching into scan from another mode
SCAN_SUN_FACTOR = 0.45  # share of full array power available while nadir pointing
WHEEL_BASE_W = 4.0
WHEEL_SPEED_W = 12.0  # extra wheel power at 6000 rpm
WHEEL_GROWTH = 88.0  # wheel-fraction growth per (N m / rpm) per second


class ToyScanEnv(TextEnv):
    env_id = "toy-scan"

    def __init__(self, task: Task):
        super().__init__(task)
        self.conditions, self.params = sc.resolve(task)
        self._spec = sc.scan_spec(self.params)
        self._durations = {
            sc.SCAN: self.params["scan_s"],
            sc.CHARGE: self.params["charge_s"],
            sc.DOWNLINK: self.params["downlink_s"],
            sc.DESAT: self.params["desat_s"],
        }
        self._ready = False

    @property
    def spec(self) -> EnvSpec:
        return self._spec

    @property
    def query(self) -> str:
        return sc.scan_query(self.conditions, self.params)

    def retask(self, task: Task) -> bool:
        if task.env_id != self.env_id or sc.resolve(task) != (self.conditions, self.params):
            return False
        self.task = task
        self._ready = False
        return True

    # ------------------------------------------------------------------ dynamics

    def _in_eclipse(self, t: float) -> bool:
        return ((t + self._ecl_phase) % ORBIT_S) < ECLIPSE_FRACTION * ORBIT_S

    def _eclipse_times(self, t: float) -> tuple[float, float]:
        position = (t + self._ecl_phase) % ORBIT_S
        eclipse_len = ECLIPSE_FRACTION * ORBIT_S
        if position < eclipse_len:
            return ORBIT_S - position, eclipse_len - position
        return ORBIT_S - position, ORBIT_S - position + eclipse_len

    def _gs_times(self, t: float) -> tuple[float, float]:
        position = (t + self._gs_phase) % GS_PERIOD_S
        if position < GS_WINDOW_S:
            return 0.0, GS_WINDOW_S - position
        return GS_PERIOD_S - position, GS_PERIOD_S - position + GS_WINDOW_S

    def _overlap(self, t0: float, dt: float, predicate, grain: float = 10.0) -> float:
        """Seconds within ``[t0, t0 + dt)`` for which ``predicate(t)`` holds."""
        n = max(int(round(dt / grain)), 1)
        ticks = t0 + (np.arange(n) + 0.5) * (dt / n)
        return float(sum(predicate(t) for t in ticks)) * (dt / n)

    def _features(self) -> dict[str, float]:
        ecl_start, ecl_end = self._eclipse_times(self._t)
        gs_open, gs_close = self._gs_times(self._t)
        duration = self.params["duration_s"]
        f = {
            "battery": self._battery_wh / self.conditions["battery_capacity_wh"],
            "storage": self._storage_mb / self.conditions["storage_capacity_mb"],
            "wheel_speed": self._wheel,
            "in_eclipse": 1.0 if self._in_eclipse(self._t) else 0.0,
            "eclipse_start_s": ecl_start,
            "eclipse_end_s": ecl_end,
            "gs_in_view": 1.0 if gs_open == 0.0 else 0.0,
            "gs_open_s": gs_open,
            "gs_close_s": gs_close,
            "time_frac": min(self._t / duration, 1.0),
            "time_left_s": max(duration - self._t, 0.0),
            "last_reward": self._last_reward,
        }
        f.update(sc.previous_action_features(self._last_action))
        return f

    def _observe(self) -> Observation:
        f = self._features()
        return Observation(
            text=sc.render_observation(f, self._t, self._last_action),
            features=f,
            brief=sc.brief_observation(f, self._t),
        )

    # ------------------------------------------------------------------ TextEnv

    def reset(self) -> Observation:
        rng = np.random.default_rng(self.task.seed)
        c, p = self.conditions, self.params
        self._t = 0.0
        self._battery_wh = c["battery_capacity_wh"] * rng.uniform(
            p["init_battery_min"], p["init_battery_max"]
        )
        self._storage_mb = c["storage_capacity_mb"] * rng.uniform(
            p["init_storage_min"], p["init_storage_max"]
        )
        self._wheel = float(rng.uniform(0.0, p["init_wheel_frac"]))
        self._ecl_phase = float(rng.uniform(0.0, ORBIT_S))
        self._gs_phase = float(rng.uniform(0.0, GS_PERIOD_S))
        self._wheel_noise = float(rng.uniform(0.6, 1.4))
        self._last_action: str | None = None
        self._last_reward = 0.0
        self._alive = True
        self._failure: str | None = None
        self._log: list[dict] = []
        self._ready = True
        return self._observe()

    def parse_action(self, text: str) -> Action:
        return Action(match_action_name(text, sc.ACTIONS, sc.ACTION_ALIASES))

    def fallback_action(self) -> Action:
        return Action(sc.CHARGE)

    def step(self, action: Action) -> StepResult:
        if not self._ready:
            raise RuntimeError("call reset() before step()")
        if action.name not in self._durations:
            raise ActionParseError(f"unknown action {action.name!r}")
        c, p = self.conditions, self.params
        name = action.name
        dt = min(self._durations[name], p["duration_s"] - self._t)
        before = self._features()
        in_eclipse_before = self._in_eclipse(self._t)
        sunlit_s = dt - self._overlap(self._t, dt, self._in_eclipse)
        panel = sc.panel_power_w(c)

        wheel_power = WHEEL_BASE_W + WHEEL_SPEED_W * self._wheel * c["max_wheel_speed_rpm"] / 6000.0
        load = c["base_power_w"] + wheel_power
        generation_factor = 1.0 if name == sc.CHARGE else SCAN_SUN_FACTOR
        reward = 0.0

        if name == sc.SCAN:
            load += c["instrument_power_w"]
            usable = dt - (SETTLE_S if self._last_action != sc.SCAN else 0.0)
            room_s = (c["storage_capacity_mb"] - self._storage_mb) / c["instrument_rate_mb_s"]
            recorded = max(min(usable, room_s), 0.0)
            self._storage_mb += recorded * c["instrument_rate_mb_s"]
            reward = recorded / p["duration_s"]
        elif name == sc.DOWNLINK:
            load += c["transmitter_power_w"]
            contact = self._overlap(self._t, dt, lambda t: self._gs_times(t)[0] == 0.0)
            self._storage_mb = max(self._storage_mb - contact * c["downlink_rate_mb_s"], 0.0)
        elif name == sc.DESAT:
            load += c["thruster_power_w"]
            self._wheel = max(self._wheel - 0.01 * dt, 0.0)

        energy_wh = (panel * generation_factor * sunlit_s - load * dt) / 3600.0
        self._battery_wh = min(self._battery_wh + energy_wh, c["battery_capacity_wh"])
        if name != sc.DESAT:
            growth = WHEEL_GROWTH * c["disturbance_torque_nm"] / c["max_wheel_speed_rpm"]
            self._wheel += growth * self._wheel_noise * dt
        self._t += dt

        terminated = False
        if self._battery_wh <= 0.0:
            self._battery_wh, self._alive, self._failure = 0.0, False, "battery"
        elif self._wheel >= 1.0:
            self._wheel, self._alive, self._failure = 1.0, False, "wheels"
        recorded_reward = reward  # what was earned by recording, before any penalty
        if not self._alive:
            reward -= 1.0
            terminated = True
        truncated = (not terminated) and self._t >= p["duration_s"] - 1e-9

        self._last_action, self._last_reward = name, reward
        features = self._features()
        self._log.append(
            {
                "action": name,
                # The failure penalty is not recorded data; keep it out of the scan tally.
                "reward": recorded_reward,
                "dt": dt,
                "battery": features["battery"],
                "wheel_speed": features["wheel_speed"],
                "in_eclipse_before": in_eclipse_before,
            }
        )
        info = {"sim_time_s": self._t, "failure": self._failure}
        observation = Observation(
            text=sc.render_observation(features, self._t, name),
            features=features,
            brief=sc.brief_observation(features, self._t),
        )
        return StepResult(
            observation,
            reward,
            terminated,
            truncated,
            info,
            summary=sc.step_summary(before, features, reward),
            event=sc.end_event(self._alive, self._failure, truncated),
        )

    def outcome(self) -> Outcome:
        metrics = sc.summarise_episode(self._log, self._alive, self._failure, self.params)
        score = sum(s["reward"] for s in self._log) - (0.0 if self._alive else 1.0)
        return Outcome(
            score=round(score, 6),
            success=bool(self._alive and metrics["scan_fraction"] >= self.params["success_score"]),
            failure=self._failure,
            terminated=not self._alive,
            truncated=self._alive and self._t >= self.params["duration_s"] - 1e-9,
            metrics=metrics,
        )


register(ToyScanEnv.env_id, ToyScanEnv)
