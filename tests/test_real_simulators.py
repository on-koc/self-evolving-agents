"""Checks against the real simulators: Basilisk (via BSK-RL) and DiscoveryWorld.

Skipped when the optional packages are missing, or when Basilisk cannot obtain its
SPICE kernels (first use downloads them from naif.jpl.nasa.gov).
"""

from __future__ import annotations

import os

import pytest

from conftest import requires_bsk, requires_dw
from self_evolving_agents.agents import PolicyAgent
from self_evolving_agents.envs import ActionParseError, discoveryworld_task, make_env, scan_task
from self_evolving_agents.policies import always, scanning_policy
from self_evolving_agents.types import Action

pytestmark = pytest.mark.filterwarnings("ignore")

# --------------------------------------------------------------------------- Basilisk


@pytest.fixture(scope="module")
def bsk_ready():
    """Build one environment to make sure Basilisk and its kernels are usable."""
    env = make_env(scan_task("bsk-scan", seed=0))
    try:
        env.reset()
    except Exception as exc:  # noqa: BLE001 - any setup failure means "cannot test here"
        pytest.skip(f"Basilisk is installed but not usable here: {type(exc).__name__}: {exc}")
    finally:
        env.close()


def play(task, policy):
    env = make_env(task)
    try:
        traj = PolicyAgent(policy).run(env)
    finally:
        env.close()
    return traj


@requires_bsk
@pytest.mark.bsk
def test_bsk_episode_is_exactly_reproducible(bsk_ready):
    task = scan_task("bsk-scan", "nominal", seed=11)
    a, b = play(task, scanning_policy()), play(task, scanning_policy())
    assert a.outcome.to_dict() == b.outcome.to_dict()
    assert [s.action for s in a.steps] == [s.action for s in b.steps]
    assert [s.features for s in a.steps] == [s.features for s in b.steps]
    other = play(scan_task("bsk-scan", "nominal", seed=12), scanning_policy())
    assert other.outcome.to_dict() != a.outcome.to_dict()


@requires_bsk
@pytest.mark.bsk
def test_bsk_same_seed_gives_matched_initial_conditions_across_policies(bsk_ready):
    task = scan_task("bsk-scan", "nominal", seed=4)
    a, b = play(task, always("scan")), play(task, scanning_policy(charge_below=0.6))
    assert a.steps[0].features == b.steps[0].features, "matched seeds start from the same state"
    assert a.outcome.score != b.outcome.score


@requires_bsk
@pytest.mark.bsk
def test_bsk_retask_reuses_the_simulator_and_matches_a_fresh_one(bsk_ready):
    env = make_env(scan_task("bsk-scan", "nominal", seed=1))
    try:
        PolicyAgent(scanning_policy()).run(env)
        assert env.retask(scan_task("bsk-scan", "nominal", seed=11))
        reused = PolicyAgent(scanning_policy()).run(env)
        assert not env.retask(scan_task("bsk-scan", "small_battery", seed=11))
    finally:
        env.close()
    fresh = play(scan_task("bsk-scan", "nominal", seed=11), scanning_policy())
    assert reused.outcome.to_dict() == fresh.outcome.to_dict()


@requires_bsk
@pytest.mark.bsk
def test_bsk_features_are_sane_and_time_advances_by_the_action_duration(bsk_ready):
    env = make_env(scan_task("bsk-scan", "nominal", seed=3))
    try:
        observation = env.reset()
        f = observation.features
        assert set(f) == set(env.spec.feature_names)
        for name in ("battery", "storage", "wheel_speed", "time_frac"):
            assert 0.0 <= f[name] <= 1.0, name
        assert f["time_frac"] == 0.0 and f["time_left_s"] == 17100.0
        assert f["eclipse_start_s"] > 0 and f["eclipse_end_s"] > 0
        assert bool(f["in_eclipse"]) == (f["eclipse_start_s"] > f["eclipse_end_s"])
        assert f["gs_close_s"] > f["gs_open_s"] >= 0.0
        assert f"Battery {f['battery'] * 100:.0f}%" in observation.text

        elapsed = 0.0
        for name, duration in (
            ("scan", 180.0),
            ("charge", 120.0),
            ("downlink", 60.0),
            ("desat", 60.0),
        ):
            result = env.step(Action(name))
            elapsed += duration
            assert result.info["sim_time_s"] == pytest.approx(elapsed)
            assert result.observation.features[f"prev_{name}"] == 1.0
            assert result.summary.startswith("reward ")
        assert env.outcome().metrics["n_steps"] == 4
    finally:
        env.close()


@requires_bsk
@pytest.mark.bsk
def test_bsk_always_scanning_a_tiny_battery_loses_the_spacecraft(bsk_ready):
    traj = play(scan_task("bsk-scan", "tiny_battery", seed=0), always("scan"))
    outcome = traj.outcome
    assert outcome.failure == "battery" and outcome.success is False and outcome.terminated
    assert outcome.metrics["elapsed_s"] < 17100.0
    assert outcome.score == pytest.approx(outcome.metrics["scan_fraction"] - 1.0, abs=1e-5)
    assert traj.total_reward == pytest.approx(outcome.score, abs=1e-5)
    assert "battery was fully depleted" in traj.steps[-1].result
    assert outcome.metrics["min_battery"] == pytest.approx(0.0, abs=0.02)


@requires_bsk
@pytest.mark.bsk
def test_bsk_reference_policy_runs_to_the_time_limit(bsk_ready):
    traj = play(scan_task("bsk-scan", "nominal", seed=2), scanning_policy())
    m = traj.outcome.metrics
    assert traj.outcome.failure is None and traj.outcome.truncated and not traj.outcome.terminated
    assert m["elapsed_s"] == pytest.approx(17100.0)
    assert 0.0 < traj.outcome.score <= 1.0
    assert traj.outcome.score == pytest.approx(m["scan_fraction"], abs=1e-5)
    assert "time limit reached" in traj.steps[-1].result


