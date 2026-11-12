"""Records, provenance store, embeddings and rule policies."""

from __future__ import annotations

import json

import numpy as np
import pytest

from self_evolving_agents.embeddings import HashingEmbedder, condition_similarity
from self_evolving_agents.policies import PolicyError, RulePolicy, always, evaluate, scanning_policy
from self_evolving_agents.provenance import USED, WAS_DERIVED_FROM, ProvenanceStore
from self_evolving_agents.types import (
    Action,
    Observation,
    Outcome,
    Step,
    Task,
    Trajectory,
    jsonable,
    stable_hash,
)

# --------------------------------------------------------------------------- types


def make_trajectory(traj_id="traj_1", memory=()):
    task = Task("toy-scan", "nominal", seed=3, conditions={"battery_capacity_wh": 200.0})
    return Trajectory(
        id=traj_id,
        task=task,
        query="do the thing",
        steps=[
            Step(
                0,
                "obs0",
                "think0",
                "scan",
                0.01,
                brief="b0",
                result="r0",
                features={"battery": 0.5},
            ),
            Step(1, "obs1", "", "charge", 0.0, brief="b1", result="r1", llm_call_id="llm_x"),
        ],
        outcome=Outcome(score=0.01, success=True, metrics={"alive": True}),
        final_observation="the end",
        agent={"id": "agent:test", "type": "test"},
        memory_item_ids=list(memory),
        meta={"sample": 0},
    )


def test_task_identity_and_round_trip():
    a = Task("toy-scan", "nominal", seed=1, conditions={"x": 1.0, "y": 2.0})
    b = Task("toy-scan", "nominal", seed=2, conditions={"y": 2.0, "x": 1.0})
    assert a.key != b.key
    assert a.family == b.family, "family ignores the seed and the order of conditions"
    assert Task.from_dict(json.loads(json.dumps(a.to_dict()))) == a


def test_trajectory_round_trip_is_lossless():
    traj = make_trajectory()
    again = Trajectory.from_dict(json.loads(json.dumps(traj.to_dict())))
    assert again.to_dict() == traj.to_dict()
    assert again.total_reward == pytest.approx(0.01)
    assert again.steps[1].llm_call_id == "llm_x"


def test_jsonable_handles_numpy_and_non_finite():
    out = jsonable({"a": np.float64(1.5), "b": np.arange(3), "c": float("nan"), 4: (1, 2)})
    assert out == {"a": 1.5, "b": [0, 1, 2], "c": None, "4": [1, 2]}
    json.dumps(out)


def test_stable_hash_ignores_key_order():
    assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})
    assert stable_hash({"a": 1}) != stable_hash({"a": 2})


def test_observation_brief_defaults_to_first_lines():
    assert Observation(text="line one\nline two\nline three").brief == "line one | line two"
    assert Observation(text="x", brief="given").brief == "given"


def test_action_render():
    assert Action("scan").render() == "scan"
    assert json.loads(Action("USE", {"arg1": 1}).render()) == {"action": "USE", "arg1": 1}


# --------------------------------------------------------------------------- provenance


def test_store_records_trajectory_and_links(tmp_path):
    store = ProvenanceStore(tmp_path / "prov.sqlite")
    run_id = store.start_run("test", "unit")
    store.add_node("mem_1", "memory_item", label="lesson")
    traj = make_trajectory(memory=["mem_1"])
    store.record_trajectory(traj)

    loaded = store.load_trajectory(traj.id)
    assert loaded.to_dict() == traj.to_dict()
    assert {(e["relation"], e["dst"]) for e in store.edges(src=traj.id)} == {
        (USED, "mem_1"),
        ("wasAssociatedWith", "agent:test"),
        ("wasGeneratedBy", run_id),
    }
    assert store.counts()["steps"] == 2
    store.close()

    reopened = ProvenanceStore(tmp_path / "prov.sqlite")
    assert reopened.load_trajectory(traj.id).query == "do the thing"


def test_store_can_drop_step_payloads():
    store = ProvenanceStore()
    store.record_trajectory(make_trajectory(), store_steps=False)
    assert store.counts()["steps"] == 0
    assert store.get_node("traj_1")["data"]["n_steps"] == 2


