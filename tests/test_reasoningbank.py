"""Memory items, the bank, judging, extraction and the closed-loop pipeline.

Everything here uses scripted stand-ins for the model, so these tests pin down the
mechanics (what is retrieved, which prompt is used, what gets linked to what), not
whether memory helps a real model.
"""

from __future__ import annotations

import json

import pytest

from conftest import ITEM
from self_evolving_agents.agents import PolicyAgent, StepwiseAgent
from self_evolving_agents.envs import make_env, scan_task
from self_evolving_agents.llm import ScriptedLLM, TrackedLLM, make_backend
from self_evolving_agents.methods.reasoningbank import (
    Experience,
    MemoryItem,
    ReasoningBank,
    Verdict,
    parse_memory_items,
    prompts,
)
from self_evolving_agents.methods.reasoningbank.induction import (
    EnvJudge,
    LLMJudge,
    MemoryExtractor,
    refine_notes,
    select_best,
)
from self_evolving_agents.methods.reasoningbank.pipeline import (
    PipelineConfig,
    ReasoningBankPipeline,
    summarise,
)
from self_evolving_agents.methods.reasoningbank.render import render_memory, render_trajectory
from self_evolving_agents.policies import always, scanning_policy
from self_evolving_agents.provenance import ProvenanceStore

# --------------------------------------------------------------------------- parsing


def test_parse_memory_items_reference_format():
    text = """Thinking about why it worked...

```
# Memory Item 1
## Title Check the buffer first
## Description Use when the buffer may be full; not needed right after a downlink.
## Content Scanning with a full buffer records nothing.
It wastes the whole step.

# Memory Item 2
## Title: Second
## Description
on the next line
## Content **bold content**
```
"""
    items = parse_memory_items(text, source="success")
    assert [i.title for i in items] == ["Check the buffer first", "Second"]
    assert (
        items[0].content == "Scanning with a full buffer records nothing. It wastes the whole step."
    )
    assert items[1].description == "on the next line"
    assert items[1].content == "bold content"
    assert all(i.source == "success" for i in items)


def test_parse_memory_items_drops_incomplete_blocks_and_honours_limit():
    text = "# Memory Item 1\n## Title only a title\n\n" + "\n\n".join(
        f"# Memory Item {i}\n## Title T{i}\n## Description D\n## Content C{i}" for i in range(2, 7)
    )
    items = parse_memory_items(text, source="failure", limit=3)
    assert [i.title for i in items] == ["T2", "T3", "T4"]
    assert parse_memory_items("no items here at all", source="failure") == []


def test_memory_item_render_round_trips_through_the_parser():
    item = MemoryItem("A title", "When to use it.", "What to do.")
    parsed = parse_memory_items(render_memory([item, item]), source="success")
    assert [(p.title, p.description, p.content) for p in parsed] == [
        ("A title", "When to use it.", "What to do.")
    ] * 2


# --------------------------------------------------------------------------- bank


def experience(query, titles, *, task_key="", conditions=None, created_at=None):
    items = [MemoryItem(t, f"about {t}", f"content of {t}") for t in titles]
    exp = Experience(query=query, items=items, task_key=task_key, conditions=conditions or {})
    if created_at is not None:
        exp.created_at = created_at
        for item in items:
            item.created_at = created_at
    return exp


def test_experience_retrieval_returns_all_items_of_the_nearest_experience():
    bank = ReasoningBank()
    bank.add(experience("pick up the microscope and put it in the pot", ["grab", "place"]))
    bank.add(experience("measure the soil acidity with the pH meter", ["measure"]))
    bank.add(experience("unlock the door with the rusted key", ["unlock"]))

    got = bank.retrieve("pick up the thermometer and put it in the jar", k=1)
    assert [r.item.title for r in got] == ["grab", "place"]
    assert len({r.experience_id for r in got}) == 1
    two = bank.retrieve("pick up the thermometer and put it in the jar", k=2)
    assert len({r.experience_id for r in two}) == 2
    assert bank.retrieve("anything", k=0) == []
    assert [r.item.title for r in bank.retrieve("pick up the thermometer", k=1, max_items=1)] == [
        "grab"
    ]


