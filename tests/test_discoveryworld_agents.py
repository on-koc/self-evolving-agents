"""DiscoveryWorld's own baselines (ReAct, Plan-and-Execute, random), every scenario, and
how they combine with this repository's methods.

The fidelity tests compare the ports with fingerprints of what DiscoveryWorld's released
code did when given the same scripted replies (``dw_scripted.py``): every prompt of
ReAct and Plan-and-Execute, every action of the random agent.
"""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import dw_scripted
from conftest import requires_dw
from self_evolving_agents.agents.discoveryworld import prompts, recoma
from self_evolving_agents.agents.discoveryworld.plan_execute import (
    executer_input,
    extract_step,
    planner_input,
)
from self_evolving_agents.agents.discoveryworld.random_agent import random_action
from self_evolving_agents.llm import LLMRequest, LLMResponse, TrackedLLM, apply_stop
from self_evolving_agents.types import Action

DATA = Path(__file__).parent / "data"
REFERENCE = json.loads((DATA / "discoveryworld_baseline_prompts.json").read_text())
RANDOM_REFERENCE = json.loads((DATA / "discoveryworld_random_agent_actions.json").read_text())


class Scripted:
    """The scripted model of ``dw_scripted.py``, recording every request."""

    model = "scripted"

    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(text=dw_scripted.reply(request.messages, request.max_tokens), model="s")


# --------------------------------------------------------------------------- templates


def test_templates_are_the_released_files():
    for name, variable in (
        ("react_prompt.txt", prompts.REACT_TEMPLATE),
        ("executer_prompt.txt", prompts.EXECUTER_TEMPLATE),
        ("planner_prompt.txt", prompts.PLANNER_TEMPLATE),
    ):
        assert hashlib.sha256(variable.encode()).hexdigest() == REFERENCE["templates"][name]


def test_renderer_matches_jinja():
    jinja2 = pytest.importorskip("jinja2")
    rng = random.Random(0)
    pool = ["x", "{{ input_str }}", "a\nb\n", "", "{% else %}", '{\n    "a": 1\n}', "end\n"]
    keys = [
        "facing_direction",
        "additional_instructions",
        "input_str",
        "observation",
        "dialog_box",
        "known_actions",
        "teleport_destinations",
        "interactable_objects",
    ]
    for template in (prompts.REACT_TEMPLATE, prompts.EXECUTER_TEMPLATE, prompts.PLANNER_TEMPLATE):
        for _ in range(60):
            values: dict[str, Any] = {k: rng.choice(pool) for k in keys}
            values["valid_dirs"] = rng.choice([["north", "east"], []])
            values["in_dialog"] = rng.choice([True, False])
            assert prompts.render(template, values) == jinja2.Template(template).render(values)


# --------------------------------------------------------------------------- ReComA pieces


def test_role_messages_follow_recoma():
    assert recoma.extract_role_messages("just text") == [{"role": "user", "content": "just text"}]
    text = "USER:\nhello\nASSISTANT:\nStep 1: go\nUSER:\n --done\n"
    assert recoma.extract_role_messages(text) == [
        {"role": "user", "content": "hello\n"},
        {"role": "assistant", "content": "Step 1: go\n"},
        {"role": "user", "content": " --done\n"},
    ]
    # Roles are matched in any letter case once a capitalised ASSISTANT line is present.
    mixed = recoma.extract_role_messages("USER:\na user:\nb\nASSISTANT:\nc")
    assert [m["role"] for m in mixed] == ["user", "user", "assistant"]
    with pytest.raises(ValueError, match="no assigned role"):
        recoma.extract_role_messages("preamble\nASSISTANT:\nx")


def test_json_extraction_follows_the_react_controller():
    full = 'Thinking.\n```json\n{"action": "PICKUP", "arg1": 5}\n```\nmore'
    assert recoma.extract_json_output(full) == ('{"action": "PICKUP", "arg1": 5}',) * 2
    partial = 'x ```json\n{"a": 1}\n```json\n{"action": "EAT"}\n'
    assert recoma.extract_json_output(partial)[0] == '{"a": 1}'  # first full block wins
    cut = 'note\n```json\n{"action": "EAT", "arg1": 3}\n'
    assert recoma.extract_json_output(cut) == ('{"action": "EAT", "arg1": 3}',) * 2
    assert recoma.extract_json_output('{"action": "READ"}') == ('{"action": "READ"}',) * 2
    assert recoma.extract_json_output("no json here")[0] is None


