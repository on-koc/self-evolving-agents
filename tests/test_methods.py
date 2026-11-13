"""Every method other than the baseline, the registry, and the walls between them.

Scripted stand-ins for the model throughout: these tests pin down mechanics, not
whether any method helps a real model.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pytest

from conftest import ITEM
from self_evolving_agents.agents import StepwiseAgent
from self_evolving_agents.embeddings import CachedEmbedder, GeminiEmbedder, make_embedder
from self_evolving_agents.envs import make_env, scan_task
from self_evolving_agents.llm import ScriptedLLM, TrackedLLM
from self_evolving_agents.methods import registry
from self_evolving_agents.methods.conditioned_retrieval import (
    CONDITION_NOTES,
    ConditionedBank,
    ConditionedConfig,
)
from self_evolving_agents.methods.matts import ParallelScaling, make_scaling, select_best
from self_evolving_agents.methods.matts import prompts as matts_prompts
from self_evolving_agents.methods.reasoningbank import Experience, MemoryItem
from self_evolving_agents.methods.reasoningbank import prompts as published
from self_evolving_agents.methods.stream import (
    Memory,
    Scaling,
    StreamLoop,
    TaskRecord,
    load_records,
    summarise,
)
from self_evolving_agents.provenance import ProvenanceStore

SRC = Path(__file__).resolve().parent.parent / "src" / "self_evolving_agents"


def tasks(n, regime="tiny_battery", duration_s=3600.0, **params):
    """Short episodes in which scanning without ever charging is certain to drain the battery."""
    params = {"init_battery_min": 0.3, "init_battery_max": 0.35, **params}
    return [
        scan_task("toy-scan", regime, seed=s, duration_s=duration_s, **params) for s in range(n)
    ]


def built(tmp_path, backend, method, options=None, **kwargs):
    store = ProvenanceStore(tmp_path / "prov.sqlite")
    store.start_run("test", method, options or {})
    llm = TrackedLLM(backend, store=store)
    return registry.build_stream(
        method, options, llm=llm, bank_path=tmp_path / "bank.jsonl", store=store, **kwargs
    )


# --------------------------------------------------------------------------- the walls


def imports_of(path: Path) -> set[str]:
    """Absolute dotted names of everything a module imports from this package."""
    package = list(path.relative_to(SRC.parent).with_suffix("").parts)
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - node.level]
                found.add(".".join(base + ([node.module] if node.module else [])))
            elif node.module and node.module.startswith("self_evolving_agents"):
                found.add(node.module)
        elif isinstance(node, ast.Import):
            found.update(a.name for a in node.names if a.name.startswith("self_evolving_agents"))
    return found


def method_dependencies(folder: str) -> set[str]:
    """Which other method folders the modules of one method folder import from."""
    found: set[str] = set()
    for path in (SRC / "methods" / folder).rglob("*.py"):
        for name in imports_of(path):
            parts = name.split(".")
            if "methods" in parts and len(parts) > parts.index("methods") + 1:
                other = parts[parts.index("methods") + 1]
                if other != folder:
                    found.add(other)
    return found


#: What each method may build on. Anything else is an unintended dependency.
ALLOWED = {
    "no_memory": {"stream"},
    "reasoningbank": {"stream"},
    "matts": {"stream", "reasoningbank"},
    "conditioned_retrieval": {"stream", "reasoningbank"},
    "policy_program": {"reasoningbank"},
    "claim_graph": set(),
    "claim_memory": {"stream", "reasoningbank", "claim_graph"},
}


@pytest.mark.parametrize("folder", sorted(ALLOWED))
def test_a_method_imports_only_what_it_is_documented_to_build_on(folder):
    assert method_dependencies(folder) <= ALLOWED[folder]


def test_the_baseline_does_not_know_any_adaptation_exists():
    assert method_dependencies("reasoningbank") == {"stream"}
    text = "".join(p.read_text() for p in (SRC / "methods" / "reasoningbank").glob("*.py"))
    for word in ("condition_weight", "utility", "dedup", "diversity", "claim", "policy_program"):
        assert word not in text, f"the baseline's code mentions {word}"


def test_shared_infrastructure_imports_no_method():
    shared = [SRC / name for name in ("agents", "envs", "llm", "experiments", "provenance")]
    files = [p for folder in shared for p in folder.rglob("*.py")]
    files += [SRC / name for name in ("types.py", "policies.py", "embeddings.py", "tasks.py")]
    for path in files:
        offending = [n for n in imports_of(path) if ".methods" in n]
        assert not offending, f"{path.relative_to(SRC)} imports {offending}"
    stream = imports_of(SRC / "methods" / "stream.py")
    assert not [n for n in stream if ".methods." in n], "the shared loop imports no method folder"


def test_every_method_has_a_folder_a_page_and_a_registry_entry():
    folders = {p.name for p in (SRC / "methods").iterdir() if p.is_dir() and p.name[0] != "_"}
    assert folders == set(registry.METHODS) == set(ALLOWED)
    docs = SRC.parent.parent / "docs" / "methods"
    for spec in registry.METHODS.values():
        assert (docs / f"{spec.name}.md").exists(), f"no documentation page for {spec.name}"
        assert spec.origin in ("paper", "reference point", "adaptation", "extension")
    assert registry.METHODS["claim_graph"].runner == "study"
    assert not registry.METHODS["claim_graph"].needs_model


# --------------------------------------------------------------------------- registry


def test_registry_builds_every_stream_method_and_rejects_unknown_options(tmp_path, scripted):
    for name, spec in registry.METHODS.items():
        if spec.runner != "stream" or name == "claim_memory":
            continue
        made = built(tmp_path / name, scripted, name)
        assert made.describe["method"] == name and made.describe["origin"] == spec.origin
    with pytest.raises(ValueError, match="has no option condition_weight"):
        registry.make_config("reasoningbank", {"condition_weight": 0.5})
    with pytest.raises(ValueError, match="is a study"):
        registry.make_config("claim_graph")
    with pytest.raises(ValueError, match="unknown method"):
        registry.make_config("telepathy")
    with pytest.raises(ValueError, match="needs claims="):
        built(tmp_path / "cm", scripted, "claim_memory")


def test_the_baselines_registry_defaults_are_the_published_values():
    defaults = registry.defaults("reasoningbank")
    assert defaults["retrieve_k"] == 1 and defaults["max_items"] == 3
    assert defaults["judge"] == "llm" and defaults["include_failures"] is True
    assert registry.defaults("matts")["scaling"] == "parallel"
    assert registry.defaults("matts")["scaling_k"] == 5, "the paper's headline configuration"


# --------------------------------------------------------------------------- no memory


def test_no_memory_retrieves_nothing_learns_nothing_and_judges_nothing(tmp_path, scripted):
    made = built(tmp_path, scripted, "no_memory")
    records = made.loop.run_stream(tasks(2))
    assert all(not r.new_item_ids and not r.retrieved_item_ids for r in records)
    assert set(scripted.purposes()) == {"act"}, "no judge or extraction calls"
    assert all(r.judged_success is None and r.judge_source == "" for r in records)
    assert not (tmp_path / "bank.jsonl").exists()
    assert all(published.MEMORY_INSTRUCTION not in r.system for r in scripted.requests)
    judged = built(tmp_path / "j", scripted, "no_memory", {"judge": "llm"})
    assert judged.loop.run_task(tasks(1)[0]).judged_success is False


# --------------------------------------------------------------------------- MaTTS


def test_T2_T4_published_scaling_prompts():
    parallel = matts_prompts.parallel_system("spacecraft operations")
    for sentence in (
        "You will be given a user query and multiple trajectories showing how an agent "
        "attempted the task. Some trajectories may be successful, and others may have failed.",
        "Use **self-contrast reasoning**:",
        "Think first: Why did some trajectories succeed while others failed?",
        "You can extract *at most 5* memory items from all trajectories combined.",
        "## Content <1-5 sentences describing the insights learned to successfully "
        "accomplishing the task>",
    ):
        assert sentence in parallel, sentence
    assert "start from the same situation" not in parallel, "an instruction this project had added"
    selection = matts_prompts.selection_system("spacecraft operations", 3)
    assert "and 3 candidate trajectories" in selection
    for heading in (
        "### Progress Toward Goal",
        "### Trajectory Efficiency",
        "### Loop Detection",
        "### Error Severity and Stability",
        "### Overall Trajectory Quality",
        '"index": [best_trajectory_index]',
    ):
        assert heading in selection
    assert matts_prompts.SEQUENTIAL_CHECK_PUBLISHED.startswith(
        "Important: Let's carefully re-examine the previous trajectory"
    )


def test_T2_parallel_scaling_contrasts_k_unlabelled_rollouts_under_one_memory(tmp_path, scripted):
    made = built(tmp_path, scripted, "matts", {"scaling_k": 3})
    assert isinstance(made.loop.scaling, ParallelScaling) and made.loop.scaling.k == 3
    first, second = made.loop.run_stream(tasks(2))

    assert len(first.trajectory_ids) == 3 and len(first.attempt_scores) == 3
    assert scripted.purposes().count("extract") == 2, "one extraction per task, not per rollout"
    extract = next(r for r in scripted.requests if r.purpose == "extract")
    assert extract.system == matts_prompts.parallel_system(make_env(tasks(1)[0]).spec.domain)
    body = extract.messages[0]["content"]
    assert body.count("Trajectory 1:") == 1 and "Trajectory 3:" in body
    assert "success" not in body.lower() and "fail" not in body.lower(), "no labels are given"
    assert scripted.purposes().count("judge") == 2, "only the selected rollout is judged"
    assert scripted.purposes().count("select") == 2

    systems = {r.system for r in scripted.requests if r.purpose == "act" and "Keep a" in r.system}
    assert len(systems) == 1, "all rollouts of a task see the same retrieved memory"
    samples = {r.sample for r in scripted.requests if r.purpose == "act"}
    assert samples == {0, 1, 2}, "each rollout is a separate draw"
    item = made.memory.bank.items[0]
    assert item.source == "contrast" and len(made.memory.bank) == 2
    assert len(made.memory.bank.experiences[0].trajectory_ids) == 3


def test_T4_best_of_n_reads_the_published_json_answer():
    env = make_env(tasks(1)[0])
    trajs = [StepwiseAgent(ScriptedLLM("<think>x</think><action>scan</action>")).run(env)] * 3
    for reply, expected in (
        ('```\n{"index": [2], "analysis": "second is best"}\n```', 1),
        ('{"index": 3, "analysis": "third"}', 2),
        ('{"index": [9], "analysis": "out of range"}', 0),
        ("I like them all.", 0),
    ):
        llm = ScriptedLLM(reply)
        index, _, _ = select_best(llm, env.spec, "q", trajs)
        assert index == expected, reply
    sent = llm.requests[0]
    assert sent.purpose == "select" and sent.temperature == 0.0
    body = sent.messages[0]["content"]
    assert "step_num: 1" in body and "think_output: x" in body and "action_output: scan" in body
    assert select_best(llm, env.spec, "q", trajs[:1])[0] == 0 and len(llm.requests) == 1


def test_T5_vanilla_scaling_turns_every_rollout_into_memory_on_its_own(tmp_path, scripted):
    made = built(tmp_path, scripted, "matts", {"scaling": "vanilla", "scaling_k": 2})
    record = made.loop.run_task(tasks(1)[0])
    assert len(record.experience_ids) == 2 and len(made.memory.bank) == 2
    assert scripted.purposes().count("judge") == 2 and scripted.purposes().count("extract") == 2
    extract = next(r for r in scripted.requests if r.purpose == "extract")
    assert "attempted to resolve the task but failed" in extract.system, "the single-run prompt"


def test_T5_scaling_without_memory_learns_nothing(tmp_path, scripted):
    made = built(tmp_path, scripted, "matts", {"scaling_k": 2, "memory": False})
    record = made.loop.run_task(tasks(1)[0])
    assert len(record.trajectory_ids) == 2 and record.new_item_ids == []
    assert "extract" not in scripted.purposes() and "select" in scripted.purposes()


def test_T1_a_scaling_factor_of_one_is_the_baseline(tmp_path, scripted):
    made = built(tmp_path, scripted, "matts", {"scaling_k": 1})
    assert type(made.loop.scaling) is Scaling
    record = made.loop.run_task(tasks(1)[0])
    assert len(record.trajectory_ids) == 1 and "select" not in scripted.purposes()
    assert type(make_scaling("none", scripted, 4)) is Scaling
    with pytest.raises(ValueError, match="scaling must be"):
        make_scaling("sideways", scripted, 2)


def test_restart_scaling_carries_the_agents_own_notes_into_the_next_attempt(tmp_path, scripted):
    """An adaptation, not the paper's sequential scaling: the task is started again."""
    made = built(tmp_path, scripted, "matts", {"scaling": "restart", "scaling_k": 3})
    record = made.loop.run_task(tasks(1)[0])
    assert len(record.trajectory_ids) == 3 and record.selected == 2, "the last attempt counts"
    assert scripted.purposes().count("refine") == 2
    refine = [r for r in scripted.requests if r.purpose == "refine"]
    assert (
        refine[0]
        .messages[0]["content"]
        .rstrip()
        .endswith("Reply with a short list of notes for your next attempt.")
    )
    assert "Let's check again." in refine[1].messages[0]["content"]
    by_sample = {
        s: next(r for r in scripted.requests if r.purpose == "act" and r.sample == s)
        for s in (0, 1, 2)
    }
    assert "charge earlier" not in by_sample[0].system
    assert matts_prompts.RESTART_NOTES_HEADER in by_sample[1].system
    assert by_sample[2].system.count("- charge earlier") == 2
    extract = next(r for r in scripted.requests if r.purpose == "extract")
    assert "a series of attempts at it by the same agent" in extract.system
    assert "Notes written after attempt 2:" in extract.messages[0]["content"]
    assert made.memory.bank.items[0].source == "restart"


