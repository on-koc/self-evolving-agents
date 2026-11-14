"""SQLite provenance store.

The store is a small property graph plus two bulk tables:

* ``nodes``  – every trajectory, memory item, experience, claim, experiment, LLM call ...
* ``edges``  – typed links between nodes. Edges point from the *later* thing to the
  thing it depends on, following W3C PROV (``wasDerivedFrom``, ``used``,
  ``wasGeneratedBy`` ...), so "where did this come from?" is a walk along edges and
  "what did this influence?" is a walk against them.
* ``steps`` and ``llm_calls`` – the bulky payloads, kept out of the graph tables.

One process writes; experiment workers hand their results back to the parent.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ..types import Trajectory, jsonable, new_id

# Relations borrowed from W3C PROV-O.
USED = "used"
WAS_GENERATED_BY = "wasGeneratedBy"
WAS_DERIVED_FROM = "wasDerivedFrom"
WAS_ASSOCIATED_WITH = "wasAssociatedWith"
WAS_INFORMED_BY = "wasInformedBy"
# Domain relations between claims and their evidence.
SUPPORTS = "supports"
CONTRADICTS = "contradicts"
SPECIALIZES = "specializes"
SUPERSEDES = "supersedes"
REQUIRES = "requires"
TESTS = "tests"

PROV_RELATIONS = {USED, WAS_GENERATED_BY, WAS_DERIVED_FROM, WAS_ASSOCIATED_WITH, WAS_INFORMED_BY}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id         TEXT PRIMARY KEY,
    kind       TEXT NOT NULL,
    prov_type  TEXT NOT NULL DEFAULT 'entity',
    run_id     TEXT,
    label      TEXT,
    created_at REAL NOT NULL,
    data       TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS nodes_kind ON nodes(kind);
CREATE INDEX IF NOT EXISTS nodes_run ON nodes(run_id);

CREATE TABLE IF NOT EXISTS edges (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    src        TEXT NOT NULL,
    relation   TEXT NOT NULL,
    dst        TEXT NOT NULL,
    created_at REAL NOT NULL,
    data       TEXT NOT NULL DEFAULT '{}',
    UNIQUE (src, relation, dst)
);
CREATE INDEX IF NOT EXISTS edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS edges_dst ON edges(dst);

CREATE TABLE IF NOT EXISTS steps (
    trajectory_id TEXT NOT NULL,
    idx           INTEGER NOT NULL,
    data          TEXT NOT NULL,
    PRIMARY KEY (trajectory_id, idx)
);

CREATE TABLE IF NOT EXISTS llm_calls (
    id         TEXT PRIMARY KEY,
    run_id     TEXT,
    purpose    TEXT,
    model      TEXT,
    cached     INTEGER NOT NULL DEFAULT 0,
    latency_s  REAL,
    created_at REAL NOT NULL,
    usage      TEXT NOT NULL DEFAULT '{}',
    request    TEXT NOT NULL,
    response   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS llm_calls_run ON llm_calls(run_id);
"""


