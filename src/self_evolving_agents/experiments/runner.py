"""Run many (task, policy) episodes: in parallel, reproducibly, and without repeating work.

An episode is fully determined by its task (environment, conditions, parameters,
seed) and the rule policy executed in it, so its outcome can be cached under a hash
of those two things. Experiments that share an arm or a set of seeds then cost
nothing the second time, and an interrupted study resumes where it stopped.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import sqlite3
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..agents.rule import PolicyAgent
from ..envs.base import TextEnv, make_env
from ..policies import RulePolicy
from ..types import Outcome, Task, stable_hash


@dataclass(frozen=True)
class EpisodeSpec:
    """One episode to run: a task and the rule policy to execute in it."""

    task: Task
    policy: RulePolicy

    @property
    def key(self) -> str:
        return stable_hash({"task": self.task.to_dict(), "policy": self.policy.fingerprint}, 24)

    @property
    def config_key(self) -> str:
        """Identifies the simulator configuration (everything but the seed and the policy)."""
        return stable_hash(
            {
                "env": self.task.env_id,
                "conditions": self.task.conditions,
                "params": self.task.params,
            },
            16,
        )


class EpisodeCache:
    """Outcomes of finished episodes, keyed by :attr:`EpisodeSpec.key`."""

    def __init__(self, path: str | Path | None = None):
        self.path = str(path) if path else ":memory:"
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS episodes ("
            "key TEXT PRIMARY KEY, task TEXT NOT NULL, policy TEXT NOT NULL, "
            "outcome TEXT NOT NULL, wall_s REAL, created_at REAL)"
        )
        self._db.commit()

    def get(self, key: str) -> Outcome | None:
        row = self._db.execute("SELECT outcome FROM episodes WHERE key = ?", (key,)).fetchone()
        return Outcome.from_dict(json.loads(row[0])) if row else None

    def put(self, spec: EpisodeSpec, outcome: Outcome, wall_s: float) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO episodes VALUES (?, ?, ?, ?, ?, ?)",
            (
                spec.key,
                json.dumps(spec.task.to_dict(), sort_keys=True),
                spec.policy.fingerprint,
                json.dumps(outcome.to_dict()),
                wall_s,
                time.time(),
            ),
        )

    def commit(self) -> None:
        self._db.commit()

    def wall_seconds(self, keys: Iterable[str]) -> float:
        """Time the given episodes took to simulate, summed (whenever they were run)."""
        wanted = list(keys)
        total = 0.0
        for start in range(0, len(wanted), 500):
            chunk = wanted[start : start + 500]
            marks = ",".join("?" * len(chunk))
            row = self._db.execute(
                f"SELECT COALESCE(SUM(wall_s), 0) FROM episodes WHERE key IN ({marks})", chunk
            ).fetchone()
            total += float(row[0])
        return total

    def __len__(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]

    def close(self) -> None:
        self._db.commit()
        self._db.close()


# Worker-side state: one environment per simulator configuration, reused across seeds.
_ENVS: dict[str, TextEnv] = {}
_MAX_ENVS = 4


def _run_one(payload: tuple[dict[str, Any], dict[str, Any], str]) -> tuple[dict[str, Any], float]:
    task_dict, policy_dict, config_key = payload
    task = Task.from_dict(task_dict)
    policy = RulePolicy.from_dict(policy_dict)
    started = time.time()
    env = _ENVS.get(config_key)
    if env is None or not env.retask(task):
        if len(_ENVS) >= _MAX_ENVS:
            _, stale = _ENVS.popitem()
            stale.close()
        env = make_env(task)
        _ENVS[config_key] = env
    outcome = PolicyAgent(policy).run(env).outcome
    assert outcome is not None
    return outcome.to_dict(), time.time() - started


def _close_worker_envs() -> None:
    while _ENVS:
        _, env = _ENVS.popitem()
        env.close()


def default_workers() -> int:
    return max(1, min(8, (os.cpu_count() or 2)))


class EpisodeRunner:
    """Executes episode specs, consulting and filling the cache.

    Args:
        cache: where finished episodes are remembered. ``None`` keeps them in memory
            for the lifetime of the runner only.
        workers: number of worker processes. ``0`` runs in this process, which is
            what the tests and the toy environment want. Worker processes are
            started with ``spawn`` because Basilisk does not survive ``fork``.
        on_progress: called as ``on_progress(done, total)`` while a batch runs.
    """

    def __init__(
        self,
        cache: EpisodeCache | None = None,
        *,
        workers: int = 0,
        on_progress: Callable[[int, int], None] | None = None,
    ):
        # Not `cache or ...`: an empty cache is falsy, and would be silently replaced.
        self.cache = cache if cache is not None else EpisodeCache()
        self.workers = workers
        self.on_progress = on_progress
        self.episodes_run = 0
        self.episodes_cached = 0
        self._seen: set[str] = set()
        self._pool: Any = None

    @property
    def episodes_distinct(self) -> int:
        """Different episodes asked for so far, whether simulated now or found in the cache.

        Unlike ``episodes_run`` this does not depend on what the cache already held,
        so it is the number to budget with.
        """
        return len(self._seen)

    def simulation_seconds(self) -> float:
        """Single-core simulation time of every episode asked for so far.

        Read from the cache, so it is the same whether the episodes were simulated in
        this process or reused.
        """
        return self.cache.wall_seconds(self._seen)

    def _ensure_pool(self) -> Any:
        if self._pool is None:
            self._pool = mp.get_context("spawn").Pool(self.workers)
        return self._pool

    def run(self, specs: Sequence[EpisodeSpec]) -> list[Outcome]:
        """Return one outcome per spec, in order."""
        results: dict[str, Outcome] = {}
        missing: dict[str, EpisodeSpec] = {}
        for spec in specs:
            key = spec.key
            self._seen.add(key)
            if key in results or key in missing:
                continue
            cached = self.cache.get(key)
            if cached is not None:
                results[key] = cached
            else:
                missing[key] = spec
        self.episodes_cached += len(results)

        if missing:
            # Group by simulator configuration so workers can reuse their environment.
            ordered = sorted(missing.values(), key=lambda s: (s.config_key, s.task.seed))
            payloads = [(s.task.to_dict(), s.policy.to_dict(), s.config_key) for s in ordered]
            total = len(ordered)
            if self.workers and len(ordered) > 1:
                chunk = max(1, min(8, len(ordered) // (self.workers * 4) or 1))
                iterator = self._ensure_pool().imap(_run_one, payloads, chunksize=chunk)
            else:
                iterator = map(_run_one, payloads)
            pairs = zip(ordered, iterator, strict=True)
            for done, (spec, (outcome_dict, wall_s)) in enumerate(pairs, start=1):
                outcome = Outcome.from_dict(outcome_dict)
                results[spec.key] = outcome
                self.cache.put(spec, outcome, wall_s)
                if done % 32 == 0:
                    self.cache.commit()
                if self.on_progress is not None:
                    self.on_progress(done, total)
            self.cache.commit()
            self.episodes_run += total
        return [results[spec.key] for spec in specs]

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool.join()
            self._pool = None
        _close_worker_envs()
        self.cache.commit()

    def __enter__(self) -> EpisodeRunner:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