def test_identical_queries_resolve_to_the_newest_experience():
    bank = ReasoningBank()
    bank.add(experience("same task", ["old lesson"], created_at=100.0))
    bank.add(experience("same task", ["new lesson"], created_at=200.0))
    assert [r.item.title for r in bank.retrieve("same task", k=1)] == ["new lesson"]


def test_condition_weight_prefers_the_matching_regime():
    bank = ReasoningBank()
    bank.add(
        experience(
            "same task",
            ["big battery lesson"],
            conditions={"battery_capacity_wh": 400.0},
            created_at=200.0,
        )
    )
    bank.add(
        experience(
            "same task",
            ["small battery lesson"],
            conditions={"battery_capacity_wh": 50.0},
            created_at=100.0,
        )
    )
    current = {"battery_capacity_wh": 60.0}
    text_only = bank.retrieve("same task", k=1, conditions=current)
    weighted = bank.retrieve("same task", k=1, conditions=current, condition_weight=0.5)
    assert text_only[0].item.title == "big battery lesson", "without the weight, recency decides"
    assert weighted[0].item.title == "small battery lesson"


def test_item_retrieval_diversifies_and_caps():
    bank = ReasoningBank()
    for i in range(4):
        bank.add(
            experience("same task", ["charge before the battery runs low"], created_at=100.0 + i)
        )
    bank.add(experience("same task", ["unload the reaction wheels early"], created_at=50.0))

    query = "when should I charge the battery"
    greedy = bank.retrieve(query, mode="item", max_items=2, diversity=0.0)
    diverse = bank.retrieve(query, mode="item", max_items=2, diversity=0.5)
    assert len({r.item.title for r in greedy}) == 1, "pure relevance returns near-duplicates"
    assert [r.item.title for r in diverse] == [
        "charge before the battery runs low",
        "unload the reaction wheels early",
    ], "the most relevant item first, then something different"
    assert len(bank.retrieve(query, mode="item", max_items=3)) == 3
    with pytest.raises(ValueError, match="max_items"):
        bank.retrieve("same task", mode="item")
    with pytest.raises(ValueError, match="mode"):
        bank.retrieve("same task", mode="psychic")


def test_utility_weight_promotes_items_with_a_good_track_record():
    bank = ReasoningBank()
    bank.add(experience("same task", ["lesson that helped"], created_at=1.0))
    bank.add(experience("same task", ["lesson that hurt"], created_at=2.0))
    helped, hurt = bank.items
    bank.record_outcome([helped.id], 0.9, True)
    bank.record_outcome([hurt.id], -0.8, False)
    assert (helped.uses, helped.mean_score, helped.successes) == (1, 0.9, 1)

    plain = bank.retrieve("same task", mode="item", max_items=1, diversity=0.0)
    weighted = bank.retrieve(
        "same task", mode="item", max_items=1, diversity=0.0, utility_weight=1.0
    )
    assert plain[0].item.title == "lesson that hurt", "newest wins a relevance tie"
    assert weighted[0].item.title == "lesson that helped"


def test_exclude_task_keys():
    bank = ReasoningBank()
    bank.add(experience("task a", ["from a"], task_key="a"))
    bank.add(experience("task a", ["from b"], task_key="b"))
    assert [r.item.title for r in bank.retrieve("task a", k=5, exclude_task_keys=["b"])] == [
        "from a"
    ]
    assert bank.retrieve("task a", k=5, exclude_task_keys=["a", "b"]) == []


def test_bank_persists_items_and_usage(tmp_path):
    path = tmp_path / "bank.jsonl"
    bank = ReasoningBank(path)
    bank.add(experience("first task", ["one", "two"], task_key="k", conditions={"x": 1.0}))
    bank.record_outcome([bank.items[0].id], 0.5, True)

    lines = path.read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["query"] == "first task"
    again = ReasoningBank(path)
    assert again.stats() == bank.stats()
    assert again.items[0].uses == 1 and again.experiences[0].conditions == {"x": 1.0}
    assert all(i.experience_id == again.experiences[0].id for i in again.items)
    assert [r.item.title for r in again.retrieve("first task")] == ["one", "two"]


