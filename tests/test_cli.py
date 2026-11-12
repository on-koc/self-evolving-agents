"""The command line, end to end on the toy environment.

These are smoke tests: every command runs, writes what it says it writes, and its
output is consistent with what the previous command produced. Nothing here says
anything about a real simulator or a real language model; the model is the rule-based
stand-in.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from self_evolving_agents.cli import main

STUDIES = Path(__file__).resolve().parent.parent / "studies"
WH = "battery_capacity_wh"


def sea(capsys, *argv) -> tuple[int, str]:
    code = main([str(a) for a in argv])
    return code, capsys.readouterr().out


# --------------------------------------------------------------------------- basics


def test_envs_lists_environments_and_regimes(capsys):
    code, out = sea(capsys, "envs")
    assert code == 0
    assert "toy-scan" in out and "bsk-scan" in out and "small_battery" in out


def test_policy_run_reports_every_episode(capsys):
    code, out = sea(
        capsys,
        *("policy", "run", "--env", "toy-scan", "--regime", "small_battery"),
        *("--seeds", "0:3", "--set", "charge_below=0.4"),
    )
    assert code == 0
    assert len(re.findall(r"seed=\d+: score", out)) == 3
    assert "charge_below" in out and "mean score" in out and "over 3 episodes" in out


def test_policy_run_refuses_an_environment_without_features():
    with pytest.raises(SystemExit, match="named features"):
        main(["policy", "run", "--env", "discoveryworld"])


# --------------------------------------------------------------------------- ReasoningBank


@pytest.fixture(scope="module")
def rb_run(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("rb") / "dry"
    code = main(
        [
            *("rb", "run", "--env", "toy-scan", "--regime", "small_battery", "--seeds", "0:4"),
            *("--llm", "offline-demo", "--retrieval", "item", "--out", str(out)),
        ]
    )
    assert code == 0
    return out


def test_rb_run_writes_a_complete_run_directory(rb_run):
    for name in ("config.json", "provenance.sqlite", "bank.jsonl", "records.jsonl", "summary.json"):
        assert (rb_run / name).exists(), name
    summary = json.loads((rb_run / "summary.json").read_text())
    assert summary["pipeline"]["tasks"] == 4
    assert summary["bank"]["items"] >= 1 and summary["bank"]["items_used"] >= 1
    assert summary["llm"]["model"] == "offline-demo" and summary["llm"]["calls"] > 4
    records = [json.loads(line) for line in (rb_run / "records.jsonl").read_text().splitlines()]
    assert len(records) == 4
    assert json.loads((rb_run / "config.json").read_text())["env"] == "toy-scan"


def test_rb_run_with_the_policy_writing_agent(tmp_path, capsys):
    code, out = sea(
        capsys,
        *("rb", "run", "--env", "toy-scan", "--regime", "nominal,small_battery"),
        *("--order", "interleaved", "--seeds", "0:2", "--agent", "policy"),
        *("--llm", "offline-demo", "--out", tmp_path / "run"),
    )
    assert code == 0
    summary = json.loads((tmp_path / "run" / "summary.json").read_text())
    assert summary["pipeline"]["tasks"] == 4
    assert summary["llm"]["calls"] < 40, "one call per episode plus judging and extraction"


def test_rb_show_then_lineage_in_both_directions(rb_run, capsys):
    code, out = sea(capsys, "rb", "show", rb_run)
    assert code == 0 and "memory items in" in out
    used = re.search(r"\[(mem_[0-9a-f]+)\] \([^)]*used \d+x", out)
    assert used, "the dry run reuses at least one item"
    item = used.group(1)

    code, out = sea(capsys, "prov", "lineage", rb_run, item)
    assert code == 0 and "derived from:" in out
    assert "trajectory" in out, "an item traces back to the episode it was distilled from"

    code, out = sea(capsys, "prov", "lineage", rb_run, item, "--down")
    assert code == 0 and "influenced:" in out
    assert "trajectory" in out, "and forward to the episodes that were given it"

    code, out = sea(capsys, "prov", "lineage", rb_run, "no-such-id")
    assert code == 1 and "no record" in out


def test_prov_export_writes_prov_json(rb_run, tmp_path, capsys):
    target = tmp_path / "prov.json"
    code, out = sea(capsys, "prov", "export", rb_run, target)
    doc = json.loads(target.read_text())
    assert code == 0 and str(target) in out
    assert doc["entity"] and doc["activity"] and doc["wasDerivedFrom"]


# --------------------------------------------------------------------------- claims


@pytest.fixture(scope="module")
def study(tmp_path_factory) -> Path:
    """A small study on the toy environment, run through the command line."""
    root = tmp_path_factory.mktemp("claims")
    config = json.loads((STUDIES / "toy_battery.json").read_text())
    config["graph"] = {"max_depth": 5}
    config["evaluation"].update(
        test_points={"held out": [{WH: 35}, {WH: 280}]},
        seeds=[5000, 5008],
        oracle_grid={"charge_below": [0.1, 0.25, 0.4]},
        tuning_seeds=[6000, 6004],
    )
    (root / "config.json").write_text(json.dumps(config))
    out = root / "toy"
    code = main(
        ["claims", "study", "--config", str(root / "config.json"), "--out", str(out)]
        + ["--budget", "600"]
    )
    assert code == 0
    return out


def test_claims_study_writes_a_complete_run_directory(study):
    for name in (
        *("config.json", "graph.json", "study.json", "experiments.jsonl", "transfer.json"),
        *("composition.json", "report.md", "episodes.sqlite", "provenance.sqlite"),
    ):
        assert (study / name).exists(), name
    summary = json.loads((study / "study.json").read_text())
    assert summary["budget"] == 600 <= summary["episodes_used"]
    assert summary["episodes_simulated"] == summary["episodes_used"], "nothing was cached"
    assert summary["evaluation_episodes"] > 0 and summary["simulation_core_s"] > 0
    assert summary["graph"]["claims"] >= summary["graph"]["families"] >= 2
    experiments = (study / "experiments.jsonl").read_text().splitlines()
    assert len(experiments) == summary["experiments"]
    assert sum(json.loads(x)["episodes"] for x in experiments) == summary["episodes_used"]
    transfer = json.loads((study / "transfer.json").read_text())
    assert set(transfer) == {"held out"}
    assert set(transfer["held out"]["overall"]) == {
        *("reference", "flat", "pooled", "conditional", "oracle")
    }
    report = (study / "report.md").read_text()
    assert "## Transfer: held out" in report and "work together?" in report


def test_claims_study_honours_the_graph_section_of_the_config(study, monkeypatch):
    from self_evolving_agents.claims import cli as claims_cli
    from self_evolving_agents.claims.graph import ClaimGraph

    seen = {}
    original = ClaimGraph.__init__

    def spy(self, *args, **kwargs):
        seen.update(kwargs)
        original(self, *args, **kwargs)

    monkeypatch.setattr(ClaimGraph, "__init__", spy)
    config = json.loads((study / "config.json").read_text())
    claims_cli.run_study(config, study.parent / "again", budget=100, evaluate=False, quiet=True)
    assert seen["max_depth"] == 5


def test_claims_show_and_recommend(study, capsys):
    code, out = sea(capsys, "claims", "show", study)
    assert code == 0 and '"families"' in out and "explanation [" in out

    code, out = sea(capsys, "claims", "recommend", study, "--condition", f"{WH}=70")
    assert code == 0
    for mode in ("reference:", "flat:", "pooled:", "conditional:"):
        assert f"\n{mode}" in out
    assert "reference: reference settings" in out


def test_claims_report_and_plot(study, tmp_path, capsys):
    code, out = sea(capsys, "claims", "report", study, "--out", tmp_path / "again.md")
    assert code == 0
    assert (tmp_path / "again.md").read_text() == (study / "report.md").read_text()

    pytest.importorskip("matplotlib")
    code, out = sea(capsys, "claims", "plot", study, "--out", tmp_path, "--x-label", "battery (Wh)")
    assert code == 0
    for name in ("claims.png", "transfer.png"):
        assert (tmp_path / name).stat().st_size > 10_000, name


def test_claims_evaluate_reuses_the_cache_and_reproduces_the_numbers(study, capsys):
    before = json.loads((study / "transfer.json").read_text())
    code, out = sea(capsys, "claims", "evaluate", study)
    assert code == 0 and "\n0 episodes run, " in out and "reused from the cache" in out
    assert json.loads((study / "transfer.json").read_text()) == before


def test_rerunning_a_study_simulates_nothing_and_finds_the_same_claims(study, capsys):
    def claims() -> list[tuple]:
        graph = json.loads((study / "graph.json").read_text())
        return sorted(
            (c["statement"], json.dumps(c["scope"], sort_keys=True), c["status"])
            for c in graph["claims"]
        )

    before = claims()
    summary_before = json.loads((study / "study.json").read_text())
    code, _ = sea(
        capsys,
        *("claims", "study", "--config", study / "config.json", "--out", study),
        *("--budget", "600"),
    )
    assert code == 0
    summary = json.loads((study / "study.json").read_text())
    assert summary["episodes_simulated"] == 0
    assert summary["episodes_used"] == summary_before["episodes_used"]
    assert claims() == before