class ProvenanceStore:
    """Append-mostly record of what was run, what it produced and what depended on what."""

    def __init__(self, path: str | Path | None = None, run_id: str | None = None):
        self.path = str(path) if path is not None else ":memory:"
        if path is not None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        if self.path != ":memory:":
            self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.executescript(_SCHEMA)
        self._db.commit()
        self.run_id = run_id
        self._depth = 0

    # ------------------------------------------------------------------ plumbing

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Group writes; nested use is fine and commits once at the outermost exit."""
        with self._lock:
            self._depth += 1
            try:
                yield
            except BaseException:
                if self._depth == 1:
                    self._db.rollback()
                raise
            else:
                if self._depth == 1:
                    self._db.commit()
            finally:
                self._depth -= 1

    def close(self) -> None:
        with self._lock:
            self._db.commit()
            self._db.close()

    def __enter__(self) -> ProvenanceStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ generic graph

    def start_run(self, kind: str, name: str, config: dict[str, Any] | None = None) -> str:
        """Open a run (one invocation of an experiment or pipeline) and make it current."""
        run_id = new_id("run")
        self.run_id = run_id
        self.add_node(
            run_id,
            "run",
            prov_type="activity",
            label=name,
            data={"kind": kind, "name": name, "config": config or {}},
            run_id=run_id,
        )
        return run_id

    def add_node(
        self,
        node_id: str,
        kind: str,
        *,
        prov_type: str = "entity",
        label: str | None = None,
        data: dict[str, Any] | None = None,
        run_id: str | None = None,
        created_at: float | None = None,
    ) -> str:
        """Insert a node, or replace its label/data if the id already exists."""
        with self.transaction():
            self._db.execute(
                "INSERT INTO nodes (id, kind, prov_type, run_id, label, created_at, data) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET label=excluded.label, data=excluded.data",
                (
                    node_id,
                    kind,
                    prov_type,
                    run_id if run_id is not None else self.run_id,
                    label,
                    created_at if created_at is not None else time.time(),
                    json.dumps(jsonable(data or {}), sort_keys=True),
                ),
            )
        return node_id

    def link(self, src: str, relation: str, dst: str, data: dict[str, Any] | None = None) -> None:
        """Record ``src --relation--> dst``. Repeating the same link is a no-op."""
        with self.transaction():
            self._db.execute(
                "INSERT OR IGNORE INTO edges (src, relation, dst, created_at, data) "
                "VALUES (?, ?, ?, ?, ?)",
                (src, relation, dst, time.time(), json.dumps(jsonable(data or {}), sort_keys=True)),
            )

    def link_many(self, src: str, relation: str, dsts: Iterable[str]) -> None:
        with self.transaction():
            for dst in dsts:
                self.link(src, relation, dst)

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        row = self._db.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        return _node(row) if row else None

    def nodes(self, kind: str | None = None, run_id: str | None = None) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM nodes", []
        clauses = []
        if kind is not None:
            clauses.append("kind = ?")
            args.append(kind)
        if run_id is not None:
            clauses.append("run_id = ?")
            args.append(run_id)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at, id"
        return [_node(r) for r in self._db.execute(sql, args)]

    def edges(
        self, src: str | None = None, dst: str | None = None, relation: str | None = None
    ) -> list[dict[str, Any]]:
        sql, args, clauses = "SELECT * FROM edges", [], []
        for column, value in (("src", src), ("dst", dst), ("relation", relation)):
            if value is not None:
                clauses.append(f"{column} = ?")
                args.append(value)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id"
        return [
            {
                "src": r["src"],
                "relation": r["relation"],
                "dst": r["dst"],
                "created_at": r["created_at"],
                "data": json.loads(r["data"]),
            }
            for r in self._db.execute(sql, args)
        ]

    def lineage(
        self, node_id: str, direction: str = "upstream", max_depth: int = 8
    ) -> list[dict[str, Any]]:
        """Everything a node depends on (``upstream``) or that depends on it (``downstream``).

        Returns ``{"id", "kind", "label", "depth", "via"}`` rows ordered by depth, where
        ``via`` is the relation of the edge that first reached the node.
        """
        if direction not in ("upstream", "downstream"):
            raise ValueError("direction must be 'upstream' or 'downstream'")
        here, there = ("src", "dst") if direction == "upstream" else ("dst", "src")
        rows = self._db.execute(
            f"""
            WITH RECURSIVE walk(id, depth, via) AS (
                SELECT ?, 0, ''
                UNION
                SELECT e.{there}, w.depth + 1, e.relation
                FROM edges e JOIN walk w ON e.{here} = w.id
                WHERE w.depth < ?
            )
            SELECT w.id AS id, MIN(w.depth) AS depth, w.via AS via, n.kind AS kind, n.label AS label
            FROM walk w LEFT JOIN nodes n ON n.id = w.id
            WHERE w.depth > 0
            GROUP BY w.id
            ORDER BY depth, w.id
            """,
            (node_id, max_depth),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ typed helpers

    def record_trajectory(self, traj: Trajectory, store_steps: bool = True) -> str:
        """Persist an episode. ``store_steps=False`` keeps only the header and outcome."""
        header = traj.to_dict()
        header.pop("steps")
        header["n_steps"] = len(traj.steps)
        header["total_reward"] = traj.total_reward
        with self.transaction():
            self.add_node(
                traj.id,
                "trajectory",
                label=traj.task.key,
                data=header,
                created_at=traj.started_at,
            )
            if store_steps:
                self._db.executemany(
                    "INSERT OR REPLACE INTO steps (trajectory_id, idx, data) VALUES (?, ?, ?)",
                    [(traj.id, s.index, json.dumps(s.to_dict())) for s in traj.steps],
                )
            for item_id in traj.memory_item_ids:
                self.link(traj.id, USED, item_id)
            agent_id = traj.agent.get("id")
            if agent_id:
                self.add_node(agent_id, "agent", prov_type="agent", label=agent_id, data=traj.agent)
                self.link(traj.id, WAS_ASSOCIATED_WITH, agent_id)
            if self.run_id:
                self.link(traj.id, WAS_GENERATED_BY, self.run_id)
        return traj.id

    def load_trajectory(self, trajectory_id: str) -> Trajectory | None:
        node = self.get_node(trajectory_id)
        if node is None or node["kind"] != "trajectory":
            return None
        data = dict(node["data"])
        data["steps"] = [
            json.loads(r["data"])
            for r in self._db.execute(
                "SELECT data FROM steps WHERE trajectory_id = ? ORDER BY idx", (trajectory_id,)
            )
        ]
        return Trajectory.from_dict(data)

    def record_llm_call(
        self,
        call_id: str,
        *,
        purpose: str,
        model: str,
        request: dict[str, Any],
        response: str,
        usage: dict[str, Any],
        latency_s: float,
        cached: bool,
    ) -> str:
        with self.transaction():
            self._db.execute(
                "INSERT OR REPLACE INTO llm_calls "
                "(id, run_id, purpose, model, cached, latency_s, created_at, usage, request, response) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    call_id,
                    self.run_id,
                    purpose,
                    model,
                    int(cached),
                    latency_s,
                    time.time(),
                    json.dumps(jsonable(usage)),
                    json.dumps(jsonable(request)),
                    response,
                ),
            )
            self.add_node(
                call_id,
                "llm_call",
                prov_type="activity",
                label=f"{purpose}:{model}",
                data={"purpose": purpose, "model": model, "cached": cached, "usage": usage},
            )
        return call_id

    def get_llm_call(self, call_id: str) -> dict[str, Any] | None:
        row = self._db.execute("SELECT * FROM llm_calls WHERE id = ?", (call_id,)).fetchone()
        if row is None:
            return None
        out = dict(row)
        out["usage"] = json.loads(out["usage"])
        out["request"] = json.loads(out["request"])
        out["cached"] = bool(out["cached"])
        return out

    def llm_usage(self, run_id: str | None = None) -> dict[str, Any]:
        """Token totals per purpose, for cost accounting."""
        sql, args = "SELECT purpose, cached, usage FROM llm_calls", []
        if run_id is not None:
            sql += " WHERE run_id = ?"
            args.append(run_id)
        totals: dict[str, dict[str, float]] = {}
        for row in self._db.execute(sql, args):
            bucket = totals.setdefault(row["purpose"] or "unknown", {"calls": 0, "cached_calls": 0})
            bucket["calls"] += 1
            bucket["cached_calls"] += int(row["cached"])
            for key, value in json.loads(row["usage"]).items():
                if isinstance(value, (int, float)):
                    bucket[key] = bucket.get(key, 0) + value
        return totals

    def counts(self) -> dict[str, int]:
        out = {
            r["kind"]: r["n"]
            for r in self._db.execute("SELECT kind, COUNT(*) AS n FROM nodes GROUP BY kind")
        }
        out["edges"] = self._db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        out["steps"] = self._db.execute("SELECT COUNT(*) FROM steps").fetchone()[0]
        return out

    # ------------------------------------------------------------------ export

    def export_prov_json(self, run_id: str | None = None) -> dict[str, Any]:
        """Serialise the graph as W3C PROV-JSON (https://www.w3.org/submissions/prov-json/).

        Trajectories are entities; the episode that produced each one is synthesised as
        an activity so that ``used`` has an activity on its left-hand side, as PROV asks.
        Domain relations (supports, contradicts, ...) are exported as qualified
        ``wasInfluencedBy`` statements carrying the relation name.
        """
        doc: dict[str, Any] = {
            "prefix": {"sea": "https://github.com/on-koc/self-evolving-agents#"},
            "entity": {},
            "activity": {},
            "agent": {},
        }
        nodes = self.nodes(run_id=run_id)
        ids = {n["id"] for n in nodes}
        for n in nodes:
            attrs = {"prov:type": f"sea:{n['kind']}", "prov:label": n["label"] or n["id"]}
            doc[n["prov_type"]][f"sea:{n['id']}"] = attrs
            if n["kind"] == "trajectory":
                doc["activity"][f"sea:episode-{n['id']}"] = {
                    "prov:type": "sea:episode",
                    "prov:startTime": _iso(n["data"].get("started_at")),
                    "prov:endTime": _iso(n["data"].get("finished_at")),
                }
                doc.setdefault("wasGeneratedBy", {})[f"_:gen-{n['id']}"] = {
                    "prov:entity": f"sea:{n['id']}",
                    "prov:activity": f"sea:episode-{n['id']}",
                }
        kinds = {n["id"]: n["kind"] for n in nodes}
        for i, e in enumerate(self.edges()):
            if e["src"] not in ids or e["dst"] not in ids:
                continue
            src, dst, rel = f"sea:{e['src']}", f"sea:{e['dst']}", e["relation"]
            key = f"_:e{i}"
            if kinds[e["src"]] == "trajectory" and rel in (USED, WAS_ASSOCIATED_WITH):
                src = f"sea:episode-{e['src']}"
            if rel == USED:
                doc.setdefault("used", {})[key] = {"prov:activity": src, "prov:entity": dst}
            elif rel == WAS_GENERATED_BY:
                doc.setdefault("wasGeneratedBy", {})[key] = {
                    "prov:entity": src,
                    "prov:activity": dst,
                }
            elif rel == WAS_DERIVED_FROM:
                doc.setdefault("wasDerivedFrom", {})[key] = {
                    "prov:generatedEntity": src,
                    "prov:usedEntity": dst,
                }
            elif rel == WAS_ASSOCIATED_WITH:
                doc.setdefault("wasAssociatedWith", {})[key] = {
                    "prov:activity": src,
                    "prov:agent": dst,
                }
            elif rel == WAS_INFORMED_BY:
                doc.setdefault("wasInformedBy", {})[key] = {
                    "prov:informed": src,
                    "prov:informant": dst,
                }
            else:
                doc.setdefault("wasInfluencedBy", {})[key] = {
                    "prov:influencee": src,
                    "prov:influencer": dst,
                    "sea:relation": rel,
                }
        return doc


def _node(row: sqlite3.Row) -> dict[str, Any]:
    out = dict(row)
    out["data"] = json.loads(out["data"])
    return out


def _iso(ts: float | None) -> str | None:
    if not ts:
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