def test_history_is_trimmed_newest_first_and_warned():
    history = recoma.ReactHistory()
    for i in range(30):
        history.add_action(json.dumps({"action": "X", "thought": "Task: " + "t" * 200, "i": i}), {})
        history.add_observation(json.dumps({"errors": [], "success": True, "i": i}))
    text = recoma.react_input("Do it.", history, max_output_length=2000)
    assert len(text) <= 2000 and text.startswith("Do it.\n\nHistory of action-observations:\n")
    assert '"i": 29' in text and '"i": 0,' not in text  # the newest entries are kept
    assert "Task :" in text and "Task: t" not in text  # ReComA's guard for the task line
    warned = recoma.react_input("Do it.", history, termination_suggestion=10)
    assert warned.endswith(recoma.CONTINUE_WARNING)
    assert not recoma.react_input("Do it.", history, termination_suggestion=40).endswith(
        recoma.CONTINUE_WARNING
    )
    # A task text longer than the limit makes the original loop forever; the port stops.
    long = recoma.react_input("x" * 50, history, max_output_length=20)
    assert long.startswith("x" * 50) and recoma.TRIMMED in long


def test_planner_and_executer_inputs():
    plan = [("Step 1: Find the key", "Task completed!got it"), ("Go", "Task failed!no")]
    assert planner_input("Open the door.", plan) == (
        "Open the door.\n\nPlan:\nASSISTANT:\nStep 1: Find the key\nUSER:\n --Task completed!got it\n"
        "ASSISTANT:\nGo\nUSER:\n --Task failed!no\n"
    )
    assert executer_input("Step 3: Open it", plan) == (
        "**Step 3: Open it**\n\nPrevious Sub-Tasks:\nSubtask 1: Find the key\n Result: Task "
        "completed!got it\nSubtask 2: Go\n Result: Task failed!no\n"
    )
    assert extract_step("Step 12: Walk") == "Walk" and extract_step("Walk") == "Walk"


# --------------------------------------------------------------------------- stop strings


def test_stop_strings_cut_the_reply_and_key_the_cache(tmp_path):
    class Echo:
        model = "echo"

        def complete(self, request):
            return LLMResponse(text='{"a": 1}\n```\nafter', model="echo")

    llm = TrackedLLM(Echo(), cache_dir=tmp_path)
    plain = LLMRequest(system="", messages=[{"role": "user", "content": "q"}])
    stopped = LLMRequest(system="", messages=[{"role": "user", "content": "q"}], stop=["```\n"])
    assert llm.complete(stopped).text == '{"a": 1}\n'
    assert llm.complete(plain).text.endswith("after")
    assert plain.cache_key("m") != stopped.cache_key("m")
    assert apply_stop("a\nb```\nc", ["\n", "```\n"]) == "a"


def test_backends_pass_stop_strings(fake_openai, fake_ollama):
    from self_evolving_agents.llm import make_backend

    request = LLMRequest(
        system="", messages=[{"role": "user", "content": "q"}], max_tokens=50, stop=["```\n", "\n"]
    )
    make_backend(f"openai:m@{fake_openai.base_url}").complete(request)
    assert fake_openai.requests[-1]["body"]["stop"] == ["```\n", "\n"]
    make_backend(f"ollama:m@{fake_ollama.base_url}").complete(request)
    assert fake_ollama.requests[-1]["body"]["options"]["stop"] == ["```\n", "\n"]
    anthropic = pytest.importorskip("anthropic")
    from self_evolving_agents.llm.anthropic_backend import AnthropicBackend

    backend = AnthropicBackend("claude-opus-5-5", client=anthropic.Anthropic(api_key="x"))
    # Whitespace-only stop sequences are refused by the API; they are applied afterwards.
    assert backend._params(request)["stop_sequences"] == ["```\n"]


# --------------------------------------------------------------------------- fidelity


def run_port(agent: str, scenario: str, difficulty: str, seed: int, max_steps: int):
    from self_evolving_agents.agents.discoveryworld import PlanExecuteAgent, ReActAgent
    from self_evolving_agents.envs import discoveryworld_task, make_env

    llm = Scripted()
    env = make_env(discoveryworld_task(scenario, difficulty, seed=seed, max_steps=max_steps))
    try:
        first = env.reset()
        cls = ReActAgent if agent == "react" else PlanExecuteAgent
        traj = cls(llm).run(env, first_observation=first)
    finally:
        env.close()
    return traj, llm