def test_dedup_threshold_drops_near_duplicates():
    bank = ReasoningBank(dedup_threshold=0.95)
    bank.add(experience("t", ["charge early"]))
    added = bank.add(experience("t", ["charge early", "something else entirely"]))
    assert [i.title for i in added.items] == ["something else entirely"]
    assert added.meta["dropped_duplicates"][0]["duplicate_of"] == bank.experiences[0].items[0].id
    default = ReasoningBank()
    default.add(experience("t", ["charge early"]))
    default.add(experience("t", ["charge early"]))
    assert len(default.items) == 2, "the paper's consolidation appends without pruning"


# --------------------------------------------------------------------------- judge and extractor


def trajectory(policy, regime="small_battery", seed=0, env_id="toy-scan"):
    return PolicyAgent(policy).run(make_env(scan_task(env_id, regime, seed=seed)))


def spec():
    return make_env(scan_task("toy-scan")).spec


def test_env_judge_uses_ground_truth():
    lost = trajectory(always("scan"))
    verdict = EnvJudge().judge(spec(), lost.query, lost)
    assert (verdict.success, verdict.source) == (False, "env")
    assert "battery" in verdict.thoughts
    assert EnvJudge().judge(spec(), "q", trajectory(scanning_policy(), "nominal", seed=2)).success


def test_llm_judge_prompt_and_parsing():
    llm = ScriptedLLM(
        'Thoughts: The spacecraft was lost\nwhen the battery ran flat.\nStatus: "failure"'
    )
    traj = trajectory(always("scan"))
    verdict = LLMJudge(TrackedLLM(llm)).judge(spec(), traj.query, traj)
    assert verdict.success is False and verdict.source == "llm" and verdict.llm_call_id
    assert verdict.thoughts == "The spacecraft was lost when the battery ran flat."

    sent = llm.requests[0]
    assert sent.purpose == "judge" and sent.temperature == 0.0
    assert "A false success is more harmful than a false failure" in sent.system
    assert "survives to the time limit" in sent.system, (
        "the environment's success criterion is included"
    )
    content = sent.messages[0]["content"]
    assert "spacecraft lost because the battery was fully depleted" in content
    assert "Rules of the environment" in content and "Final state" in content
    for hidden in ("scan_fraction", "min_battery", "'alive'", '"alive"'):
        assert hidden not in content, "ground-truth metrics must never reach the judge"


@pytest.mark.parametrize(
    "reply, expected",
    [
        ('Thoughts: fine\nStatus: "success"', True),
        ("Thoughts: fine\nStatus: success", True),
        ("Thoughts: x\nStatus: **Failure**", False),
        ("Status: success\n...reconsidering...\nStatus: failure", False),
        ("I think it went well.", False),
        ("", False),
    ],
)
def test_llm_judge_status_parsing(reply, expected):
    traj = trajectory(scanning_policy(), "nominal", seed=2)
    verdict = LLMJudge(ScriptedLLM(reply)).judge(spec(), traj.query, traj)
    assert verdict.success is expected
    if "Status" not in reply:
        assert "no parsable status" in verdict.thoughts


def test_extractor_picks_the_prompt_from_the_verdict():
    llm = ScriptedLLM(ITEM)
    extractor = MemoryExtractor(llm, max_items=3)
    traj = trajectory(always("scan"))

    failed, _ = extractor.extract(spec(), traj.query, traj, Verdict(False, "battery ran flat"))
    succeeded, _ = extractor.extract(spec(), traj.query, traj, Verdict(True, "it survived"))
    fail_req, ok_req = llm.requests

    assert failed[0].source == "failure" and succeeded[0].source == "success"
    assert "attempted to resolve the task but failed" in fail_req.system
    assert "successfully accomplished the task" in ok_req.system
    assert "at most 3" in fail_req.system and "spacecraft operations" in fail_req.system
    assert "state the conditions under which the insight was observed" in fail_req.system
    assert fail_req.temperature == 1.0 and fail_req.purpose == "extract"
    assert "The task failed because: battery ran flat" in fail_req.messages[0]["content"]
    assert "The task succeeded because: it survived" in ok_req.messages[0]["content"]


