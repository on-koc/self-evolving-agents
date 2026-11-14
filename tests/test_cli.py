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


# --------------------------------------------------------------------------- stream methods


def test_methods_lists_every_method_with_its_origin_and_evidence(capsys):
    code, out = sea(capsys, "methods")
    assert code == 0
    for line in (
        "reasoningbank  (paper)  ReasoningBank",
        "no_memory  (reference point)",
        "matts  (paper)",
        "conditioned_retrieval  (adaptation)",
        "policy_program  (adaptation)",
        "claim_memory  (extension)",
        "claim_graph  (extension)",
        "never run with a language model",
        "run with: sea claims study",
        "documentation: docs/methods/reasoningbank.md",
    ):
        assert line in out, line
    code, out = sea(capsys, "methods", "--options")
    assert "retrieve_k = 1" in out and "scaling_k = 5" in out and "condition_weight = 0.5" in out


@pytest.fixture(scope="module")
def rb_run(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("rb") / "dry"
    code = main(
        [
            *("run", "--method", "reasoningbank", "--set", "tie_break=newest"),
            *("--env", "toy-scan", "--regime", "small_battery", "--seeds", "0:4"),
            *("--llm", "offline-demo", "--out", str(out)),
        ]
    )
    assert code == 0
    return out


def test_run_with_an_openai_compatible_server_applies_the_published_temperatures(
    fake_openai, tmp_path, capsys
):
    out = tmp_path / "rb-openai"
    code, _ = sea(
        capsys,
        *("run", "--method", "reasoningbank", "--env", "toy-scan", "--regime", "small_battery"),
        *("--seeds", "0:2", "--llm", f"openai:local-model@{fake_openai.base_url}"),
        *("--llm-option", "seed=5", "--llm-option", "price_in=0", "--llm-option", "price_out=0"),
        *("--embedder", f"openai:embed-model@{fake_openai.base_url}", "--out", out),
    )
    assert code == 0
    config = json.loads((out / "config.json").read_text())
    assert config["llm"] == f"openai:local-model@{fake_openai.base_url}"
    assert config["llm_options"] == {"seed": 5, "price_in": 0, "price_out": 0}
    summary = json.loads((out / "summary.json").read_text())
    assert summary["stand_in_model"] is False and summary["completed"] == 2
    assert summary["llm"]["estimated_cost_usd"] == 0.0
    assert summary["memory"]["embedder"] == "openai-embed-model"
    chats = [r["body"] for r in fake_openai.requests if r["path"].endswith("/chat/completions")]
    by_kind = {}
    for body in chats:
        system = body["messages"][0]["content"]
        kind = (
            "judge"
            if '"success" or "failure"' in system
            else "extract"
            if "# Memory Item i\n" in system
            else "act"
        )
        by_kind.setdefault(kind, set()).add(body.get("temperature"))
    # ReasoningBank's decoding temperatures (Appendix A.2), applied because this backend can.
    assert by_kind == {"act": {0.7}, "judge": {0.0}, "extract": {1.0}}
    assert any(r["path"].endswith("/embeddings") for r in fake_openai.requests)


def test_run_with_ollama_passes_backend_options(fake_ollama, tmp_path, capsys):
    out = tmp_path / "none-ollama"
    code, _ = sea(
        capsys,
        *("run", "--method", "no_memory", "--env", "toy-scan", "--seeds", "0:1"),
        *("--llm", f"ollama:llama3.2:3b@{fake_ollama.base_url}"),
        *("--llm-option", "num_ctx=16384", "--llm-option", "think=false", "--out", out),
    )
    assert code == 0
    bodies = [r["body"] for r in fake_ollama.requests if r["path"] == "/api/chat"]
    assert bodies and all(b["options"]["num_ctx"] == 16384 and b["think"] is False for b in bodies)
    assert json.loads((out / "summary.json").read_text())["llm"]["estimated_cost_usd"] == 0.0


def test_compare_can_swap_the_model_backend(fake_openai, tmp_path, capsys):
    protocol = dict(
        PROTOCOL,
        arms={"no_memory": {"method": "no_memory"}, "reasoningbank": {"method": "reasoningbank"}},
        repeats=1,
    )
    (tmp_path / "protocol.json").write_text(json.dumps(protocol))
    out = tmp_path / "comparison"
    code, text = sea(
        capsys,
        *("compare", "run", "--protocol", tmp_path / "protocol.json", "--out", out),
        *("--llm", f"openai:local-model@{fake_openai.base_url}", "--llm-option", "seed=1"),
    )
    assert code == 0
    resolved = json.loads((out / "protocol.json").read_text())
    assert resolved["model"]["llm_options"] == {"seed": 1}
    assert "These numbers are not results" not in text
    assert 'with `{"seed": 1}`' in (out / "comparison.md").read_text()
    config = json.loads((out / "reasoningbank" / "rep-0" / "config.json").read_text())
    assert config["llm_options"] == {"seed": 1}


def test_run_writes_a_complete_run_directory(rb_run):
    for name in ("config.json", "provenance.sqlite", "bank.jsonl", "records.jsonl", "summary.json"):
        assert (rb_run / name).exists(), name
    summary = json.loads((rb_run / "summary.json").read_text())
    assert summary["method"] == "reasoningbank" and summary["stand_in_model"] is True
    assert summary["completed"] == summary["planned"] == summary["metrics"]["tasks"] == 4
    assert summary["memory"]["items"] >= 1 and summary["memory"]["embedder"] == "hashing-1024-c3"
    assert summary["llm"]["model"] == "offline-demo" and summary["llm"]["calls"] > 4
    records = [json.loads(line) for line in (rb_run / "records.jsonl").read_text().splitlines()]
    assert len(records) == 4
    config = json.loads((rb_run / "config.json").read_text())
    assert config["method"] == "reasoningbank" and config["origin"] == "paper"
    assert config["config"]["tie_break"] == "newest" and config["config"]["retrieve_k"] == 1
    assert config["agent"]["type"] == "stepwise" and config["llm"] == "offline-demo"
    assert [t["seed"] for t in config["tasks"]] == [0, 1, 2, 3], "the exact stream is recorded"
    assert config["judge"] == "llm" and config["scaling"] == {"name": "none", "k": 1}


def test_run_rejects_an_option_the_method_does_not_have(tmp_path):
    with pytest.raises(SystemExit, match="reasoningbank has no option condition_weight"):
        main(
            [
                *("run", "--method", "reasoningbank", "--set", "condition_weight=0.5"),
                *("--env", "toy-scan", "--llm", "offline-demo", "--out", str(tmp_path / "x")),
            ]
        )


@pytest.mark.parametrize(
    "method, extra, expect",
    [
        ("no_memory", [], {"memory": {}, "judge": "none"}),
        ("matts", ["--set", "scaling_k=2"], {"scaling": {"name": "parallel", "k": 2}}),
        ("matts", ["--set", "scaling=restart", "--set", "scaling_k=2"], {"judge": "llm"}),
        ("conditioned_retrieval", ["--set", "judge=env"], {"judge": "env"}),
        ("policy_program", [], {"judge": "llm"}),
    ],
)
def test_run_every_stream_method_with_the_stand_in_model(tmp_path, capsys, method, extra, expect):
    out = tmp_path / "run"
    code, _ = sea(
        capsys,
        *("run", "--method", method, *extra, "--env", "toy-scan"),
        *("--regime", "nominal,small_battery", "--order", "interleaved", "--seeds", "0:1"),
        *("--llm", "offline-demo", "--out", out),
    )
    assert code == 0
    summary = json.loads((out / "summary.json").read_text())
    config = json.loads((out / "config.json").read_text())
    assert summary["metrics"]["tasks"] == 2 and config["method"] == method
    for key, value in expect.items():
        assert (summary.get(key) if key == "memory" else config[key]) == value
    if method == "policy_program":
        assert config["agent"]["type"] == "policy-program"
        assert summary["llm"]["calls"] < 20, "one call per episode plus judging and extraction"


def test_run_claim_memory_from_a_recorded_study(tmp_path, capsys):
    out = tmp_path / "run"
    code, _ = sea(
        capsys,
        *("run", "--method", "claim_memory", "--set", "claims=results/bsk-battery"),
        *("--env", "toy-scan", "--regime", "small_battery", "--seeds", "0:1"),
        *("--llm", "offline-demo", "--out", out),
    )
    assert code == 0
    summary = json.loads((out / "summary.json").read_text())
    assert summary["memory"] == {"claims": 21}
    record = json.loads((out / "records.jsonl").read_text().splitlines()[0])
    assert len(record["retrieved_item_ids"]) >= 2 and record["new_item_ids"] == []


def test_show_then_lineage_in_both_directions(rb_run, capsys):
    code, out = sea(capsys, "show", rb_run)
    assert code == 0 and "memory items in" in out
    item = re.search(r"\[(mem_[0-9a-f]+)\]", out).group(1)

    code, out = sea(capsys, "prov", "lineage", rb_run, item)
    assert code == 0 and "derived from:" in out
    assert "trajectory" in out, "an item traces back to the episode it was distilled from"

    records = [json.loads(line) for line in (rb_run / "records.jsonl").read_text().splitlines()]
    used = next(i for r in records for i in r["retrieved_item_ids"])
    code, out = sea(capsys, "prov", "lineage", rb_run, used, "--down")
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


# --------------------------------------------------------------------------- comparison protocol

PROTOCOL = {
    "name": "toy-check",
    "title": "Toy protocol",
    "stream": {
        "env": "toy-scan",
        "regimes": ["nominal", "small_battery"],
        "order": "interleaved",
        "seeds": "0:2",
    },
    "agent": "stepwise",
    "model": {"llm": "offline-demo", "embedder": "hashing"},
    "budget": {"max_calls_per_run": 100000},
    "repeats": 2,
    "baseline": "reasoningbank",
    "arms": {
        "no_memory": {"method": "no_memory"},
        "reasoningbank": {"method": "reasoningbank"},
        "newest_on_ties": {"method": "reasoningbank", "options": {"tie_break": "newest"}},
        "conditioned": {"method": "conditioned_retrieval"},
    },
}


def test_compare_runs_every_arm_on_the_same_stream_and_reports(tmp_path, capsys):
    (tmp_path / "protocol.json").write_text(json.dumps(PROTOCOL))
    out = tmp_path / "comparison"
    code, text = sea(
        capsys, "compare", "run", "--protocol", tmp_path / "protocol.json", "--out", out
    )
    assert code == 0
    streams = []
    for arm in PROTOCOL["arms"]:
        for rep in (0, 1):
            config = json.loads((out / arm / f"rep-{rep}" / "config.json").read_text())
            assert (config["protocol"], config["arm"], config["repeat"]) == ("toy-check", arm, rep)
            assert config["llm"] == "offline-demo"
            streams.append([(t["name"], t["seed"]) for t in config["tasks"]])
    assert all(s == streams[0] for s in streams), "every arm and repeat ran the same tasks"
    assert streams[0] == [
        ("nominal", 0),
        ("small_battery", 0),
        ("nominal", 1),
        ("small_battery", 1),
    ]

    result = json.loads((out / "comparison.json").read_text())
    assert result["stand_in_model"] is True and result["baseline"] == "reasoningbank"
    assert set(result["arms"]) == set(PROTOCOL["arms"])
    arm = result["arms"]["conditioned"]
    assert arm["origin"] == "adaptation" and arm["repeats"] == 2
    assert arm["tasks_completed"] == [4, 4] and arm["metrics"]["tasks"] == 8
    assert set(arm["by_group"]) == {"nominal", "small_battery"}
    assert arm["cost"]["model_calls_per_run"] > 0
    assert set(result["comparisons"]) == {
        "no_memory_minus_reasoningbank",
        "newest_on_ties_minus_reasoningbank",
        "conditioned_minus_reasoningbank",
    }
    paired = result["comparisons"]["no_memory_minus_reasoningbank"]
    assert paired["tasks"] == 4 and {"diff", "ci_low", "ci_high", "p_value"} <= set(paired["score"])
    # The same paired difference within each task group (a hypothesis may be about one regime).
    assert set(paired["by_group"]) == {"nominal", "small_battery"}
    assert paired["by_group"]["small_battery"]["tasks"] == 2
    assert "diff" in paired["by_group"]["small_battery"]["score"]
    report = (out / "comparison.md").read_text()
    for needle in (
        "**These numbers are not results.**",
        "## Arms",
        "## Outcome metrics",
        "## Paired differences against `reasoningbank`",
        "## Cost per run",
        "## By task group",
        "Paired difference in score against `reasoningbank` within each group:",
        "| conditioned | `conditioned_retrieval` | adaptation |",
    ):
        assert needle in report, needle
    assert "These numbers are not results" in text

    code, again = sea(capsys, "compare", "report", out)
    assert code == 0 and json.loads((out / "comparison.json").read_text()) == result


def test_compare_checks_a_protocol_before_spending_anything(tmp_path):
    from self_evolving_agents.compare import load_protocol

    def write(**changes):
        protocol = json.loads(json.dumps(PROTOCOL))
        for key, value in changes.items():
            if value is None:
                protocol.pop(key)
            else:
                protocol[key] = value
        (tmp_path / "p.json").write_text(json.dumps(protocol))
        return tmp_path / "p.json"

    load_protocol(write())
    with pytest.raises(ValueError, match="baseline arm 'missing'"):
        load_protocol(write(baseline="missing"))
    with pytest.raises(ValueError, match="has no 'stream'"):
        load_protocol(write(stream=None))
    with pytest.raises(ValueError, match="is not a stream method"):
        load_protocol(write(arms={"reasoningbank": {"method": "claim_graph"}}))
    bad = {"reasoningbank": {"method": "reasoningbank", "options": {"temperature_of_room": 21}}}
    with pytest.raises(ValueError, match="has no option temperature_of_room"):
        load_protocol(write(arms=bad))


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
    from self_evolving_agents.methods.claim_graph import cli as claims_cli
    from self_evolving_agents.methods.claim_graph.graph import ClaimGraph

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


def test_claims_verify_accepts_a_rerun_and_reports_a_changed_number(study, tmp_path, capsys):
    # The same configuration, run again from an empty cache.
    again = tmp_path / "again"
    code = main(
        ["claims", "study", "--config", str(study.parent / "config.json"), "--out", str(again)]
        + ["--budget", "600"]
    )
    assert code == 0
    first = json.loads((study / "graph.json").read_text())["claims"][0]["id"]
    second = json.loads((again / "graph.json").read_text())["claims"][0]["id"]
    assert first != second, "identifiers are random, so a plain diff would always differ"

    code, out = sea(capsys, "claims", "verify", study, again)
    assert code == 0, out
    assert out.count(": identical") == 6 and "6 of 6 files identical" in out

    transfer = json.loads((again / "transfer.json").read_text())
    transfer["held out"]["overall"]["conditional"]["mean_score"] += 0.001
    (again / "transfer.json").write_text(json.dumps(transfer))
    code, out = sea(capsys, "claims", "verify", study, again)
    assert code == 1
    assert "transfer.json: DIFFERS" in out and "overall.conditional.mean_score" in out
    assert "5 of 6 files identical" in out
    code, out = sea(capsys, "claims", "verify", study, again, "--tolerance", "0.01")
    assert code == 0, "a tolerance for numbers, for runs on another machine"

    (again / "composition.json").unlink()
    code, out = sea(capsys, "claims", "verify", study, again, "--tolerance", "0.01")
    assert code == 1 and "composition.json: DIFFERS" in out and "missing in" in out


def test_claims_replicate_runs_each_seed_base_and_summarises(study, tmp_path, capsys):
    config = json.loads((study / "config.json").read_text())
    config["budget"] = 300
    (tmp_path / "config.json").write_text(json.dumps(config))
    out = tmp_path / "replication"
    code, _ = sea(
        capsys,
        *("claims", "replicate", "--config", tmp_path / "config.json", "--out", out),
        *("--seed-bases", "1000,2000"),
    )
    assert code == 0
    for base in (1000, 2000):
        assert (
            json.loads((out / f"seed-{base}" / "config.json").read_text())["tester"]["seed_base"]
            == base
        )
        assert not (out / f"seed-{base}" / "episodes.sqlite").exists(), "one shared cache"
    assert (out / "episodes.sqlite").exists()
    summary = json.loads((out / "replication.json").read_text())
    assert summary["replicates"] == ["1000", "2000"]
    held_out = summary["aggregate"]["held out"]
    reference = held_out["methods"]["reference"]["mean_score"]
    assert reference["n"] == 2 and reference["sd"] == 0, "independent of the training seeds"
    assert len(held_out["methods"]["conditional"]["mean_score"]["values"]) == 2
    assert {
        "mean",
        "sd",
        "min",
        "max",
        "intervals_above_zero",
        "by_seed_intervals_above_zero",
    } <= set(held_out["comparisons"]["conditional_minus_reference"])
    assert all(len(row["choices"]) >= 1 for row in held_out["settings"])
    text = (out / "replication.md").read_text()
    for needle in (
        "## Size and cost of each replicate",
        "## Held-out score: held out",
        "replicates whose 95% interval excludes zero",
        "the same, resampling whole seeds",
        "## Do the replicates reach the same verdicts?",
    ):
        assert needle in text, needle

    code, _ = sea(
        capsys,
        *("claims", "replicate", "--config", tmp_path / "config.json", "--out", out),
        *("--seed-bases", "1000,2000", "--summary-only"),
    )
    assert code == 0 and json.loads((out / "replication.json").read_text()) == summary

    code, text = sea(
        capsys,
        *("claims", "compare", out / "seed-1000", out / "seed-2000"),
        *("--cache", out / "episodes.sqlite", "--out", tmp_path / "compare.json"),
    )
    assert code == 0 and "held out: A " in text and "A minus B" in text
    compared = json.loads((tmp_path / "compare.json").read_text())
    group = compared["groups"]["held out"]
    assert group["a_minus_b"]["n"] == 2 * 8, "two conditions, eight held-out seeds"
    assert group["a_minus_b_by_seed"]["n"] == 8 and "resampling whole seeds" in text
    first = held_out["methods"]["conditional"]["mean_score"]["values"]
    assert group["a_minus_b"]["mean_a"] == pytest.approx(first[0], abs=1e-4)
    assert group["a_minus_b"]["mean_b"] == pytest.approx(first[1], abs=1e-4)


def test_replication_refuses_training_seeds_that_overlap_the_held_out_ones(study, tmp_path):
    from self_evolving_agents.methods.claim_graph.replicate import check_seeds

    config = json.loads((study / "config.json").read_text())
    check_seeds(config)
    config["tester"]["seed_base"] = 4990  # 4990..5037 overlaps the held-out 5000..5007
    with pytest.raises(ValueError, match="overlap the evaluation seeds"):
        check_seeds(config)
    config["tester"]["seed_base"] = 5990
    with pytest.raises(ValueError, match="overlap the evaluation tuning_seeds"):
        check_seeds(config)
