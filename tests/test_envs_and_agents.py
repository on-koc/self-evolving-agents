"""The toy scanning environment and the three agent types (no simulator, no real model)."""

from __future__ import annotations

import json

import pytest

from self_evolving_agents.agents import (
    PolicyAgent,
    PolicyProgramAgent,
    StepwiseAgent,
    extract_json_object,
    parse_reply,
)
from self_evolving_agents.envs import ActionParseError, available_envs, make_env, scan_task
from self_evolving_agents.envs import scanning as sc
from self_evolving_agents.envs.base import match_action_name
from self_evolving_agents.llm import Budget, BudgetExceeded, LLMRefusal, ScriptedLLM, TrackedLLM
from self_evolving_agents.policies import always, scanning_policy
from self_evolving_agents.reasoningbank.schema import MemoryItem
from self_evolving_agents.types import Action, Task


def play(env, policy):
    observation = env.reset()
    done = False
    while not done:
        result = env.step(Action(policy.act(observation.features)))
        observation, done = result.observation, result.done
    return result, env.outcome()


# --------------------------------------------------------------------------- task construction


def test_scan_task_merges_regime_and_overrides():
    task = scan_task("toy-scan", "small_battery", seed=4, conditions={"panel_area_m2": 0.1})
    assert task.conditions["battery_capacity_wh"] == 50.0
    assert task.conditions["panel_area_m2"] == 0.1
    assert task.conditions["instrument_power_w"] == sc.DEFAULT_CONDITIONS["instrument_power_w"]
    assert task.name == "small_battery+custom"
    with pytest.raises(KeyError):
        scan_task("toy-scan", "no_such_regime")
    with pytest.raises(KeyError):
        scan_task("toy-scan", conditions={"warp_factor": 9})
    with pytest.raises(KeyError):
        scan_task("toy-scan", not_a_param=1)


def test_registry_lists_all_adapters_and_rejects_unknown():
    assert {"toy-scan", "bsk-scan", "discoveryworld"} <= set(available_envs())
    with pytest.raises(KeyError, match="unknown environment"):
        make_env(Task("nope", "x"))


def test_query_states_the_operating_conditions():
    query = make_env(scan_task("toy-scan", "small_battery")).query
    assert "50 Wh" in query and "17100 s" in query
    assert "charge when" not in query.lower(), "the task statement must not contain strategy advice"


# --------------------------------------------------------------------------- toy dynamics


def test_toy_episode_is_reproducible_and_seed_dependent():
    policy = scanning_policy()
    _, a = play(make_env(scan_task("toy-scan", seed=5)), policy)
    _, b = play(make_env(scan_task("toy-scan", seed=5)), policy)
    _, c = play(make_env(scan_task("toy-scan", seed=6)), policy)
    assert a.to_dict() == b.to_dict()
    assert a.to_dict() != c.to_dict()


def test_toy_retask_reuses_the_instance_only_for_the_same_configuration():
    env = make_env(scan_task("toy-scan", "nominal", seed=1))
    assert env.retask(scan_task("toy-scan", "nominal", seed=2))
    assert env.task.seed == 2
    assert not env.retask(scan_task("toy-scan", "small_battery", seed=2))
    assert not env.retask(scan_task("toy-scan", "nominal", seed=2, duration_s=5700.0))
    with pytest.raises(RuntimeError):
        env.step(Action("scan"))  # retask requires a fresh reset


def test_always_scanning_drains_the_battery():
    result, outcome = play(make_env(scan_task("toy-scan", "small_battery", seed=0)), always("scan"))
    assert result.terminated and not result.truncated
    assert outcome.failure == "battery" and outcome.success is False
    assert outcome.score == pytest.approx(outcome.metrics["scan_fraction"] - 1.0)
    assert "battery was fully depleted" in result.event
    assert result.reward < 0


def test_high_disturbance_without_desat_saturates_the_wheels():
    task = scan_task("toy-scan", conditions={"disturbance_torque_nm": 1e-2})
    result, outcome = play(make_env(task), always("charge"))
    assert outcome.failure == "wheels"
    assert "reaction wheel" in result.event


def test_reference_policy_survives_and_reports_mediators():
    result, outcome = play(make_env(scan_task("toy-scan", seed=2)), scanning_policy())
    assert result.truncated and not result.terminated
    assert outcome.failure is None and outcome.metrics["alive"]
    m = outcome.metrics
    assert m["elapsed_s"] == pytest.approx(17100.0)
    assert m["time_scan_s"] + m["time_charge_s"] + m["time_downlink_s"] + m[
        "time_desat_s"
    ] == pytest.approx(17100.0)
    assert 0 <= m["min_battery"] <= 1 and m["mode_switches"] > 0
    assert outcome.score == pytest.approx(m["scan_fraction"])