def test_contrast_and_refine_extraction_show_every_attempt():
    llm = ScriptedLLM(ITEM)
    extractor = MemoryExtractor(llm, max_items_contrast=5)
    a, b = trajectory(always("scan")), trajectory(scanning_policy())

    items, _ = extractor.extract_contrast(spec(), a.query, [a, b])
    assert items[0].source == "contrast"
    contrast = llm.requests[0]
    assert "compare and contrast" in contrast.system and "at most 5" in contrast.system
    assert "**Trajectory 1:**" in contrast.messages[0]["content"]
    assert "**Trajectory 2:**" in contrast.messages[0]["content"]

    items, _ = extractor.extract_refine(spec(), a.query, [a, b], ["charge earlier"])
    assert items[0].source == "refine"
    assert (
        "Notes written after attempt 1:**\ncharge earlier" in llm.requests[1].messages[0]["content"]
    )


def test_refine_notes_and_selection():
    a, b = trajectory(always("scan")), trajectory(scanning_policy())
    llm = ScriptedLLM(
        {"refine": " - be careful ", "select": "Thoughts: second is better.\nBest: 2"}
    )
    note, _ = refine_notes(llm, spec(), a.query, [a], [])
    assert note == "- be careful"
    assert prompts.SEQUENTIAL_CHECK in llm.requests[0].messages[0]["content"]
    refine_notes(llm, spec(), a.query, [a, b], [note])
    assert prompts.SEQUENTIAL_CHECK_FOLLOWING in llm.requests[1].messages[0]["content"]
    assert "**Your notes after attempt 1:**" in llm.requests[1].messages[0]["content"]

    assert select_best(llm, spec(), a.query, [a, b])[0] == 1
    assert select_best(ScriptedLLM("Best: 7"), spec(), a.query, [a, b])[0] == 0, (
        "out of range falls back"
    )
    assert select_best(ScriptedLLM("unused"), spec(), a.query, [a])[0] == 0


def test_render_trajectory_collapses_runs_and_respects_the_budget():
    traj = trajectory(always("scan"), "nominal", seed=1)
    text = render_trajectory(traj)
    assert "repeated" in text and "more times" in text
    assert text.count("<action>scan</action>") < len(traj.steps)
    assert f"over {len(traj.steps)} steps" in text
    assert "The agent committed to this policy" in text

    verbose = StepwiseAgent(
        ScriptedLLM("<think>" + "word " * 60 + "</think><action>scan</action>")
    ).run(make_env(scan_task("toy-scan", seed=1)))
    short = render_trajectory(verbose, max_chars=3000)
    assert len(short) < 3600 and "step records omitted for length" in short
    assert "[step 1]" in short and f"[step {len(verbose.steps)}]" in short, "both ends are kept"


# --------------------------------------------------------------------------- pipeline


def build(tmp_path, llm_backend, agent=None, judge="llm", **config):
    store = ProvenanceStore(tmp_path / "prov.sqlite")
    store.start_run("test", "pipeline", config)
    llm = TrackedLLM(llm_backend, store=store)
    bank = ReasoningBank(tmp_path / "bank.jsonl")
    pipeline = ReasoningBankPipeline(
        agent or StepwiseAgent(llm),
        LLMJudge(llm) if judge == "llm" else EnvJudge(),
        bank=bank,
        extractor=MemoryExtractor(llm),
        llm=llm,
        store=store,
        config=PipelineConfig(**config),
    )
    return pipeline, bank, store, llm


def tasks(n, regime="tiny_battery", duration_s=3600.0, **params):
    """Short episodes in which scanning without ever charging is certain to drain the battery."""
    params = {"init_battery_min": 0.3, "init_battery_max": 0.35, **params}
    return [
        scan_task("toy-scan", regime, seed=s, duration_s=duration_s, **params) for s in range(n)
    ]


