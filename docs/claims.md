# Conditional claims, tested in simulation

ReasoningBank stores lessons as free text and trusts them once written. This layer
asks more of a lesson before it is acted on: it has to say *where* it applies, it
has to survive a controlled test there, and the reason given for it is checked
separately from whether it works.

The question it is built to answer is the one posed for this project:

> Can an agent build an increasingly reliable, conditional model of which strategies
> work, use it to choose informative experiments, and transfer that knowledge to
> unfamiliar simulation conditions?

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
  | entirely inside (-d, d) | equivalent |
  | anything else | inconclusive |

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
| baseline better or equivalent everywhere tested | root **refuted**; a *reversed* claim is created where the baseline won |
| different answers in different places | root **superseded**; the tested points are partitioned and each region gets its own claim |

Partitioning is a small decision tree over the tested points. It picks the variable
and threshold (the geometric mean of two adjacent tested values) that best separates
the labels, and recurses up to three levels.

- A region where the intervention won keeps the claim, **narrowed** to that region.
- A region where the baseline won gets the **reversed** claim.
- A region where they were equivalent gets no claim: there is nothing to recommend.

As boundary probes come in, existing claims are **re-scoped** in place rather than
replaced, and a claim whose region the evidence no longer supports is **retired**.
Nothing is deleted: a superseded root keeps every test that contradicted it, and each
narrowed claim carries the counterexamples that fixed its boundary. Every change is
written to the revision log and mirrored into the provenance store.

## Choosing the next experiment

`claims.loop.Planner` ranks candidate experiments each round:

1. **test** — a hypothesis nobody has tested, at the context it came from.
2. **boundary** — two tested points on the same line gave different labels: probe
   their geometric midpoint. Repeats until the two sides are within a chosen ratio
   (1.3 by default), i.e. bisection on a log scale.
3. **moderator** — a supported claim has an explanation with a moderator: sweep it.
4. **coverage** — the untested grid point farthest from anything tested for this
   comparison.

Budget is counted in simulator episodes actually run; cached episodes are free.

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

`claims.policy.recommend(graph, conditions)` collects the supported claims whose
scope contains the conditions and chains them per parameter group ("0.40 beats 0.25
here" then "0.60 beats 0.40 here" gives 0.60). It reports, for each claim used, the
distance from the query to the nearest supporting test, so tested ground can be told
from extrapolation; `max_distance` refuses to extrapolate beyond a chosen distance.

For a language-model agent, `claims.report.claims_as_memory` renders the applicable
claims as memory items that state the scope, the nearest supporting test, the known
counterexamples and the status of each explanation. `sea rb run --claims RUN` puts
them in the agent's prompt.

## Evaluating transfer

`claims.evaluate.evaluate_transfer` compares ways of using the same evidence at
conditions that were never part of an experiment, on seeds that were never used:

| Method | What it does |
|---|---|
| `reference` | the untuned policy |
| `flat` | every lesson that held at the reference conditions, applied everywhere: a memory of unconditional lessons |
| `conditional` | the claim graph: a lesson is applied only inside its scope |
| `oracle` | for each test point, the best of a grid of settings chosen on separate tuning seeds: a ceiling |

`composition_check` then verifies that settings supported one at a time still help
when combined, since each family is tested against the reference policy with only its
own change.

## Limits of the current design

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
- **Open-ended scopes are extrapolations.** "battery >= 141 Wh" was tested up to
  400 Wh. The graph says so through the distance it reports, but it does not stop
  anyone from using the claim at 4000 Wh unless `max_distance` is set.
- **Mediation is correlational.** A mediator that moves is consistent with an
  explanation, not proof of it.
