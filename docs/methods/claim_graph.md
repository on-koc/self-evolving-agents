# Conditional claim graph (extension)

**Origin:** this project. **Code:** `methods/claim_graph/`.
**Evidence in this repository:** evaluated on the Basilisk simulator, with no
language model involved: two studies, a five-fold replication and an ablation of
active experiment selection. See [`../comparison.md`](../comparison.md) and
[`../results-bsk-battery.md`](../results-bsk-battery.md).

## Motivation

ReasoningBank stores lessons as free text and trusts them once written. This method
asks more of a lesson before it is acted on: it has to say *where* it applies, it
has to survive a controlled test there, and the reason given for it is checked
separately from whether it works.

The question it is built to answer is the one posed for this project:

> Can an agent build an increasingly reliable, conditional model of which strategies
> work, use it to choose informative experiments, and transfer that knowledge to
> unfamiliar simulation conditions?

## Differences from the ReasoningBank baseline

| | ReasoningBank | Claim graph |
|---|---|---|
| Unit of memory | a free-text item: title, description, content | a comparative claim: within a scope, this setting beats that one by at least a margin |
| Where it comes from | a model reading one trajectory | a hypothesis (from a person, a rule or a model), then experiments |
| What makes it trusted | being written | a matched-seed experiment whose interval excludes zero |
| Scope | whatever the text says | an explicit region of condition space, drawn around the tests that agree |
| What disagreement does | nothing: items accumulate | the claim is narrowed or reversed, and the counterexamples are kept |
| Explanations | part of the text | separate predictions about measured quantities, tested on their own |
| Choosing what to try next | not part of the method | a planner ranks experiments by what the graph does not yet know |
| What it needs | a language model, and tasks | a simulator that can rerun a seed, and strategies that can be executed |
| What it costs | model calls per task | simulator episodes (thousands), no model calls |

The two are not alternatives for the same job. ReasoningBank works wherever an agent
acts and a model can read the result. The claim graph works only where a strategy is
an executable object and an episode can be repeated exactly. `claim_memory.md`
describes how its output can be given to a language-model agent.

## The unit of memory: a conditional, comparative claim

```
within <scope>, running the policy with <intervention> instead of <baseline>
improves <metric> by at least <min_effect>            [status]
  because <mechanism>                                 [status, judged separately]
```

| Part | Field | Example |
|---|---|---|
| Context and preconditions | `scope` (a box in condition space) | `battery_capacity_wh >= 141` |
| Strategy | `intervention` vs `baseline` (policy parameters) | `charge_below = 0.10` instead of `0.25` |
| Predicted consequence | `metric`, `min_effect` | score up by at least 0.02 |
| Evidence | `evidence[]`, one entry per controlled comparison | effect, interval, p, seeds, failures per arm, conditions |
| Applicability and uncertainty | scope vs. where it was actually tested | distance from a query point to the nearest supporting test |
| Explanation | `mechanisms[]` with a mediator and/or a moderator | "less time is spent charging": `time_charge_s` should fall |
| Relations | `specializes`, `contradicts`, `supersedes`, `requires` | a narrowed claim specialises the over-general one it replaced |

Claims are about *executable* strategies: settings of a rule policy
(`policies.RulePolicy`). That is what makes them testable. The same policy can be
rerun on the same seeds with exactly one thing changed.

## Evidence comes from matched-seed A/B experiments