@requires_dw
@pytest.mark.discoveryworld
@pytest.mark.parametrize("case", range(len(REFERENCE["cases"])))
def test_ports_send_the_released_agents_prompts(case, tmp_path, monkeypatch):
    """Every prompt of the ports is byte-identical to DiscoveryWorld's released agent's."""
    monkeypatch.chdir(tmp_path)
    fixture = REFERENCE["cases"][case]
    scenario, difficulty, seed = fixture["world"]
    traj, llm = run_port(fixture["agent"], scenario, difficulty, seed, fixture["max_steps"])
    produced = [
        {
            "sha256": dw_scripted.fingerprint(r.messages),
            "messages": len(r.messages),
            "max_tokens": r.max_tokens,
            "stop": r.stop,
            "temperature": r.temperature,
        }
        for r in llm.requests
    ]
    original = fixture["calls"]
    for i, (ours, theirs) in enumerate(zip(produced, original, strict=False)):
        assert ours == theirs, f"call {i} differs from the released agent's"
    # The released runner asks once more after the step limit and discards the answer.
    assert len(original) - len(produced) in (0, 1)
    if len(original) > len(produced):
        assert traj.outcome.metrics["ended_by"] == "step_limit"
    assert traj.outcome.metrics["n_steps"] == fixture["actions"]
    assert all(r.system == "" for r in llm.requests)


@requires_dw
@pytest.mark.discoveryworld
@pytest.mark.parametrize("case", range(len(RANDOM_REFERENCE["cases"])))
def test_random_agent_takes_the_released_agents_actions(case, tmp_path, monkeypatch):
    from self_evolving_agents.agents.discoveryworld import RandomAgent
    from self_evolving_agents.envs import discoveryworld_task, make_env

    monkeypatch.chdir(tmp_path)
    fixture = RANDOM_REFERENCE["cases"][case]
    scenario, difficulty, seed = fixture["world"]
    env = make_env(discoveryworld_task(scenario, difficulty, seed=seed, max_steps=fixture["steps"]))
    try:
        traj = RandomAgent(rng_seed=fixture["rng_seed"]).run(env, first_observation=env.reset())
    finally:
        env.close()
    expected = []
    for action in fixture["actions"]:
        if "chosen_dialog_option_int" in action:
            expected.append(Action("DIALOG", dict(action)).render())
        else:
            args = {k: action[k] for k in ("arg1", "arg2") if action.get(k) is not None}
            expected.append(Action(action["action"], args).render())
    assert [s.action for s in traj.steps] == expected


def test_random_agent_answers_dialogs():
    class Env:
        def in_dialog(self):
            return True

    observation = {"ui": {"dialog_box": {"dialogOptions": {1: "yes", 2: "no", 3: "bye"}}}}
    choices = {
        random_action(random.Random(i), Env(), observation)["chosen_dialog_option_int"]
        for i in range(30)
    }
    assert choices == {1, 2, 3}


# --------------------------------------------------------------------------- environment


@requires_dw
@pytest.mark.discoveryworld
def test_submit_raw_actions_and_the_logging_read(tmp_path, monkeypatch):
    from self_evolving_agents.envs import discoveryworld_task, make_env

    monkeypatch.chdir(tmp_path)

    def measure(read_after_action: bool) -> tuple[str, Any]:
        env = make_env(
            discoveryworld_task(
                "Small Skills: Instrument Measurement Test", "Normal", seed=0, max_steps=10
            )
        )
        try:
            env.reset()
            env.read_after_action = read_after_action
            ui = env.api_observation()["ui"]
            nearby = [o for objs in ui["nearbyObjects"]["objects"].values() for o in objs]
            meter = next(o for o in nearby if "meter" in o["name"])
            env.step(Action("TELEPORT_TO_OBJECT", {"arg1": meter["uuid"]}))
            env.step(Action("PICKUP", {"arg1": meter["uuid"]}))
            ui = env.api_observation()["ui"]
            reach = [o for o in ui["accessibleEnvironmentObjects"]]
            result = env.step(Action("USE", {"arg1": meter["uuid"], "arg2": reach[0]["uuid"]}))
            assert "PH meter" in result.summary or "meter" in result.summary
            return env.api_observation()["ui"]["extended_action_message"], env
        finally:
            env.close()

    shown, _ = measure(False)
    hidden, _ = measure(True)
    # A reading is a high-importance message; the released runs' logging read removes it.
    assert "meter" in shown and hidden == ""

    env = make_env(discoveryworld_task("Combinatorial Chemistry", "Easy", seed=0, max_steps=5))
    try:
        env.reset()
        result = env.step(Action("FLY", {}, payload={"action": "FLY", "thought": "x"}))
        assert env.last_action_result() == {"errors": [], "success": False}
        assert "Unknown action 'FLY'" in result.summary
        before = env.api_observation()["ui"]["world_steps"]
        done = env.step(Action("SUBMIT", {"arg1": "Task completed!"}))
        assert done.done and done.info["submitted"]
        assert env.api_observation()["ui"]["world_steps"] == before  # no time passed
        outcome = env.outcome()
        assert outcome.metrics["n_steps"] == 1 and outcome.metrics["ended_by"] == "agent_submitted"
    finally:
        env.close()