# --------------------------------------------------------------------------- conditioned retrieval


def conditioned_experience(query, battery, *titles):
    return Experience(
        query=query,
        items=[MemoryItem(t, f"about {t}", f"do {t}") for t in titles],
        task={"conditions": {"battery_capacity_wh": battery}},
    )


def test_condition_weight_prefers_the_experience_from_the_matching_regime():
    bank = ConditionedBank()
    bank.add(conditioned_experience("operate the satellite", 200.0, "large battery lesson"))
    bank.add(conditioned_experience("operate the satellite", 50.0, "small battery lesson"))
    here = {"battery_capacity_wh": 55.0}
    plain = bank.retrieve("operate the satellite")
    assert plain[0].item.title == "small battery lesson", "a tie; this bank prefers the newest"
    for conditions, expected in (
        ({"battery_capacity_wh": 210.0}, "large battery lesson"),
        (here, "small battery lesson"),
    ):
        got = bank.retrieve_conditioned(
            "operate the satellite", mode="experience", conditions=conditions, condition_weight=0.5
        )
        assert got[0].item.title == expected
    ignored = bank.retrieve_conditioned(
        "operate the satellite",
        mode="experience",
        conditions={"battery_capacity_wh": 210.0},
        condition_weight=0.0,
    )
    assert ignored[0].item.title == "small battery lesson"


