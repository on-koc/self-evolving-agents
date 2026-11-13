"""Claims, evidence, revision, planning and policy assembly.

Graph logic is tested with hand-made evidence so that each rule is pinned down
exactly; the end-to-end loop is then run on the toy environment. Results on the toy
environment check the machinery, not the physics.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from self_evolving_agents.experiments import (
    EpisodeCache,
    EpisodeRunner,
    EpisodeSpec,
    interaction_compare,
    mean_interval,
    paired_compare,
    trend_test,
)
from self_evolving_agents.llm import ScriptedLLM
from self_evolving_agents.methods.claim_graph import (
    ActiveLoop,
    Claim,
    ClaimGraph,
    ClaimTester,
    Domain,
    Evidence,
    HypothesisError,
    LadderProposer,
    LLMProposer,
    Mechanism,
    Planner,
    Region,
    assemble_policy,
    claim_from_spec,
    composition_check,
    evaluate_transfer,
    load_hypotheses,
    partition,
    policy_map,
    recommend,
)
from self_evolving_agents.methods.claim_graph.report import render_report
from self_evolving_agents.methods.claim_graph.schema import (
    A_BETTER,
    B_BETTER,
    CONTESTED,
    CONTRADICTS,
    HYPOTHESIS,
    INCONCLUSIVE,
    NO_BENEFIT,
    REFUTED,
    RETIRED,
    SUPERSEDED,
    SUPPORTED,
    SUPPORTS,
    log_distance,
)
from self_evolving_agents.methods.claim_graph.testing import ABResult, classify_effect, metric_value
from self_evolving_agents.methods.claim_memory import ClaimMemory, claims_as_memory
from self_evolving_agents.policies import scanning_policy
from self_evolving_agents.provenance import ProvenanceStore
from self_evolving_agents.types import Outcome

WH = "battery_capacity_wh"
STUDIES = Path(__file__).resolve().parent.parent / "studies"

# --------------------------------------------------------------------------- statistics


def test_paired_compare_detects_a_consistent_shift_and_is_deterministic():
    rng = np.random.default_rng(1)
    base = rng.normal(0, 5, size=30)  # large seed-to-seed variation, shared by both arms
    a, b = base + 0.3 + rng.normal(0, 0.1, 30), base
    result = paired_compare(a, b)
    assert result.diff == pytest.approx(0.3, abs=0.06)
    assert result.ci_low > 0.2 and result.ci_high < 0.4 and result.p_value < 0.01
    assert paired_compare(a, b).to_dict() == result.to_dict()


def test_paired_compare_finds_nothing_in_noise():
    rng = np.random.default_rng(2)
    result = paired_compare(rng.normal(0, 1, 40), rng.normal(0, 1, 40))
    assert result.ci_low < 0 < result.ci_high and result.p_value > 0.05


def test_paired_compare_degenerate_cases():
    same = paired_compare([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert (same.diff, same.ci_low, same.ci_high, same.p_value) == (0.0, 0.0, 0.0, 1.0)
    constant = paired_compare([2.0] * 8, [1.0] * 8)
    assert constant.ci_low == constant.ci_high == 1.0 and constant.p_value == pytest.approx(2 / 256)
    with pytest.raises(ValueError):
        paired_compare([1.0], [2.0])
    with pytest.raises(ValueError):
        paired_compare([1.0, 2.0], [1.0])


def test_interaction_trend_and_mean_interval():
    rng = np.random.default_rng(3)
    low = rng.normal(0.0, 0.05, 24)
    high = low + 0.2
    assert interaction_compare(high, low).ci_low > 0.15
    rising = trend_test([1, 2, 3, 4, 5], [0.0, 0.1, 0.2, 0.35, 0.5])
    assert rising.rho == pytest.approx(1.0) and rising.p_value < 0.05
    flat = trend_test([1, 2, 3], [0.1, 0.1, 0.1])
    assert flat.rho == 0.0 and flat.p_value == 1.0
    mean, lo, hi = mean_interval([1.0, 2.0, 3.0, 4.0])
    assert lo < mean == 2.5 < hi
    assert mean_interval([3.0]) == (3.0, 3.0, 3.0)


@pytest.mark.parametrize(
    "low, high, mean, expected",
    [
        (0.03, 0.09, 0.06, A_BETTER),
        (0.001, 0.015, 0.008, NO_BENEFIT),  # positive but too small to matter
        (-0.5, -0.2, -0.35, B_BETTER),
        (-0.01, 0.015, 0.002, NO_BENEFIT),
        (-0.045, 0.000, -0.021, NO_BENEFIT),  # the claimed gain is ruled out; a loss is not shown
        (-0.05, 0.2, 0.07, INCONCLUSIVE),
        (0.005, 0.2, 0.015, INCONCLUSIVE),  # could still be a real effect
        (-0.2, 0.019, -0.09, NO_BENEFIT),
    ],
)
def test_classify_effect(low, high, mean, expected):
    assert classify_effect(low, high, mean, min_effect=0.02) == expected


# --------------------------------------------------------------------------- regions


def test_region_contains_restrict_and_describe():
    region = Region({WH: (100.0, None)})
    assert region.contains({WH: 100.0}) and region.contains({WH: 5000.0})
    assert not region.contains({WH: 99.9})
    assert not region.contains({"other": 1.0}), "an unknown value cannot be assumed to be in range"
    narrowed = region.restrict(WH, high=400.0).restrict("panel_area_m2", low=0.2)
    assert narrowed.contains({WH: 399.0, "panel_area_m2": 0.25})
    assert not narrowed.contains({WH: 400.0, "panel_area_m2": 0.25}), "the upper bound is exclusive"
    assert narrowed.describe() == "100 <= battery_capacity_wh < 400 and panel_area_m2 >= 0.2"
    assert Region().describe() == "all tested conditions" and Region().contains({})
    assert region.restrict(WH, low=50.0).bounds[WH] == (100.0, None), "restrict only ever narrows"
    assert (
        Region.from_dict(json.loads(json.dumps(narrowed.to_dict()))).to_dict() == narrowed.to_dict()
    )


def test_region_relations():
    low, high = Region({WH: (None, 100.0)}), Region({WH: (100.0, None)})
    assert not low.intersects(high) and low.intersects(Region({WH: (50.0, 150.0)}))
    assert Region({WH: (120.0, 300.0)}).within(high) and not Region({WH: (50.0, 300.0)}).within(
        high
    )
    assert not Region().within(high) and high.within(Region())
    assert Region({WH: (5.0, 5.0)}).is_empty() and not high.is_empty()
    assert log_distance({WH: 50.0}, {WH: 100.0}, [WH]) == pytest.approx(
        log_distance({WH: 100.0}, {WH: 200.0}, [WH])
    )


# --------------------------------------------------------------------------- partitioning


def points(*pairs):
    return [({WH: float(x)}, label) for x, label in pairs]


def test_partition_single_label_is_one_region():
    leaves = partition(points((50, A_BETTER), (200, A_BETTER)), Region())
    assert [(leaf.label, leaf.region.describe()) for leaf in leaves] == [
        (A_BETTER, "all tested conditions")
    ]


def test_partition_splits_at_the_geometric_midpoint():
    leaves = partition(
        points((50, B_BETTER), (100, B_BETTER), (200, A_BETTER), (400, A_BETTER)), Region()
    )
    assert [leaf.label for leaf in leaves] == [B_BETTER, A_BETTER]
    assert leaves[0].region.bounds[WH] == (None, pytest.approx(141.42, abs=0.01))
    assert leaves[1].region.bounds[WH] == (pytest.approx(141.42, abs=0.01), None)


def test_partition_three_way_and_two_variables():
    three = partition(points((25, NO_BENEFIT), (50, B_BETTER), (200, A_BETTER)), Region())
    assert [leaf.label for leaf in three] == [NO_BENEFIT, B_BETTER, A_BETTER]

    grid = [
        ({WH: 50.0, "panel_area_m2": 0.1}, B_BETTER),
        ({WH: 50.0, "panel_area_m2": 0.25}, A_BETTER),
        ({WH: 200.0, "panel_area_m2": 0.1}, B_BETTER),
        ({WH: 200.0, "panel_area_m2": 0.25}, A_BETTER),
    ]
    leaves = partition(grid, Region())
    assert len(leaves) == 2, "the variable that actually separates the labels is chosen"
    assert all(leaf.region.constrained == ["panel_area_m2"] for leaf in leaves)


def test_partition_reports_unsplittable_disagreement_as_mixed():
    leaves = partition(points((100, A_BETTER), (100, B_BETTER)), Region())
    assert [leaf.label for leaf in leaves] == ["mixed"]


def test_partition_pulls_a_checkerboard_apart():
    """No single split helps here, but two do; it is not an unsplittable disagreement."""
    grid = [
        ({WH: 50.0, "panel_area_m2": 0.1}, A_BETTER),
        ({WH: 50.0, "panel_area_m2": 0.25}, B_BETTER),
        ({WH: 200.0, "panel_area_m2": 0.1}, B_BETTER),
        ({WH: 200.0, "panel_area_m2": 0.25}, A_BETTER),
    ]
    leaves = partition(grid, Region())
    assert sorted(leaf.label for leaf in leaves) == sorted([A_BETTER, B_BETTER] * 2)
    assert all(len(leaf.points) == 1 and len(leaf.region.constrained) == 2 for leaf in leaves)
    for conditions, label in grid:
        (home,) = [leaf for leaf in leaves if leaf.region.contains(conditions)]
        assert home.label == label


FIVE_RUNS = (
    (10, A_BETTER),
    (20, INCONCLUSIVE),
    (40, A_BETTER),
    (80, INCONCLUSIVE),
    (160, NO_BENEFIT),
)


def test_partition_depth_limit_leaves_a_mixed_region_that_more_depth_separates():
    """Five runs of verdicts along one variable need four splits in a row.

    This is the pattern that marked claims as contested for a while in the Basilisk
    study, until further experiments changed the order of the splits.
    """
    shallow = partition(points(*FIVE_RUNS), Region(), max_depth=3)
    assert "mixed" in [leaf.label for leaf in shallow]
    deep = partition(points(*FIVE_RUNS), Region(), max_depth=6)
    assert [leaf.label for leaf in deep] == [label for _, label in FIVE_RUNS]


# --------------------------------------------------------------------------- graph revision


def claim(**kw):
    defaults = dict(
        statement="A lower charge threshold collects more data.",
        intervention={"charge_below": 0.10},
        baseline={"charge_below": 0.25},
    )
    return Claim(**{**defaults, **kw})


def outcome(wh, label, effect=None, **details):
    effect = (
        {A_BETTER: 0.1, B_BETTER: -0.4, NO_BENEFIT: 0.0, INCONCLUSIVE: 0.03}[label]
        if effect is None
        else effect
    )
    width = 0.2 if label == INCONCLUSIVE else 0.01
    verdict = {A_BETTER: SUPPORTS, B_BETTER: CONTRADICTS, NO_BENEFIT: CONTRADICTS}.get(
        label, INCONCLUSIVE
    )
    return Evidence(
        experiment_id=f"xp_{wh}_{label}",
        kind="outcome",
        verdict=verdict,
        label=label,
        conditions={WH: float(wh)},
        n=16,
        effect=effect,
        ci_low=effect - width,
        ci_high=effect + width,
        p_value=0.01,
        details=details,
    )


def test_claim_validation():
    with pytest.raises(ValueError, match="same policy parameters"):
        claim(baseline={"desat_above": 0.6})
    with pytest.raises(ValueError, match="identical"):
        claim(baseline={"charge_below": 0.10})
    with pytest.raises(ValueError, match="at least one"):
        Claim("x", {}, {})
    c = claim()
    assert c.is_root and c.family == c.id and c.status == HYPOTHESIS
    assert Claim.from_dict(json.loads(json.dumps(c.to_dict()))).to_dict() == c.to_dict()


def test_supported_everywhere_tested_stays_one_claim():
    graph = ClaimGraph()
    root = graph.add(claim())
    graph.record(root.id, outcome(200, A_BETTER))
    graph.record(root.id, outcome(400, A_BETTER))
    assert root.status == SUPPORTED and graph.children(root.id) == []
    assert [c.id for c, _ in graph.applicable({WH: 300.0})] == [root.id]


def test_inconclusive_evidence_decides_nothing():
    graph = ClaimGraph()
    root = graph.add(claim())
    graph.record(root.id, outcome(200, INCONCLUSIVE))
    assert root.status == HYPOTHESIS and graph.applicable({WH: 200.0}) == []


def test_unresolved_points_get_no_claim_instead_of_inheriting_their_neighbours():
    """Support at two points does not cover a third where the test stayed inconclusive."""
    graph = ClaimGraph()
    root = graph.add(claim())
    graph.record(root.id, outcome(100, A_BETTER))
    assert root.status == SUPPORTED and graph.applicable({WH: 400.0}) != []

    graph.record(root.id, outcome(400, INCONCLUSIVE))
    assert root.status == SUPERSEDED
    assert any("only part of its scope" in entry["detail"] for entry in graph.log)
    (narrowed,) = graph.children(root.id)
    assert narrowed.scope.bounds[WH] == (None, pytest.approx(200.0))
    assert root.origin["unresolved_regions"] == ["battery_capacity_wh >= 200"]
    assert graph.applicable({WH: 400.0}) == [], (
        "nothing is recommended where nothing was established"
    )
    assert [c.id for c, _ in graph.applicable({WH: 120.0})] == [narrowed.id]


def test_no_benefit_contradicts_without_reversing():
    graph = ClaimGraph()
    root = graph.add(claim())
    graph.record(root.id, outcome(100, A_BETTER))
    graph.record(root.id, outcome(400, NO_BENEFIT))
    (narrowed,) = graph.children(root.id)
    assert root.status == SUPERSEDED and narrowed.intervention == root.intervention
    assert root.origin["no_benefit_regions"] == ["battery_capacity_wh >= 200"]
    assert graph.applicable({WH: 400.0}) == []


def test_disagreement_narrows_the_claim_and_reverses_it_across_the_boundary():
    graph = ClaimGraph()
    root = graph.add(claim())
    graph.record(root.id, outcome(200, A_BETTER))
    log = graph.record(root.id, outcome(50, B_BETTER))

    assert root.status == SUPERSEDED
    narrowed, reversed_ = sorted(
        graph.children(root.id), key=lambda c: c.intervention["charge_below"]
    )
    assert narrowed.status == reversed_.status == SUPPORTED
    assert narrowed.intervention == {"charge_below": 0.10}
    assert narrowed.scope.bounds[WH] == (pytest.approx(100.0), None)
    assert reversed_.intervention == {"charge_below": 0.25} and reversed_.baseline == {
        "charge_below": 0.10
    }
    assert reversed_.scope.bounds[WH] == (None, pytest.approx(100.0))
    assert reversed_.statement.startswith("Here the reverse holds: charge_below=0.25 does better.")

    assert {op["op"] for op in log} == {"evidence", "supersede", "specialize", "support"}
    relations = set(graph.relations)
    assert (narrowed.id, "specializes", root.id) in relations
    assert (reversed_.id, "contradicts", root.id) in relations
    assert (narrowed.id, "supersedes", root.id) in relations

    # Each claim keeps the test that fixed its boundary, re-read from its own side.
    assert [e.conditions[WH] for e in narrowed.counterexamples()] == [50.0]
    assert [e.conditions[WH] for e in reversed_.counterexamples()] == [200.0]
    flipped = next(e for e in reversed_.evidence if e.conditions[WH] == 50.0)
    assert flipped.verdict == SUPPORTS and flipped.effect == pytest.approx(0.4)
    assert (flipped.ci_low, flipped.ci_high) == (pytest.approx(0.39), pytest.approx(0.41))
    assert [c.id for c, _ in graph.applicable({WH: 60.0})] == [reversed_.id]
    assert [c.id for c, _ in graph.applicable({WH: 300.0})] == [narrowed.id]


def test_boundary_probes_rescope_existing_claims_instead_of_replacing_them():
    graph = ClaimGraph()
    root = graph.add(claim())
    for wh, label in ((200, A_BETTER), (50, B_BETTER)):
        graph.record(root.id, outcome(wh, label))
    before = {c.id: c.scope.describe() for c in graph.children(root.id)}
    log = graph.record(root.id, outcome(100, B_BETTER))

    after = {c.id: c.scope.describe() for c in graph.children(root.id)}
    assert set(after) == set(before), "the same claims, with moved boundaries"
    assert after != before and [op["op"] for op in log].count("rescope") == 2
    narrowed = next(c for c in graph.children(root.id) if c.intervention["charge_below"] == 0.10)
    assert narrowed.scope.bounds[WH][0] == pytest.approx(141.42, abs=0.01)


def test_equivalent_region_gets_no_claim_and_refuted_roots_keep_their_reverse():
    graph = ClaimGraph()
    root = graph.add(claim())
    graph.record(root.id, outcome(25, NO_BENEFIT))
    assert root.status == REFUTED and graph.children(root.id) == []
    assert root.origin["no_benefit_regions"] == ["all tested conditions"]
    assert graph.applicable({WH: 25.0}) == []

    graph.record(root.id, outcome(50, B_BETTER))
    (reverse,) = graph.children(root.id)
    assert root.status == REFUTED and reverse.status == SUPPORTED
    assert reverse.scope.bounds[WH][0] == pytest.approx(35.36, abs=0.01)
    assert graph.applicable({WH: 25.0}) == [], "nothing is recommended where nothing was better"


def test_retest_replaces_earlier_evidence_and_can_restore_the_root():
    graph = ClaimGraph()
    root = graph.add(claim())
    graph.record(root.id, outcome(200, A_BETTER))
    graph.record(root.id, outcome(50, B_BETTER))
    children = graph.children(root.id)
    graph.record(root.id, outcome(50, A_BETTER))  # more seeds overturned the earlier result

    assert len([e for e in root.evidence if e.conditions[WH] == 50.0]) == 1
    assert root.status == SUPPORTED
    assert all(c.status == RETIRED for c in children)
    assert graph.children(root.id) == [] and len(graph.children(root.id, active_only=False)) == 2
    assert [c.id for c, _ in graph.applicable({WH: 60.0})] == [root.id]


def test_unsplittable_disagreement_is_contested():
    graph = ClaimGraph()
    root = graph.add(claim())
    graph.record(root.id, outcome(100, A_BETTER, background={"desat_above": 0.3}))
    graph.record(root.id, outcome(100, B_BETTER, background={}))
    (child,) = graph.children(root.id)
    assert child.status == CONTESTED and graph.applicable({WH: 100.0}) == []


def test_graph_depth_decides_whether_a_crowded_family_is_separated():
    def build(depth):
        graph = ClaimGraph(max_depth=depth)
        root = graph.add(claim())
        for wh, label in FIVE_RUNS:
            graph.record(root.id, outcome(wh, label))
        return graph, root

    graph, root = build(3)
    contested = [c for c in graph.children(root.id) if c.status == CONTESTED]
    assert len(contested) == 1 and contested[0].scope.contains({WH: 40.0})
    assert graph.applicable({WH: 40.0}) == [], "a contested claim is never applied"
    assert any("disagree and could not be separated" in e["detail"] for e in graph.log)

    graph, root = build(6)
    assert all(c.status == SUPPORTED for c in graph.children(root.id))
    assert [c.scope.contains({WH: 40.0}) for c, _ in graph.applicable({WH: 40.0})] == [True]
    assert graph.applicable({WH: 80.0}) == [], "the unresolved point still gets no claim"
    assert len(root.origin["unresolved_regions"]) == 2

    with pytest.raises(ValueError, match="max_depth"):
        ClaimGraph(max_depth=0)


def test_a_claim_is_not_applied_past_a_nearer_test_that_disagrees():
    """With two variables a region can reach across to a row where it was never tested."""
    PA = "panel_area_m2"

    def at(wh, area, label):
        e = outcome(wh, label)
        e.conditions = {WH: float(wh), PA: area}
        e.experiment_id = f"xp_{wh}_{area}"
        return e

    graph = ClaimGraph(max_depth=8)
    root = graph.add(claim())
    for wh, area, label in (
        (100, 0.25, B_BETTER),
        (200, 0.25, B_BETTER),
        (100, 0.1, B_BETTER),
        (141, 0.1, A_BETTER),
    ):
        graph.record(root.id, at(wh, area, label))
    (narrowed,) = [c for c in graph.children(root.id) if c.intervention == root.intervention]
    assert PA not in narrowed.scope.bounds, "the supported region spans every array area"
    low, high = narrowed.scope.bounds[WH]
    assert low < 141 < 150 < high

    small_array, large_array = {WH: 150.0, PA: 0.1}, {WH: 150.0, PA: 0.25}
    assert narrowed.scope.contains(small_array) and narrowed.scope.contains(large_array)
    assert [c.id for c, _ in graph.applicable(small_array)] == [narrowed.id]
    # At the large array the nearest test is (200 Wh, 0.25): baseline better.
    assert [e.conditions[WH] for e in graph.nearest_tests(root.id, large_array)] == [200.0]
    assert graph.applicable(large_array) == [], "box and nearest test disagree: no claim"
    unchecked = graph.applicable(large_array, check_nearest=False)
    assert narrowed.id in [c.id for c, _ in unchecked]
    assert recommend(graph, small_array).settings == {"charge_below": 0.1}
    assert recommend(graph, large_array).settings == {}


def test_a_claim_still_applies_when_the_nearest_test_agrees_from_a_neighbouring_region():
    """Agreement is what counts, not which region the nearest test was filed under."""
    PA = "panel_area_m2"

    def at(wh, area, label):
        e = outcome(wh, label)
        e.conditions = {WH: float(wh), PA: area}
        e.experiment_id = f"xp_{wh}_{area}"
        return e

    graph = ClaimGraph(max_depth=8)
    root = graph.add(claim())
    for wh, area, label in (
        (100, 0.25, A_BETTER),
        (200, 0.25, A_BETTER),
        (100, 0.1, INCONCLUSIVE),
        (141, 0.1, A_BETTER),
    ):
        graph.record(root.id, at(wh, area, label))
    narrowed = [c for c in graph.children(root.id) if c.status == SUPPORTED]
    assert len(narrowed) == 2, "two supported regions around the unresolved point"
    query = {WH: 140.0, PA: 0.2}
    (holder,) = [c for c in narrowed if c.scope.contains(query)]
    (nearest,) = graph.nearest_tests(root.id, query)
    assert nearest.conditions == {WH: 100.0, PA: 0.25} and nearest.label == A_BETTER
    assert not holder.scope.contains(nearest.conditions), "it sits in the other region"
    assert [c.id for c, _ in graph.applicable(query)] == [holder.id]
    assert recommend(graph, query).settings == {"charge_below": 0.1}
    assert recommend(graph, {WH: 100.0, PA: 0.1}).settings == {}, "unresolved there"
    assert recommend(graph, query, check_nearest=False).settings == {"charge_below": 0.1}


def test_the_nearest_test_check_never_bites_along_a_single_variable():
    graph = ClaimGraph()
    root = graph.add(claim())
    for wh, label in (
        *((25, NO_BENEFIT), (42, B_BETTER), (70.7, B_BETTER), (119, B_BETTER)),
        *((154, INCONCLUSIVE), (200, A_BETTER), (400, A_BETTER)),
    ):
        graph.record(root.id, outcome(wh, label))
    edges = sorted(
        bound for c in graph.children(root.id) for bound in c.scope.bounds[WH] if bound is not None
    )
    queries = [10 * 1.07**i for i in range(70)] + edges + [e * (1 + 1e-12) for e in edges]
    for wh in queries:
        point = {WH: wh}
        checked = [c.id for c, _ in graph.applicable(point)]
        assert checked == [c.id for c, _ in graph.applicable(point, check_nearest=False)], wh
    assert len(edges) >= 3 and graph.nearest_tests(root.id, {}) == []


def test_policy_map_lists_the_recommendation_region_by_region():
    graph = ClaimGraph()
    lower = graph.add(claim())
    for wh, label in ((50, B_BETTER), (200, A_BETTER), (400, A_BETTER)):
        graph.record(lower.id, outcome(wh, label))
    desat = graph.add(
        claim(
            statement="Unloading the wheels early helps.",
            intervention={"desat_above": 0.3},
            baseline={"desat_above": 0.6},
        )
    )
    for wh, label in ((50, A_BETTER), (200, A_BETTER), (400, NO_BENEFIT)):
        graph.record(desat.id, outcome(wh, label))

    rows = policy_map(graph)
    table = [(row["region"].bounds[WH], row["settings"]) for row in rows]
    assert table == [
        ((None, pytest.approx(100.0)), {"desat_above": 0.3}),
        ((pytest.approx(100.0), pytest.approx(282.84, abs=0.01)), _both()),
        ((pytest.approx(282.84, abs=0.01), None), {"charge_below": 0.1}),
    ]
    assert all(row["claims"] for row in rows)
    for row in rows:  # the table agrees with asking the graph directly
        low, high = row["region"].bounds[WH]
        probe = {WH: (low or high / 2) * 1.01}
        assert recommend(graph, probe).settings == row["settings"]

    text = render_report(graph, title="t")
    assert "## What the graph recommends, by condition" in text
    assert "| below 100 | · | 0.3 |" in text and "| 282.8 and above | 0.1 | · |" in text
    assert policy_map(ClaimGraph()) == [{"region": Region(), "settings": {}, "claims": []}], (
        "an empty graph recommends the reference policy everywhere"
    )
    assert "What the graph recommends" not in render_report(ClaimGraph(), title="t")


def _both():
    return {"charge_below": 0.1, "desat_above": 0.3}


def test_policy_map_of_a_claim_that_holds_everywhere_is_one_row():
    """No claim has a boundary, so there is no condition to stand on; this used to crash."""
    graph = ClaimGraph()
    root = graph.add(claim())
    graph.record(root.id, outcome(200, A_BETTER))
    assert policy_map(graph) == [
        {"region": Region(), "settings": {"charge_below": 0.1}, "claims": [root.id]}
    ]
    ((found, distance),) = graph.applicable({})
    assert found.id == root.id and distance == float("inf")
    text = render_report(graph, title="t")
    assert "| any |" not in text and "| 0.1 |" in text


def test_policy_map_merges_neighbouring_regions_with_the_same_recommendation():
    graph = ClaimGraph()
    lower = graph.add(claim())
    graph.record(lower.id, outcome(50, A_BETTER))
    graph.record(lower.id, outcome(200, A_BETTER))
    desat = graph.add(
        claim(
            statement="Unloading the wheels early helps.",
            intervention={"desat_above": 0.3},
            baseline={"desat_above": 0.6},
        )
    )
    # Supported on both sides of a stretch where it could not be established.
    for wh, label in ((25, A_BETTER), (50, INCONCLUSIVE), (100, A_BETTER)):
        graph.record(desat.id, outcome(wh, label))
    rows = policy_map(graph)
    assert [row["settings"] for row in rows] == [_both(), {"charge_below": 0.1}, _both()]
    assert rows[0]["region"].bounds[WH][0] is None and rows[-1]["region"].bounds[WH][1] is None


def test_applicable_reports_distance_to_the_nearest_supporting_test():
    graph = ClaimGraph()
    root = graph.add(claim())
    graph.record(root.id, outcome(200, A_BETTER))
    assert graph.applicable({WH: 200.0})[0][1] == 0.0
    assert graph.applicable({WH: 400.0})[0][1] == pytest.approx(np.log(2))
    assert graph.applicable({WH: 200.0}, env_id="other-env") == []


def test_duplicates_are_recognised_in_either_direction():
    graph = ClaimGraph()
    root = graph.add(claim())
    assert graph.find_duplicate(claim()) is root
    mirrored = claim(intervention={"charge_below": 0.25}, baseline={"charge_below": 0.10})
    assert graph.find_duplicate(mirrored) is root
    assert graph.find_duplicate(claim(intervention={"charge_below": 0.05})) is None
    with pytest.raises(ValueError, match="already exists"):
        graph.add(root)


def test_graph_persists_and_mirrors_into_provenance(tmp_path):
    store = ProvenanceStore()
    graph = ClaimGraph(tmp_path / "graph.json", store=store)
    root = graph.add(claim(mechanisms=[Mechanism("less charging", "time_charge_s", -1)]))
    graph.record(root.id, outcome(200, A_BETTER))
    evidence = outcome(50, B_BETTER)
    graph.record(root.id, evidence)

    again = ClaimGraph(tmp_path / "graph.json")
    assert again.summary() == graph.summary()
    assert again.get(root.id).mechanisms[0].mediator == "time_charge_s"
    assert set(again.relations) == set(graph.relations)

    child = graph.children(root.id)[0]
    assert store.get_node(root.id)["kind"] == "claim"
    assert (evidence.id, "contradicts", root.id) in {
        (e["src"], e["relation"], e["dst"]) for e in store.edges(dst=root.id)
    }
    assert store.edges(src=child.id, relation="specializes")[0]["dst"] == root.id
    assert (
        store.edges(src=evidence.id, relation="wasGeneratedBy")[0]["dst"] == evidence.experiment_id
    )
    assert root.id in {r["id"] for r in store.lineage(child.id)}


# --------------------------------------------------------------------------- evidence from experiments


def fake_ab(
    treatment, control, t_fail=None, c_fail=None, metrics_t=None, metrics_c=None, conditions=None
):
    n = len(treatment)

    def arm(scores, fails, metrics):
        return [
            Outcome(
                score=float(scores[i]),
                failure=(fails or [None] * n)[i],
                metrics={k: v[i] for k, v in (metrics or {}).items()},
            )
            for i in range(n)
        ]

    return ABResult(
        conditions=conditions or {WH: 200.0, "max_wheel_speed_rpm": 6000.0},
        treatment_params={},
        control_params={},
        seeds=list(range(n)),
        treatment=arm(treatment, t_fail, metrics_t),
        control=arm(control, c_fail, metrics_c),
    )


@pytest.fixture
def tester():
    domain = Domain(variables={WH: [25, 50, 100, 200, 400]}, env_id="toy-scan")
    return ClaimTester(EpisodeRunner(), domain, batch=16, max_seeds=48)


def test_metric_value_reads_scores_failures_and_metrics():
    o = Outcome(score=0.4, failure="wheels", metrics={"time_charge_s": 120.0})
    assert metric_value(o, "score") == 0.4 and metric_value(o, "time_charge_s") == 120.0
    assert metric_value(o, "failure:wheels") == 1.0 and metric_value(o, "failure:battery") == 0.0
    assert metric_value(o, "failure") == 1.0
    with pytest.raises(KeyError, match="not reported"):
        metric_value(o, "happiness")


def test_tester_tightens_confidence_for_repeated_looks(tester):
    assert tester.confidence == pytest.approx(1 - 0.0221), "three looks at 16, 32 and 48 seeds"
    single = ClaimTester(EpisodeRunner(), tester.domain, batch=16, max_seeds=16)
    assert single.confidence == pytest.approx(0.95)
    with pytest.raises(ValueError):
        ClaimTester(EpisodeRunner(), tester.domain, batch=2, max_seeds=16)


def test_outcome_evidence_labels(tester):
    rng = np.random.default_rng(0)
    base = rng.normal(0.5, 0.2, 16)
    better = tester.outcome_evidence(claim(), fake_ab(base + 0.1 + rng.normal(0, 0.01, 16), base))
    worse = tester.outcome_evidence(claim(), fake_ab(base - 0.5, base, t_fail=["battery"] * 16))
    same = tester.outcome_evidence(claim(), fake_ab(base + rng.normal(0, 0.002, 16), base))
    assert (better.label, better.verdict) == (A_BETTER, SUPPORTS)
    assert (worse.label, worse.verdict) == (B_BETTER, CONTRADICTS)
    assert (same.label, same.verdict) == (NO_BENEFIT, CONTRADICTS)
    assert better.conditions == {WH: 200.0}, "only the explored variables identify the point"
    assert worse.details["treatment"]["failures"] == {"battery": 16}
    assert better.n == 16 and better.details["metric"] == "score"


def test_mediator_that_never_moved_contradicts_the_explanation(tester):
    """The effect is real, but the story about why cannot be right."""
    base = np.linspace(0.4, 0.7, 16)
    ab = fake_ab(
        base + 0.06,
        base,
        metrics_t={"time_charge_s": [4000.0 + i for i in range(16)]},
        metrics_c={"time_charge_s": [5200.0 + i for i in range(16)]},
    )
    assert tester.outcome_evidence(claim(), ab).label == A_BETTER

    saturation = Mechanism("it prevents wheel saturation", "failure:wheels", -1)
    verdict = tester.mediator_evidence(saturation, ab)
    assert verdict.verdict == CONTRADICTS and verdict.details["unmoved"] is True
    assert verdict.effect == 0.0

    power = Mechanism("slower wheels draw less power", "time_charge_s", -1)
    supported = tester.mediator_evidence(power, ab)
    assert supported.verdict == SUPPORTS and supported.effect == pytest.approx(1200.0)
    assert supported.details["treatment_mean"] < supported.details["control_mean"]

    wrong_way = tester.mediator_evidence(Mechanism("more charging", "time_charge_s", +1), ab)
    assert wrong_way.verdict == CONTRADICTS and wrong_way.effect == pytest.approx(-1200.0)
    assert tester.mediator_evidence(Mechanism("no prediction"), ab) is None


def test_moderator_evidence_contrasts_the_extreme_levels(tester):
    rng = np.random.default_rng(4)
    base = rng.normal(0.5, 0.2, 16)

    def at(level, effect):
        return fake_ab(
            base + effect + rng.normal(0, 0.005, 16),
            base,
            conditions={WH: 200.0, "max_wheel_speed_rpm": level},
        )

    grows = {1500.0: at(1500.0, 0.0), 3000.0: at(3000.0, 0.03), 6000.0: at(6000.0, 0.08)}
    mechanism = Mechanism("power", moderator="max_wheel_speed_rpm", moderator_direction=1)
    evidence = tester.moderator_evidence(claim(), mechanism, grows)
    assert evidence.verdict == SUPPORTS and evidence.effect == pytest.approx(0.08, abs=0.01)
    assert evidence.details["levels"] == [1500.0, 3000.0, 6000.0]
    assert evidence.details["trend"]["rho"] == pytest.approx(1.0)
    assert evidence.conditions == {WH: 200.0}

    opposite = Mechanism("power", moderator="max_wheel_speed_rpm", moderator_direction=-1)
    assert tester.moderator_evidence(claim(), opposite, grows).verdict == CONTRADICTS
    constant = {1500.0: at(1500.0, 0.05), 6000.0: at(6000.0, 0.05)}
    assert tester.moderator_evidence(claim(), mechanism, constant).verdict == CONTRADICTS
    assert tester.moderator_evidence(claim(), mechanism, {6000.0: at(6000.0, 0.05)}) is None


def test_mechanism_status_is_independent_of_the_outcome_status():
    graph = ClaimGraph()
    root = graph.add(
        claim(
            mechanisms=[
                Mechanism("prevents saturation", "failure:wheels", -1),
                Mechanism("less power", "time_charge_s", -1),
            ]
        )
    )
    graph.record(root.id, outcome(200, A_BETTER))

    def mediator(verdict):
        return Evidence(
            "xp",
            "mediator",
            verdict,
            {WH: 200.0},
            16,
            0.0,
            0.0,
            0.0,
            1.0,
            details={"mediator": "m", "treatment_mean": 0, "control_mean": 0},
        )

    graph.record_mechanism(root.id, 0, mediator(CONTRADICTS))
    graph.record_mechanism(root.id, 1, mediator(SUPPORTS))
    assert root.status == SUPPORTED
    assert [m.status for m in root.mechanisms] == [REFUTED, SUPPORTED]
    assert [e["op"] for e in graph.log].count("mechanism") == 2
    assert "explanation hypothesis -> refuted" in graph.log[-2]["detail"]


# --------------------------------------------------------------------------- hypotheses


def test_claim_from_spec_fills_defaults_and_validates():
    made = claim_from_spec(
        {
            "statement": "Unload the wheels early.",
            "intervention": {"desat_above": 0.3},
            "scope": {WH: [100, None]},
            "context": {WH: 200},
            "mechanisms": [
                {
                    "statement": "less power",
                    "mediator": "time_charge_s",
                    "mediator_direction": -1,
                    "moderator": "max_wheel_speed_rpm",
                    "moderator_direction": 1,
                }
            ],
        }
    )
    assert made.baseline == {"desat_above": 0.6}, "the baseline defaults to the reference setting"
    assert made.scope.bounds[WH] == (100.0, None) and made.origin["context"] == {WH: 200.0}
    assert made.mechanisms[0].moderator == "max_wheel_speed_rpm" and made.status == HYPOTHESIS

    bad = [
        {},
        {"statement": "x"},
        {"statement": "x", "intervention": {"warp": 1}},
        {"statement": "x", "intervention": {"desat_above": 0.3}, "baseline": {"charge_below": 0.1}},
        {"statement": "x", "intervention": {"desat_above": "fast"}},
        {"statement": "x", "intervention": {"desat_above": 0.3}, "scope": {"mood": [0, 1]}},
        {"statement": "x", "intervention": {"desat_above": 0.3}, "scope": {WH: [200, 100]}},
        {"statement": "x", "intervention": {"desat_above": 0.6}},
        {"statement": "x", "intervention": {"desat_above": 0.3}, "mechanisms": [{"mediator": "m"}]},
        {
            "statement": "x",
            "intervention": {"desat_above": 0.3},
            "mechanisms": [{"statement": "s", "moderator": "mood", "moderator_direction": 1}],
        },
        {
            "statement": "x",
            "intervention": {"desat_above": 0.3},
            "mechanisms": [{"statement": "s", "mediator_direction": 5}],
        },
    ]
    for spec in bad:
        with pytest.raises(HypothesisError):
            claim_from_spec(spec)


def test_load_hypotheses_from_the_shipped_study_files():
    for name in ("toy_battery.json", "bsk_battery.json", "bsk_battery_panel.json"):
        config = json.loads((STUDIES / name).read_text())
        claims = [
            claim_from_spec(spec, env_id=config["domain"]["env_id"])
            for spec in config["hypotheses"]
        ]
        assert len(claims) >= 2 and all(c.origin["author"] == "seed (hand-written)" for c in claims)


def test_load_hypotheses_file(tmp_path):
    path = tmp_path / "h.json"
    path.write_text(json.dumps([{"statement": "s", "intervention": {"desat_above": 0.3}}]))
    assert len(load_hypotheses(path)) == 1
    path.write_text(json.dumps({"statement": "s"}))
    with pytest.raises(HypothesisError, match="list"):
        load_hypotheses(path)


def test_llm_proposer_validates_and_attributes_proposals():
    reply = (
        "Thinking...\n```json\n"
        + json.dumps(
            [
                {
                    "statement": "Charge earlier when the battery is small.",
                    "intervention": {"charge_below": 0.4},
                    "scope": {WH: [None, 100]},
                    "mechanisms": [
                        {
                            "statement": "reserve covers the eclipse",
                            "mediator": "min_battery",
                            "mediator_direction": 1,
                        }
                    ],
                },
                {"statement": "Use the warp drive.", "intervention": {"warp": 9}},
            ]
        )
        + "\n```"
    )
    llm = ScriptedLLM(reply, model="test-model")
    domain = Domain(variables={WH: [50, 200]}, env_id="toy-scan")
    graph = ClaimGraph()
    graph.add(claim())
    proposer = LLMProposer(llm, domain, policy_text=scanning_policy().describe(), every=2)

    claims = proposer.propose(graph)
    assert len(claims) == 1 and claims[0].origin["author"] == "llm:test-model"
    assert claims[0].status == HYPOTHESIS and claims[0].env_id == "toy-scan"
    assert "unknown policy parameter" in proposer.rejected[0]["reason"]
    assert proposer.propose(graph) == [] and len(llm.requests) == 1, "asked only every second round"

    request = llm.requests[0]
    assert request.purpose == "propose"
    assert "charge_below = 0.25" in request.system and "failure:wheels" in request.system
    assert "battery_capacity_wh (reference 200); studied at [50.0, 200.0]" in request.system
    assert "Why it came out that way is not known from the outcome alone" in request.system
    assert "A lower charge threshold collects more data." in request.messages[0]["content"]

    assert LLMProposer(ScriptedLLM("no json at all"), domain, policy_text="p").propose(graph) == []


# --------------------------------------------------------------------------- planner


def planner_for(graph, **kw):
    domain = Domain(variables={WH: [25, 50, 100, 200, 400]}, env_id="toy-scan")
    return Planner(graph, domain, **kw), domain


def test_planner_tests_untested_hypotheses_first_at_their_context():
    graph = ClaimGraph()
    a = graph.add(claim())
    b = graph.add(
        claim(
            intervention={"desat_above": 0.3},
            baseline={"desat_above": 0.6},
            origin={"context": {WH: 50.0}},
        )
    )
    planner, _ = planner_for(graph)
    proposals = planner.propose()
    assert [(p.kind, p.root_id) for p in proposals] == [("test", a.id), ("test", b.id)]
    assert proposals[0].conditions[WH] == 200.0, "no stated context: the reference point"
    assert proposals[1].conditions[WH] == 50.0


def test_planner_respects_a_hypothesis_scope_when_choosing_where_to_test():
    graph = ClaimGraph()
    graph.add(claim(scope=Region({WH: (None, 80.0)})))
    planner, _ = planner_for(graph)
    (proposal,) = planner.propose()
    assert proposal.conditions[WH] == 50.0, "the in-scope grid point nearest the reference"

    outside = ClaimGraph()
    outside.add(claim(scope=Region({WH: (1000.0, None)})))
    assert planner_for(outside)[0].propose() == []


def test_planner_bisects_between_disagreeing_neighbours_until_resolved():
    graph = ClaimGraph()
    root = graph.add(claim())
    graph.record(root.id, outcome(200, A_BETTER))
    graph.record(root.id, outcome(50, B_BETTER))
    planner, _ = planner_for(graph, boundary_ratio=1.3, coverage=False)

    probes = []
    for _ in range(10):
        proposals = planner.propose()
        if not proposals:
            break
        assert proposals[0].kind == "boundary"
        value = proposals[0].conditions[WH]
        probes.append(value)
        graph.record(root.id, outcome(value, A_BETTER if value >= 120 else B_BETTER))
    assert probes[0] == 100.0 and probes[1] == 141.0
    assert all(50 < p < 200 for p in probes)
    tested = sorted(e.conditions[WH] for e in root.evidence)
    below = max(t for t in tested if t < 120)
    above = min(t for t in tested if t >= 120)
    assert above / below <= 1.3, "bisection stops once the boundary is located to the chosen ratio"
    narrowed = next(c for c in graph.children(root.id) if c.intervention["charge_below"] == 0.10)
    assert below < narrowed.scope.bounds[WH][0] < above


def test_planner_prioritises_boundary_over_moderator_over_coverage():
    graph = ClaimGraph()
    root = graph.add(
        claim(mechanisms=[Mechanism("power", "time_charge_s", -1, "max_wheel_speed_rpm", 1)])
    )
    graph.record(root.id, outcome(200, A_BETTER))
    planner, domain = planner_for(graph, sweeps={"max_wheel_speed_rpm": [6000, 1500]})

    kinds = [p.kind for p in planner.propose()]
    assert kinds[0] == "moderator" and "coverage" in kinds and "boundary" not in kinds
    moderator = planner.propose()[0]
    assert moderator.levels == [1500, 6000] and moderator.mechanism == 0
    coverage = [p for p in planner.propose() if p.kind == "coverage"]
    assert coverage[0].conditions[WH] == 25.0, "the grid point farthest from anything tested"
    assert len(coverage) <= 2

    graph.record(root.id, outcome(50, B_BETTER))
    assert planner.propose()[0].kind == "boundary"
    planner.skip.add(planner.propose()[0].key(domain))
    assert planner.propose()[0].kind == "moderator"


# --------------------------------------------------------------------------- policy assembly


def graph_with_boundary():
    """Low threshold wins above ~141 Wh and loses below; 0.40 beats 0.25 below ~71 Wh."""
    graph = ClaimGraph()
    low = graph.add(claim())
    for wh, label in ((400, A_BETTER), (200, A_BETTER), (100, B_BETTER), (50, B_BETTER)):
        graph.record(low.id, outcome(wh, label))
    higher = graph.add(
        claim(
            statement="0.40 beats 0.25",
            intervention={"charge_below": 0.40},
            baseline={"charge_below": 0.25},
        )
    )
    for wh, label in ((50, A_BETTER), (100, NO_BENEFIT)):
        graph.record(higher.id, outcome(wh, label))
    desat = graph.add(
        claim(
            statement="desat early",
            intervention={"desat_above": 0.3},
            baseline={"desat_above": 0.6},
        )
    )
    graph.record(desat.id, outcome(200, A_BETTER))
    return graph


def test_recommend_modes():
    graph = graph_with_boundary()
    domain = Domain(variables={WH: [25, 50, 100, 200, 400]}, env_id="toy-scan")

    def settings(wh, mode):
        return recommend(graph, domain.conditions(**{WH: wh}), mode=mode, domain=domain).settings

    assert settings(300, "reference") == {}
    assert settings(300, "conditional") == {"charge_below": 0.10, "desat_above": 0.3}
    assert settings(120, "conditional") == {"desat_above": 0.3}, "0.25 stays: nothing beats it here"
    assert settings(60, "conditional") == {"charge_below": 0.40, "desat_above": 0.3}
    # The flat memory learned "0.10 is better" at the reference point and applies it everywhere.
    assert settings(60, "flat") == {"charge_below": 0.10, "desat_above": 0.3}
    assert settings(300, "flat") == settings(60, "flat")
    # Pooled: one setting for everywhere, from the average effect over all tested points.
    # "0.10 vs 0.25" averages (0.1 + 0.1 - 0.4 - 0.4) / 4 < 0, so 0.25 is kept; "0.40 vs 0.25"
    # averages (0.1 + 0.0) / 2 > 0, so 0.40 is adopted, here and at 300 Wh alike.
    assert settings(60, "pooled") == {"charge_below": 0.40, "desat_above": 0.3}
    assert settings(300, "pooled") == settings(60, "pooled")
    with pytest.raises(ValueError):
        recommend(graph, domain.conditions(), mode="guess")


def test_recommend_chains_and_explains_itself():
    graph = graph_with_boundary()
    further = graph.add(
        claim(
            statement="0.60 beats 0.40",
            intervention={"charge_below": 0.60},
            baseline={"charge_below": 0.40},
        )
    )
    graph.record(further.id, outcome(50, A_BETTER))
    domain = Domain(variables={WH: [25, 50, 100, 200, 400]}, env_id="toy-scan")

    rec = recommend(graph, domain.conditions(**{WH: 50}), domain=domain)
    assert rec.settings["charge_below"] == 0.60, "0.25 -> 0.40 -> 0.60"
    chain = [r for r in rec.reasons if "charge_below" in r["set"]]
    assert [r["set"]["charge_below"] for r in chain] == [0.40, 0.60]
    assert all(r["nearest_support_distance"] == 0 for r in chain)

    far = recommend(graph, domain.conditions(**{WH: 3000}), domain=domain)
    assert far.settings["charge_below"] == 0.10
    distance = next(r for r in far.reasons if "charge_below" in r["set"])[
        "nearest_support_distance"
    ]
    assert distance == pytest.approx(np.log(3000 / 400), abs=0.01)
    cautious = recommend(graph, domain.conditions(**{WH: 3000}), domain=domain, max_distance=1.0)
    assert "charge_below" not in cautious.settings, "refuses to extrapolate that far"


def test_assemble_policy_builds_a_runnable_policy():
    graph = graph_with_boundary()
    domain = Domain(variables={WH: [25, 50, 100, 200, 400]}, env_id="toy-scan")
    policy, rec = assemble_policy(graph, domain.conditions(**{WH: 60}), domain=domain)
    assert policy.params["charge_below"] == 0.40 and policy.params["charge_until"] == 0.40
    assert policy.params["desat_above"] == 0.3 and policy.name == "conditional"
    assert len(rec.reasons) == 2


def test_claims_as_memory_states_scope_footing_and_explanation_status():
    graph = ClaimGraph()
    root = graph.add(
        claim(mechanisms=[Mechanism("less time is spent charging", "time_charge_s", -1)])
    )
    graph.record(root.id, outcome(200, A_BETTER))
    graph.record(root.id, outcome(50, B_BETTER))
    graph.record_mechanism(
        root.id,
        0,
        Evidence(
            "xp",
            "mediator",
            SUPPORTS,
            {WH: 200.0},
            16,
            1.0,
            0.5,
            1.5,
            0.01,
            details={"mediator": "time_charge_s", "treatment_mean": 1, "control_mean": 2},
        ),
    )
    exact = claims_as_memory(graph, {WH: 200.0})
    assert len(exact) == 1 and exact[0].source == "claim"
    assert "battery_capacity_wh >= 100" in exact[0].description
    assert "tested under exactly these conditions" in exact[0].description
    assert "`charge_below` = 0.1 instead of 0.25" in exact[0].content
    assert (
        "Outside the stated range it did not hold (tested at battery_capacity_wh=50)"
        in exact[0].content
    )
    assert "'less time is spent charging' is supported" in exact[0].content

    extrapolated = claims_as_memory(graph, {WH: 800.0})
    assert "treat it as an extrapolation" in extrapolated[0].description
    small = claims_as_memory(graph, {WH: 60.0})
    assert "`charge_below` = 0.25 instead of 0.1" in small[0].content
    assert small[0].title.startswith("Here the opposite of this holds: A lower charge threshold")
    assert "Explanation" not in small[0].content, "the explanation was for the original direction"


# --------------------------------------------------------------------------- experiment runner


def test_runner_caches_and_preserves_order(tmp_path):
    from self_evolving_agents.envs import scan_task

    specs = [EpisodeSpec(scan_task("toy-scan", seed=s), scanning_policy()) for s in (3, 1, 2, 1)]
    with EpisodeRunner(EpisodeCache(tmp_path / "ep.sqlite")) as runner:
        first = runner.run(specs)
        assert runner.episodes_run == 3, "the repeated seed is run once"
        assert first[1].to_dict() == first[3].to_dict()
        again = runner.run(specs)
        assert runner.episodes_run == 3 and [o.to_dict() for o in again] == [
            o.to_dict() for o in first
        ]
        assert runner.episodes_distinct == 3
    with EpisodeRunner(EpisodeCache(tmp_path / "ep.sqlite")) as fresh:
        assert [o.score for o in fresh.run(specs)] == [o.score for o in first]
        assert fresh.episodes_run == 0 and len(fresh.cache) == 3
        assert fresh.episodes_distinct == 3, "counted whether or not they were cached"
    assert specs[0].key != specs[1].key and specs[0].config_key == specs[1].config_key
    other = EpisodeSpec(scan_task("toy-scan", seed=3), scanning_policy(charge_below=0.4))
    assert other.key != specs[0].key


def test_runner_parallel_matches_serial():
    from self_evolving_agents.envs import scan_task

    specs = [
        EpisodeSpec(scan_task("toy-scan", regime, seed=s), scanning_policy())
        for regime in ("nominal", "small_battery")
        for s in range(4)
    ]
    serial = EpisodeRunner().run(specs)
    with EpisodeRunner(workers=2) as parallel:
        assert [o.to_dict() for o in parallel.run(specs)] == [o.to_dict() for o in serial]


# --------------------------------------------------------------------------- the whole loop


@pytest.fixture(scope="module")
def toy_study():
    domain = Domain(variables={WH: [25, 50, 100, 200, 400]}, env_id="toy-scan")
    graph = ClaimGraph()
    config = json.loads((STUDIES / "toy_battery.json").read_text())
    for spec in config["hypotheses"]:
        graph.add(claim_from_spec(spec, env_id="toy-scan"))
    runner = EpisodeRunner()
    tester = ClaimTester(runner, domain, **config["tester"])
    planner = Planner(graph, domain, sweeps=config["sweeps"], **config["planner"])
    events = []
    loop = ActiveLoop(
        graph,
        tester,
        planner,
        budget_episodes=config["budget"],
        per_round=4,
        proposers=[LadderProposer(config["ladders"], env_id="toy-scan")],
        on_event=events.append,
    )
    result = loop.run()
    return graph, domain, runner, tester, loop, result, events


def test_planner_without_boundary_probes_only_works_through_the_grid():
    """The passive design: the same planner with the bisection switched off."""
    domain = Domain(variables={WH: [25, 50, 100, 200, 400]}, env_id="toy-scan")
    graph = ClaimGraph()
    root = graph.add(claim())
    graph.record(root.id, outcome(50, B_BETTER))
    graph.record(root.id, outcome(200, A_BETTER))
    active = {p.kind for p in Planner(graph, domain).propose()}
    passive = Planner(graph, domain, boundaries=False).propose()
    assert "boundary" in active
    assert {p.kind for p in passive} == {"coverage"}
    assert all(p.conditions[WH] in (25.0, 100.0, 400.0) for p in passive)


def test_budget_does_not_depend_on_what_is_cached(tmp_path):
    """A resumed study must stop where an uninterrupted one would."""
    config = json.loads((STUDIES / "toy_battery.json").read_text())

    def study():
        domain = Domain(variables={WH: [25, 50, 100, 200, 400]}, env_id="toy-scan")
        graph = ClaimGraph()
        for spec in config["hypotheses"]:
            graph.add(claim_from_spec(spec, env_id="toy-scan"))
        with EpisodeRunner(EpisodeCache(tmp_path / "ep.sqlite")) as runner:
            tester = ClaimTester(runner, domain, **config["tester"])
            planner = Planner(graph, domain, **config["planner"])
            loop = ActiveLoop(graph, tester, planner, budget_episodes=400, per_round=4)
            result = loop.run()
        return result, [(x["kind"], tuple(x["conditions"].items())) for x in loop.experiments]

    first, experiments = study()
    again, repeated = study()
    assert first["episodes_simulated"] == first["episodes_used"] >= 400
    assert again["episodes_simulated"] == 0 and again["episodes_used"] == first["episodes_used"]
    assert repeated == experiments and len(experiments) > 3


def test_active_loop_runs_to_completion_within_budget(toy_study):
    graph, domain, runner, tester, loop, result, events = toy_study
    assert result["experiments"] == len(loop.experiments) > 10
    assert 0 < result["episodes_used"] <= result["budget"] + 6 * 2 * tester.max_seeds
    assert result["episodes_used"] == result["episodes_simulated"] == runner.episodes_run
    kinds = {x["kind"] for x in loop.experiments}
    assert {"test", "boundary", "coverage", "moderator"} <= kinds
    assert loop.experiments[0]["kind"] == "test"
    keys = [
        (x["kind"] == "moderator", x["family"], tuple(x["conditions"].items()))
        for x in loop.experiments
    ]
    assert len(keys) == len(set(keys)), "no experiment is run twice"
    assert events and all("op" in e for e in events)


def test_active_loop_draws_a_boundary_and_separates_explanations(toy_study):
    graph, domain, *_ = toy_study
    low = next(r for r in graph.roots() if r.intervention == {"charge_below": 0.10})
    assert low.status == SUPERSEDED, "true for big batteries, false for small ones"
    kids = graph.children(low.id)
    assert {tuple(c.intervention.values()) for c in kids} == {(0.10,), (0.25,)}
    narrowed = next(c for c in kids if c.intervention == {"charge_below": 0.10})
    boundary = narrowed.scope.bounds[WH][0]
    assert 50 < boundary < 200
    tested = sorted(e.conditions[WH] for e in low.evidence if e.kind == "outcome")
    assert len([t for t in tested if t not in domain.variables[WH]]) >= 2, (
        "boundary probes were run"
    )

    desat = next(r for r in graph.roots() if "desat_above" in r.intervention)
    statuses = {m.statement: m.status for m in desat.mechanisms}
    assert statuses["it prevents the wheels from reaching their speed limit"] == REFUTED
    assert statuses["slower wheels draw less power, so less time is spent charging"] == SUPPORTED
    kinds = {e.kind for m in desat.mechanisms for e in m.evidence}
    assert kinds == {"mediator", "moderator"}


def test_active_loop_proposers_extend_the_search(toy_study):
    graph, *_ = toy_study
    programmatic = [r for r in graph.roots() if r.origin.get("author") == "program"]
    assert programmatic, "the ladder proposer added comparisons"
    assert {r.origin["rule"] for r in programmatic} <= {"keep-going", "nothing-works-here"}
    assert all(len(r.parameters) == 1 and r.parameters[0] == "charge_below" for r in programmatic)
    pairs = [
        (r.intervention["charge_below"], r.baseline["charge_below"])
        for r in graph.roots()
        if "charge_below" in r.intervention
    ]
    assert len(pairs) == len(set(pairs)), "no comparison is proposed twice"


def test_by_seed_averages_over_conditions():
    from self_evolving_agents.methods.claim_graph.evaluate import by_seed

    # Two conditions, three seeds each, laid out condition by condition.
    assert by_seed([1.0, 2.0, 3.0, 3.0, 4.0, 5.0], 3) == [2.0, 3.0, 4.0]
    with pytest.raises(ValueError, match="whole blocks"):
        by_seed([1.0, 2.0, 3.0], 2)


def test_transfer_evaluation_and_composition_check(toy_study):
    graph, domain, runner, *_ = toy_study
    result = evaluate_transfer(
        runner,
        graph,
        domain,
        [{WH: 35.0}, {WH: 280.0}],
        range(5000, 5012),
        oracle_grid={"charge_below": [0.10, 0.25, 0.40]},
        tuning_seeds=range(6000, 6008),
    )
    assert set(result["overall"]) == {"reference", "flat", "pooled", "conditional", "oracle"}
    assert all(row["episodes"] == 24 for row in result["overall"].values())
    assert set(result["comparisons"]) == {
        "conditional_minus_pooled",
        "conditional_minus_flat",
        "conditional_minus_reference",
        "pooled_minus_reference",
        "flat_minus_reference",
        "oracle_minus_conditional",
    }
    # Two conditions reuse the same twelve seeds: the second interval resamples seeds.
    pooled = result["comparisons"]["conditional_minus_flat"]["score"]
    clustered = result["comparisons"]["conditional_minus_flat"]["score_by_seed"]
    assert (pooled["n"], clustered["n"]) == (24, 12)
    assert clustered["diff"] == pytest.approx(pooled["diff"], abs=1e-6), "the same mean difference"
    assert "failure_rate_by_seed" in result["comparisons"]["conditional_minus_flat"]
    small = result["per_point"][0]["methods"]
    assert (
        small["reference"]["settings"] == {} and small["flat"]["settings"]["charge_below"] == 0.10
    )
    assert small["conditional"]["settings"].get("charge_below") != 0.10
    assert small["conditional"]["claims_applied"]
    assert small["conditional"]["mean_score"] > small["flat"]["mean_score"], (
        "toy check of the wiring"
    )
    with pytest.raises(ValueError, match="tuning_seeds"):
        evaluate_transfer(
            runner,
            graph,
            domain,
            [{WH: 35.0}],
            range(5000, 5004),
            oracle_grid={"charge_below": [0.1]},
        )

    rows = composition_check(runner, graph, domain, [{WH: 280.0}], range(5000, 5012))
    assert rows[0]["finding"] in ("consistent", "unhelpful change", "negative interaction")
    assert set(rows[0]["single_change_means"]) <= {"charge_below", "desat_above"}
    assert rows[0]["best_single_change"] in rows[0]["single_change_means"]
    assert rows[0]["combined_minus_reference"]["n"] == 12
    assert rows[0]["combined_minus_best_single"]["n"] == 12


@pytest.mark.parametrize(
    "scores, finding, unhelpful",
    [
        # (reference, a alone, b alone, both)
        ((0.50, 0.60, 0.55, 0.62), "consistent", []),
        ((0.50, 0.60, 0.55, 0.595), "consistent", []),  # within the tolerance
        ((0.50, 0.60, 0.47, 0.57), "unhelpful change", ["b"]),
        ((0.50, 0.60, 0.55, 0.52), "negative interaction", []),
        ((0.50, 0.60, 0.47, 0.61), "consistent", ["b"]),  # b costs nothing in combination
    ],
)
def test_composition_check_tells_an_unhelpful_change_from_an_interaction(
    monkeypatch, scores, finding, unhelpful
):
    """The verdicts, pinned down with made-up scores in place of a simulator."""
    from types import SimpleNamespace

    from self_evolving_agents.methods.claim_graph import evaluate
    from self_evolving_agents.methods.claim_graph.policy import Recommendation

    reference, a_alone, b_alone, both = scores
    table = {(): reference, ("a",): a_alone, ("b",): b_alone, ("a", "b"): both}

    def fake_run(runner, domain, policy_factory, conditions, settings, seeds):
        base = table[tuple(sorted(settings))]
        return [SimpleNamespace(score=base + 0.001 * (i % 3)) for i, _ in enumerate(seeds)]

    def fake_recommend(graph, conditions, **kwargs):
        return Recommendation(
            settings={"a": 1.0, "b": 2.0}, reasons=[{"set": {"a": 1.0}}, {"set": {"b": 2.0}}]
        )

    def factory(**knobs):
        return None

    factory.defaults = {"a": 0.0, "b": 0.0}
    monkeypatch.setattr(evaluate, "_run", fake_run)
    monkeypatch.setattr(evaluate, "recommend", fake_recommend)
    domain = Domain({WH: [50.0, 200.0]}, env_id="toy-scan")
    (row,) = composition_check(
        None, ClaimGraph(), domain, [{WH: 100.0}], range(8), policy_factory=factory
    )
    assert row["finding"] == finding and row["unhelpful_alone"] == unhelpful
    assert row["best_single_change"] == "a"
    assert row["combined_minus_best_single"]["diff"] == pytest.approx(both - a_alone)
    text = render_report(ClaimGraph(), title="t", composition=[row])
    assert f"| {finding} |" in text
    if finding == "unhelpful change":
        assert "applied where it does not hold" in text and "`b` (+0.471 against +0.501)" in text
    if finding == "negative interaction":
        assert "together they score below the best of them" in text


def test_report_reads_composition_rows_written_before_findings_were_split():
    old = {
        "conditions": {WH: 600.0},
        "combined_minus_reference": {"diff": 0.03, "ci_low": -0.02, "ci_high": 0.09},
        "single_change_means": {"charge_below": 0.9, "desat_above": 0.83},
        "combined_mean": 0.877,
        "reference_mean": 0.843,
        "interaction": "negative",
    }
    text = render_report(ClaimGraph(), title="t", composition=[old])
    assert "| below best single change |" in text
    assert "scores below its best single change" in text


def test_report_renders_every_section(toy_study):
    graph, domain, runner, tester, loop, result, _ = toy_study
    transfer = {
        "held-out": evaluate_transfer(runner, graph, domain, [{WH: 35.0}], range(5000, 5008))
    }
    text = render_report(
        graph,
        title="Toy",
        study=result,
        transfer=transfer,
        composition=composition_check(runner, graph, domain, [{WH: 35.0}], range(5000, 5008)),
    )
    for needle in (
        "# Toy",
        "## Claims by comparison",
        "A lower charge threshold collects more data.",
        "Too general as stated",
        "(reversed)",
        "(narrowed)",
        "Explanations (judged separately",
        "identical in every seed",
        "effect by `max_wheel_speed_rpm`",
        "## Revision history",
        "`specialize`",
        "## Transfer: held-out",
        "| conditional |",
        "conditional minus flat",
        "## Do the recommended settings still work together?",
    ):
        assert needle in text, needle


def test_claim_memory_hands_applicable_claims_to_an_llm_agent(tmp_path):
    """Claims reach the agent's prompt, scoped to the task's conditions, and are traceable."""
    from self_evolving_agents.agents import StepwiseAgent
    from self_evolving_agents.envs import scan_task
    from self_evolving_agents.llm import TrackedLLM
    from self_evolving_agents.methods.stream import EnvJudge, StreamLoop

    graph = ClaimGraph()
    root = graph.add(claim())
    graph.record(root.id, outcome(200, A_BETTER))
    graph.record(root.id, outcome(50, B_BETTER))
    narrowed = next(c for c in graph.children(root.id) if c.intervention["charge_below"] == 0.10)
    reverse = next(c for c in graph.children(root.id) if c.intervention["charge_below"] == 0.25)

    scripted = ScriptedLLM("<think>ok</think><action>charge</action>")
    store = ProvenanceStore()
    memory = ClaimMemory(graph, store=store)
    assert not memory.learns, "the agent's own episodes add nothing to the claims"
    pipeline = StreamLoop(
        StepwiseAgent(TrackedLLM(scripted, store=store)),
        memory=memory,
        judge=EnvJudge(),
        store=store,
    )
    big = pipeline.run_task(scan_task("toy-scan", "nominal", seed=0, duration_s=600.0))
    small = pipeline.run_task(scan_task("toy-scan", "small_battery", seed=0, duration_s=600.0))
    assert big.new_item_ids == [] and len(big.retrieved_item_ids) == 1

    systems = [r.system for r in scripted.requests]
    assert "`charge_below` = 0.1 instead of 0.25" in systems[0]
    assert "`charge_below` = 0.25 instead of 0.1" in systems[-1]
    assert "Applies where battery_capacity_wh >= 100" in systems[0]
    assert (
        "Outside the stated range it did not hold (tested at battery_capacity_wh=50)" in systems[0]
    )

    used = [e["dst"] for e in store.edges(src=big.trajectory_ids[0], relation="used")]
    assert len(used) == 1
    assert store.edges(src=used[0], relation="wasDerivedFrom")[0]["dst"] == narrowed.id
    used_small = [e["dst"] for e in store.edges(src=small.trajectory_ids[0], relation="used")]
    assert store.edges(src=used_small[0], relation="wasDerivedFrom")[0]["dst"] == reverse.id


def test_planner_resolves_each_variable_to_its_own_ratio():
    """Two explored conditions: bisect one finely, leave the other at its grid levels."""
    domain = Domain(variables={WH: [50, 200], "panel_area_m2": [0.1, 0.25]}, env_id="toy-scan")
    graph = ClaimGraph()
    root = graph.add(claim())

    def at(wh, area, label):
        e = outcome(wh, label)
        e.conditions = {WH: float(wh), "panel_area_m2": float(area)}
        e.experiment_id = f"xp_{wh}_{area}"
        return e

    graph.record(root.id, at(200, 0.25, A_BETTER))
    graph.record(root.id, at(50, 0.25, B_BETTER))
    graph.record(root.id, at(200, 0.1, B_BETTER))

    fine = Planner(graph, domain, coverage=False).propose()
    assert {(p.conditions[WH], p.conditions["panel_area_m2"]) for p in fine} == {
        (100.0, 0.25),
        (200.0, 0.158),
    }
    coarse = Planner(
        graph, domain, coverage=False, boundary_ratios={"panel_area_m2": 3.0}
    ).propose()
    assert [(p.conditions[WH], p.conditions["panel_area_m2"]) for p in coarse] == [(100.0, 0.25)]

    kids = graph.children(root.id)
    narrowed = next(c for c in kids if c.intervention == root.intervention)
    assert narrowed.scope.contains({WH: 200.0, "panel_area_m2": 0.25})
    assert not narrowed.scope.contains({WH: 200.0, "panel_area_m2": 0.1})
    assert not narrowed.scope.contains({WH: 50.0, "panel_area_m2": 0.25})
    assert len(narrowed.scope.constrained) == 2, "the scope is a box in both conditions"


def test_figures_are_written(toy_study, tmp_path):
    pytest.importorskip("matplotlib")
    from self_evolving_agents.methods.claim_graph.plots import plot_claims, plot_transfer

    graph, domain, runner, *_ = toy_study
    claims_png = plot_claims(graph, tmp_path / "claims.png", x=WH, x_label="battery capacity (Wh)")
    assert claims_png.stat().st_size > 20_000
    with pytest.raises(ValueError, match="no outcome evidence"):
        plot_claims(graph, tmp_path / "none.png", x=WH, fixed={"panel_area_m2": 9.0})

    transfer = {
        "inside": evaluate_transfer(
            runner, graph, domain, [{WH: 35.0}, {WH: 280.0}], range(5000, 5008)
        ),
        "outside": evaluate_transfer(runner, graph, domain, [{WH: 600.0}], range(5000, 5008)),
    }
    assert plot_transfer(transfer, tmp_path / "transfer.png").stat().st_size > 10_000
