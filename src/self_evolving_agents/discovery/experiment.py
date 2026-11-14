"""The DiscoveryWorld memory experiment: experience, then transfer with the memory frozen.

A protocol (JSON, see ``protocols/discovery_*.json``) fixes the model, the agent, the
worlds of each phase, the arms and the number of repeats:

1. **Experience.** Each arm works through the same stream of worlds, learning as it
   goes (arms without a memory just work through them).
2. **Transfer.** The memory is frozen and the arm is evaluated on held-out worlds, in
   named conditions. The design uses three:

   * ``same_world``: a world from the experience phase again (same scenario,
     difficulty and seed, hence the same answer). Remembering the answer helps here.
   * ``new_world``: the same kind of task with a seed not seen before, hence a
     different answer. Remembering the answer is useless or harmful; knowing how to
     find it is what helps.
   * ``new_theme``: a scenario not seen at all, a different mechanism. Only a way of
     investigating can carry over.

3. **Lesions.** The same frozen memory with one kind of memory removed, on the same
   transfer worlds. A behaviour that depends on remembered strategies should drop.

Each phase of each arm and repeat is one run directory (``sea run`` format), so
every episode, prompt and model call is recorded and replayable.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ..envs import answer_key, discoveryworld_task
from ..llm import split_spec
from ..methods.registry import METHODS, check_combination, make_config, protocol_agent
from ..methods.run import run_method
from ..tasks import parse_seeds
from ..types import Task, Trajectory

CONDITIONS = ("same_world", "new_world", "new_theme")


def world_tasks(
    specs: list[dict[str, Any]], max_steps: int | None, order: str = "sequential"
) -> list[Task]:
    """Tasks from ``[{"scenario", "difficulty", "seeds"}]``; interleaved by seed if asked.

    Without a step limit (here or in a spec) a world gets the paper's for its difficulty.
    """
    groups = []
    for spec in specs:
        seeds = spec["seeds"]
        seeds = parse_seeds(seeds) if isinstance(seeds, str) else [int(s) for s in seeds]
        limit = spec.get("max_steps", max_steps)
        groups.append(
            [
                discoveryworld_task(
                    spec["scenario"],
                    spec.get("difficulty", "Normal"),
                    seed=seed,
                    max_steps=None if limit is None else int(limit),
                )
                for seed in seeds
            ]
        )
    if order == "interleaved":
        longest = max((len(g) for g in groups), default=0)
        return [g[i] for i in range(longest) for g in groups if i < len(g)]
    return [task for group in groups for task in group]


def load_protocol(path: str | Path) -> dict[str, Any]:
    """Read and check a protocol before anything is spent on it."""
    protocol = json.loads(Path(path).read_text())
    for key in ("name", "model", "experience", "transfer", "arms"):
        if key not in protocol:
            raise ValueError(f"protocol has no '{key}'")
    for name, arm in protocol["arms"].items():
        method = arm.get("method")
        if method not in METHODS or METHODS[method].runner != "stream":
            raise ValueError(f"arm {name!r}: {method!r} is not a stream method")
        make_config(method, arm.get("options"))
        agent, _ = protocol_agent({"agent": "hypothesizer", **protocol}, arm)
        check_combination(method, agent, {"discoveryworld"}, arm.get("options"))
        for lesion in (protocol.get("lesions") or {}).get(name, []):
            make_config(method, {**(arm.get("options") or {}), **(lesion.get("options") or {})})
    for name in protocol.get("lesions") or {}:
        if name not in protocol["arms"]:
            raise ValueError(f"lesion for unknown arm {name!r}")
    if not isinstance(protocol["transfer"], dict) or not protocol["transfer"]:
        raise ValueError("'transfer' must name at least one condition")
    max_steps = protocol.get("max_steps")
    world_tasks(protocol["experience"]["worlds"], max_steps)
    for specs in protocol["transfer"].values():
        world_tasks(specs, max_steps)
    return protocol


def _questions(world: dict[str, Any]) -> frozenset[str]:
    key = answer_key(world["scenario"], world["difficulty"], int(world["seed"]))
    return frozenset(q for task in key for q in task["critical_questions"])


def check_design(protocol: dict[str, Any]) -> dict[str, Any]:
    """Whether the transfer worlds are what their conditions claim, judged by the answers.

    The answer a world hides is read from its critical questions. ``new_world`` worlds
    must not be experience worlds and must not hide the same answer as one (in
    Combinatorial Chemistry, Easy, seeds 2 and 4 both hide Substance C);
    ``same_world`` worlds must be experience worlds; ``new_theme`` worlds must be of a
    scenario the experience phase does not contain. These are ``problems``. A
    ``new_world`` world that shares some critical questions with experience worlds
    (Archaeology Dating, Easy, seeds 2 to 4 all have their oldest artifact at 890,000
    years) is a ``warning``: remembering the shared part would score on it, which is
    why grades also give the knowledge score on the questions no experience world has
    (``knowledge_novel``). Needs DiscoveryWorld (the answers are read from the worlds).
    """
    max_steps = protocol.get("max_steps")
    experience = [
        world_of_record(t.to_dict())
        for t in world_tasks(protocol["experience"]["worlds"], max_steps)
    ]
    seen_worlds = {(w["scenario"], w["difficulty"], w["seed"]) for w in experience}
    seen_scenarios = {w["scenario"] for w in experience}
    seen_questions: dict[str, dict[str, Any]] = {}
    for world in experience:
        for question in _questions(world):
            seen_questions.setdefault(question, world)
    result: dict[str, Any] = {"conditions": {}, "problems": [], "warnings": []}
    for condition, specs in protocol["transfer"].items():
        rows = []
        for task in world_tasks(specs, max_steps):
            world = world_of_record(task.to_dict())
            name = f"{world['scenario']} / {world['difficulty']} / seed {world['seed']}"
            questions = _questions(world)
            shared = sorted(q for q in questions if q in seen_questions)
            identical = [
                e for e in experience if questions and _questions(e) == questions and e != world
            ]
            is_seen = (world["scenario"], world["difficulty"], world["seed"]) in seen_worlds
            rows.append(
                {
                    "world": world,
                    "questions": len(questions),
                    "shared_questions": shared,
                    "same_answer_as": identical,
                    "experience_world": is_seen,
                }
            )
            if condition == "same_world" and not is_seen:
                result["problems"].append(f"same_world: {name} is not an experience world")
            if condition == "new_world":
                if is_seen:
                    result["problems"].append(f"new_world: {name} is an experience world")
                elif identical:
                    other = identical[0]
                    result["problems"].append(
                        f"new_world: {name} hides the same answer as experience world "
                        f"{other['scenario']} / {other['difficulty']} / seed {other['seed']}"
                    )
                elif shared:
                    result["warnings"].append(
                        f"new_world: {name} shares {len(shared)} of {len(questions)} critical "
                        "questions with experience worlds"
                    )
                if world["scenario"] not in seen_scenarios:
                    result["warnings"].append(
                        f"new_world: {name} is of a scenario the experience phase does not "
                        "contain (that is a new theme)"
                    )
            if condition == "new_theme" and world["scenario"] in seen_scenarios:
                result["problems"].append(
                    f"new_theme: {name} is of a scenario the experience phase contains"
                )
        result["conditions"][condition] = rows
    return result


def _seeded(llm: str, options: dict[str, Any], repeat: int) -> dict[str, Any]:
    """Repeats differ by the model's seed where the backend takes one."""
    options = dict(options)
    if split_spec(llm)[0] in ("openai", "ollama", "hf"):
        options["seed"] = int(options.get("seed", 0)) + 1000 * repeat
    return options


