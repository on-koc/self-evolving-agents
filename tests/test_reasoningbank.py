"""The ReasoningBank baseline, checked against the published specification.

Each test names the row of ``docs/reasoningbank-fidelity.md`` it pins down (S, M, R,
A, J, E). Everything uses scripted stand-ins for the model, so these tests show that
the mechanics are the published ones: what is retrieved, which prompt is used, what
the judge and the extractor are and are not shown. They say nothing about whether
memory helps a real model.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from conftest import ITEM
from self_evolving_agents.agents import PolicyAgent, StepwiseAgent
from self_evolving_agents.envs import make_env, scan_task
from self_evolving_agents.llm import ScriptedLLM, TrackedLLM
from self_evolving_agents.methods.reasoningbank import (
    Experience,
    LLMJudge,
    MemoryExtractor,
    MemoryItem,
    ReasoningBank,
    ReasoningBankConfig,
    ReasoningBankMemory,
    build,
    parse_memory_items,
    prompts,
)
from self_evolving_agents.methods.reasoningbank.render import (
    final_state,
    memory_block,
    render_actions,
    render_memory,
    render_trajectory,
)
from self_evolving_agents.methods.stream import EnvJudge, StreamLoop, Verdict
from self_evolving_agents.policies import always, scanning_policy
from self_evolving_agents.provenance import ProvenanceStore

# --------------------------------------------------------------------------- helpers


def tasks(n, regime="tiny_battery", duration_s=3600.0, **params):
    """Short episodes in which scanning without ever charging is certain to drain the battery."""
    params = {"init_battery_min": 0.3, "init_battery_max": 0.35, **params}
    return [
        scan_task("toy-scan", regime, seed=s, duration_s=duration_s, **params) for s in range(n)
    ]


def trajectory(policy, regime="small_battery", seed=0):
    return PolicyAgent(policy).run(make_env(scan_task("toy-scan", regime, seed=seed)))


def stepwise_trajectory(reply="<think>collect data</think><action>scan</action>", n=1):
    return StepwiseAgent(ScriptedLLM(reply)).run(make_env(tasks(n)[-1]))


def spec():
    return make_env(scan_task("toy-scan")).spec


def loop(tmp_path, backend, **options):
    """The baseline as ``build`` wires it, on the shared stream loop."""
    store = ProvenanceStore(tmp_path / "prov.sqlite")
    store.start_run("test", "baseline", options)
    llm = TrackedLLM(backend, store=store)
    memory, judge = build(
        ReasoningBankConfig(**options), llm, bank_path=tmp_path / "bank.jsonl", store=store
    )
    return StreamLoop(StepwiseAgent(llm), memory=memory, judge=judge, store=store), memory, store


# --------------------------------------------------------------------------- M1: schema


def test_M1_memory_item_has_title_description_and_content():
    text = """Some thinking first.

