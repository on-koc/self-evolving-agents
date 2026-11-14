"""The DiscoveryWorld use case: environment, Hypothesizer, investigation memory, measures.

The model is always a script or the rule-based stand-in. Tests marked
``discoveryworld`` run the real DiscoveryWorld.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from conftest import requires_dw
from self_evolving_agents.agents import MemoryBlock
from self_evolving_agents.llm import ScriptedLLM, TrackedLLM
from self_evolving_agents.methods.investigation_memory import (
    InvestigationGraph,
    InvestigationMemory,
    InvestigationMemoryConfig,
)
from self_evolving_agents.methods.stream import Verdict
from self_evolving_agents.types import Outcome, Step, Task, Trajectory

DATA = Path(__file__).parent / "data"
SRC = Path(__file__).resolve().parent.parent / "src" / "self_evolving_agents"

# Chemistry, Easy, seed 0: object ids (DiscoveryWorld's ids are fixed by the seed).
JAR, DISPENSER_A, DISPENSER_B, KEY, CLEANER = 35632, 21559, 57736, 33120, 51739


def act(action, arg1=None, arg2=None, **extra):
    payload = {"action": action, **({"arg1": arg1} if arg1 is not None else {})}
    if arg2 is not None:
        payload["arg2"] = arg2
    return json.dumps(
        {
            **payload,
            "explanation": extra.get("why", "testing"),
            "memory": "",
            "running_hypotheses": [],
        }
    )


def chemistry_script(clean: bool) -> list[str]:
    steps = [
        act("TELEPORT_TO_OBJECT", JAR),
        act("PICKUP", JAR),
        act("TELEPORT_TO_OBJECT", DISPENSER_A),
        act("USE", DISPENSER_A, JAR),
        act("TELEPORT_TO_OBJECT", KEY),
        act("PICKUP", KEY),
        act("PUT", KEY, JAR),
        act("PICKUP", KEY),
    ]
    if clean:
        steps += [act("TELEPORT_TO_OBJECT", CLEANER), act("USE", CLEANER, JAR)]
    steps += [
        act("TELEPORT_TO_OBJECT", DISPENSER_B),
        act("USE", DISPENSER_B, JAR),
        act("PUT", KEY, JAR),
    ]
    return steps


def run_hypothesizer(
    scenario, difficulty, seed, acts, knowledge='{"scientific_knowledge": []}', memory=None
):
    from self_evolving_agents.envs import discoveryworld_task, make_env
    from self_evolving_agents.methods.hypothesizer import HypothesizerAgent

    llm = ScriptedLLM({"act": list(acts), "knowledge": knowledge, "consolidate": knowledge})
    env = make_env(discoveryworld_task(scenario, difficulty, seed=seed, max_steps=len(acts)))
    try:
        first = env.reset()
        traj = HypothesizerAgent(llm).run(env, first_observation=first, memory=memory)
    finally:
        env.close()
    return traj, llm


# --------------------------------------------------------------------------- environment


@requires_dw
@pytest.mark.discoveryworld
@pytest.mark.parametrize("difficulty", ["Easy", "Normal", "Challenge"])
def test_rocket_science_loads_on_this_python(difficulty, tmp_path, monkeypatch):
    from self_evolving_agents.envs import discoveryworld_task, make_env

    monkeypatch.chdir(tmp_path)
    env = make_env(
        discoveryworld_task("It's (not) Rocket Science!", difficulty, seed=1, max_steps=2)
    )
    try:
        env.reset()
        assert "rocket" in env.query.lower()
    finally:
        env.close()


@requires_dw
@pytest.mark.discoveryworld
def test_noop_and_argument_names(tmp_path, monkeypatch):
    from self_evolving_agents.envs import discoveryworld_task, make_env
    from self_evolving_agents.types import Action

    monkeypatch.chdir(tmp_path)
    env = make_env(discoveryworld_task("Combinatorial Chemistry", "Easy", seed=0, max_steps=5))
    try:
        env.reset()
        start = env.api_observation()["ui"]["world_steps"]
        result = env.step(Action("NOOP", {"reason": "unreadable reply"}))
        assert env.api_observation()["ui"]["world_steps"] == start + 1, "time passes"
        assert result.info["action_ok"] is False and result.info["errors"] == ["unreadable reply"]
        result = env.step(
            env.parse_action(json.dumps({"action": "TELEPORT_TO_OBJECT", "arg1": JAR}))
        )
        assert result.info["arg_names"] == {"arg1": "jar"}
        assert env.world == {"scenario": "Combinatorial Chemistry", "difficulty": "Easy", "seed": 0}
        assert set(env.known_actions()) >= {"USE", "PICKUP", "TELEPORT_TO_OBJECT"}
    finally:
        env.close()


@requires_dw
@pytest.mark.discoveryworld
def test_answer_keys_differ_between_seeds_of_one_kind():
    from self_evolving_agents.envs import answer_key

    first = answer_key("Combinatorial Chemistry", "Easy", 0)
    second = answer_key("Combinatorial Chemistry", "Easy", 1)
    assert "Substance B" in first[0]["critical_questions"][0]
    assert first[0]["critical_questions"] != second[0]["critical_questions"]


# --------------------------------------------------------------------------- Hypothesizer


@requires_dw
@pytest.mark.discoveryworld
@pytest.mark.parametrize("case", [0, 1])
def test_hypothesizer_prompts_are_byte_identical_to_the_original(case, tmp_path, monkeypatch):
    """Fingerprints of the prompts of DiscoveryWorld's own Hypothesizer, same replies."""
    monkeypatch.chdir(tmp_path)
    fixture = json.loads((DATA / "hypothesizer_reference_prompts.json").read_text())["cases"][case]
    from self_evolving_agents.envs import discoveryworld_task, make_env
    from self_evolving_agents.methods.hypothesizer import HypothesizerAgent

    scenario, difficulty, seed = fixture["world"]
    llm = ScriptedLLM(
        {
            "act": list(fixture["act"]),
            "knowledge": list(fixture["knowledge"]),
            "consolidate": list(fixture["consolidate"]),
        }
    )
    env = make_env(
        discoveryworld_task(scenario, difficulty, seed=seed, max_steps=fixture["max_steps"])
    )
    try:
        first = env.reset()
        HypothesizerAgent(llm).run(env, first_observation=first)
    finally:
        env.close()
    produced = [
        {
            "sha256": hashlib.sha256(r.messages[0]["content"].encode()).hexdigest(),
            "chars": len(r.messages[0]["content"]),
            "max_tokens": r.max_tokens,
            "temperature": r.temperature,
        }
        for r in llm.requests
    ]
    assert len(produced) == len(fixture["prompts"])
    for i, (ours, theirs) in enumerate(zip(produced, fixture["prompts"], strict=True)):
        assert ours == theirs, f"call {i} ({llm.requests[i].purpose}) differs from the original"
    assert all(r.system == "" for r in llm.requests), "the original sends one user message"


