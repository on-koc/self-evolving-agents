"""``bsk-scan``: nadir scanning on the Basilisk astrodynamics simulator, via BSK-RL.

The spacecraft follows the BSK-RL nadir-scanning example (Stephenson & Schaub):
a continuous-imaging satellite with a data buffer, a battery charged by a
body-fixed solar array, reaction wheels subject to an external disturbance torque,
and downlink to a ground-station network. The agent picks one of four modes per
step; Basilisk's flight-software models do the pointing and actuation.

Episodes are exactly reproducible: BSK-RL seeds NumPy's global generator from the
reset seed, and every randomised quantity (orbit, epoch, initial charge, buffer
level, wheel speeds, disturbance torque) is drawn from it. Two runs with the same
task therefore start from the same state and differ only through the actions taken.

Basilisk and BSK-RL are imported on first use. The first reset downloads about
116 MB of SPICE kernels from naif.jpl.nasa.gov into Basilisk's support-data cache.
"""

from __future__ import annotations

import contextlib
from typing import Any

from ..types import Action, Observation, Outcome, Task
from . import scanning as sc
from .base import ActionParseError, EnvSpec, StepResult, TextEnv, match_action_name, register

_ACTION_INDEX = {sc.SCAN: 0, sc.CHARGE: 1, sc.DOWNLINK: 2, sc.DESAT: 3}
_OBS_LEN = 10


def _build_bsk_env(conditions: dict[str, float], params: dict[str, float]) -> Any:
    """Construct the BSK-RL ``SatelliteTasking`` environment for one operating regime."""
    try:
        import numpy as np
        from Basilisk.architecture import bskLogging
        from bsk_rl import act, data, obs, sats, scene
        from bsk_rl.gym import SatelliteTasking
        from bsk_rl.sim import dyn, fsw
    except ImportError as exc:  # pragma: no cover - depends on the optional extra
        raise ImportError(
            "bsk-scan needs Basilisk and BSK-RL: pip install 'self-evolving-agents[bsk]'"
        ) from exc

    bskLogging.setDefaultLogLevel(bskLogging.BSK_ERROR)
    c, p = conditions, params

    class ScanningDynModel(dyn.ContinuousImagingDynModel, dyn.GroundStationDynModel):
        pass

    class ScanningSatellite(sats.AccessSatellite):
        # The order here fixes the layout of the observation vector read in
        # ``BSKScanEnv._features``.
        observation_spec = [
            obs.SatProperties(
                dict(prop="storage_level_fraction"),
                dict(prop="battery_charge_fraction"),
                dict(prop="wheel_speeds_fraction"),
            ),
            obs.OpportunityProperties(
                dict(prop="opportunity_open"),
                dict(prop="opportunity_close"),
                type="ground_station",
                n_ahead_observe=1,
            ),
            obs.Eclipse(),
            obs.Time(),
        ]
        action_spec = [
            act.Scan(duration=p["scan_s"]),
            act.Charge(duration=p["charge_s"]),
            act.Downlink(duration=p["downlink_s"]),
            act.Desat(duration=p["desat_s"]),
        ]
        dyn_type = ScanningDynModel
        fsw_type = fsw.ContinuousImagingFSWModel

    battery_j = c["battery_capacity_wh"] * 3600.0
    storage_bits = c["storage_capacity_mb"] * 8e6
    wheel_limit = c["max_wheel_speed_rpm"]
    sat_args = dict(
        # Data
        dataStorageCapacity=storage_bits,
        storageInit=lambda: (
            np.random.uniform(p["init_storage_min"], p["init_storage_max"]) * storage_bits
        ),
        instrumentBaudRate=c["instrument_rate_mb_s"] * 8e6,
        transmitterBaudRate=-c["downlink_rate_mb_s"] * 8e6,
        # Power
        batteryStorageCapacity=battery_j,
        storedCharge_Init=lambda: (
            np.random.uniform(p["init_battery_min"], p["init_battery_max"]) * battery_j
        ),
        basePowerDraw=-c["base_power_w"],
        instrumentPowerDraw=-c["instrument_power_w"],
        transmitterPowerDraw=-c["transmitter_power_w"],
        thrusterPowerDraw=-c["thruster_power_w"],
        panelArea=c["panel_area_m2"],
        panelEfficiency=c["panel_efficiency"],
        # Attitude
        imageAttErrorRequirement=0.1,
        imageRateErrorRequirement=0.1,
        disturbance_vector=lambda: np.random.normal(scale=c["disturbance_torque_nm"], size=3),
        maxWheelSpeed=wheel_limit,
        wheelSpeeds=lambda: (
            np.random.uniform(-p["init_wheel_frac"], p["init_wheel_frac"], 3) * wheel_limit
        ),
        desatAttitude="nadir",
    )
    satellite = ScanningSatellite("Scanner", sat_args=sat_args)
    return SatelliteTasking(
        satellite=satellite,
        scenario=scene.UniformNadirScanning(value_per_second=1.0 / p["duration_s"]),
        rewarder=data.ScanningTimeReward(),
        time_limit=p["duration_s"],
        failure_penalty=-1.0,
        terminate_on_time_limit=True,
        log_level="CRITICAL",
    )