```
# Memory Item 1
## Title Keep a battery reserve
## Description One sentence about the item.
## Content Charge before the battery gets low.
It takes two lines.

# Memory Item 2
## Title: Downlink during passes
## Description
Use it when a station is in view.
## Content Send data whenever a station is visible.
```"""
    items = parse_memory_items(text, source="success")
    assert [i.title for i in items] == ["Keep a battery reserve", "Downlink during passes"]
    assert items[0].content == "Charge before the battery gets low. It takes two lines."
    assert items[1].description == "Use it when a station is in view."
    assert all(i.source == "success" and i.id.startswith("mem_") for i in items)
    assert set(items[0].to_dict()) == {
        *("id", "title", "description", "content", "source"),
        *("experience_id", "created_at", "meta"),
    }, "no usage statistics or other adaptation fields on the baseline's item"
    assert MemoryItem.from_dict(items[0].to_dict()).to_dict() == items[0].to_dict()


def test_E1_at_most_three_items_and_incomplete_blocks_are_dropped():
    blocks = "\n".join(f"# Memory Item {i}\n## Title T{i}\n## Content C{i}" for i in range(1, 6))
    assert [i.title for i in parse_memory_items(blocks, "success", limit=3)] == ["T1", "T2", "T3"]
    broken = "# Memory Item 1\n## Title only a title\n# Memory Item 2\n## Content only content"
    assert parse_memory_items(broken, "failure") == []
    assert parse_memory_items("no items here", "failure") == []


# --------------------------------------------------------------------------- R5, R6: injection


def test_R6_items_are_shown_by_title_and_content_by_default():
    item = parse_memory_items(ITEM, "failure")[0]
    shown = render_memory([item])
    assert shown == (
        "# Memory Item 1\n## Title Keep a reserve\n"
        "## Content Charge before the battery gets low (rule: charge_below=0.35)."
    )
    assert "## Description" not in shown, "the paper: each item by its title and content"
    with_description = render_memory([item], with_description=True)
    assert "## Description Use when the battery can run flat." in with_description
    assert parse_memory_items(with_description, "failure")[0].content == item.content


def test_R5_memory_block_is_the_published_instruction_followed_by_the_items():
    item = parse_memory_items(ITEM, "failure")[0]
    block = memory_block([item])
    assert block.text.startswith(
        "Below are some memory items that I accumulated from past interaction from the "
        "environment that may be helpful to solve the task. You can use it when you feel it's "
        "relevant. In each step, please first explicitly discuss if you want to use each memory "
        "item or not, and then take action.\n\n# Memory Item 1"
    )
    assert block.item_ids == [item.id]
    assert not memory_block([]), "nothing retrieved means nothing is added to the prompt"


# --------------------------------------------------------------------------- E2, J2: prompts

# Sentences of the published prompts (figures 9 and 10) that must be present, and
# sentences this project once added to them that must not be.
PUBLISHED_EXTRACTION = (
    "You will be given a user query, the corresponding trajectory",
    "The goal of summarized memory items is to be helpful and generalizable for future similar",
    "You can extract *at most 3* memory items from the trajectory.",
    "You must not repeat similar or overlapping items.",
    "Do not mention specific websites, queries, or string contents, but rather focus on the "
    "generalizable insights.",
    "## Description <one sentence summary of the memory item>",
    "## Content <1-3 sentences describing the insights learned to successfully accomplishing "
    "the task>",
)
NOT_PUBLISHED = (
    "state the conditions under which the insight was observed",
    "mark the explanation as a hypothesis",
    "A rule that works under one configuration",
    "identifiers that only exist in this episode",
)


def test_E2_extraction_prompts_are_the_published_ones_with_only_the_domain_replaced():
    success = prompts.success_extraction_system("spacecraft operations")
    failure = prompts.failure_extraction_system("spacecraft operations")
    for text in (success, failure):
        assert text.startswith("You are an expert in spacecraft operations.")
        for sentence in PUBLISHED_EXTRACTION:
            assert sentence in text, sentence
        for sentence in NOT_PUBLISHED:
            assert sentence not in text, f"not part of the published prompt: {sentence}"
    assert "**how an agent successfully accomplished the task**" in success
    assert "You must first think why the trajectory is successful" in success
    assert "**how an agent attempted to resolve the task but failed**" in failure
    assert "You must first reflect and think why the trajectory failed" in failure
    assert "strategies to prevent the failure in the future" in failure
    web = prompts.success_extraction_system("web navigation")
    assert web.replace("web navigation", "spacecraft operations") == success


def test_E2_the_reference_codes_later_wording_is_an_option_that_is_off_by_default():
    revised = prompts.success_extraction_system("x", revised=True)
    assert "Prefer concrete, actionable procedures over abstract principles." in revised
    assert "describing when or when NOT to use the memory item" in revised
    assert "recovery procedures" in prompts.failure_extraction_system("x", revised=True)
    default = prompts.success_extraction_system("x")
    assert "Prefer concrete" not in default and "when NOT to use" not in default


def test_J2_judge_prompt_keeps_the_published_frame_and_answer_format():
    text = prompts.judge_system("spacecraft operations", "Survive and record data.")
    assert text.startswith(
        "You are an expert in evaluating the performance of an agent working on spacecraft "
        "operations."
    )
    assert "the agent's action history and the final state" in text
    assert "your goal is to decide whether the agent's execution is successful or not" in text
    assert "Survive and record data." in text
    assert text.rstrip().endswith('Status: "success" or "failure"')
    assert "Thoughts: <your thoughts and reasoning process>" in text
    assert "Strictness rules" not in text, "added to the reference code after publication"
    strict = prompts.judge_system("x", "", strict=True)
    assert "A false success is more harmful than a false failure" in strict
    sent = prompts.judge_input("the task", "1. scan", "Battery 0%")
    assert sent.startswith("User Intent: the task\n\nTrajectory:\n1. scan\n\n")
    assert "The detailed final state of the environment:" in sent and "```md\nBattery 0%" in sent


# --------------------------------------------------------------------------- M2, M3, R1-R4: bank


def experience(query, *titles, key=""):
    return Experience(
        query=query,
        items=[MemoryItem(t, f"about {t}", f"do {t}") for t in titles],
        task_key=key or query,
    )


def test_M3_consolidation_appends_and_nothing_else():
    bank = ReasoningBank()
    same = [bank.add(experience("scan the Earth", "a")) for _ in range(3)]
    assert len(bank) == 3 and len(bank.items) == 3, "identical items are all kept"
    assert [e.id for e in bank.experiences] == [e.id for e in same], "in order of arrival"
    assert not hasattr(bank, "dedup_threshold") and not hasattr(bank, "record_outcome")


def test_R2_retrieval_returns_all_items_of_the_most_similar_experience():
    bank = ReasoningBank()
    bank.add(experience("operate a satellite with a small battery", "reserve", "eclipse"))
    bank.add(experience("find the cause of the illness in the colony", "interview", "sample"))
    got = bank.retrieve("operate a satellite with a large battery")
    assert [r.item.title for r in got] == ["reserve", "eclipse"], "k = 1: one experience, whole"
    assert len({r.experience_id for r in got}) == 1 and got[0].score > 0.5
    both = bank.retrieve("operate a satellite with a large battery", k=2)
    assert [r.item.title for r in both] == ["reserve", "eclipse", "interview", "sample"]
    assert bank.retrieve("anything", k=0) == [] and ReasoningBank().retrieve("anything") == []


def test_R2_only_the_query_decides_what_is_retrieved():
    """Neither the items' text nor anything about the task besides its query is looked at."""
    bank = ReasoningBank()
    bank.add(experience("alpha beta gamma", "satellite battery reserve"))
    bank.add(experience("satellite battery reserve", "alpha beta gamma"))
    assert bank.retrieve("satellite battery reserve")[0].item.title == "alpha beta gamma"
    import inspect

    assert list(inspect.signature(bank.retrieve).parameters) == ["query", "k"]