def test_item_retrieval_ranks_single_items_diversifies_and_caps():
    bank = ConditionedBank()
    bank.add(conditioned_experience("operate the satellite", 50.0, "charge early", "charge early"))
    bank.add(conditioned_experience("operate the satellite", 50.0, "downlink during passes"))
    diverse = bank.retrieve_conditioned("operate the satellite", max_items=2, diversity=0.6)
    assert {r.item.title for r in diverse} == {"charge early", "downlink during passes"}
    assert len(bank.retrieve_conditioned("operate the satellite", max_items=1)) == 1
    with pytest.raises(ValueError, match="mode"):
        bank.retrieve_conditioned("q", mode="telepathy")


def test_usage_statistics_promote_items_with_a_good_track_record():
    bank = ConditionedBank()
    bank.add(conditioned_experience("operate the satellite", 50.0, "good lesson"))
    bank.add(conditioned_experience("operate the satellite", 50.0, "bad lesson"))
    good, bad = bank.items
    for _ in range(3):
        bank.record_outcome([good.id], 0.8, True)
        bank.record_outcome([bad.id], -0.9, False)
    assert bank.mean_score(good) == pytest.approx(0.8) and good.meta["usage"]["uses"] == 3
    ranked = bank.retrieve_conditioned(
        "operate the satellite", max_items=1, utility_weight=1.0, diversity=0.0
    )
    assert ranked[0].item.title == "good lesson"
    assert bank.stats()["items_used"] == 2