def test_lineage_walks_both_directions():
    store = ProvenanceStore()
    for node in ("traj_a", "exp_a", "mem_a", "traj_b"):
        store.add_node(node, node.split("_")[0])
    store.link("exp_a", WAS_DERIVED_FROM, "traj_a")
    store.link("mem_a", WAS_DERIVED_FROM, "exp_a")
    store.link("traj_b", USED, "mem_a")
    store.link("traj_b", USED, "mem_a")  # duplicates are ignored

    upstream = store.lineage("traj_b")
    assert [(r["id"], r["depth"]) for r in upstream] == [("mem_a", 1), ("exp_a", 2), ("traj_a", 3)]
    downstream = {r["id"] for r in store.lineage("traj_a", "downstream")}
    assert downstream == {"exp_a", "mem_a", "traj_b"}
    assert len(store.edges()) == 3
    with pytest.raises(ValueError):
        store.lineage("traj_a", "sideways")


def test_transaction_rolls_back_on_error():
    store = ProvenanceStore()
    with pytest.raises(RuntimeError), store.transaction():
        store.add_node("n1", "thing")
        raise RuntimeError("boom")
    assert store.get_node("n1") is None


def test_llm_calls_and_usage_totals():
    store = ProvenanceStore()
    store.record_llm_call(
        "llm_1",
        purpose="act",
        model="m",
        request={"system": "s", "messages": []},
        response="r",
        usage={"input_tokens": 10, "output_tokens": 2},
        latency_s=0.1,
        cached=False,
    )
    store.record_llm_call(
        "llm_2",
        purpose="act",
        model="m",
        request={"system": "s", "messages": []},
        response="r",
        usage={"input_tokens": 5, "output_tokens": 1},
        latency_s=0.0,
        cached=True,
    )
    assert store.get_llm_call("llm_1")["response"] == "r"
    usage = store.llm_usage()["act"]
    assert (usage["calls"], usage["cached_calls"], usage["input_tokens"]) == (2, 1, 15)


def test_prov_json_export_shapes_statements():
    store = ProvenanceStore()
    store.add_node("mem_1", "memory_item", label="lesson")
    store.add_node("claim_1", "claim")
    store.add_node("exp_1", "experiment", prov_type="activity")
    store.record_trajectory(make_trajectory(memory=["mem_1"]))
    store.link("mem_1", WAS_DERIVED_FROM, "traj_1")
    store.link("exp_1", "supports", "claim_1")
    doc = store.export_prov_json()

    assert "sea:traj_1" in doc["entity"] and "sea:episode-traj_1" in doc["activity"]
    used = list(doc["used"].values())
    assert used == [{"prov:activity": "sea:episode-traj_1", "prov:entity": "sea:mem_1"}]
    assert {"prov:generatedEntity": "sea:mem_1", "prov:usedEntity": "sea:traj_1"} in doc[
        "wasDerivedFrom"
    ].values()
    influenced = list(doc["wasInfluencedBy"].values())[0]
    assert influenced["sea:relation"] == "supports"
    json.dumps(doc)


# --------------------------------------------------------------------------- embeddings


def test_hashing_embedder_is_deterministic_and_normalised():
    embedder = HashingEmbedder(dim=256)
    a = embedder.embed(["charge before eclipse", ""])
    b = HashingEmbedder(dim=256).embed(["charge before eclipse", ""])
    assert np.array_equal(a, b)
    assert np.linalg.norm(a[0]) == pytest.approx(1.0)
    assert np.all(a[1] == 0), "empty text embeds to the zero vector, not NaN"


def test_hashing_embedder_ranks_overlap_higher():
    embedder = HashingEmbedder()
    q, near, far = embedder.embed(
        [
            "pick up the microscope and place it in the pot",
            "pick up the thermometer and place it in the jar",
            "desaturate reaction wheels before they reach the limit",
        ]
    )
    assert q @ near > q @ far


def test_condition_similarity():
    base = {"battery_capacity_wh": 200.0, "scenario": "A"}
    assert condition_similarity(base, base) == pytest.approx(1.0)
    half = condition_similarity(base, {"battery_capacity_wh": 100.0, "scenario": "A"})
    double = condition_similarity(base, {"battery_capacity_wh": 400.0, "scenario": "A"})
    assert half == pytest.approx(double), "ratios are compared on a log scale"
    assert half < 1.0
    assert condition_similarity(base, {"scenario": "B"}) == 0.0
    assert condition_similarity(base, {"other": 1}) is None