def test_scanning_a_full_buffer_earns_nothing():
    task = scan_task("toy-scan", init_storage_min=1.0, init_storage_max=1.0)
    env = make_env(task)
    env.reset()
    result = env.step(Action("scan"))
    assert result.reward == 0.0
    assert "buffer 100%->100%" in result.summary


def test_observation_text_and_features_agree():
    env = make_env(scan_task("toy-scan", seed=9))
    observation = env.reset()
    f = observation.features
    assert set(f) == set(env.spec.feature_names)
    assert f"Battery {f['battery'] * 100:.0f}%" in observation.text
    assert ("In eclipse" in observation.text) == bool(f["in_eclipse"])
    assert ("Ground station in view" in observation.text) == bool(f["gs_in_view"])
    assert observation.brief.startswith("t=0s")
    after = env.step(Action("charge")).observation
    assert after.features["prev_charge"] == 1.0 and after.features["prev_scan"] == 0.0
    assert "Last action: charge" in after.text


def test_action_parsing():
    names = sc.ACTIONS
    assert match_action_name("scan", names) == "scan"
    assert match_action_name("  `Charge`. ", names) == "charge"
    assert match_action_name("I will downlink now", names) == "downlink"
    assert match_action_name("recharge", names, sc.ACTION_ALIASES) == "charge"
    with pytest.raises(ActionParseError, match="several"):
        match_action_name("scan or charge", names)
    with pytest.raises(ActionParseError, match="not one of"):
        match_action_name("hover", names)
    with pytest.raises(ActionParseError):
        match_action_name("rescanning", names)  # substrings of other words do not count


# --------------------------------------------------------------------------- reply parsing


@pytest.fixture
def toy():
    env = make_env(scan_task("toy-scan", seed=1, duration_s=1800.0))
    env.reset()
    return env


def test_parse_reply_variants(toy):
    assert parse_reply("<think>low battery</think><action>charge</action>", toy) == (
        "low battery",
        Action("charge"),
    )
    thought, action = parse_reply("Battery is fine.\n<action> SCAN </action>", toy)
    assert thought == "Battery is fine." and action == Action("scan")
    # several action blocks: the last one is the decision
    assert parse_reply("<action>scan</action> no wait <action>desat</action>", toy)[1] == Action(
        "desat"
    )
    # no tags at all, but the text is a clean action
    assert parse_reply("<think>x</think>\ndownlink", toy)[1] == Action("downlink")


@pytest.mark.parametrize(
    "reply",
    [
        "",
        "<think>still thinking",
        "<action></action>",
        "<action>teleport</action>",
        "<action>scan charge</action>",
    ],
)
def test_parse_reply_rejects_unusable_replies(toy, reply):
    with pytest.raises(ActionParseError):
        parse_reply(reply, toy)


def test_extract_json_object():
    assert extract_json_object('text ```json\n{"a": 1}\n``` more') == {"a": 1}
    assert extract_json_object('first ```json\n{"a": 1}\n``` then ```json\n{"a": 2}\n```') == {
        "a": 2
    }
    assert extract_json_object('no fence {"a": {"b": 2}} trailing') == {"a": {"b": 2}}
    for bad in ["nothing here", "```json\n{broken\n```", "[1, 2]"]:
        with pytest.raises(ValueError):
            extract_json_object(bad)


# --------------------------------------------------------------------------- agents


def short_task(seed=1):
    return scan_task("toy-scan", seed=seed, duration_s=1800.0)


def test_policy_agent_records_a_complete_trajectory():
    traj = PolicyAgent(scanning_policy()).run(make_env(short_task()))
    assert traj.outcome is not None and traj.finished_at is not None
    assert [s.index for s in traj.steps] == list(range(len(traj.steps)))
    assert all(s.action in sc.ACTIONS for s in traj.steps)
    assert traj.steps[-1].result.endswith("time limit reached with the spacecraft alive.")
    assert traj.total_reward == pytest.approx(traj.outcome.score)
    assert traj.agent["type"] == "rule-policy" and "policy_text" in traj.meta
    assert traj.steps[0].features["time_frac"] == 0.0
    assert "rule" in traj.steps[0].info