def run_protocol(
    protocol: dict[str, Any],
    out: str | Path,
    *,
    llm: str | None = None,
    llm_options: dict[str, Any] | None = None,
    arms: list[str] | None = None,
    repeats: int | None = None,
    quiet: bool = False,
) -> dict[str, list[int]]:
    """Run every phase of every arm. Re-running continues from the call caches."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    model = dict(protocol["model"])
    if llm:
        model["llm"] = llm
        model["llm_options"] = dict(llm_options or {})
    elif llm_options:
        model["llm_options"] = {**(model.get("llm_options") or {}), **llm_options}
    n_repeats = int(repeats or protocol.get("repeats", 1))
    max_steps = protocol.get("max_steps")
    experience = world_tasks(
        protocol["experience"]["worlds"],
        max_steps,
        protocol["experience"].get("order", "sequential"),
    )
    transfer = {
        condition: world_tasks(specs, max_steps)
        for condition, specs in protocol["transfer"].items()
    }
    design = check_design(protocol)
    (out / "design.json").write_text(json.dumps(design, indent=2))
    if design["problems"] and not protocol.get("allow_design_problems"):
        raise ValueError(
            "the protocol's transfer worlds are not what their conditions claim:\n  "
            + "\n  ".join(design["problems"])
            + "\n(set allow_design_problems to run it anyway)"
        )
    if not quiet:
        for warning in design["warnings"]:
            print(f"warning: {warning}")
    resolved = {**protocol, "model": model, "repeats": n_repeats}
    (out / "protocol.json").write_text(json.dumps(resolved, indent=2))
    budget = protocol.get("budget") or {}
    statuses: dict[str, list[int]] = {}

    for name, arm in protocol["arms"].items():
        if arms and name not in arms:
            continue
        statuses[name] = []
        agent, agent_options = protocol_agent({"agent": "hypothesizer", **protocol}, arm)
        for rep in range(n_repeats):
            base = out / name / f"rep-{rep}"
            common = dict(
                llm=model["llm"],
                llm_options=_seeded(model["llm"], model.get("llm_options") or {}, rep),
                agent=agent,
                agent_options=agent_options,
                embedder=model.get("embedder", "hashing"),
                embedder_options=model.get("embedder_options"),
                max_cost=budget.get("max_cost_usd_per_run"),
                max_calls=budget.get("max_calls_per_run"),
                quiet=quiet,
            )
            tag = {"protocol": protocol["name"], "arm": name, "repeat": rep}
            if not quiet:
                print(
                    f"=== {name}, repeat {rep + 1} of {n_repeats}: experience ({len(experience)} worlds)"
                )
            status, _ = run_method(
                arm["method"],
                experience,
                base / "experience",
                options=arm.get("options"),
                extra_config={**tag, "phase": "experience", "condition": "experience"},
                **common,
            )
            statuses[name].append(status)
            memory = base / "experience" / "bank.jsonl"
            variants = [("transfer", arm.get("options") or {})] + [
                (
                    f"lesion-{lesion['name']}",
                    {**(arm.get("options") or {}), **(lesion.get("options") or {})},
                )
                for lesion in (protocol.get("lesions") or {}).get(name, [])
            ]
            for prefix, options in variants:
                for condition, tasks in transfer.items():
                    if not quiet:
                        print(
                            f"=== {name}, repeat {rep + 1}: {prefix} / {condition} ({len(tasks)} worlds)"
                        )
                    status, _ = run_method(
                        arm["method"],
                        tasks,
                        base / f"{prefix}-{condition}",
                        options=options,
                        bank=memory,
                        learn=False,
                        extra_config={**tag, "phase": prefix, "condition": condition},
                        **common,
                    )
                    statuses[name].append(status)
    return statuses


# --------------------------------------------------------------------------- reading back


def run_dirs(out: str | Path) -> Iterator[Path]:
    for config in sorted(Path(out).glob("*/rep-*/*/config.json")):
        yield config.parent


def episodes(out: str | Path) -> Iterator[dict[str, Any]]:
    """Every episode of a protocol's runs, with where it belongs in the design."""
    from ..methods.stream import load_records
    from ..provenance import ProvenanceStore

    for run in run_dirs(out):
        config = json.loads((run / "config.json").read_text())
        records_path = run / "records.jsonl"
        if not records_path.exists():
            continue
        store = ProvenanceStore(run / "provenance.sqlite")
        try:
            for position, record in enumerate(load_records(records_path)):
                trajectory = store.load_trajectory(record.trajectory_ids[record.selected])
                yield {
                    "key": f"{config.get('arm')}/rep-{config.get('repeat')}/{run.name}/{position}",
                    "arm": config.get("arm"),
                    "method": config.get("method"),
                    "repeat": config.get("repeat"),
                    "phase": config.get("phase"),
                    "condition": config.get("condition"),
                    "position": position,
                    "world": world_of_record(record.task),
                    "record": record,
                    "trajectory": trajectory,
                    "stand_in": str(config.get("llm", "")).startswith("offline"),
                    "run": str(run),
                }
        finally:
            store.close()