# --------------------------------------------------------------------------- policies

FEATURES = {"battery": 0.2, "in_eclipse": 0.0, "wheel_speed": 0.7, "eclipse_start_s": 300.0}


def test_evaluate_grammar():
    assert evaluate({"battery": {"<": 0.25}}, FEATURES, {})
    assert not evaluate({"battery": {"<": 0.25, ">": 0.21}}, FEATURES, {})
    assert evaluate({"battery": {"<": "$t"}}, FEATURES, {"t": 0.3})
    assert evaluate({"all": [{"battery": {"<": 0.25}}, {"in_eclipse": {"==": 0}}]}, FEATURES, {})
    assert evaluate({"any": [{"battery": {">": 0.9}}, {"wheel_speed": {">=": 0.7}}]}, FEATURES, {})
    assert evaluate({"not": {"battery": {">": 0.9}}}, FEATURES, {})
    assert not evaluate({"battery": {"<": 0.25}, "in_eclipse": {"==": 1}}, FEATURES, {})


@pytest.mark.parametrize(
    "condition",
    [
        {},
        {"nope": {"<": 1}},
        {"battery": {"~": 1}},
        {"battery": {"<": "$missing"}},
        {"battery": {"<": "0.5"}},
        {"battery": 0.5},
        {"all": []},
        {"battery": {"<": True}},
    ],
)
def test_evaluate_rejects_malformed_conditions(condition):
    with pytest.raises(PolicyError):
        evaluate(condition, FEATURES, {})


def test_policy_first_match_wins_and_explains():
    policy = RulePolicy(
        rules=[
            {"if": {"wheel_speed": {">": 0.6}}, "do": "desat"},
            {"if": {"battery": {"<": 0.25}}, "do": "charge"},
        ],
        default="scan",
    )
    assert policy.explain(FEATURES) == ("desat", 0)
    assert policy.explain({**FEATURES, "wheel_speed": 0.1}) == ("charge", 1)
    assert policy.explain({**FEATURES, "wheel_speed": 0.1, "battery": 0.9}) == ("scan", None)


def test_policy_params_round_trip_and_fingerprint():
    base = scanning_policy()
    tuned = base.with_params(charge_below=0.4)
    assert base.params["charge_below"] == 0.25, "with_params must not mutate the original"
    moved = scanning_policy(charge_below=0.4, charge_margin=0.1)
    assert moved.params["charge_until"] == pytest.approx(0.5), (
        "the stop level follows the threshold"
    )
    assert scanning_policy.defaults["charge_margin"] == 0.0
    with pytest.raises(PolicyError, match="unknown knob"):
        scanning_policy(charge_until=0.5)
    assert tuned.fingerprint != base.fingerprint
    assert (
        RulePolicy.from_dict(json.loads(json.dumps(tuned.to_dict()))).fingerprint
        == tuned.fingerprint
    )
    assert scanning_policy(name="other").fingerprint == base.fingerprint, "names do not matter"
    with pytest.raises(PolicyError):
        base.with_params(not_a_param=1.0)
    assert "$charge_below" in base.describe()


def test_policy_validation_catches_bad_names():
    features = ["battery", "wheel_speed"]
    actions = ["scan", "charge"]
    RulePolicy([{"if": {"battery": {"<": 0.2}}, "do": "charge"}], "scan").validate(
        features, actions
    )
    bad = [
        RulePolicy([], "fly"),
        RulePolicy([{"if": {"battery": {"<": 0.2}}, "do": "fly"}], "scan"),
        RulePolicy([{"if": {"altitude": {"<": 0.2}}, "do": "charge"}], "scan"),
        RulePolicy([{"if": {"battery": {"<": "$x"}}, "do": "charge"}], "scan"),
        RulePolicy([{"when": {"battery": {"<": 0.2}}, "do": "charge"}], "scan"),
    ]
    for policy in bad:
        with pytest.raises(PolicyError):
            policy.validate(features, actions)


def test_always_policy():
    assert always("scan").act({}) == "scan"