@requires_dw
@pytest.mark.discoveryworld
def test_hypothesizer_keeps_knowledge_and_survives_bad_replies(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    knowledge = (
        '```json\n{"scientific_knowledge": [{"measurement": "the key is heavily rusted"}]}\n```'
    )
    traj, llm = run_hypothesizer(
        "Combinatorial Chemistry",
        "Easy",
        0,
        [act("TELEPORT_TO_OBJECT", JAR), "not json", act("FLY_AWAY")],
        knowledge=knowledge,
        memory=MemoryBlock(text="Notes from earlier: clean the jar.", item_ids=["str_1"]),
    )
    assert [s.action.split('"action": ')[-1][:12] for s in traj.steps][1:] == ['"NOOP", "rea'] * 2
    assert traj.steps[1].info["parse_failure"] is True
    assert "unknown action 'FLY_AWAY'" in traj.steps[2].info["parse_error"]
    assert len(traj.meta["scientific_knowledge"]) == 3
    assert all(item["step"] >= 1 for item in traj.meta["scientific_knowledge"])
    assert "Notes from earlier: clean the jar." in llm.requests[0].messages[0]["content"]
    assert traj.memory_item_ids == ["str_1"]
    # The cross-episode memory goes in the action prompt only, not into the knowledge step.
    assert "Notes from earlier" not in llm.requests[1].messages[0]["content"]


# --------------------------------------------------------------------------- detectors


@requires_dw
@pytest.mark.discoveryworld
def test_detectors_read_a_real_chemistry_investigation(tmp_path, monkeypatch):
    from self_evolving_agents.discovery.behaviours import chemistry_tests, detect

    monkeypatch.chdir(tmp_path)
    traj, _ = run_hypothesizer("Combinatorial Chemistry", "Easy", 0, chemistry_script(clean=True))
    tests = chemistry_tests(traj)
    assert [t["contents"] for t in tests] == [["A"], ["B"]]
    assert [t["worked"] for t in tests] == [False, True], "substance B removes the rust in seed 0"
    found = detect(traj)
    assert found["tests"] == 2 and found["distinct_tests"] == 2 and found["first_test"] == ["A"]
    assert found["alternatives"] is True and found["first_working_test"] == 1
    assert found["confounds"] == 1.0, "the jar was cleaned before the second, different test"
    assert found["revision"] == 1.0, "the failed test was followed by a different one"
    assert found["contaminated_tests"] == 0

    dirty, _ = run_hypothesizer("Combinatorial Chemistry", "Easy", 0, chemistry_script(clean=False))
    found = detect(dirty)
    assert [t["contents"] for t in chemistry_tests(dirty)] == [["A"], ["A", "B"]]
    assert found["confounds"] == 0.0 and found["contaminated_tests"] == 1


def _traj(steps, scenario="Proteomics", difficulty="Easy", terminated=True, query="task"):
    return Trajectory(
        id="traj_x",
        task=Task(
            "discoveryworld",
            f"{scenario}/{difficulty}",
            0,
            {"scenario": scenario, "difficulty": difficulty},
        ),
        query=query,
        steps=steps,
        outcome=Outcome(score=1.0, success=terminated, terminated=terminated),
    )


def _use(index, tool, target, target_id):
    return Step(
        index=index,
        observation="",
        thought="",
        action=json.dumps({"action": "USE", "arg1": 1, "arg2": target_id}),
        reward=0.0,
        info={"action_ok": True, "arg_names": {"arg1": tool, "arg2": target}},
    )


def test_generic_and_reference_detectors():
    from self_evolving_agents.discovery.behaviours import detect

    steps = [
        _use(0, "proteomics meter", "vortisquid", 11),
        _use(1, "proteomics meter", "animaplant", 12),
        _use(2, "proteomics meter", "animaplant", 12),
        Step(
            index=3,
            observation="",
            thought="",
            action=json.dumps({"action": "DROP", "arg1": 5}),
            reward=0.0,
        ),
    ]
    found = detect(_traj(steps))
    assert found["candidates_before_commit"] == 2 and found["alternatives"] is True
    assert found["repeated_measurements"] == 1 and found["commit_step"] == 3
    assert found["premature_commit"] is False

    reactor = detect(
        _traj(
            [
                _use(0, "microscope", "quantum crystal 1", 1),
                _use(1, "microscope", "quantum crystal 3", 3),
            ],
            scenario="Reactor Lab",
            query="the correct frequencies for Crystal 1 and Crystal 2, which are in their reactors",
        )
    )
    assert reactor["controls"] is True and reactor["reference_measurements"] == 1
    digs = detect(
        _traj(
            [_use(0, "radioisotope meter", "ancient artifact", 9)],
            scenario="Archaeology Dating",
            difficulty="Challenge",
        )
    )
    assert digs["controls"] is False and digs["premature_commit"] is True


# --------------------------------------------------------------------------- investigation memory


class FakeEnv:
    spec = None


def _task(scenario="Combinatorial Chemistry", seed=0):
    return Task(
        "discoveryworld", f"{scenario}/Easy", seed, {"scenario": scenario, "difficulty": "Easy"}
    )


EXTRACTION = {
    "evidence": [
        {"text": "Substance A left the key heavily rusted", "step": 6},
        {"text": "Substance B removed the rust", "step": 12},
    ],
    "hypotheses": [
        {
            "statement": "Substance B removes rust",
            "conditions": "this shed",
            "status": "supported",
            "supported_by": [1],
            "contradicted_by": [],
        },
        {
            "statement": "Substance A removes rust",
            "conditions": "this shed",
            "status": "refuted",
            "supported_by": [],
            "contradicted_by": [0],
        },
    ],
    "strategies": [
        {
            "statement": "Empty the container before each new test",
            "applies_when": "several candidates share one container",
            "test": "use the cleaner between tests",
            "basis": "the second test only worked after cleaning",
        }
    ],
}


def learned_memory(tmp_path, **options):
    llm = ScriptedLLM({"extract_investigation": json.dumps(EXTRACTION)})
    memory = InvestigationMemory(
        InvestigationMemoryConfig(**options), llm, path=tmp_path / "memory.json"
    )
    traj = _traj([], scenario="Combinatorial Chemistry")
    traj.id = "traj_first"
    traj.final_observation = "Task status: complete"
    memory.learn_single(
        FakeEnv(), _task(seed=0), "Remove the rust from the key.", traj, Verdict(True, "it worked")
    )
    return memory, llm


def test_extraction_builds_a_linked_graph(tmp_path):
    memory, llm = learned_memory(tmp_path)
    graph = InvestigationGraph(tmp_path / "memory.json")
    assert graph.counts()["evidence"] == 2 and graph.counts()["strategies"] == 1
    refuted = next(h for h in graph.hypotheses.values() if h.status == "refuted")
    assert graph.evidence[refuted.contradicted_by[0]].text.startswith("Substance A")
    assert "supported_by" in {rel for _, rel, _ in graph.links()}
    request = llm.requests[0]
    assert request.purpose == "extract_investigation" and request.temperature == 0.0
    assert "strategy_review" not in request.system, "no review when no strategy was shown"


def test_retrieval_scopes_findings_to_their_world(tmp_path):
    memory, _ = learned_memory(tmp_path)
    same = memory.retrieve(FakeEnv(), _task(seed=0), "Remove the rust from the key.")
    other = memory.retrieve(FakeEnv(), _task(seed=1), "Remove the rust from the key.")
    elsewhere = memory.retrieve(FakeEnv(), _task("Proteomics", seed=0), "Find the outlier animal.")
    assert "Findings from an earlier attempt in this same world" in same.block.text
    assert "Measurements from an earlier attempt" in same.block.text
    assert "this same world" not in other.block.text and "Measurements" not in other.block.text
    assert "Findings from other worlds of this kind" in other.block.text
    assert "Observed under: this shed" in other.block.text
    assert "Substance B" not in elsewhere.block.text, "another kind of task gets no findings"
    assert "Empty the container before each new test" in elsewhere.block.text, "strategies travel"
    kinds = {d["kind"] for d in other.details}
    assert kinds == {"strategy", "hypothesis"}


def test_variants_lesions_answers_placebo_instructed(tmp_path):
    memory, _ = learned_memory(tmp_path)
    full = memory.retrieve(FakeEnv(), _task(seed=1), "q").block.text
    memory.config.include = ["evidence", "hypotheses"]
    assert "Empty the container" not in memory.retrieve(FakeEnv(), _task(seed=1), "q").block.text
    memory.config.include = ["strategies"]
    assert "Substance B" not in memory.retrieve(FakeEnv(), _task(seed=1), "q").block.text
    memory.config.include = ["evidence", "hypotheses", "strategies"]
    memory.config.other_worlds = "hide"
    assert "other worlds" not in memory.retrieve(FakeEnv(), _task(seed=1), "q").block.text

    memory.config.mode = "answers"
    answers = memory.retrieve(FakeEnv(), _task(seed=1), "q").block
    assert "- Substance B removes rust" in answers.text and "Observed under" not in answers.text
    assert "Substance A" not in answers.text, "only what was found to hold"

    memory.config.mode = "placebo"
    memory.config.other_worlds = "scoped"
    placebo = memory.retrieve(FakeEnv(), _task(seed=1), "q")
    assert placebo.block.item_ids == [] and "Substance" not in placebo.block.text
    assert abs(len(placebo.block.text) - len(full)) < 200, "similar length, no content"

    memory.config.mode = "instructed"
    instructed = memory.retrieve(FakeEnv(), _task(seed=1), "q").block.text
    assert "control condition" in instructed and "confounding" in instructed


def test_strategy_review_updates_the_record_and_replaces_what_failed(tmp_path):
    memory, _ = learned_memory(tmp_path)
    shown = memory.retrieve(FakeEnv(), _task("Proteomics"), "Find the outlier animal.")
    review = {
        **EXTRACTION,
        "strategies": [],
        "strategy_review": [
            {
                "id": "S1",
                "used": True,
                "outcome": "did not help",
                "reason": "nothing to clean here",
                "revised_statement": "Empty the container before each new test of a liquid",
                "revised_applies_when": "candidates are liquids mixed in one container",
            }
        ],
    }
    memory.llm = ScriptedLLM({"extract_investigation": json.dumps(review)})
    traj = _traj([], scenario="Proteomics")
    traj.meta["retrieval"] = shown.details
    memory.learn_single(
        FakeEnv(),
        _task("Proteomics"),
        "Find the outlier animal.",
        traj,
        Verdict(False, "flag misplaced"),
    )
    request = memory.llm.requests[0]
    assert (
        "strategy_review" in request.system
        and "S1: Empty the container" in request.messages[0]["content"]
    )
    old = next(s for s in memory.graph.strategies.values() if s.revised_from is None)
    new = next(s for s in memory.graph.strategies.values() if s.revised_from == old.id)
    assert old.status == "replaced" and old.uses == 1 and old.did_not_help == 1
    assert new.applies_when.startswith("candidates are liquids") and new.status == "active"


def test_frozen_memory_is_consulted_but_not_changed(tmp_path):
    from self_evolving_agents.methods.stream import StreamLoop

    memory, _ = learned_memory(tmp_path)
    before = (tmp_path / "memory.json").read_text()

    class Agent:
        descriptor = {"id": "fake"}

        def run(self, env, *, first_observation=None, memory=None, notes="", sample=0, meta=None):
            self.seen = memory.text
            return _traj([], scenario="Combinatorial Chemistry")

    class Env:
        query = "Remove the rust from the key."
        spec = None

        def reset(self):
            return None

        def close(self):
            pass

    agent = Agent()
    loop = StreamLoop(agent, memory=memory, judge=None, env_factory=lambda task: Env(), learn=False)
    loop.run_task(_task(seed=0))
    assert "Empty the container" in agent.seen
    assert (tmp_path / "memory.json").read_text() == before


# --------------------------------------------------------------------------- prompts and graders

BEHAVIOUR_WORDS = re.compile(
    r"\b(control|confound\w*|alternative\w*|revisit\w*|reconsider\w*|competing)\b", re.I
)


def test_no_prompt_outside_the_instructed_arm_names_the_measured_behaviours():
    from self_evolving_agents.methods.hypothesizer import prompts as hyp
    from self_evolving_agents.methods.investigation_memory import prompts as inv

    texts = {
        "hypothesizer action": hyp.action_prompt_head({}, {}, "", [], {}, "north", [])
        + hyp.action_prompt_tail({}, "[]")
        + hyp.DEBUG_TEXT,
        "hypothesizer dialog": hyp.dialog_text({}, fixed=True),
        "hypothesizer knowledge": hyp.knowledge_prompt("", {"scientific_knowledge": []}),
        "hypothesizer consolidation": hyp.consolidation_prompt({"scientific_knowledge": []}, 10),
        "extraction": inv.extraction_system(True)
        + inv.extraction_input(
            "t", "x", "n", "e", [{"label": "S1", "statement": "s", "applies_when": "a"}]
        ),
        "headings": " ".join(
            [
                inv.MEMORY_HEADING,
                inv.STRATEGY_HEADING,
                inv.SAME_WORLD_HEADING,
                inv.ELSEWHERE_HEADING,
                inv.EVIDENCE_HEADING,
                inv.ANSWERS_HEADING,
            ]
        ),
        "placebo": " ".join(inv.PLACEBO_SENTENCES),
    }
    for name, text in texts.items():
        assert not BEHAVIOUR_WORDS.search(text), (
            f"{name}: {BEHAVIOUR_WORDS.search(text).group(0)!r}"
        )
    assert BEHAVIOUR_WORDS.search(inv.INSTRUCTED), "only the instructed control names them"


def test_grading_prompt_is_discoveryworlds_own():
    from self_evolving_agents.discovery.knowledge import grading_prompt

    text = grading_prompt("TASK DESCRIPTION", "KNOWLEDGE TEXT", "QUESTION?")
    # Fingerprint of the prompt built by scripts/knowledgeScorer.py (allenai/discoveryworld at
    # fd59132) for these three inputs.
    assert hashlib.sha256(text.encode()).hexdigest() == (
        "1adb4ac938f391a2f715d85331c79ce6cde88bc215c57fb32a2bf8f3c6250a13"
    )


@requires_dw
@pytest.mark.discoveryworld
def test_knowledge_and_stale_knowledge_scores():
    from self_evolving_agents.discovery.knowledge import KnowledgeScorer

    def grader(request):
        text = request.messages[0]["content"]
        question = re.search(r"Critical Question:\n```\n(.*?)\n```", text, re.S).group(1)
        knowledge = re.search(r"Agent's Knowledge:\n```\n(.*?)\n```", text, re.S).group(1)
        answer = re.findall(r"`([^`]+)`", question)
        return json.dumps(
            {"evaluation": int(bool(answer) and answer[0] in knowledge), "explanation": "x"}
        )

    scorer = KnowledgeScorer(TrackedLLM(ScriptedLLM(grader)))
    world0 = {"scenario": "Combinatorial Chemistry", "difficulty": "Easy", "seed": 0}
    world1 = {**world0, "seed": 1}
    right = scorer.grade(world0, "The rust remover is Substance B.")
    assert right["score"] == 1.0 and len(right["questions"]) == 1
    # In world 1 the answer is another substance; stating world 0's answer there is stale.
    stale = scorer.stale(world1, "The rust remover is Substance B.", [world0])
    assert stale["score"] == 1.0
    assert scorer.stale(world1, "The rust remover is Substance D.", [world0])["score"] == 0.0
    assert scorer.stale(world0, "x", [world0])["score"] is None, "the same world is not earlier"


def test_coder_record_is_redacted_and_kappa():
    from self_evolving_agents.discovery.behaviours import BehaviourCoder, cohen_kappa, redact

    assert "memory" not in redact("I will follow my memory here. Then test A.").lower()
    assert "Then test A." in redact("Following strategy S1 now. Then test A.")
    step = Step(
        index=0,
        observation="",
        thought="My notes from earlier tasks say clean it. I clean it.",
        action="{}",
        reward=0.0,
    )
    traj = _traj([step])
    reply = json.dumps({"control": {"present": True, "step": 0, "evidence": "x"}})
    coder = BehaviourCoder(TrackedLLM(ScriptedLLM({"code_behaviour": reply})))
    coded = coder.code(traj)
    assert (
        coded["codes"]["control"]["present"] is True
        and coded["codes"]["revision"]["present"] is None
    )
    assert "notes from earlier" not in coder.llm.backend.requests[0].messages[0]["content"].lower()
    assert cohen_kappa([True, True, False, False], [True, True, False, False]) == 1.0
    assert cohen_kappa([True, False, True, False], [False, True, False, True]) == -1.0


# --------------------------------------------------------------------------- end to end


@requires_dw
@pytest.mark.discoveryworld
def test_discovery_protocol_runs_grades_and_reports(tmp_path, monkeypatch, capsys):
    from self_evolving_agents.cli import main

    monkeypatch.chdir(tmp_path)
    protocol = json.loads(
        (Path(__file__).parent.parent / "protocols" / "discovery_dry_run.json").read_text()
    )
    protocol.update(
        max_steps=3,
        experience={
            "order": "interleaved",
            "worlds": [
                {"scenario": "Combinatorial Chemistry", "difficulty": "Easy", "seeds": [0, 1]}
            ],
        },
        transfer={
            "new_world": [
                {"scenario": "Combinatorial Chemistry", "difficulty": "Easy", "seeds": [2]}
            ],
            "new_theme": [{"scenario": "Proteomics", "difficulty": "Easy", "seeds": [0]}],
        },
        arms={k: protocol["arms"][k] for k in ("hypothesizer", "investigation_memory")},
    )
    (tmp_path / "p.json").write_text(json.dumps(protocol))
    out = tmp_path / "out"
    assert (
        main(["discovery", "run", "--protocol", str(tmp_path / "p.json"), "--out", str(out)]) == 0
    )
    memory_file = (
        out / "investigation_memory" / "rep-0" / "experience" / "investigation_memory.json"
    )
    graph = json.loads(memory_file.read_text())
    assert len(graph["episodes"]) == 2 and graph["strategies"], "learned during experience"
    # Transfer and lesion runs read the frozen memory and leave it as it was.
    for run in ("transfer-new_world", "lesion-strategies_removed-new_theme"):
        config = json.loads(
            (out / "investigation_memory" / "rep-0" / run / "config.json").read_text()
        )
        assert config["learn"] is False
    assert json.loads(memory_file.read_text()) == graph
    lesion = json.loads(
        (
            out
            / "investigation_memory"
            / "rep-0"
            / "lesion-strategies_removed-new_world"
            / "config.json"
        ).read_text()
    )
    assert lesion["config"]["include"] == ["evidence", "hypotheses"]

    assert main(["discovery", "grade", str(out), "--grader", "offline-demo"]) == 0
    grades = [json.loads(line) for line in (out / "grades.jsonl").read_text().splitlines()]
    assert len(grades) == 2 * 2 + 2 * 2 + 2, "every episode graded once"
    assert main(["discovery", "grade", str(out), "--grader", "offline-demo"]) == 0
    assert len((out / "grades.jsonl").read_text().splitlines()) == len(grades), "resumes"

    capsys.readouterr()
    assert main(["discovery", "report", str(out)]) == 0
    text = capsys.readouterr().out
    for needle in (
        "These numbers are not results",
        "## Outcomes by arm and condition",
        "## Behaviours detected from the actions",
        "## Paired differences on the transfer worlds",
        "## Lesions",
        "investigation_memory minus hypothesizer",
    ):
        assert needle in text, needle
    report = json.loads((out / "report.json").read_text())
    assert report["summary"]["episodes"] == len(grades)

    sample = tmp_path / "sample.jsonl"
    assert main(["discovery", "code-sample", str(out), "--sample", str(sample), "--n", "3"]) == 0
    rows = [json.loads(line) for line in sample.read_text().splitlines()]
    assert (
        len(rows) == 3 and "arm" not in rows[0] and "investigation_memory" not in rows[0]["record"]
    )
    for row in rows:
        row["labels"] = {name: False for name in row["labels"]}
    sample.write_text("\n".join(json.dumps(r) for r in rows))
    assert main(["discovery", "agreement", str(out), "--labels", str(sample)]) == 0