def test_stepwise_agent_prompts_contain_task_memory_and_history():
    llm = ScriptedLLM("<think>go</think><action>scan</action>")
    item = MemoryItem("Keep a reserve", "when low", "charge early")
    traj = StepwiseAgent(llm, history_window=2).run(
        make_env(short_task()), memory=[item], notes="be careful"
    )

    first, later = llm.requests[0], llm.requests[-1]
    assert first.purpose == "act"
    assert first.system == later.system, "the system prompt must stay fixed so it can be cached"
    for needle in (
        "## Actions",
        "## Task",
        "50 Wh" if False else "200 Wh",
        "<action>",
        "Keep a reserve",
        "be careful",
        "explicitly discuss if you want to use each memory item",
    ):
        assert needle in first.system
    assert "## Recent steps" not in first.messages[0]["content"]
    content = later.messages[0]["content"]
    assert "## Recent steps" in content and "earlier steps not shown" in content
    assert content.count("\nstep ") + content.count("step ") >= 2
    assert "your reasoning then: go" in content
    assert "## Current observation" in content
    assert traj.memory_item_ids == [item.id]
    assert all(s.thought == "go" and s.llm_call_id is None for s in traj.steps), (
        "bare backends give no call ids"
    )


def test_stepwise_agent_without_memory_has_no_memory_block():
    llm = ScriptedLLM("<action>scan</action>")
    StepwiseAgent(llm).run(make_env(short_task()))
    assert "memory items" not in llm.requests[0].system


def test_stepwise_agent_retries_then_falls_back():
    replies = iter(["garbage", "<action>charge</action>"] + ["nonsense"] * 100)
    llm = ScriptedLLM(lambda r: next(replies))
    traj = StepwiseAgent(llm, parse_retries=1).run(make_env(short_task()))

    assert traj.steps[0].action == "charge", "the retry succeeded"
    assert traj.steps[0].info["parse_attempts"] == 2
    retry = llm.requests[1]
    assert [m["role"] for m in retry.messages] == ["user", "assistant", "user"]
    assert "could not be used" in retry.messages[-1]["content"]

    assert traj.steps[1].info.get("fallback") is True
    assert traj.steps[1].action == make_env(short_task()).fallback_action().name
    assert traj.outcome is not None, "an unparsable model must not crash the episode"


def test_stepwise_agent_survives_refusals_but_not_a_spent_budget():
    def refuse(request):
        raise LLMRefusal("declined")

    traj = StepwiseAgent(ScriptedLLM(refuse)).run(make_env(short_task()))
    assert all("llm_error" in s.info for s in traj.steps)

    budgeted = TrackedLLM(ScriptedLLM("<action>scan</action>"), budget=Budget(max_calls=3))
    with pytest.raises(BudgetExceeded):
        StepwiseAgent(budgeted).run(make_env(short_task()))


def test_tracked_llm_gives_steps_call_ids():
    traj = StepwiseAgent(TrackedLLM(ScriptedLLM("<action>scan</action>"))).run(
        make_env(short_task())
    )
    ids = [s.llm_call_id for s in traj.steps]
    assert all(ids) and len(set(ids)) == len(ids)


VALID_POLICY = {
    "name": "mine",
    "params": {"low": 0.3},
    "rules": [{"if": {"battery": {"<": "$low"}}, "do": "charge"}],
    "default": "scan",
}


def test_policy_program_agent_executes_the_models_policy():
    llm = ScriptedLLM("Rationale: keep a reserve.\n```json\n" + json.dumps(VALID_POLICY) + "\n```")
    traj = PolicyProgramAgent(llm).run(make_env(short_task()))
    assert len(llm.requests) == 1, "one call for the whole episode"
    assert llm.requests[0].purpose == "policy"
    system = llm.requests[0].system
    assert "`battery`: battery state of charge" in system and "`scan`" in system
    assert traj.meta["policy"]["params"] == {"low": 0.3}
    assert traj.meta["policy_rationale"].startswith("Rationale")
    assert "policy_error" not in traj.meta
    assert {s.action for s in traj.steps} <= {"scan", "charge"}


def test_policy_program_agent_feeds_validation_errors_back():
    broken = dict(VALID_POLICY, rules=[{"if": {"altitude": {"<": 1}}, "do": "charge"}])
    llm = ScriptedLLM(
        [
            "```json\n" + json.dumps(broken) + "\n```",
            "```json\n" + json.dumps(VALID_POLICY) + "\n```",
        ]
    )
    traj = PolicyProgramAgent(llm).run(make_env(short_task()))
    assert traj.meta["policy_attempts"] == 2
    assert "unknown feature(s) altitude" in llm.requests[1].messages[-1]["content"]
    assert traj.meta["policy"]["name"] == "mine"


def test_policy_program_agent_falls_back_when_no_valid_policy_arrives():
    traj = PolicyProgramAgent(ScriptedLLM("I refuse to write JSON"), max_attempts=2).run(
        make_env(short_task())
    )
    assert "no JSON object" in traj.meta["policy_error"]
    assert {s.action for s in traj.steps} == {"charge"}