def test_config_validation():
    for bad in (dict(memory="telepathy"), dict(scaling="sideways"), dict(k=0), dict(k=3)):
        with pytest.raises(ValueError):
            PipelineConfig(**bad)
    assert PipelineConfig(retrieval_mode="item").max_items == 6


def test_pipeline_requires_what_its_mode_needs(scripted):
    agent = StepwiseAgent(scripted)
    with pytest.raises(ValueError, match="bank and an extractor"):
        ReasoningBankPipeline(agent, EnvJudge())
    with pytest.raises(ValueError, match="needs an llm"):
        ReasoningBankPipeline(
            agent,
            EnvJudge(),
            bank=ReasoningBank(),
            extractor=MemoryExtractor(scripted),
            config=PipelineConfig(scaling="parallel", k=2),
        )
    ReasoningBankPipeline(agent, EnvJudge(), config=PipelineConfig(memory="none"))


def test_closed_loop_feeds_earlier_lessons_to_later_tasks(tmp_path, scripted):
    pipeline, bank, store, llm = build(tmp_path, scripted)
    first, second = pipeline.run_stream(tasks(2))

    assert first.retrieved_item_ids == [], "the bank starts empty"
    assert len(first.new_item_ids) == 1 and first.judged_success is False
    assert second.retrieved_item_ids == first.new_item_ids, "task 2 is given task 1's lesson"

    act_systems = [r.system for r in scripted.requests if r.purpose == "act"]
    assert "Keep a reserve" not in act_systems[0]
    assert "Keep a reserve" in act_systems[-1]
    assert bank.get_item(first.new_item_ids[0]).uses == 1
    assert bank.stats()["experiences"] == 2


def test_no_memory_baseline_learns_nothing(tmp_path, scripted):
    pipeline, bank, store, _ = build(tmp_path, scripted, memory="none")
    records = pipeline.run_stream(tasks(2))
    assert all(not r.new_item_ids and not r.retrieved_item_ids for r in records)
    assert len(bank) == 0 and "extract" not in scripted.purposes()
    assert store.counts()["trajectory"] == 2


def test_success_only_ablation_skips_failed_trajectories(tmp_path, scripted):
    pipeline, bank, _, _ = build(tmp_path, scripted, include_failures=False)
    pipeline.run_stream(tasks(2))  # always-scan on a small battery: both fail
    assert len(bank) == 0 and "extract" not in scripted.purposes()


def test_env_judge_mode_makes_no_judge_calls(tmp_path, scripted):
    pipeline, bank, _, _ = build(tmp_path, scripted, judge="env")
    record = pipeline.run_task(tasks(1)[0])
    assert record.judge_source == "env" and "judge" not in scripted.purposes()
    assert record.judged_success == record.success


def test_provenance_links_items_to_their_sources_and_uses(tmp_path, scripted):
    pipeline, bank, store, _ = build(tmp_path, scripted)
    first, second = pipeline.run_stream(tasks(2))
    item_id, traj_1, traj_2 = (
        first.new_item_ids[0],
        first.trajectory_ids[0],
        second.trajectory_ids[0],
    )

    upstream = {(r["kind"], r["via"]) for r in store.lineage(item_id)}
    assert ("trajectory", "wasDerivedFrom") in upstream
    assert ("experience", "wasDerivedFrom") in upstream
    assert ("llm_call", "wasGeneratedBy") in upstream
    assert traj_1 in {r["id"] for r in store.lineage(item_id)}
    assert traj_2 in {r["id"] for r in store.lineage(item_id, "downstream")}, "who used this item?"

    verdict = store.get_node(f"verdict_{traj_1}")
    assert verdict["data"]["success"] is False and verdict["data"]["source"] == "llm"
    extract_call = next(e["dst"] for e in store.edges(src=item_id, relation="wasGeneratedBy"))
    assert store.get_llm_call(extract_call)["purpose"] == "extract"
    stored = store.load_trajectory(traj_2)
    assert stored.memory_item_ids == [item_id]
    assert stored.meta["retrieval"][0]["item"] == item_id
    assert store.get_llm_call(stored.steps[0].llm_call_id)["purpose"] == "act"