class BSKScanEnv(TextEnv):
    env_id = "bsk-scan"

    def __init__(self, task: Task):
        super().__init__(task)
        self.conditions, self.params = sc.resolve(task)
        self._spec = sc.scan_spec(self.params)
        self._env: Any = None
        self._ready = False

    @property
    def spec(self) -> EnvSpec:
        return self._spec

    @property
    def query(self) -> str:
        return sc.scan_query(self.conditions, self.params)

    def retask(self, task: Task) -> bool:
        """Switch to another seed of the same configuration without rebuilding Basilisk.

        Returns ``False`` (and changes nothing) if the task needs a different spacecraft.
        """
        if task.env_id != self.env_id or sc.resolve(task) != (self.conditions, self.params):
            return False
        self.task = task
        self._ready = False
        return True

    # ------------------------------------------------------------------ observation

    def _features(self, vector: Any, sim_time: float) -> dict[str, float]:
        if len(vector) != _OBS_LEN:
            raise RuntimeError(f"unexpected BSK-RL observation length {len(vector)}")
        storage, battery = float(vector[0]), float(vector[1])
        wheel = max(abs(float(w)) for w in vector[2:5])
        gs_open, gs_close = float(vector[5]), float(vector[6])
        ecl_start, ecl_end = float(vector[7]), float(vector[8])
        duration = self.params["duration_s"]

        if ecl_start <= 0.0 and ecl_end <= 0.0:
            # BSK-RL's "no eclipse found in the search window" answer.
            in_eclipse, ecl_start, ecl_end = False, sc.FAR, sc.FAR
        else:
            in_eclipse = ecl_start > ecl_end
        if gs_close <= 0.0:
            gs_in_view, gs_open, gs_close = False, sc.FAR, sc.FAR
        else:
            gs_in_view = gs_open <= 0.0
            gs_open = max(gs_open, 0.0)

        f = {
            "battery": battery,
            "storage": storage,
            "wheel_speed": wheel,
            "in_eclipse": 1.0 if in_eclipse else 0.0,
            "eclipse_start_s": ecl_start,
            "eclipse_end_s": ecl_end,
            "gs_in_view": 1.0 if gs_in_view else 0.0,
            "gs_open_s": gs_open,
            "gs_close_s": gs_close,
            "time_frac": min(sim_time / duration, 1.0),
            "time_left_s": max(duration - sim_time, 0.0),
            "last_reward": self._last_reward,
        }
        f.update(sc.previous_action_features(self._last_action))
        return f

    def _observe(self, vector: Any) -> Observation:
        sim_time = float(self._env.simulator.sim_time)
        f = self._features(vector, sim_time)
        return Observation(
            text=sc.render_observation(f, sim_time, self._last_action),
            features=f,
            raw=vector,
            brief=sc.brief_observation(f, sim_time),
        )

    # ------------------------------------------------------------------ TextEnv

    def reset(self) -> Observation:
        if self._env is None:
            self._env = _build_bsk_env(self.conditions, self.params)
        self._last_action: str | None = None
        self._last_reward = 0.0
        self._alive = True
        self._failure: str | None = None
        self._log: list[dict[str, Any]] = []
        vector, _info = self._env.reset(seed=int(self.task.seed))
        self._ready = True
        observation = self._observe(vector)
        self._features_now = observation.features
        self._in_eclipse_now = bool(observation.features["in_eclipse"])
        return observation

    def parse_action(self, text: str) -> Action:
        return Action(match_action_name(text, sc.ACTIONS, sc.ACTION_ALIASES))

    def fallback_action(self) -> Action:
        return Action(sc.CHARGE)

    def step(self, action: Action) -> StepResult:
        if not self._ready:
            raise RuntimeError("call reset() before step()")
        if action.name not in _ACTION_INDEX:
            raise ActionParseError(f"unknown action {action.name!r}")
        t_before = float(self._env.simulator.sim_time)
        before = self._features_now
        in_eclipse_before = self._in_eclipse_now
        vector, reward, terminated, truncated, _info = self._env.step(_ACTION_INDEX[action.name])
        reward = float(reward)
        sim_time = float(self._env.simulator.sim_time)

        satellite = self._env.satellite
        if not satellite.is_alive():
            self._alive = False
            dynamics = satellite.dynamics
            if not dynamics.battery_valid():
                self._failure = "battery"
            elif not dynamics.rw_speeds_valid():
                self._failure = "wheels"
            else:
                self._failure = "other"

        self._last_action, self._last_reward = action.name, reward
        observation = self._observe(vector)
        f = observation.features
        self._features_now = f
        self._in_eclipse_now = bool(f["in_eclipse"])
        self._log.append(
            {
                "action": action.name,
                # The failure penalty is not recorded data; keep it out of the scan tally.
                "reward": reward + (1.0 if not self._alive else 0.0),
                "dt": sim_time - t_before,
                "battery": f["battery"],
                "wheel_speed": f["wheel_speed"],
                "in_eclipse_before": in_eclipse_before,
            }
        )
        # BSK-RL reports the time limit as termination; keep "terminated" for losses only.
        lost = not self._alive
        timed_out = (not lost) and (bool(terminated) or bool(truncated))
        info = {"sim_time_s": sim_time, "failure": self._failure}
        return StepResult(
            observation,
            reward,
            lost,
            timed_out,
            info,
            summary=sc.step_summary(before, f, reward),
            event=sc.end_event(self._alive, self._failure, timed_out),
        )

    def outcome(self) -> Outcome:
        metrics = sc.summarise_episode(self._log, self._alive, self._failure, self.params)
        score = sum(s["reward"] for s in self._log) - (0.0 if self._alive else 1.0)
        finished = metrics["elapsed_s"] >= self.params["duration_s"] - 1.0
        return Outcome(
            score=round(score, 6),
            success=bool(self._alive and metrics["scan_fraction"] >= self.params["success_score"]),
            failure=self._failure,
            terminated=not self._alive,
            truncated=self._alive and finished,
            metrics=metrics,
        )

    def close(self) -> None:
        if self._env is not None:
            # BSK-RL's close() assumes a simulator exists.
            with contextlib.suppress(AttributeError):
                self._env.close()
            self._env = None
        self._ready = False


register(BSKScanEnv.env_id, BSKScanEnv)