A test of a claim at a point of condition space runs two policies that differ only
in the claim's parameters, on the same seeds. In BSK-RL a seed fixes the orbit, the
epoch and every initial state, so the per-seed difference isolates the effect of the
change. (Seed-to-seed variation is large: the orbit's inclination itself is random.)

- **Analysis.** Mean paired difference, bootstrap percentile interval, sign-flip
  permutation test (`experiments.stats`). All resampling is seeded.
- **Sequential testing.** Seeds are added in batches (16, 32, 48 by default) until the
  comparison is decisive. The interval at each look is tightened with Pocock's
  boundary (97.8% per look for three looks) so that the overall false-finding rate
  stays near 5%.
- **Reading the interval.** With `d` the minimum effect that matters:

  | Interval for (intervention - baseline) | Label |
  |---|---|
  | entirely above 0 and mean >= d | intervention better |
  | entirely below 0 and mean <= -d | baseline better |
  | upper end below d, and not the case above | no meaningful benefit |
  | anything else | inconclusive: more seeds are added |

  A comparison that is still inconclusive at the largest sample is **unresolved**.
  "No meaningful benefit" counts against the claim without supporting its reverse.

An unsuccessful episode on its own is never evidence for a claim. Only a controlled
comparison is.

## Outcome and explanation are judged separately

Simulator metrics can show that a strategy scored better without showing why. Each
explanation attached to a claim is therefore turned into predictions that are tested
on their own:

- **Mediator test.** The explanation names a measured quantity through which the
  effect is said to flow. Wherever the outcome test succeeded, that quantity is
  compared between the arms. If it did not move, the explanation is contradicted, no
  matter how well the outcome claim is doing. A mediator that is *identical in every
  seed* (for example, zero wheel failures in both arms) is the clearest case: whatever
  produced the benefit, it was not the prevention of something that never happened.
- **Moderator test.** The explanation names a condition that should strengthen or
  weaken the effect. The A/B is repeated at several levels of that condition on the
  same seeds, and the effect at the highest level is contrasted with the effect at
  the lowest, seed by seed.

One trap is handled explicitly. Quantities that accumulate over an episode (seconds
spent charging, mode switches) are compared only on seeds where **both** arms ran to
the time limit. Otherwise an arm that loses the spacecraft early shows "less
charging" merely because its episodes were shorter. Failure-rate mediators use every
seed.

A supported mediator is consistent with the explanation; it does not prove it.
A contradicted one rules it out for those conditions.

## Revision: what happens when evidence disagrees

Claims are grouped into *families*: one comparison studied across condition space.
The family's root holds the pooled evidence. After every new result the family is
revised (`ClaimGraph.revise`):

| Pooled evidence says | Result |
|---|---|
| intervention better everywhere tested | root **supported** |
| no decisive result in its favour anywhere | root **refuted**; a *reversed* claim is created where the baseline won |
| different answers in different places, or established in only part of the scope | root **superseded**; the tested points are partitioned and each region gets its own claim |

Partitioning is a small decision tree over the tested points. It picks the variable
and threshold (the geometric mean of two adjacent tested values) that best separates
the labels, and recurses. Every tested point takes part, including unresolved ones.

- A region where the intervention won keeps the claim, **narrowed** to that region.
- A region where the baseline won gets the **reversed** claim.
- A region with no meaningful benefit gets no claim: there is nothing to recommend.
- A region whose tests stayed unresolved gets no claim either. It is listed as *not
  established*, and is not covered by what its neighbours showed. This is what keeps
  a claim from spreading over conditions where it was looked for and not found.

How many times in a row the space may be split is limited (`max_depth`, three by
default; `"graph": {"max_depth": N}` in a study file). A region that still holds
conflicting results at the limit becomes a **contested** claim, which is never
applied. Three is enough for one variable with a few changes of verdict along it. In
the one-variable Basilisk study it was reached four times along the way, each time
resolved by later experiments; the two-variable study uses eight.

As boundary probes come in, existing claims are **re-scoped** in place rather than
replaced, and a claim whose region the evidence no longer supports is **retired**.
Nothing is deleted: a superseded root keeps every test that contradicted it, and each
narrowed claim carries the counterexamples that fixed its boundary. Every change is
written to the revision log and mirrored into the provenance store.

## Choosing the next experiment

`claim_graph.loop.Planner` ranks candidate experiments each round:

1. **test** — a hypothesis nobody has tested, at the context it came from.
2. **boundary** — two tested points on the same line gave different labels: probe
   their geometric midpoint. Repeats until the two sides are within a chosen ratio
   (1.25 by default, settable per variable), i.e. bisection on a log scale.
   "Unresolved" is a label like any other here, so both edges of an unresolved
   stretch are closed in on. A probe within 3% of an existing test is skipped.
3. **moderator** — a supported claim has an explanation with a moderator: sweep it.
4. **coverage** — the untested grid point farthest from anything tested for this
   comparison.

Whether this ordering beats a plain grid has been tested once, for one condition
variable: it did not. A fixed nine-point grid reached the same held-out score with
17% fewer episodes (`../comparison.md`, B.6). `planner.boundaries=false` switches
the boundary probes off.

The budget is counted in the different simulator episodes the experiments need.
Asking for the same episode again within a study is free (a sequential test re-uses
its first seeds). Episodes found in the on-disk cache are counted like simulated
ones, so a study that is interrupted and resumed stops where an uninterrupted one
would, and a finished study can be replayed from its cache in seconds.

## Where hypotheses come from

Every hypothesis enters the graph in the same form with status `hypothesis`,
whoever wrote it, and its author is recorded.

| Source | Class | Notes |
|---|---|---|
| A person | `load_hypotheses`, the `hypotheses` list of a study file | |
| Coordinate search | `LadderProposer` | *keep going* (a supported step along a ladder of values suggests the next one) and *nothing works here* (both settings fail often at some point, so try one step outward on each side) |
| A language model | `LLMProposer` | Shown the policy, its parameters, the conditions, the measurable quantities and a digest of the graph; asked for hypotheses with checkable mechanisms. Proposals that do not validate are dropped and listed with the reason. Tested here only with a scripted stand-in. |

The model proposes; the simulator decides. No status ever changes because a model
said so.

## Using the graph

`claim_graph.policy.recommend(graph, conditions)` collects the supported claims that apply
at the conditions and chains them per parameter group ("0.40 beats 0.25 here" then
"0.60 beats 0.40 here" gives 0.60). It reports, for each claim used, the distance from
the query to the nearest supporting test, so tested ground can be told from
extrapolation; `max_distance` refuses to extrapolate beyond a chosen distance.

A claim applies when two things hold: its scope contains the conditions, and the
nearest test of its comparison came out the way the claim says. The second condition
matters once there is more than one condition variable. A scope is a box around tests
that agree, and a box can reach across to a level of another variable where the claim
was never tested, past neighbouring tests there that disagree. Requiring the nearest
test to agree stops a result obtained with one solar array from standing in for
another. Along a single variable it never bites, since the bounds are the midpoints
between neighbouring tests. Where box and nearest test disagree, nothing is
recommended.

`claim_graph.policy.policy_map(graph)` tabulates the recommendation for every region
the supported claims tell apart; the study report opens with it.

For a language-model agent, the separate method `claim_memory`
([`claim_memory.md`](claim_memory.md)) renders the applicable claims as memory items
that state the scope, the nearest supporting test, the known counterexamples and the
status of each explanation, and puts them in the agent's prompt.

## Evaluating transfer

`claim_graph.evaluate.evaluate_transfer` compares ways of using the same evidence at
conditions that were never part of an experiment, on seeds that were never used:

| Method | What it does |
|---|---|
| `reference` | the untuned policy |
| `flat` | every lesson that held at the reference conditions, applied everywhere: a memory of unconditional lessons |
| `pooled` | the best single setting given every test in the graph (per comparison, whichever side wins on average), applied everywhere. Same evidence as `conditional`, no conditioning: the control for whether the conditions matter |
| `conditional` | the claim graph: a lesson is applied only inside its scope |
| `oracle` | for each test point, the best of a grid of settings, chosen on separate tuning seeds at that very point. A yardstick, not a ceiling: the grid covers only the parameters it lists |

`composition_check` then looks at whether settings supported one at a time still help
when combined, since each family is tested against the reference policy with only its
own change. On the held-out seeds it runs the reference, each recommended change on
its own, and all of them together, and reports:

| Finding | Meaning |
|---|---|
| consistent | the combination is at least as good as its best single change |
| unhelpful change | the combination is below its best single change, and one of the changes is below the reference on its own: a claim is being applied where it does not hold |
| negative interaction | the combination is below its best single change although every change helps on its own |

These compare means with a tolerance of 0.01 and are a screen, not a test; the paired
interval against the best single change is reported alongside.

## Implementation

| Module | Contents |
|---|---|
| `schema.py` | `Claim`, `Region`, `Evidence`, `Mechanism`; statuses and labels |
| `testing.py` | `Domain`, `ClaimTester`: matched-seed A/B with sequential looks; mediator and moderator tests |
| `graph.py` | `ClaimGraph`: evidence, partition into regions, revision, applicability |
| `loop.py` | `Planner`, `ActiveLoop`, `LadderProposer` |
| `hypotheses.py` | hypotheses from a study file, and `LLMProposer` |
| `policy.py` | `recommend`, `assemble_policy`, `policy_map`; the reference, flat and pooled controls |
| `evaluate.py` | `evaluate_transfer`, `composition_check` |
| `replicate.py` | replication across training seeds; paired comparison of two runs |
| `report.py`, `plots.py` | the Markdown report and the figures |
| `cli.py` | `sea claims study, replicate, compare, evaluate, show, recommend, report, plot` |

It uses the shared episode runner and statistics (`experiments/`), the rule policies
(`policies.py`) and the environments. It imports from no other method folder.

## Parameters

A study is described by a JSON file (`studies/`):

| Key | Meaning | Value in the recorded battery study |
|---|---|---|
| `domain.variables` | the conditions explored and their grid | battery capacity: 25, 50, 100, 200, 400 Wh |
| `hypotheses` | starting claims with their explanations | four, written by hand |
| `ladders` | parameter values the ladder rule may propose steps along | `charge_below`: 0.05 to 0.8 |
| `sweeps` | levels for moderator tests | wheel speed limit: 1500, 3000, 6000 rpm |
| `tester.batch`, `tester.max_seeds` | seeds per look, and at most | 16, 48 |
| `tester.seed_base` | first training seed | 1000 |
| `planner.boundary_ratio` | stop bisecting when two disagreeing tests are this close | 1.3 |
| `planner.boundaries` | probe between disagreeing tests (false: fixed grid only) | true |
| `graph.max_depth` | how deep a family's condition space may be split | 3 (8 in the two-variable study) |
| `budget` | different episodes the experiments may use | 4,500 |
| `evaluation` | held-out conditions, held-out seeds, grid and seeds for the tuned yardstick | six conditions, seeds 5000 to 5031 |

Fixed in code: the smallest effect that counts (0.02 of score), the per-look
confidence (97.79% for three looks), the tolerance of the composition screen (0.01).

## Running it

A study on the toy surrogate (seconds; checks the machinery, says nothing about a
real simulator):

```bash
sea claims study --config studies/toy_battery.json --out runs/toy-claims
```

The recorded battery study on Basilisk (about 30 minutes on four cores):

```bash
sea claims study --config studies/bsk_battery.json --out runs/bsk-battery --workers 4
```

What the recorded graph recommends for a spacecraft it has not seen:

```bash
sea claims recommend results/bsk-battery --condition battery_capacity_wh=70
```

Replication and the ablation are in `../protocols/robustness.md`.

## Limits of the current design

- **Single claims are not stable across runs.** When the first study was repeated
  with other training seeds, the held-out score barely moved (standard deviation
  0.015) but the five graphs recommended different settings at every held-out
  condition, and 23 of 59 tests made by all five did not get the same label in all
  of them (`../comparison.md`, B.5). A graph should be read as one of several nearly
  equivalent sets of recommendations. A claim near a boundary needs replication
  before it is treated as a finding.
- **Active selection is unproven.** See above: no benefit over a grid at the one
  scale tested. Its expected advantage, with several conditions at once, has not
  been measured.
- **One change at a time.** Families are tested against the reference policy. An
  interaction between two recommended settings is only caught afterwards by the
  composition check. Testing against the current best policy instead is supported by
  `ClaimTester.test_claim_at(background=...)` and the `requires` relation, but the
  loop does not use it yet.
- **Axis-aligned scopes.** A boundary that depends on a combination of conditions
  (say, battery energy relative to eclipse load) is approximated by boxes. A
  mechanism-level claim in the right variable would transfer better; nothing here
  discovers such variables.
- **Rule-policy strategies only.** Claims are about parameters of an executable
  policy. Free-text strategies for a step-by-step language-model agent (as in
  DiscoveryWorld) can be stored but not tested by this machinery. Testing them would
  mean A/B runs of the agent with and without the claim in its prompt, which costs
  model calls rather than simulator time.
- **Open-ended scopes are extrapolations.** "battery >= 28.5 Wh" for early wheel
  unloading was tested up to 400 Wh. The graph says so through the distance it
  reports, but nothing stops the claim being used at 600 Wh, and in the Basilisk
  study it did not hold there (`../results-bsk-battery.md`). `max_distance` refuses any
  claim beyond a chosen distance; that would also have refused a claim that did keep
  holding at 600 Wh. The effect sizes were already shrinking towards the edge, and
  using that trend is the obvious next step.
- **Mediation is correlational.** A mediator that moves is consistent with an
  explanation, not proof of it.
