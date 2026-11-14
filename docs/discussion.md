# Effectiveness, failure modes and what to do next

A critical reading of what has been built and measured. Seven questions, each
answered in the same order: what the evidence in this repository shows, what the
ReasoningBank authors report, and what follows only from analysis.

Every paragraph is labelled:

- **Evidence**: measured here. Numbers are from [`comparison.md`](comparison.md),
  Part B, where the files behind them are named.
- **Reported**: stated in the ReasoningBank paper for its own benchmarks; not
  reproduced here.
- **Analysis**: reasoning from how a method works. Not tested.

One fact frames everything below. The claim graph has been measured on a simulator.
No method that needs a language model has been run with one, the ReasoningBank
baseline included. The questions about ReasoningBank can therefore be answered here
only by analysis, and the answers say so.

## 1. How effective is the original ReasoningBank method overall?

**Evidence.** None. This repository contains no measurement of ReasoningBank's
performance in any environment.

What was established is narrower: the implementation follows the published
procedure and prompts, row by row, with the deviations listed in
[`reasoningbank-fidelity.md`](reasoningbank-fidelity.md). That is a statement about
what the code does, not about how well it works.

**Reported.** On WebArena the authors report success rates of 48.8 against 40.5
without memory (Gemini 2.5 Flash), 53.9 against 46.7 (Gemini 2.5 Pro) and 46.3
against 41.7 (Claude 3.7 Sonnet), with fewer steps per task (8.3 against 9.7) and
about 4% more tokens per task; on SWE-Bench-Verified 38.8 against 34.2 and 57.4
against 54.0. Learning from failures as well as successes adds about three points on
one subset (49.7 against 46.5). Retrieving more than one past experience lowers the
success rate (49.7, 46.0, 45.5, 44.4 for one to four).

**Analysis.**

- *The reported gains are consistent and moderate, on benchmarks that suit the
  method.* Every task there has its own query, so "the most similar past task" is
  meaningful, and a strategy that worked on one shopping site plausibly works on
  another.
- *The authors' own ablation points at the weak link.* That more retrieved memory
  hurts suggests retrieval precision, not memory content, limits the method. A
  memory that only grows and is never revised will make this worse over a long
  stream.
- *The published description and the released code are not the same system.* The
  audit found the code differing from the paper in what the extractor is shown (the
  judge's reasoning is appended), in how items are injected (with their
  description), in prompts revised after publication, in the temperature of the
  self-contrast call, and in missing parts (no sequential scaling pipeline, no
  Best-of-N). Anyone reproducing the paper from the code is not running the paper's
  configuration. This repository's baseline follows the paper and offers the code's
  variants as options.
- *In a simulation task family the method's central assumption fails in a specific,
  predictable way.* All episodes of one regime share one query. With identical
  queries every similarity is a tie, the reference code's sort keeps the oldest, and
  with one retrieved experience the agent is given the lessons of its *first*
  episode of that regime for the rest of the stream. Nothing learned later is ever
  retrieved. This follows from the algorithm and is fixed by a test of the
  mechanics; its effect on scores is unmeasured.

So: effective on its own benchmarks by its authors' account; untested here; and
expected, by analysis, to lose much of its benefit on streams of same-query
episodes unless the tie rule is changed.

## 2. How effective are the proposed extensions?

**Evidence, claim graph.** On conditions and seeds that no experiment used:

- Against the untuned policy, inside the studied ranges: +0.27 to +0.32 in mean
  score, and 2% of spacecraft lost instead of about 20%.
- Against the same evidence without conditions (`pooled`): +0.09 to +0.23 inside the
  studied ranges, with an interval that excludes zero in both studies and in all
  five replicates of the first.
- Against tuning on the held-out condition itself: within ±0.015, not
  distinguishable, inside the studied ranges. Outside them it is behind: by 0.10 to
  0.12 in every replicate of study 1, by 0.017 in study 2.
- The scores do not depend much on the draw of training seeds: over five
  replicates of study 1 the held-out mean score is +0.611 with a standard deviation
  of 0.015 inside the range, the ordering reference < `pooled` < `conditional` holds
  in every replicate, and the claim graph is not distinguishable from tuning in any
  of them.
- The content of the graph does depend on the draw: at every held-out condition the
  five replicates recommend at least two different settings, and of 59 tests made by
  all five, 23 do not receive the same label in all of them.
- It costs as many simulator episodes as tuning at 14 (study 1) or 29 (study 2)
  separate conditions.