def test_parallel_scaling_contrasts_attempts_into_one_experience(tmp_path, scripted):
    pipeline, bank, store, _ = build(tmp_path, scripted, scaling="parallel", k=3)
    record = pipeline.run_task(tasks(1)[0])

    assert len(record.trajectory_ids) == 3 and len(record.attempt_scores) == 3
    assert len(bank) == 1 and bank.items[0].source == "contrast"
    assert bank.experiences[0].trajectory_ids == record.trajectory_ids
    purposes = scripted.purposes()
    assert purposes.count("judge") == 3 and purposes.count("extract") == 1
    assert purposes.count("select") == 1 and record.selected == 0
    samples = {r.sample for r in scripted.requests if r.purpose == "act"}
    assert samples == {0, 1, 2}, "each attempt is a separate draw"
    sources = {e["dst"] for e in store.edges(src=bank.items[0].id, relation="wasDerivedFrom")}
    assert set(record.trajectory_ids) <= sources


def test_vanilla_scaling_extracts_each_attempt_separately(tmp_path, scripted):
    pipeline, bank, _, _ = build(tmp_path, scripted, scaling="vanilla", k=2)
    record = pipeline.run_task(tasks(1)[0])
    assert len(bank) == 2 and {i.source for i in bank.items} == {"failure"}
    assert scripted.purposes().count("extract") == 2 and len(record.new_item_ids) == 2


def test_sequential_scaling_carries_notes_into_the_next_attempt(tmp_path, scripted):
    pipeline, bank, _, _ = build(tmp_path, scripted, scaling="sequential", k=3)
    record = pipeline.run_task(tasks(1)[0])

    assert len(record.trajectory_ids) == 3 and record.selected == 2, (
        "the last attempt is the answer"
    )
    assert scripted.purposes().count("refine") == 2
    by_sample = {}
    for request in scripted.requests:
        if request.purpose == "act":
            by_sample.setdefault(request.sample, request.system)
    assert "your own notes" not in by_sample[0]
    assert "- charge earlier" in by_sample[1] and by_sample[2].count("- charge earlier") == 2
    assert len(bank) == 1 and bank.items[0].source == "refine"
    assert bank.experiences[0].meta["notes"] == ["- charge earlier", "- charge earlier"]


def test_summary_and_saved_records(tmp_path, scripted):
    pipeline, _, _, _ = build(tmp_path, scripted)
    pipeline.run_stream(tasks(3))
    summary = pipeline.summary()
    assert summary["tasks"] == 3 and summary["success_rate"] == 0.0
    assert summary["failures_by_mode"] == {"battery": 3}
    assert summary["judge_agreement"] == 1.0 and summary["new_items"] == 3
    assert summary["mean_steps_successful"] is None and summary["mean_steps_failed"] > 0
    assert summarise([]) == {"tasks": 0}

    path = tmp_path / "records.jsonl"
    pipeline.save_records(path)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 3 and rows[0]["task"]["env_id"] == "toy-scan"


def test_policy_agent_can_be_driven_through_the_pipeline(tmp_path, scripted):
    pipeline, bank, _, _ = build(
        tmp_path, scripted, agent=PolicyAgent(scanning_policy()), judge="env"
    )
    record = pipeline.run_task(scan_task("toy-scan", "nominal", seed=2))
    assert record.success is True and bank.items[0].source == "success"
    assert "committed to this policy" in scripted.requests[-1].messages[0]["content"]


def test_offline_demo_runs_the_whole_loop_and_obeys_its_own_lessons(tmp_path):
    """Plumbing check only: the stand-in reads back tags it wrote itself."""
    pipeline, bank, store, llm = build(
        tmp_path, make_backend("offline-demo"), retrieval_mode="item", max_items=6
    )
    records = pipeline.run_stream(
        [scan_task("toy-scan", "small_battery", seed=s) for s in range(4)]
    )
    assert records[0].failure == "battery", "with an empty bank the stand-in scans until it dies"
    assert records[-1].failure is None, "once the lesson is in memory it charges"
    assert records[-1].retrieved_item_ids
    assert {i.source for i in bank.items} >= {"failure", "success"}
    assert store.counts()["memory_item"] == len(bank.items)