def test_R4_a_best_match_from_which_nothing_was_extracted_yields_nothing():
    bank = ReasoningBank()
    bank.add(experience("operate a satellite", "reserve"))
    bank.add(experience("find the cause of the illness"))  # extraction produced no items
    assert bank.retrieve("find the cause of the illness") == []


def test_ties_go_to_the_oldest_experience_as_in_the_reference_code():
    """Exact ties are rare on the paper's benchmarks and normal in a repeated task."""
    bank = ReasoningBank()
    bank.add(experience("same task", "first lesson"))
    bank.add(experience("same task", "second lesson"))
    bank.add(experience("same task", "third lesson"))
    assert bank.retrieve("same task")[0].item.title == "first lesson"
    newest = ReasoningBank(tie_break="newest")
    for title in ("first lesson", "second lesson", "third lesson"):
        newest.add(experience("same task", title))
    assert newest.retrieve("same task")[0].item.title == "third lesson"
    with pytest.raises(ValueError, match="tie_break"):
        ReasoningBank(tie_break="random")


def test_R3_instruction_wrapped_lookup_is_optional_and_leaves_stored_vectors_plain():
    class Recorder:
        name = "recorder"

        def __init__(self):
            self.seen = []

        def embed(self, texts):
            self.seen += list(texts)
            return np.ones((len(texts), 2), dtype=np.float32) / np.sqrt(2)

    plain, wrapped = Recorder(), Recorder()
    ReasoningBank(embedder=plain).retrieve("q")
    bank = ReasoningBank(embedder=plain)
    bank.add(experience("stored query", "a"))
    bank.retrieve("current query")
    assert plain.seen == ["stored query", "current query"]
    bank = ReasoningBank(embedder=wrapped, query_instruction="select relevant prior queries")
    bank.add(experience("stored query", "a"))
    bank.retrieve("current query")
    assert wrapped.seen == [
        "stored query",
        "Instruct: select relevant prior queries\nQuery: current query",
    ]