**Evidence, choosing experiments actively.** No measurable benefit. A fixed
nine-point grid reached the same held-out score as the planner's bisection (+0.003
[−0.003, +0.009] in favour of the planner, inside the range; identical outside it)
with 17% fewer episodes. This was the outcome predicted in the protocol for a single
variable over this range. The case where active selection should pay, several
conditions at once, was not tested.

**Evidence, the other extensions and adaptations.** None. `claim_memory`,
`conditioned_retrieval`, `policy_program` and `matts` have been checked for their
mechanics only.

**Analysis.** The measured result is about claims applied *mechanically*: a rule
policy's parameters are set from the claims. It shows that the knowledge in the
graph is good. It does not show that a language model given the same claims as text
would use them, which is what `claim_memory` needs. Those are different questions,
and only the first has an answer.

The extension is also not a like-for-like alternative to ReasoningBank. It needs a
simulator that can be rerun with a seed, operating conditions that are known
numbers, and strategies that are parameters of an executable policy. ReasoningBank
needs none of these. Where they are available the claim graph offers something
ReasoningBank cannot: lessons that were tested, and a record of where they stop
holding.

## 3. Under which conditions do the methods work particularly well?

**Evidence (claim graph).**

- *Where the right setting changes sign across conditions.* The gain over `pooled`
  is the value of conditioning. It comes from large batteries, where the one safe
  setting gives up a third of the score (0.489 against 0.825 at 280 Wh), and from
  mid-sized ones (0.460 against 0.575 at 70 Wh).
- *Where the default is dangerous.* At 35 Wh the reference policy loses the
  spacecraft in 75% of episodes; the claims bring that to 6%.
- *Inside the range the experiments covered.* Of the twelve held-out conditions
  inside the studied ranges, the claims score at or above tuning at seven, up to
  0.03 below it at three, and clearly below it at two (−0.08 and −0.07). Both of
  those are at 140 Wh, where the graph withholds a setting.
- *Where effects are large compared with the noise between seeds.* 53 of the 76
  outcome tests of study 1 were settled with the first 16 seeds.

**Analysis (ReasoningBank and its adaptations).**

- ReasoningBank should do well where the paper's setting holds: many distinct
  tasks, strategies that stay valid, and a judge that can tell success from the
  record of actions.
- `conditioned_retrieval` should help where regimes alternate and need different
  strategies, and nowhere else.
- `policy_program` should do well where a good strategy is a short rule list. The
  scanning task is such a case by construction.
- MaTTS should help where single attempts often fail and differ from each other.

## 4. Under which conditions do they fail or underperform?

**Evidence (claim graph).**

| Condition | What happened | Size |
|---|---|---|
| Below the smallest battery tested (18 Wh) | the claims stop at a charge threshold of 0.6; tuning finds 0.8 | −0.123 against +0.080; 41% lost against 19% |
| Above the largest battery tested (600 Wh) | a claim with an open-ended scope is applied 1.5 times beyond its last test and no longer holds | −0.022 against the best single change |
| Near a comparison left unresolved (140 Wh) | the graph abstains; tuning and the unconditional lessons both use the lower threshold | 0.636 against 0.718 |
| Where no spacecraft is at risk and lessons carry over (0.4 m² array) | unconditional lessons beat the claims | −0.017 [−0.031, −0.006] |
| Few conditions of interest | tuning each is cheaper | break-even at 14 to 29 conditions |

**Evidence (the controls).** Unconditional lessons (`flat`) fail where the
conditions differ from those the lessons were learned under: in the recorded study
they lose 78% of spacecraft at 70 Wh where the untuned policy loses 3%. Over the
five replicates they lose 30% to 43% inside the range against 19.5%; how much score
that costs depends on which lessons happened to hold for the reference spacecraft
(section 5, point 12). The single best setting (`pooled`) underperforms the untuned
policy on every battery of 140 Wh or more.

**Analysis (ReasoningBank).** It is expected to underperform, possibly below no
memory, on a stream that alternates regimes whose lessons contradict each other,
because a lesson from one regime can be retrieved in the other and nothing in the
item says where it applies. `flat` shows the cost of that mistake when it is made
every time. A language model reading the items may make it less often, since the
task statement includes the spacecraft's data sheet. How often is exactly what is
not known.

## 5. What specific failure modes can be observed?

**Observed in the measured studies.** Each has a number behind it.

1. **Negative transfer of a true lesson.** "A lower charge threshold collects more
   data" holds at 200 Wh (+0.092) and loses 16 spacecraft of 16 at 71 Wh.