def test_duplicate_filter_drops_near_copies_only_when_enabled():
    bank = ConditionedBank(dedup_threshold=0.9)
    bank.add(conditioned_experience("q", 50.0, "charge before the eclipse"))
    second = bank.add(conditioned_experience("q", 50.0, "charge before the eclipse", "downlink"))
    assert [i.title for i in second.items] == ["downlink"]
    assert second.meta["dropped_duplicates"][0]["title"] == "charge before the eclipse"
    keep_all = ConditionedBank()
    keep_all.add(conditioned_experience("q", 50.0, "charge before the eclipse"))
    assert (
        len(keep_all.add(conditioned_experience("q", 50.0, "charge before the eclipse")).items) == 1
    )


def test_conditioned_method_adds_its_instructions_to_the_published_prompt(tmp_path, scripted):
    made = built(tmp_path, scripted, "conditioned_retrieval")
    first, second = made.loop.run_stream(tasks(2))
    assert second.retrieved_item_ids == first.new_item_ids
    extract = next(r for r in scripted.requests if r.purpose == "extract")
    assert CONDITION_NOTES in extract.system
    assert extract.system.replace("\n" + CONDITION_NOTES, "") == (
        published.failure_extraction_system(make_env(tasks(1)[0]).spec.domain)
    ), "the published prompt, plus exactly the two added instructions"
    assert "<observation>" in extract.messages[0]["content"], "it shows the extractor more"
    assert made.memory.bank.items[0].meta["usage"]["uses"] == 1

    off = ConditionedConfig(
        condition_notes=False, observations=False, condition_weight=0.0, retrieval_mode="experience"
    )
    plain = built(tmp_path / "plain", scripted, "conditioned_retrieval", off.to_dict())
    plain.loop.run_task(tasks(1)[0])
    request = [r for r in scripted.requests if r.purpose == "extract"][-1]
    assert CONDITION_NOTES not in request.system
    assert "<observation>" not in request.messages[0]["content"]