def test_M2_bank_persists_one_experience_per_line_and_reloads(tmp_path):
    path = tmp_path / "bank.jsonl"
    bank = ReasoningBank(path)
    bank.add(experience("operate a satellite", "reserve", key="toy/small/seed=0"))
    lines = path.read_text().splitlines()
    assert len(lines) == 1
    stored = json.loads(lines[0])
    assert stored["query"] == "operate a satellite" and stored["task_key"] == "toy/small/seed=0"
    assert [i["title"] for i in stored["items"]] == ["reserve"]
    again = ReasoningBank(path)
    assert [r.item.title for r in again.retrieve("operate a satellite")] == ["reserve"]
    assert again.stats() == {
        "experiences": 1,
        "items": 1,
        "items_by_source": {"success": 1},
        "embedder": "hashing-1024-c3",
    }


# --------------------------------------------------------------------------- E3: what is rendered


def test_E3_the_extractor_sees_reasoning_and_action_of_each_step_and_nothing_else():
    traj = stepwise_trajectory()
    text = render_trajectory(traj)
    assert text.startswith("<think>\ncollect data\n</think>\n<action>\nscan\n</action>")
    assert text.count("<action>") == len(traj.steps), "every step, none merged"
    for hidden in ("Battery", "battery", "reward", "spacecraft lost", "<observation>", "t="):
        assert hidden not in text, f"observations and feedback are not shown: {hidden}"
    assert traj.outcome.failure == "battery", "the episode did end in a failure"
    assert "battery" not in prompts.extraction_input(traj.query, text).split("Trajectory:")[1]


def test_E3_observations_and_feedback_are_an_option_for_methods_built_on_top():
    traj = stepwise_trajectory()
    rich = render_trajectory(traj, observations=True)
    assert "<observation>\nt=0s battery" in rich and "<feedback>" in rich
    assert "spacecraft lost because the battery was fully depleted" in rich


def test_long_trajectories_are_shortened_from_the_middle():
    traj = trajectory(scanning_policy(), regime="nominal", seed=1)
    assert len(traj.steps) > 60
    full = render_trajectory(traj)
    short = render_trajectory(traj, max_chars=1500)
    assert len(short) <= 1700 < len(full)
    assert "step records omitted for length" in short
    assert short.startswith(full[:200]) and short.endswith(full[-200:])


def test_runs_of_one_action_without_reasoning_are_merged_only_for_policy_agents():
    """A rule policy repeats itself; a step-by-step agent's trajectory is never merged."""
    policy_text = render_trajectory(trajectory(always("scan")))
    assert "[scan repeated" in policy_text
    assert "repeated" not in render_trajectory(stepwise_trajectory())


def test_J2_the_judge_sees_the_action_history_and_the_final_state():
    traj = stepwise_trajectory()
    actions = render_actions(traj)
    assert actions.splitlines()[0] == "1. scan" and len(actions.splitlines()) == len(traj.steps)
    state = final_state(traj)
    assert state.startswith("Time ") and "Battery 0%" in state
    assert "Feedback to the last action:" in state
    assert "spacecraft lost because the battery was fully depleted" in state


# --------------------------------------------------------------------------- J1-J2: judge


