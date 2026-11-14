"""Run one stream method on a list of tasks into a run directory.

Used by ``sea run`` and by the comparison protocol, so that a method is run the same
way whether it is run alone or as one arm of a comparison.

A run directory holds ``config.json`` (everything needed to repeat the run),
``records.jsonl`` (one line per task), ``summary.json``, ``provenance.sqlite``, the
model-call cache ``llm_cache/`` and, for a learning memory, ``bank.jsonl``.
Re-running into the same directory replays cached model calls instead of paying for
them again.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..embeddings import make_embedder
from ..types import Task
from .registry import METHODS, build_stream


def run_method(
    method: str,
    tasks: Sequence[Task],
    out: str | Path,
    *,
    llm: str,
    options: dict[str, Any] | None = None,
    agent: str = "stepwise",
    agent_options: dict[str, Any] | None = None,
    embedder: str = "hashing",
    effort: str | None = None,
    llm_options: dict[str, Any] | None = None,
    embedder_options: dict[str, Any] | None = None,
    max_cost: float | None = None,
    max_calls: int | None = None,
    bank: str | Path | None = None,
    store_steps: bool = True,
    quiet: bool = False,
    extra_config: dict[str, Any] | None = None,
    learn: bool = True,
) -> tuple[int, dict[str, Any]]:
    """Run ``method`` over ``tasks`` in order and write the run to ``out``.

    ``llm`` and ``embedder`` are descriptions such as ``ollama:llama3.2:3b`` or
    ``hf:BAAI/bge-small-en-v1.5``; ``llm_options`` and ``embedder_options`` go to the
    backend's constructor (see :func:`..llm.make_backend` and :func:`..embeddings.make_embedder`).

    Returns ``(status, summary)``. Status 2 means the model budget ran out before the
    stream was finished; what was completed is still written.
    """
    from ..llm import Budget, BudgetExceeded, TrackedLLM, is_stand_in, make_backend, split_spec
    from ..provenance import ProvenanceStore

    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}; one of {sorted(METHODS)}")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    store = ProvenanceStore(out / "provenance.sqlite")
    stand_in = is_stand_in(llm)
    backend_options: dict[str, Any] = dict(llm_options or {})
    provider = split_spec(llm)[0]
    if effort and (provider == "anthropic" or provider.startswith("claude-")):
        # Effort is a Claude setting; other backends have their own (reasoning_effort, think).
        backend_options["effort"] = effort
    tracked = TrackedLLM(
        make_backend(llm, **backend_options),
        cache_dir=out / "llm_cache",
        budget=Budget(max_cost_usd=max_cost, max_calls=max_calls),
        store=store,
    )

    def progress(record: Any) -> None:
        task = record.task
        judged = (
            "not judged"
            if record.judged_success is None
            else f"judged {'success' if record.judged_success else 'failure'}"
        )
        print(
            f"[{len(built.loop.records):3d}/{len(tasks)}] {task['name']} seed={task['seed']}: "
            f"score {record.score:+.3f} {'ok ' if record.success else 'FAIL'} "
            f"({record.failure or 'no failure'}), {record.steps} steps, {judged}, "
            f"used {len(record.retrieved_item_ids)} items, learned {len(record.new_item_ids)}",
            flush=True,
        )

    built = build_stream(
        method,
        options,
        llm=tracked,
        agent=agent,
        agent_options=agent_options,
        bank_path=bank or out / "bank.jsonl",
        embedder=make_embedder(embedder, cache_dir=out, **(embedder_options or {})),
        store=store,
        on_record=None if quiet else progress,
        store_steps=store_steps,
        learn=learn,
    )
    config = {
        **built.describe,
        "llm": llm,
        "llm_options": llm_options or {},
        "effort": effort,
        "embedder_spec": embedder,
        "embedder_options": embedder_options or {},
        "budget": {"max_cost_usd": max_cost, "max_calls": max_calls},
        "tasks": [task.to_dict() for task in tasks],
        **(extra_config or {}),
    }
    (out / "config.json").write_text(json.dumps(config, indent=2, default=str))
    store.start_run(method, out.name, config)
    if stand_in and not quiet:
        print(
            "NOTE: offline-demo is a rule-based stand-in, not a language model. "
            "This run exercises the method's plumbing; its numbers are not results."
        )
    status = 0
    try:
        built.loop.run_stream(tasks)
    except BudgetExceeded as exc:
        if not quiet:
            print(
                f"Stopped: {exc}. Completed {len(built.loop.records)} of {len(tasks)} tasks; "
                "rerun the same command to continue from the cache with a larger budget."
            )
        status = 2
    finally:
        built.loop.save_records(out / "records.jsonl")
        summary = {
            "method": method,
            "completed": len(built.loop.records),
            "planned": len(tasks),
            "stand_in_model": stand_in,
            "metrics": built.loop.summary(),
            "memory": built.memory.stats(),
            "llm": tracked.summary(),
        }
        (out / "summary.json").write_text(json.dumps(summary, indent=2))
        store.close()
    return status, summary