@requires_bsk
@pytest.mark.bsk
def test_bsk_operating_conditions_change_the_physics(bsk_ready):
    """Halving the battery should roughly double the charge fraction a scan step uses."""

    def first_step_drop(conditions):
        env = make_env(
            scan_task(
                "bsk-scan",
                seed=7,
                conditions=conditions,
                init_battery_min=0.8,
                init_battery_max=0.8,
            )
        )
        try:
            start = env.reset().features["battery"]
            for _ in range(3):
                result = env.step(Action("downlink"))  # no station needed: just draws power
            return start, start - result.observation.features["battery"]
        finally:
            env.close()

    start_big, drop_big = first_step_drop({"battery_capacity_wh": 200.0, "panel_area_m2": 0.001})
    start_small, drop_small = first_step_drop(
        {"battery_capacity_wh": 100.0, "panel_area_m2": 0.001}
    )
    assert start_big == pytest.approx(0.8, abs=0.01) and start_small == pytest.approx(0.8, abs=0.01)
    assert drop_big > 0
    assert drop_small / drop_big == pytest.approx(2.0, rel=0.1)


# --------------------------------------------------------------------------- DiscoveryWorld

PICK_AND_PLACE = "Small Skills: Pick and Place Test"


def find_uuid(raw, name):
    """Look an object up by exact name in the raw observation (not shown to agents as such)."""
    for objects in raw["nearbyObjects"]["objects"].values():
        for obj in objects:
            if obj["name"] == name:
                return obj["uuid"]
    raise AssertionError(f"object {name!r} not found near the start position")


@requires_dw
@pytest.mark.discoveryworld
@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_discoveryworld_scripted_solution_completes_the_task(seed, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = make_env(discoveryworld_task(PICK_AND_PLACE, "Normal", seed=seed, max_steps=30))
    try:
        observation = env.reset()
        assert "pick up the `" in env.query and env.query.startswith("DiscoveryWorld task")
        thing, target = [part for i, part in enumerate(env.query.split("`")) if i % 2 == 1][:2]
        a, b = find_uuid(observation.raw, thing), find_uuid(observation.raw, target)
        assert f"[{a}] {thing}" in observation.text, "the rendered text names the object and its id"

        script = [
            f'{{"action": "TELEPORT_TO_OBJECT", "arg1": {a}}}',
            f'I will take it. {{"action": "pickup", "arg1": {a}}}',
            f'{{"action": "TELEPORT_TO_OBJECT", "arg1": {b}}}',
            f'{{"action": "PUT", "arg1": {a}, "arg2": {b}}}',
        ]
        for i, line in enumerate(script):
            result = env.step(env.parse_action(line))
            assert result.info["action_ok"], line
            assert result.reward == 0.0, "the oracle score is never handed out as reward"
            assert result.done == (i == len(script) - 1)
        assert result.terminated and "marked complete" in result.event
        assert thing in result.observation.brief or "carrying nothing" in result.observation.brief

        outcome = env.outcome()
        assert outcome.success is True and outcome.score == 1.0 and outcome.failure is None
        assert outcome.metrics["n_steps"] == 4 and outcome.metrics["invalid_actions"] == 0
        assert outcome.metrics["score_trace"][-1] == 1.0
        assert "Task status: complete" in result.observation.text
        for hidden in ("scoreNormalized", "scoreCard", "subgoal"):
            assert hidden not in result.observation.text
    finally:
        frame_dir = env._frame_dir
        env.close()
    assert not os.path.exists(tmp_path / "video"), "frames must not land in the working directory"
    assert not os.path.exists(frame_dir), "temporary frames are removed on close"


@requires_dw
@pytest.mark.discoveryworld
def test_discoveryworld_parsing_and_step_limit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = make_env(discoveryworld_task(PICK_AND_PLACE, "Normal", seed=0, max_steps=3))
    try:
        with pytest.raises(RuntimeError, match="reset"):
            _ = env.query
        env.reset()
        spec = env.spec
        assert "TELEPORT_TO_OBJECT" in spec.action_names and spec.feature_names == []
        assert "Teleport locations:" in spec.actions_doc

        assert env.parse_action('{"action": "move_direction", "arg1": "North"}') == Action(
            "MOVE_DIRECTION", {"arg1": "north"}
        )
        assert env.parse_action('{"chosen_dialog_option_int": "2"}') == Action(
            "DIALOG", {"chosen_dialog_option_int": 2}
        )
        for bad in (
            "no json here",
            '{"action": "FLY"}',
            '{"action": "MOVE_DIRECTION", "arg1": "up"}',
            "[1, 2]",
            '{"action": "USE", "arg1": }',
            '{"chosen_dialog_option_int": "two"}',
        ):
            with pytest.raises(ActionParseError):
                env.parse_action(bad)

        done = False
        while not done:
            result = env.step(env.parse_action('{"action": "PICKUP", "arg1": 999999}'))
            done = result.done
        assert result.truncated and not result.terminated
        assert "step limit reached" in result.event
        outcome = env.outcome()
        assert outcome.success is False and outcome.failure == "incomplete"
        assert outcome.metrics["invalid_actions"] == 3 and outcome.metrics["n_steps"] == 3
    finally:
        env.close()


@requires_dw
@pytest.mark.discoveryworld
def test_discoveryworld_rejects_unknown_scenarios(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = make_env(discoveryworld_task("Not A Scenario", "Normal"))
    with pytest.raises(ValueError, match="could not load"):
        env.reset()