2. **Over-caution from pooling.** One setting for all conditions must be safe for
   the worst one, and pays for it everywhere else.
3. **Scopes that outrun their evidence.** A scope is a box around tests that agree.
   Along a variable with no test beyond some point the box is open-ended, and the
   claim was applied at 600 Wh although its effect had already shrunk from +0.057 to
   +0.026 by 400 Wh. With two variables, a box reached across array areas on the
   strength of one test.
4. **Knowledge that ends where the experiments did.** At 18 Wh the step that tuning
   takes (threshold 0.8) had been tested at 25 Wh and left unresolved.
5. **Marginal evidence, applied beyond its test.** Two claims rested on intervals
   that barely excluded zero at 25 Wh (+0.129 [+0.002, +0.306]; +0.024 [+0.001,
   +0.075]). At 18 Wh both changes did nothing. The replication found the two
   effects at 25 Wh again in four and in three of five runs, so they are probably
   real there: what failed was carrying a weak effect to a neighbouring condition.
6. **Abstention with a price.** Declining to recommend on unresolved evidence cost
   0.08 at 140 Wh in study 1 (0.636 against 0.718) and 0.035 at 140 Wh with the
   large array in study 2 (0.792 against 0.827). The first of these was a matter of
   the draw: three of five replicates resolved the neighbouring test and score 0.711
   there.
7. **A guard that costs more than it saves on the data at hand.** The nearest-test
   check lowers the held-out score at the two conditions where it acts.
8. **Right outcome, wrong reason.** Unloading the wheels early helps, but not by
   protecting them: no wheel was lost in either arm of any test. An explanation
   written down from watching episodes would have been wrong here.
9. **Rules revised in the light of results.** The decision rules changed after the
   first pass, and the applicability rule after held-out numbers were visible. Both
   are recorded with before-and-after numbers, and both are still analyst choices.
10. **Selection of the question.** The condition to vary and the hypotheses were
    chosen after an exploratory sweep had shown a reversal. The studies show the
    method finds and bounds reversals that exist. They say nothing about how common
    such reversals are.
11. **Claims that would not be found again.** Of 59 tests made by all five
    replicates, 23 did not receive the same label in all of them, and no held-out
    condition got the same recommendation from all five. One test, next to a
    boundary, was decided in opposite directions. The procedure controls the error
    of each test; it does not make a given claim reproducible.
12. **A headline result at the favourable end of its range.** In the recorded study
    unconditional lessons were worse than none by 0.20. Over five replicates the
    difference ranges from −0.05 to −0.20 and is distinguishable from zero in two.
    Had only the recorded study been run, the harm would have been overstated.
13. **Machinery that did not pay for itself.** The planner's probes between
    disagreeing tests cost 21% more episodes than a fixed grid and bought no
    measurable gain in held-out score.

**Expected by analysis, not observed** (the model-dependent methods):

- retrieval frozen on the first experience when queries repeat (section 1);
- a judge that labels a lost spacecraft correctly, because the episode's end is
  reported, and a low-yield survival incorrectly, because nothing in the action
  history shows how much was recorded;
- lessons that restate the task's data sheet instead of a strategy, since the query
  contains it and the published prompt asks for generalisable insights from one
  trajectory;
- cost that grows with episode length, since the memory instruction is applied at
  every one of about a hundred steps;
- for `claim_memory`, claims phrased as policy parameters that a step-by-step agent
  cannot translate into single actions.

None of these has been seen, because none of these methods has been run.

## 6. What potential improvements can be derived from the results?

Each is tied to the failure it addresses. None has been implemented or tested.