# --------------------------------------------------------------------------- policy program

POLICY = {
    "name": "mine",
    "params": {"low": 0.3},
    "rules": [{"if": {"battery": {"<": "$low"}}, "do": "charge"}],
    "default": "scan",
}


def test_policy_program_method_shows_the_extractor_the_policy_and_the_observations(tmp_path):
    script = ScriptedLLM(
        {
            "policy": "Rationale: keep a reserve.\n```json\n" + json.dumps(POLICY) + "\n```",
            "judge": 'Status: "success"',
            "extract": ITEM,
        }
    )
    made = built(tmp_path, script, "policy_program")
    assert made.agent.descriptor["type"] == "policy-program"
    first, second = made.loop.run_stream(tasks(2))
    assert script.purposes().count("policy") == 2, "one model call per episode"
    extract = next(r for r in script.requests if r.purpose == "extract")
    body = extract.messages[0]["content"]
    assert "The agent committed to this policy before the episode:" in body
    assert "Rationale: keep a reserve." in body and "<observation>" in body
    later = [r for r in script.requests if r.purpose == "policy"][-1]
    assert "Before writing the policy, please first explicitly discuss" in later.system
    assert "Keep a reserve" in later.system
    assert second.retrieved_item_ids == first.new_item_ids


def test_any_memory_method_can_be_paired_with_the_policy_writing_agent(tmp_path):
    script = ScriptedLLM({"policy": "```json\n" + json.dumps(POLICY) + "\n```"})
    made = built(tmp_path, script, "no_memory", agent="policy_program")
    made.loop.run_task(tasks(1)[0])
    assert script.purposes() == ["policy"]
    with pytest.raises(ValueError, match="agent must be"):
        built(tmp_path / "x", script, "no_memory", agent="telepathic")


# --------------------------------------------------------------------------- metrics


def record(score, success, failure=None, steps=10, judged=None, attempts=None, name="a"):
    scores = attempts or [score]
    return TaskRecord(
        task={"name": name, "seed": 0},
        trajectory_ids=["t"] * len(scores),
        selected=0,
        score=score,
        success=success,
        failure=failure,
        steps=steps,
        total_reward=score,
        judged_success=judged,
        judge_source="llm" if judged is not None else "",
        attempt_scores=scores,
        attempt_successes=[s >= 0.2 for s in scores],
        first_score=scores[0],
        best_score=max(scores),
    )