def world_of_record(task: dict[str, Any]) -> dict[str, Any]:
    conditions = task.get("conditions") or {}
    return {
        "scenario": conditions.get("scenario"),
        "difficulty": conditions.get("difficulty"),
        "seed": int(task.get("seed", 0)),
    }


def knowledge_of(traj: Trajectory | None) -> str:
    """What the knowledge score grades: the Hypothesizer's knowledge store, as in the
    DiscoveryWorld paper; for other agents, their reasoning, as the paper did for ReAct."""
    if traj is None:
        return ""
    if traj.meta.get("knowledge_text"):
        return str(traj.meta["knowledge_text"])
    thoughts = [s.thought for s in traj.steps if s.thought]
    return "\n".join(f"Thought {i + 1}: {t}" for i, t in enumerate(thoughts))


def grade_protocol(
    out: str | Path,
    *,
    grader: str,
    grader_options: dict[str, Any] | None = None,
    code: bool = True,
    quiet: bool = False,
) -> Path:
    """Knowledge, stale knowledge and behaviour codes for every episode.

    Grades are appended to ``grades.jsonl``; episodes already graded by the same
    grader are skipped, so the command can be repeated after an interruption.
    """
    from ..llm import TrackedLLM, make_backend
    from .behaviours import BehaviourCoder
    from .knowledge import KnowledgeScorer

    out = Path(out)
    protocol = json.loads((out / "protocol.json").read_text())
    llm = TrackedLLM(make_backend(grader, **(grader_options or {})), cache_dir=out / "grader_cache")
    scorer = KnowledgeScorer(llm)
    coder = BehaviourCoder(llm)
    path = out / "grades.jsonl"
    done = set()
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                done.add((row["key"], row["grader"]))
    experience_worlds = [
        world_of_record(t.to_dict())
        for t in world_tasks(protocol["experience"]["worlds"], protocol.get("max_steps"))
    ]
    with path.open("a") as fh:
        for episode in episodes(out):
            if (episode["key"], llm.model) in done:
                continue
            traj = episode["trajectory"]
            knowledge = knowledge_of(traj)
            earlier = (
                experience_worlds[: episode["position"]]
                if episode["phase"] == "experience"
                else experience_worlds
            )
            graded = scorer.grade(episode["world"], knowledge)
            known = {q for w in earlier for q in _questions(w)}
            novel = [
                a["evaluation"] or 0 for a in graded["questions"] if a["question"] not in known
            ]
            row: dict[str, Any] = {
                "key": episode["key"],
                "grader": llm.model,
                "knowledge": graded,
                # The same grades, on the questions no earlier experience world has.
                "knowledge_novel": {
                    "score": sum(novel) / len(novel) if novel else None,
                    "questions": len(novel),
                },
                "stale": scorer.stale(episode["world"], knowledge, earlier),
            }
            if code and traj is not None:
                row["behaviour_codes"] = coder.code(traj)
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if not quiet:
                k = row["knowledge"]["score"]
                print(f"graded {episode['key']}: knowledge {k if k is None else round(k, 2)}")
    return path