| Improvement | Addresses | Why the results suggest it |
|---|---|---|
| Bound open-ended scopes by the trend of the effect: stop applying a claim where the extrapolated lower bound of its effect falls below the minimum effect | 3 | the effect had shrunk from +0.057 to +0.026 by the last test at 400 Wh, before it failed at 600 |
| Spend unused budget on unresolved comparisons that border a recommendation | 4, 6 | both studies stopped with over 40% of their budget unused while comparisons next to recommended regions were unresolved at 48 seeds |
| Let the reach of a claim depend on the strength of its evidence: a weak effect should not be extended beyond the points where it was tested | 5 | the two claims with the weakest support were the two that did nothing one step outside the tested range, although both were found again at their own test point in most replicates |
| Replace the yes-or-no applicability check by an estimate of the effect at the query condition, from all tests of the comparison | 3, 7 | three hand-written rules differed only at two conditions, and none was clearly right; the information to decide was in the neighbouring effect sizes |
| Make the trade-off between score and loss explicit: separate claims about the probability of loss, with their own threshold | 6 | whether abstaining at 140 Wh is right depends on what a spacecraft is worth, which the score fixes arbitrarily |
| Test each change against the current best policy, not the reference | interactions | changes are tested one at a time; the composition check found nothing significant, in a setting with few interactions |
| Express scopes in variables that carry the mechanism (battery energy relative to the eclipse load) | 3 | the eclipse top-up turned from a lesson about battery size into one about battery size and array area; a single derived variable might cover both |
| Control the false-discovery rate over the whole graph | 5, 11 | 76 and 156 tests at about 5% each |
| Build several graphs from different training seeds and keep what recurs: recommend by majority, and report each claim with the share of graphs that contain it | 11, 12 | the replicates agree on the score and disagree on single claims; an ensemble would give stable recommendations and a measured confidence per claim, at several times the cost |
| Use a fixed grid when one condition varies over a modest range; keep bisection for where a grid is infeasible, and test it there | 13 | the ablation found no benefit of bisection at this scale and a higher cost |
| For ReasoningBank on same-query streams: break ties by recency, or add conditions to the retrieval key | section 1 | follows from the algorithm; both exist here as options and as `conditioned_retrieval`, untested |
| Treat a model's lessons as hypotheses and test them before storing | 1, 8 | the two families meet here: a model proposes, the simulator disposes. `claim_graph` accepts hypotheses from a model; `policy_program` yields strategies that can be rerun |

## 7. What future research questions emerge?

**The ones this work was built to answer and has not.**

1. Does ReasoningBank help a language-model agent on a stream of same-task episodes
   under varying conditions, and does it ever hurt? (Protocol 1, H1 to H4.)
2. Does a language model follow a scoped, tested claim better than its own
   untested lesson? (H6, H7, H8.)
3. Does a model propose better hypotheses than a ladder rule, and at what rate are
   its proposals supported?

**Raised by the measured results.**

4. *How common are reversals?* The studies were built around one. In a broad set of
   task families, what share of lessons learned under one condition reverse under
   another? The answer decides how much conditional memory matters in practice.
5. *How should a memory extrapolate?* Abstain, extend the nearest claim, or follow
   the trend? The three applicability rules and the 600 Wh case show that the choice
   matters and that the data here cannot settle it.
6. *Does choosing experiments actively pay off in higher dimensions?* With one
   variable it did not: a fixed grid did as well with fewer episodes. A fixed grid
   grows exponentially with the number of conditions; bisection between disagreeing
   tests should not. Study 2 used bisection in two dimensions and was not compared
   with a grid.
7. *What is the right price of a loss?* A method that abstains is right or wrong
   depending on it. Results should be reported as a curve over that price, not at
   one value.
8. *How reliable is a claim graph as a whole?* Each test is controlled; the set is
   not. Replication gives an empirical answer for one study. A guarantee over a
   graph that grows sequentially is an open statistical problem.

**Raised by the gap between the two families.**

9. *Can free-text lessons be tested?* The claim graph tests parameters of a rule
   policy. A lesson for a step-by-step agent could be tested by running the agent
   with and without it, at the cost of model calls and with a model's variance
   between runs. How many episodes that takes, and whether a sequential test can
   keep it affordable, is unknown.
10. *What should a text memory do with a contradiction?* ReasoningBank appends.
    The claim graph narrows, splits and supersedes, and keeps the counterexample.
    Whether a language model can perform those operations on its own memory items,
    given a contradicting episode, has not been tried.
11. *Do claims survive a change of simulator?* Fidelity can be treated as one more
    condition. Whether claims tested in a cheap model hold in an expensive one is
    the practical form of the transfer question.
12. *Can a judge without ground truth work in a physical simulation?* The simulator
    knows the truth here, so judge error can be measured exhaustively, and its
    effect isolated by the `judge=env` control (H4).

## Summary

| Question | Answered by evidence here? |
|---|---|
| Is ReasoningBank effective in these environments? | **No.** Not run. |
| Does the baseline follow the paper? | Yes, by audit; equivalence is not claimed |
| Are conditional, tested claims better than unconditional ones? | Yes, for one task family on one simulator, in two studies and across replicates |
| Do they match tuning? | Inside the studied range, yes; outside it, no |
| Is choosing experiments actively better than a grid? | Not at the one scale tested: no difference in score, and the grid was cheaper |
| Do claims help a language-model agent? | **No evidence.** Not run. |
| Do the adaptations improve on ReasoningBank? | **No evidence.** Not run. |