@requires_dw
@pytest.mark.discoveryworld
def test_worlds_are_the_same_in_every_process(tmp_path):
    """DiscoveryWorld seeds object generators from the clock; the adapter seeds them."""
    code = (
        "import hashlib, json\n"
        "from self_evolving_agents.envs import discoveryworld_task, make_env\n"
        "from self_evolving_agents.types import Action\n"
        "out = []\n"
        "for s, d in (('Small Skills: Instrument Measurement Test', 'Normal'), ('Space Sick', 'Normal')):\n"
        "    env = make_env(discoveryworld_task(s, d, seed=1))\n"
        "    env.reset()\n"
        "    for _ in range(8):\n"
        "        env.step(Action('NOOP'))\n"
        "    out.append(hashlib.sha256(json.dumps(env.api_observation(), sort_keys=True).encode()).hexdigest())\n"
        "print(out)\n"
    )
    runs = [
        subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={**__import__("os").environ, "SDL_VIDEODRIVER": "dummy"},
            check=True,
        )
        .stdout.strip()
        .splitlines()[-1]
        for _ in range(2)
    ]
    assert runs[0] == runs[1]


@requires_dw
@pytest.mark.discoveryworld
@pytest.mark.parametrize(
    "scenario,difficulty",
    [
        pytest.param(s, d, id=f"{s}-{d}")
        for s, d in __import__("self_evolving_agents.envs", fromlist=["x"]).all_scenarios()
    ],
)
def test_every_scenario_loads_and_steps(scenario, difficulty, tmp_path, monkeypatch):
    from self_evolving_agents.envs import answer_key, discoveryworld_task, make_env, scenario_kind

    monkeypatch.chdir(tmp_path)
    task = discoveryworld_task(scenario, difficulty, seed=0)
    env = make_env(task)
    try:
        env.reset()
        assert env.query and len(env.spec.action_names) == 17
        result = env.step(env.fallback_action())
        assert not result.truncated
        outcome = env.outcome()
        assert outcome.metrics["subgoals_total"] >= 1
        assert outcome.metrics["max_steps"] == task.params["max_steps"]
    finally:
        env.close()
    questions = [q for t in answer_key(scenario, difficulty, 0) for q in t["critical_questions"]]
    # Discovery themes hide a discovery; unit tests and the tutorial test skills only.
    assert bool(questions) == (scenario_kind(scenario) == "theme")


def test_step_limits_and_scenario_validation():
    from self_evolving_agents.envs import discoveryworld_task, paper_step_limit
    from self_evolving_agents.tasks import expand_scenarios, task_stream

    assert discoveryworld_task("Proteomics", "Easy").params["max_steps"] == 100
    assert discoveryworld_task("Proteomics", "Challenge").params["max_steps"] == 1000
    assert discoveryworld_task("Small Skills: Search Test").params["max_steps"] == 100
    assert discoveryworld_task("Proteomics", "Normal", max_steps=7).params["max_steps"] == 7
    assert paper_step_limit("Tutorial", "Normal") == 100
    with pytest.raises(ValueError, match="Normal"):
        discoveryworld_task("Small Skills: Search Test", "Easy")
    with pytest.raises(ValueError, match="unknown DiscoveryWorld scenario"):
        discoveryworld_task("Alchemy", "Easy")
    assert len(expand_scenarios(["themes"])) == 8 and len(expand_scenarios(["unit-tests"])) == 10
    stream = task_stream(
        "discoveryworld", [0, 1], scenarios=["Proteomics"], difficulty=["Easy", "Normal"]
    )
    assert [(t.conditions["difficulty"], t.params["max_steps"]) for t in stream] == [
        ("Easy", 100),
        ("Easy", 100),
        ("Normal", 1000),
        ("Normal", 1000),
    ]


# --------------------------------------------------------------------------- combinations