def test_summary_metrics_follow_their_definitions(tmp_path):
    records = [
        record(0.6, True, steps=90, judged=True, attempts=[0.6, 0.7]),
        record(0.1, False, steps=95, judged=True, attempts=[0.1, 0.3]),
        record(-0.8, False, failure="battery", steps=20, judged=False, attempts=[-0.8, -0.9]),
        record(0.5, True, steps=95, judged=False, attempts=[0.5, 0.1]),
    ]
    s = summarise(records)
    assert s["tasks"] == 4
    assert s["mean_score"] == pytest.approx((0.6 + 0.1 - 0.8 + 0.5) / 4)
    assert s["success_rate"] == 0.5 and s["failure_rate"] == 0.25
    assert s["failures_by_mode"] == {"battery": 1}
    assert s["mean_steps"] == 75.0
    assert s["mean_steps_successful"] == 92.5 and s["mean_steps_failed"] == 57.5
    assert s["judge_agreement"] == 0.5 and s["judged_tasks"] == 4
    assert s["judge_false_success"] == 1 and s["judge_false_failure"] == 1
    assert s["mean_first_attempt_score"] == pytest.approx(0.1)
    assert s["first_attempt_success_rate"] == 0.5
    assert s["mean_best_attempt_score"] == pytest.approx((0.7 + 0.3 - 0.8 + 0.5) / 4)
    assert s["any_attempt_success_rate"] == 0.75
    assert summarise([]) == {"tasks": 0}
    unjudged = summarise([record(0.6, True), record(0.1, False)])
    assert unjudged["judge_agreement"] is None and unjudged["judged_tasks"] == 0

    loop = StreamLoop(StepwiseAgent(ScriptedLLM("<think>x</think><action>scan</action>")))
    loop.records = records
    loop.save_records(tmp_path / "records.jsonl")
    assert [r.to_dict() for r in load_records(tmp_path / "records.jsonl")] == [
        r.to_dict() for r in records
    ]


def test_the_default_memory_and_scaling_are_no_memory_and_one_attempt():
    loop = StreamLoop(StepwiseAgent(ScriptedLLM("<think>x</think><action>scan</action>")))
    assert type(loop.memory) is Memory and type(loop.scaling) is Scaling
    assert loop.memory.learns is False and loop.scaling.k == 1


# --------------------------------------------------------------------------- embeddings


def test_gemini_embedder_calls_the_service_as_the_reference_code_does(fake_gemini):
    from google import genai

    client = genai.Client(api_key="test-key", http_options={"base_url": fake_gemini.base_url})
    embedder = GeminiEmbedder(client=client, dimensions=3)
    vectors = embedder.embed(["first query", "second query"])
    assert vectors.shape == (2, 3)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0), "rows are L2-normalised"
    path, body = fake_gemini.requests[0]
    assert path.endswith("/models/gemini-embedding-001:batchEmbedContents")
    assert [r["content"]["parts"][0]["text"] for r in body["requests"]] == [
        "first query",
        "second query",
    ]
    assert {r["taskType"] for r in body["requests"]} == {"RETRIEVAL_DOCUMENT"}
    assert {r["outputDimensionality"] for r in body["requests"]} == {3}
    assert embedder.name == "gemini-embedding-001-3"
    assert GeminiEmbedder(client=client).dimensions == 3072, "the reference code's dimensionality"


def test_cached_embedder_asks_for_each_text_once(tmp_path):
    class Counting:
        name = "counting"

        def __init__(self):
            self.calls = []

        def embed(self, texts):
            self.calls.append(list(texts))
            return np.array([[len(t), 1.0] for t in texts], dtype=np.float32)

    inner = Counting()
    cached = CachedEmbedder(inner, tmp_path / "embeddings.jsonl")
    first = cached.embed(["alpha", "beta", "alpha"])
    assert inner.calls == [["alpha", "beta"]] and first.shape == (3, 2)
    assert np.array_equal(first[0], first[2])
    cached.embed(["beta", "gamma"])
    assert inner.calls[-1] == ["gamma"]
    reloaded = CachedEmbedder(Counting(), tmp_path / "embeddings.jsonl")
    assert np.array_equal(reloaded.embed(["alpha"]), first[:1]) and reloaded.embedder.calls == []
    assert cached.name == "counting"


def test_make_embedder():
    assert make_embedder("hashing").name == "hashing-1024-c3"
    assert make_embedder("hashing:256").dim == 256
    with pytest.raises(ValueError, match="unknown embedder"):
        make_embedder("word2vec")