def test_J1_llm_judge_labels_without_ground_truth_at_temperature_zero():
    llm = ScriptedLLM(
        'Thoughts: The spacecraft was lost\nwhen the battery ran flat.\nStatus: "failure"'
    )
    traj = stepwise_trajectory()
    verdict = LLMJudge(TrackedLLM(llm)).judge(spec(), traj.query, traj)
    assert verdict.success is False and verdict.source == "llm" and verdict.llm_call_id
    assert verdict.thoughts == "The spacecraft was lost when the battery ran flat."

    sent = llm.requests[0]
    assert sent.purpose == "judge" and sent.temperature == 0.0
    assert "survives to the time limit" in sent.system, "the environment's success criterion"
    assert "Strictness rules" not in sent.system
    body = sent.messages[0]["content"]
    assert body.startswith(f"User Intent: {traj.query}")
    assert "\n1. scan\n2. scan" in body and "Battery 0%" in body
    assert "collect data" not in body, "the published judge sees actions, not reasoning"
    for truth in ("score", "success", str(round(traj.outcome.score, 3))):
        assert truth not in body.replace("successful", ""), f"ground truth leaked: {truth}"


def test_J2_judge_options_reproduce_the_reference_code_or_show_more():
    traj = stepwise_trajectory()
    strict = ScriptedLLM('Status: "success"')
    LLMJudge(strict, strict=True).judge(spec(), traj.query, traj)
    assert "Strictness rules" in strict.requests[0].system
    steps = ScriptedLLM('Status: "success"')
    LLMJudge(steps, history="steps").judge(spec(), traj.query, traj)
    assert "collect data" in steps.requests[0].messages[0]["content"]
    with pytest.raises(ValueError, match="history"):
        LLMJudge(steps, history="everything")


@pytest.mark.parametrize(
    "reply, expected",
    [
        ('Thoughts: fine.\nStatus: "success"', True),
        ("Thoughts: fine.\nStatus: success", True),
        ("**Status**: `failure`", False),
        ("Thoughts: mentions Status: success first.\nStatus: failure", False),
        ("I cannot tell.", False),
        ("", False),
    ],
)
def test_J2_anything_but_a_success_status_is_a_failure(reply, expected):
    traj = trajectory(always("scan"))
    assert LLMJudge(ScriptedLLM(reply)).judge(spec(), "q", traj).success is expected


def test_env_judge_is_the_ground_truth_control():
    lost = trajectory(always("scan"))
    verdict = EnvJudge().judge(spec(), lost.query, lost)
    assert (verdict.success, verdict.source) == (False, "env") and "battery" in verdict.thoughts
    assert EnvJudge().judge(spec(), "q", trajectory(scanning_policy(), "nominal", seed=2)).success


# --------------------------------------------------------------------------- E1-E4: extraction


def test_E1_the_verdict_selects_the_success_or_the_failure_prompt():
    llm = ScriptedLLM(ITEM)
    extractor = MemoryExtractor(TrackedLLM(llm))
    traj = stepwise_trajectory()
    failed, call_id = extractor.extract(spec(), traj.query, traj, Verdict(False, "ran flat"))
    succeeded, _ = extractor.extract(spec(), traj.query, traj, Verdict(True, "fine"))
    assert failed[0].source == "failure" and succeeded[0].source == "success" and call_id
    first, second = llm.requests
    assert first.purpose == "extract" and first.temperature == 1.0
    assert "attempted to resolve the task but failed" in first.system
    assert "successfully accomplished the task" in second.system
    assert first.system == prompts.failure_extraction_system(spec().domain)
    body = first.messages[0]["content"]
    assert body.startswith(f"Query: {traj.query}\n\nTrajectory:\n<think>")
    assert "ran flat" not in body, "the judge's reasoning is not part of the published input"


def test_E4_judge_rationale_and_revised_prompts_are_reference_code_options():
    llm = ScriptedLLM(ITEM)
    extractor = MemoryExtractor(llm, judge_rationale=True, revised=True)
    traj = stepwise_trajectory()
    extractor.extract(spec(), traj.query, traj, Verdict(False, "the battery ran flat"))
    sent = llm.requests[0]
    assert sent.messages[0]["content"].endswith("The task failed because: the battery ran flat")
    assert "when or when NOT to use" in sent.system


# --------------------------------------------------------------------------- the closed loop