def test_agents_resolve_and_impossible_combinations_are_refused(tmp_path):
    from self_evolving_agents.methods.registry import (
        check_combination,
        default_agent,
        protocol_agent,
        resolve_agent,
    )

    assert default_agent("reasoningbank") == "stepwise"
    assert default_agent("investigation_memory") == "hypothesizer"
    assert resolve_agent("investigation_memory", "stepwise") == "stepwise"
    assert resolve_agent("reasoningbank", "react") == "react"
    with pytest.raises(ValueError, match="its own agent"):
        resolve_agent("hypothesizer", "react")
    with pytest.raises(ValueError, match="reads no memory"):
        resolve_agent("reasoningbank", "random")
    with pytest.raises(ValueError, match="named numeric"):
        check_combination("policy_program", None, {"discoveryworld"})
    with pytest.raises(ValueError, match="plays discoveryworld"):
        check_combination("no_memory", "react", {"toy-scan"})
    with pytest.raises(ValueError, match="say nothing about discoveryworld"):
        check_combination(
            "claim_memory", None, {"discoveryworld"}, {"claims": "results/bsk-battery"}
        )
    assert check_combination("matts", "plan_execute", {"discoveryworld"}) == "plan_execute"
    protocol = {"agent": "hypothesizer", "agent_options": {"observation": "json"}}
    assert protocol_agent(protocol, {"method": "reasoningbank"}) == (
        "hypothesizer",
        {"observation": "json"},
    )
    # The protocol's agent options belong to the protocol's agent only.
    assert protocol_agent(protocol, {"method": "no_memory", "agent": "react"}) == ("react", {})
    assert protocol_agent({"agent": "react"}, {"method": "hypothesizer"})[0] == "hypothesizer"


@requires_dw
@pytest.mark.discoveryworld
@pytest.mark.parametrize(
    "method,agent",
    [
        ("no_memory", "react"),
        ("no_memory", "plan_execute"),
        ("no_memory", "random"),
        ("reasoningbank", "react"),
        ("reasoningbank", "plan_execute"),
        ("investigation_memory", "react"),
        ("investigation_memory", "stepwise"),
        ("conditioned_retrieval", "react"),
        ("matts", "react"),
    ],
)
def test_methods_run_with_discoveryworlds_agents(method, agent, tmp_path, monkeypatch):
    from self_evolving_agents.envs import discoveryworld_task
    from self_evolving_agents.methods.run import run_method

    monkeypatch.chdir(tmp_path)
    tasks = [
        discoveryworld_task("Combinatorial Chemistry", "Easy", seed=s, max_steps=4) for s in (0, 1)
    ]
    options = {"scaling": "parallel", "scaling_k": 2} if method == "matts" else None
    status, summary = run_method(
        method,
        tasks,
        tmp_path / "run",
        llm="offline-demo",
        agent=agent,
        options=options,
        quiet=True,
    )
    assert status == 0 and summary["completed"] == 2
    config = json.loads((tmp_path / "run" / "config.json").read_text())
    assert config["agent"].get("kind", config["agent"].get("type")) == agent
    if method in ("reasoningbank", "investigation_memory", "conditioned_retrieval"):
        assert summary["metrics"]["new_items"] > 0


@requires_dw
@pytest.mark.discoveryworld
def test_design_check_catches_a_new_world_with_a_seen_answer():
    from self_evolving_agents.discovery.experiment import check_design, load_protocol

    protocol = load_protocol(Path(__file__).parent.parent / "protocols" / "discovery_main.json")
    assert check_design(protocol)["problems"] == []
    protocol["experience"]["worlds"] = [
        {"scenario": "Combinatorial Chemistry", "difficulty": "Easy", "seeds": [0, 1, 2]},
        {"scenario": "Archaeology Dating", "difficulty": "Easy", "seeds": [0, 1, 2]},
    ]
    protocol["transfer"] = {
        "same_world": [{"scenario": "Combinatorial Chemistry", "difficulty": "Easy", "seeds": [0]}],
        "new_world": [
            {"scenario": "Combinatorial Chemistry", "difficulty": "Easy", "seeds": [3, 4]},
            {"scenario": "Archaeology Dating", "difficulty": "Easy", "seeds": [3]},
        ],
        "new_theme": [{"scenario": "Proteomics", "difficulty": "Easy", "seeds": [0]}],
    }
    design = check_design(protocol)
    assert design["problems"] == [
        "new_world: Combinatorial Chemistry / Easy / seed 4 hides the same answer as experience "
        "world Combinatorial Chemistry / Easy / seed 2"
    ]
    assert any("Archaeology Dating / Easy / seed 3 shares 1 of 2" in w for w in design["warnings"])


def test_cli_lists_agents_and_discoveryworld_scenarios(capsys):
    from self_evolving_agents.cli import main

    assert main(["agents"]) == 0
    out = capsys.readouterr().out
    assert "plan_execute" in out and "reads memory: no" in out
    assert main(["envs"]) == 0
    out = capsys.readouterr().out
    assert "Small Skills: Search Test" in out and "Challenge: 1000" in out and "Tutorial" in out