def test_defaults_are_the_published_values():
    config = ReasoningBankConfig()
    assert (config.retrieve_k, config.max_items, config.include_failures) == (1, 3, True)
    assert (config.judge, config.judge_temperature, config.extraction_temperature) == (
        "llm",
        0.0,
        1.0,
    )
    switches = (
        config.inject_description,
        config.extractor_sees_judge_rationale,
        config.revised_prompts,
        config.judge_strict,
        config.query_instruction,
    )
    assert not any(switches), "every reference-code variant is off by default"
    with pytest.raises(ValueError):
        ReasoningBankConfig(judge="oracle")


def test_S1_S2_the_loop_starts_empty_and_feeds_earlier_lessons_to_later_tasks(tmp_path, scripted):
    stream, memory, _ = loop(tmp_path, scripted)
    first, second = stream.run_stream(tasks(2))

    assert first.retrieved_item_ids == [], "the bank starts empty"
    assert len(first.new_item_ids) == 1 and first.judged_success is False
    assert second.retrieved_item_ids == first.new_item_ids, "task 2 is given task 1's lesson"

    act_systems = [r.system for r in scripted.requests if r.purpose == "act"]
    assert "Keep a reserve" not in act_systems[0]
    assert prompts.MEMORY_INSTRUCTION in act_systems[-1] and "Keep a reserve" in act_systems[-1]
    assert "## Description" not in act_systems[-1], "title and content only"
    assert memory.stats()["experiences"] == 2
    order = [p for p in scripted.purposes() if p != "act"]
    assert order == ["judge", "extract", "judge", "extract"], "act, then judge, then extract"


def test_S3_no_ground_truth_reaches_the_judge_or_the_extractor(tmp_path, scripted):
    stream, _, _ = loop(tmp_path, scripted)
    record = stream.run_task(tasks(1)[0])
    assert record.success is False and record.failure == "battery"
    for request in scripted.requests:
        if request.purpose in ("judge", "extract"):
            text = request.system + request.messages[0]["content"]
            assert f"{record.score:.3f}"[:6] not in text
            assert "failure mode" not in text and "ground-truth" not in text


def test_success_only_ablation_skips_failed_trajectories(tmp_path, scripted):
    stream, memory, _ = loop(tmp_path, scripted, include_failures=False)
    stream.run_stream(tasks(2))  # always-scan on a tiny battery: both fail
    assert len(memory.bank) == 0 and "extract" not in scripted.purposes()
    assert scripted.purposes().count("judge") == 2, "they are still judged"


def test_env_judge_control_makes_no_judge_calls(tmp_path, scripted):
    stream, _, _ = loop(tmp_path, scripted, judge="env")
    record = stream.run_task(tasks(1)[0])
    assert record.judge_source == "env" and "judge" not in scripted.purposes()
    assert record.judged_success == record.success


def test_reference_code_variants_change_exactly_what_they_say(tmp_path, scripted):
    stream, _, _ = loop(
        tmp_path,
        scripted,
        inject_description=True,
        extractor_sees_judge_rationale=True,
        judge_strict=True,
        revised_prompts=True,
        tie_break="newest",
    )
    stream.run_stream(tasks(2))
    by = {p: [r for r in scripted.requests if r.purpose == p] for p in ("act", "judge", "extract")}
    assert "## Description Use when the battery can run flat." in by["act"][-1].system
    assert "Strictness rules" in by["judge"][0].system
    assert (
        "The task failed because: looked at the ending." in by["extract"][0].messages[0]["content"]
    )
    assert "when or when NOT to use" in by["extract"][0].system


def test_provenance_links_items_to_their_sources_and_uses(tmp_path, scripted):
    stream, _, store = loop(tmp_path, scripted)
    first, second = stream.run_stream(tasks(2))
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


def test_a_learning_memory_needs_a_judge(scripted):
    memory = ReasoningBankMemory(ReasoningBank(), MemoryExtractor(scripted))
    with pytest.raises(ValueError, match="needs a judge"):
        StreamLoop(StepwiseAgent(scripted), memory=memory)
