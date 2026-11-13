# ReasoningBank, its adaptations and extensions: a comparison

Part A compares the methods as designs. Part B compares them by experiment, as far
as experiments have been run.

**How statements are marked.** Three kinds of statement appear here and they are
kept apart:

| Mark | Meaning |
|---|---|
| **Measured** | a number produced by an experiment in this repository, with the files that hold it |
| **Reported by the authors** | a number from the ReasoningBank paper, on its own benchmarks; not reproduced here |
| **Hypothesis** | an expectation that no experiment here has tested |
| **Interpretation** | a reading of measured results that the measurements do not by themselves establish |

**The state of the evidence, in one paragraph.** One method, the claim graph, needs
no language model and has been measured on the Basilisk simulator: two studies, a
five-fold replication and one ablation. Every other method needs a language model.
None has been run with one, because no model access was available for this work.
For those methods Part A is complete, and Part B gives the protocol that would
measure them and nothing else. Nothing in this document should be read as a measured
statement about how ReasoningBank performs in these environments.

Method pages: [`methods/`](methods/README.md). Metrics: [`metrics.md`](metrics.md).
Fidelity of the baseline to the paper: [`reasoningbank-fidelity.md`](reasoningbank-fidelity.md).

---

# Part A. Methodological comparison

## A.1 The methods

| Method | Origin | In one sentence | Needs a language model |
|---|---|---|---|
| `no_memory` | paper (its "No Memory" agent) | the agent meets every task as if it were the first | yes |
| `reasoningbank` | paper | after each task a model distils short lessons from the agent's own trajectory; the lessons of the most similar past task are shown to the agent | yes |
| `matts` | paper (parallel, no-aggregation); adaptation (`restart`) | several attempts per task, contrasted with each other to distil better lessons | yes |
| `conditioned_retrieval` | adaptation | ReasoningBank whose retrieval also compares operating conditions, and whose lessons are asked to state their conditions | yes |
| `policy_program` | adaptation | the model writes one executable rule policy per episode instead of choosing every action | yes |
| `claim_graph` | extension | lessons are conditional claims, each tested by controlled experiments that the method chooses itself | no |
| `claim_memory` | extension | the tested claims are shown to a language-model agent where ReasoningBank would show its lessons | yes |

`reasoningbank` is the baseline. An *adaptation* changes how ReasoningBank is applied
to simulation environments and keeps its idea. An *extension* adds a mechanism the
paper does not have.

## A.2 Core mechanism: what a lesson is and who checks it

| Method | Unit of knowledge | Where it comes from | What validates it | How its range of validity is represented |
|---|---|---|---|---|
| `no_memory` | none | | | |
| `reasoningbank` | memory item: title, one-sentence description, content (free text) | one trajectory of the agent, read by a model | nothing after extraction; the trajectory's label comes from a model acting as judge | not represented; whatever the text says |
| `matts` | the same | k trajectories of one task, contrasted by a model | nothing after extraction | not represented |
| `conditioned_retrieval` | the same, stored with the operating conditions of the episode it came from | one trajectory | nothing after extraction; optional usage statistics | implicitly: the conditions it was *observed* under, used as a similarity term |
| `policy_program` | memory item (as the baseline); the agent's strategy itself is an explicit rule policy | one trajectory | as the baseline | not represented |
| `claim_graph` | claim: "under conditions C, setting A scores at least 0.02 better than setting B", with evidence | a hypothesis (hand-written, from a rule, or from a model) | matched-seed A/B experiments in the simulator, with a sequential test | explicitly: a region of condition space bounded by tests that agree, with the counterexamples outside it |
| `claim_memory` | a claim rendered as a memory item | a finished claim graph | inherited from the claim graph | explicitly, in the item's description |

The dividing line is the fourth column. ReasoningBank and its adaptations *record*
what a model concluded from experience. The claim graph *tests* a statement before
relying on it and stores where the test failed.

## A.3 Memory: construction, storage, retrieval, updating

| Method | Construction | Storage | Retrieval | Updating |
|---|---|---|---|---|
| `reasoningbank` | a judge model labels the trajectory success or failure; an extractor model, with a different prompt for each label, writes at most 3 items from the query and the reasoning and action of each step | append-only list of experiences (query, items, verdict, trajectory ids) with an embedding of the query | embed the new query; cosine similarity to stored queries; all items of the top k = 1 experience; exact ties go to the oldest | append only: nothing is merged, revised or removed |
| `matts` (parallel) | k trajectories under the same memory; one extraction over all of them, unlabelled, at most 5 items | as the baseline; one experience per task | as the baseline | append only |
| `matts` (no aggregation) | k trajectories, each judged and extracted on its own | up to k experiences per task | as the baseline | append only |
| `matts` (`restart`) | k attempts in sequence, each after the agent's notes on the previous ones; one extraction over the series and the notes | one experience per task | as the baseline | append only |
| `conditioned_retrieval` | the baseline's, with two added instructions (state the conditions; mark explanations as hypotheses) and with observations shown to the extractor | the baseline's, plus the episode's operating conditions and, per item, how often it was used and with what outcome | per item, not per experience: relevance = (1 − w) × query similarity + w × similarity of conditions (w = 0.5), a penalty for items similar to ones already chosen, at most 6 items; optional bonus from usage | append; optional duplicate filter; usage statistics updated after every episode |
| `policy_program` | the baseline's; the extractor is shown the policy, its rationale and what happened, since there is no per-step reasoning | as the baseline | as the baseline | append only |
| `claim_graph` | each hypothesis becomes a claim; each claim is tested where the planner chooses | a graph: claims with scope, evidence (effect, interval, seeds, label), explanations with their own verdicts, relations between claims, and a log of every revision | by operating conditions: the supported claims whose scope contains them and whose nearest test agrees | every test can support, refute, split or narrow a claim; superseded claims and all counterexamples are kept |
| `claim_memory` | none during the stream | the claim graph, read-only | as `claim_graph`, at most 8 claims | none (optionally alongside a ReasoningBank that learns as usual) |

Two things follow from the table.

- In ReasoningBank the *task query* is the retrieval key. In the claim methods the
  *operating conditions* are. `conditioned_retrieval` uses both.
- Only the claim graph ever changes what it has stored. Every other method only adds.

## A.4 Acting and reasoning

| Aspect | Step-by-step agent (`no_memory`, `reasoningbank`, `matts`, `conditioned_retrieval`, `claim_memory`) | Policy-writing agent (`policy_program`, or any memory method run with `--agent policy_program`) | `claim_graph` |
|---|---|---|---|
| Who decides each action | the model, once per step, after writing its reasoning | a rule policy the model wrote before the episode | a rule policy with parameters set by the claims |
| How memory enters | items appended to the system prompt, with the published instruction to discuss each item at every step before acting | items in the prompt, with the instruction to discuss each before writing the policy | claims set parameters directly; no text is interpreted |
| Can react to the unforeseen | yes | only as far as its rules anticipate | only as far as the fixed rule structure allows |
| Where the reasoning is | in the model's text at every step | in one rationale, then none | in the statistics: which experiment to run next, and what its interval shows |
| Is the strategy inspectable | no: it is spread over about a hundred decisions | yes: a short rule list | yes: a rule list and the claims behind each parameter |

The claim graph chooses its next experiment by a fixed order of priority: first a
claim not yet tested; then a probe between two neighbouring tests of the same
comparison that disagree; then a sweep over a condition an explanation names; then
the tested point farthest from any other. MaTTS adds two further model calls to the
step-by-step agent's reasoning: one that contrasts the attempts, one that selects
the attempt to report.

## A.5 Computational complexity and overhead

S is the number of steps of an episode (95 to 285 in the scanning task; about 105 is
typical), k the scaling factor, N the number of tasks seen so far. These counts
follow from the code; they are properties of the design, not measurements.

| Method | Model calls per task | Simulator episodes per task | Items added per task | Cost of one retrieval |
|---|---|---|---|---|
| `no_memory` | S | 1 | 0 | none |
| `reasoningbank` | S + 2 (judge, extraction) | 1 | at most 3 | one embedding, N similarities |
| `matts` parallel | k·S + 3 (selection, judge of the selected attempt, one extraction) | k | at most 5 | as the baseline |
| `matts` no aggregation | k·S + 2k + 1 | k | at most 3k | as the baseline |
| `matts` `restart` | k·S + k + 1 | k | at most 3 | as the baseline |
| `conditioned_retrieval` | S + 2, with longer prompts (up to 6 items; observations in the extraction input) | 1 | at most 3 | one embedding, similarities to every stored item, greedy selection |
| `policy_program` | 3 to 5 (policy, up to two repairs, judge, extraction) | 1 | at most 3 | as the baseline |
| `claim_memory` | S + 1 (judge, for the record) | 1, plus the study that built the claims | 0 | a scope check per claim |
| `claim_graph` | 0 | no task stream: 32 to 96 episodes per test (two arms on 16 to 48 seeds) | claims, not items | a scope check per claim |

Further overheads that the table does not show:

- **The published memory instruction is paid at every step.** It asks the model to
  discuss each retrieved item before every action, so the cost of memory grows with
  S, not with the number of tasks.
- **Configuration.** The baseline has 7 options of its own and 5 that reproduce
  details of the reference code. `conditioned_retrieval` adds 7, `matts` 3,
  `claim_memory` 3. The claim graph has its own set (batch size, maximum seeds,
  minimum effect, boundary ratio, depth of the partition, budget). More options mean
  more ways to tune on the test data; the protocols fix all of them in advance.
- **The claim graph's cost is paid before deployment**, in simulator time, and is
  then shared by every later episode. Its measured size is in B.8.

## A.6 Foundations and assumptions

| Method | What it rests on | What it assumes | Where the assumption is weakest in these environments |
|---|---|---|---|
| `reasoningbank` | case-based reasoning by retrieval into the prompt; self-supervision by a model acting as judge | a task is identified by its query; lessons transfer between similar queries; the judge is right often enough; more memory does not hurt | all episodes of one regime share one query, so "most similar" is a tie; a lesson can be right under one set of conditions and dangerous under another |
| `matts` | test-time scaling; contrast between several attempts as a learning signal | attempts differ in informative ways; a model can pick the best attempt without ground truth | attempts differ only by sampling, on the same seed; selection is among attempts at the same episode |
| `conditioned_retrieval` | retrieval conditioned on context | similar conditions call for similar strategies; the conditions a lesson was observed under are those it holds under | false near a boundary; and nothing tests where a lesson stops being true |
| `policy_program` | program synthesis: the strategy as an explicit, executable hypothesis | a fixed rule list can express a good strategy; the model can write one from a description | true for the scanning task by construction; not applicable to DiscoveryWorld |
| `claim_graph` | controlled experiments with common random numbers (matched seeds); group-sequential testing; a piecewise-constant model of where an effect holds; sampling near decision boundaries | the simulator is cheap and repeatable; conditions are known and numeric; strategies are parameters of one policy; the sign of an effect changes at few boundaries | each change is tested alone against the reference policy; interactions are screened only afterwards; explanations are checked by association, not by intervention on the mediator |
| `claim_memory` | giving a model validated, scoped rules instead of its own recollections | the model reads the scope and follows it; a claim about a policy parameter can be turned into behaviour | untested |

None of the methods comes with a guarantee. The claim graph controls the error rate
of each test, not of the set of claims.

## A.7 Advantages and disadvantages

By design. Whether an advantage shows in results is a separate question (Part B).

| Method | Advantages | Disadvantages |
|---|---|---|
| `no_memory` | cheapest; nothing can be mislearned | repeats every mistake |
| `reasoningbank` | no ground truth needed; learns from failures as well as successes; works for any task that can be described in text; minimal machinery | lessons are unverified; no notion of where a lesson applies; never revises or forgets; depends on the judge; retrieval degenerates when queries repeat |
| `matts` | more signal per task; contrast can separate what mattered from what did not | k times the cost; the published sequential form cannot run in episodes that end for good |
| `conditioned_retrieval` | retrieves by the conditions that actually differ between episodes; items carry their conditions | seven untuned switches; still unverified lessons; "observed under" is not "holds under" |
| `policy_program` | about 1/50 of the model calls; strategy is explicit and can be rerun without the model | cannot react beyond its rules; results do not carry over to the step-by-step agent |
| `claim_graph` | every lesson tested, bounded and revisable; counterexamples kept; explanations judged separately from outcomes; abstains where evidence is unresolved; no model needed | needs a simulator and a parameterised policy; cost paid up front; only compares settings someone proposed; scopes are boxes in a few numeric conditions |
| `claim_memory` | brings tested, scoped knowledge to an agent that can also react | knowledge is frozen during the stream; whether a model follows it is unknown; its preparation cost is not comparable with ReasoningBank's zero |

## A.8 When each should do better or worse

Every entry is a **hypothesis**. The identifiers refer to the pre-registered
predictions in [`protocols/model-comparison.md`](protocols/model-comparison.md).

| Method | Expected to do better when | Expected to do worse when | Tested by |
|---|---|---|---|
| `reasoningbank` vs `no_memory` | tasks recur with different queries and stable good strategies; the paper's setting | one query covers episodes that need different strategies; a lesson from one regime is retrieved in another | H1; and the prediction that it may score *below* no memory in the small-battery regime |
| oldest vs newest experience on ties | never by design; it is an artefact of a stable sort | queries repeat exactly, so later experience is never retrieved | H2 |
| learning from failures | failures are informative and the judge recognises them | the judge mislabels failures as successes | H3, H4 |
| `conditioned_retrieval` vs `reasoningbank` | regimes alternate and their lessons differ | conditions do not vary, where it only adds complexity | H5 |
| `claim_memory` vs `reasoningbank` | the conditions of the task were covered by a study; mistakes are costly | conditions lie outside the study, where no claim applies; the task needs behaviour no policy parameter expresses | H6, H7 |
| `policy_program` vs step-by-step | a good strategy is a short rule list; model calls are the binding cost | the situation calls for reactions no rule foresaw | H8 (partly) |
| `matts` vs `reasoningbank` | the first attempt often fails and attempts differ; memory makes the contrast useful | attempts barely differ; the selector cannot tell them apart | H9, H10, H11 |
| `claim_graph` vs tuning at each condition | many conditions will be met; boundaries are few; experiments are cheap | few conditions matter (tuning each is cheaper, B.8); or the conditions lie outside the studied range | **measured**, Part B |
| `claim_graph`, active vs fixed-grid experiments | the range is wide or several conditions vary, so a fixed grid of the same resolution is much larger | one variable over a narrow range | **measured** for the second case only, B.6 |

---

# Part B. Experimental comparison

## B.1 What has been measured

| Comparison | Status | Where |
|---|---|---|
| Ways of using tested evidence on held-out conditions: none, unconditional, single best setting, conditional claims, tuning at each condition | **measured**, two studies | B.3, B.4 |
| Run-to-run variability of the claim graph over training seeds | **measured**, five replicates | B.5 |
| Active against fixed-grid choice of experiments | **measured**, one ablation | B.6 |
| Sensitivity to the rule for when a claim applies, and to the decision rules | **measured** | B.7 |
| Cost of the claim graph against tuning | **measured** | B.8 |
| `reasoningbank` against `no_memory`, its ablations, `conditioned_retrieval`, `claim_memory` | **not measured**; protocol fixed | B.10 |
| The same under the policy-writing agent | **not measured**; protocol fixed | B.10 |
| `matts` against the baseline and its controls | **not measured**; protocol fixed | B.10 |
| A language model as the source of hypotheses for the claim graph | **not measured**; protocol fixed | B.10 |
| Anything on DiscoveryWorld | **not measured** | |

## B.2 Design of the measured comparison, and its fairness

**Task.** BSK-RL nadir scanning on the Basilisk simulator: three orbits, four modes,
a battery, a data buffer and reaction wheels. A strategy is one rule policy with
seven parameters; the *reference* policy has untuned defaults.

**What is compared.** Five ways of choosing the policy's settings for a spacecraft
that no experiment was run on (definitions in [`metrics.md`](metrics.md), 5.5):
`reference`, `flat`, `pooled`, `conditional`, and a grid search at the test
condition itself.

| Held fixed across the five | Value |
|---|---|
| held-out conditions | the same for all |
| held-out seeds | 5000 to 5031, the same 32 for every method and condition |
| policy family | the same rule structure and parameters |
| evidence available to `flat`, `pooled`, `conditional` | the same claim graph, built on training seeds 1000 to 1047 |
| statistics | paired differences on the same (condition, seed) episodes |

**What is not equal, and why it is still reported.**

- The grid search is given experiments at the held-out condition (16 tuning seeds,
  6000 to 6015, for each of 12 settings). No other method has that. It is a reference
  for what was attainable, not a competitor.
- `flat` and `pooled` are derived from the claim graph's own evidence. They are
  controls that remove one property each (conditions; then also multiplicity of
  settings), not independent methods with their own search.
- `flat` is **not ReasoningBank**. It applies, mechanically and everywhere, every
  change that helped at the reference conditions. ReasoningBank shows free-text
  lessons to a model that may or may not follow them. What `flat` measures is the
  cost of applying unconditional lessons; whether a model with ReasoningBank does
  that is the open question of protocol 1.

**Budget.** The studies were limited to 4,500 and 10,000 episodes; neither used its
budget. Evaluation episodes are counted separately (B.8).

## B.3 Study 1: battery capacity (measured)

Files: `results/bsk-battery/`. 77 experiments, 2,688 episodes, 21 claims. Held-out:
35, 70, 140 and 280 Wh inside the studied range (25 to 400 Wh); 18 and 600 Wh
outside it. 32 seeds each.

| Held-out conditions | reference | flat | pooled | conditional | grid search |
|---|---|---|---|---|---|
| inside the range: mean score | +0.305 | +0.103 | +0.443 | +0.598 | +0.607 |
| inside the range: spacecraft lost | 19.5% | 43.0% | 1.6% | 1.6% | 0.0% |
| inside the range: success rate | 78.1% | 57.0% | 93.0% | 97.7% | 95.3% |
| outside the range: mean score | −0.017 | −0.032 | +0.217 | +0.377 | +0.479 |
| outside the range: spacecraft lost | 48.4% | 50.0% | 17.2% | 20.3% | 9.4% |
| outside the range: success rate | 51.6% | 50.0% | 65.6% | 79.7% | 82.8% |

Success means the spacecraft survived and recorded for at least 20% of the episode.
It is the counterpart of the paper's success rate and is shown for that reason; the
grid search tunes for the score, not for this threshold, which is why it can lose no
spacecraft and still have a lower success rate than the claims
([`metrics.md`](metrics.md), 2.3).

Paired differences in mean score, with the 95% interval obtained by resampling
seeds, and the permutation p-value:

| Difference | Inside the range | Outside the range |
|---|---|---|
| conditional − reference | +0.293 [+0.224, +0.357], p = 0.0002 | +0.394 [+0.281, +0.501], p = 0.0002 |
| conditional − flat | +0.495 [+0.427, +0.552], p = 0.0002 | +0.409 [+0.296, +0.519], p = 0.0002 |
| conditional − pooled | +0.155 [+0.133, +0.176], p = 0.0002 | +0.160 [+0.019, +0.299], p = 0.03 |
| pooled − reference | +0.138 [+0.071, +0.201], p = 0.001 | +0.234 [+0.089, +0.371], p = 0.004 |
| flat − reference | −0.202 [−0.270, −0.131], p = 0.0002 | −0.015 [−0.070, +0.027], p = 0.63 |
| grid search − conditional | +0.009 [−0.018, +0.044], p = 0.57 | +0.102 [+0.022, +0.192], p = 0.02 |

Per condition (mean score, share lost):

| Battery (Wh) | reference | flat | pooled | conditional | grid search |
|---|---|---|---|---|---|
| 18 (outside) | −0.877 (97%) | −0.941 (100%) | −0.065 (34%) | −0.123 (41%) | +0.080 (19%) |
| 35 | −0.535 (75%) | −0.762 (94%) | +0.357 (6%) | +0.357 (6%) | +0.348 (0%) |
| 70 | +0.424 (3%) | −0.368 (78%) | +0.460 (0%) | +0.575 (0%) | +0.517 (0%) |
| 140 | +0.584 (0%) | +0.718 (0%) | +0.465 (0%) | +0.636 (0%) | +0.718 (0%) |
| 280 | +0.747 (0%) | +0.825 (0%) | +0.489 (0%) | +0.825 (0%) | +0.846 (0%) |
| 600 (outside) | +0.843 (0%) | +0.877 (0%) | +0.499 (0%) | +0.877 (0%) | +0.878 (0%) |

**Improvements over the reference policy.** Inside the range `conditional` gains
+0.293 in score and loses 18 percentage points fewer spacecraft. `pooled` gains
+0.138 with the same reduction in losses.

**Regressions.**

- `flat` is *worse than the reference* inside the range: −0.202 in score, and 43%
  of spacecraft lost against 19.5%.
- `pooled` is worse than the reference at every battery of 140 Wh and above (for
  example 0.489 against 0.747 at 280 Wh): it buys safety for small batteries with
  score on large ones.
- `conditional` is worse than `flat` and than the grid search at 140 Wh (0.636
  against 0.718), where it abstains on an unresolved comparison.
- `conditional` is worse than `pooled` at 18 Wh (−0.123 against −0.065), below
  anything the study tested.

## B.4 Study 2: battery capacity and solar-array area (measured)

Files: `results/bsk-battery-panel/`. 157 experiments, 5,648 episodes, 35 claims. Ten
held-out conditions in three groups, 32 seeds each.

| Held-out conditions | reference | flat | pooled | conditional | grid search |
|---|---|---|---|---|---|
| untested batteries with the small array (4 conditions) | +0.082 (21%) | −0.093 (46%) | +0.121 (2%) | +0.348 (2%) | +0.347 (2%) |
| array areas between the two studied (4 conditions) | +0.184 (20%) | −0.034 (48%) | +0.261 (2%) | +0.452 (2%) | +0.457 (1%) |
| array areas outside the studied range (2 conditions) | +0.523 (0%) | +0.604 (0%) | +0.387 (0%) | +0.587 (0%) | +0.604 (0%) |

Mean score, with the share of spacecraft lost.

| Success rate | reference | flat | pooled | conditional | grid search |
|---|---|---|---|---|---|
| small array | 52.3% | 52.3% | 27.3% | 64.1% | 58.6% |
| between areas | 68.8% | 52.3% | 63.3% | 92.2% | 73.4% |
| outside | 79.7% | 92.2% | 60.9% | 92.2% | 92.2% |

The success rate separates `pooled` from the rest more sharply than the score does:
with the small array its one safe setting keeps 98% of spacecraft alive and lets only
27% of episodes record for a fifth of the time.

| Difference (interval by seed) | Small array | Between areas | Outside |
|---|---|---|---|
| conditional − reference | +0.265 [+0.220, +0.309] | +0.268 [+0.210, +0.321] | +0.064 [+0.042, +0.084] |
| conditional − flat | +0.441 [+0.395, +0.479] | +0.485 [+0.437, +0.529] | **−0.017 [−0.031, −0.006]** |
| conditional − pooled | +0.226 [+0.204, +0.247] | +0.191 [+0.176, +0.207] | +0.200 [+0.181, +0.218] |
| pooled − reference | +0.039 [−0.005, +0.081] | +0.077 [+0.019, +0.130] | **−0.136 [−0.159, −0.113]** |
| flat − reference | **−0.176 [−0.220, −0.133]** | **−0.217 [−0.278, −0.160]** | +0.081 [+0.061, +0.098] |
| grid search − conditional | −0.001 [−0.027, +0.028] | +0.005 [−0.026, +0.039] | +0.017 [+0.006, +0.031] |

Regressions are in bold. The pattern of study 1 repeats in the first two groups. In
the third group, where no spacecraft is lost by any method, the unconditional
lessons score *above* the claim graph by 0.017: the graph withholds a lower charge
threshold that would have paid off there.

## B.5 Robustness: variability over training seeds (measured)

*Pending: the fifth replicate is still running. This section is filled in from
`results/bsk-battery-replication/` when it has finished.*

## B.6 Ablation: active against fixed-grid experiments (measured)

*Pending: runs after the replication.*

## B.7 Sensitivity to rules that changed during the work (measured)

Two sets of rules were revised while the studies were being analysed. Both versions
of each are recorded, with the held-out numbers before and after.

**Decision rules (study 1).** A first pass used rules under which an inconclusive
comparison did not limit a claim's scope. Three rules were changed after reading its
claim graph and before looking at its held-out scores
(`results/bsk-battery/first-pass/`).

| Conditional method, held-out mean score | First pass | Final |
|---|---|---|
| inside the range | 0.594 | 0.598 |
| outside the range | 0.377 | 0.377 |

**When a claim applies (study 2).** Three rules, the third adopted after held-out
numbers had been seen (`results/bsk-battery-panel/applicability-rules.json`).

| Conditional method, held-out mean score | Scope only | Nearest test in the same region | Nearest test agrees (default) |
|---|---|---|---|
| small array | 0.348 | 0.348 | 0.348 |
| between areas | 0.477 | 0.449 | 0.452 |
| outside | 0.607 | 0.583 | 0.587 |

The default rule scores **lower** than applying claims by scope alone, in two of
three groups. The difference comes from two conditions, both at 140 Wh, where the
check withholds the lower charge threshold. The rule was kept because of what it
guards against (4 spacecraft lost of 48 at the nearest test with that array), not
because the held-out data favour it. They do not.

## B.8 Computational overhead (measured)

| | Study 1 | Study 2 |
|---|---|---|
| experiments | 77 | 157 |
| episodes used by the experiments | 2,688 | 5,648 |
| simulation time, one core | 59 min | 2.6 h |
| share of the episode budget used | 60% | 56% |
| claims produced | 21 | 35 |
| model calls | 0 | 0 |
| episodes for the held-out evaluation, grid search included | 2,368 | 3,968 |

**Against tuning.** The grid search needs 12 settings × 16 tuning seeds = 192
episodes for *each* condition it is asked about. The claim graph's cost is paid once
for the whole range.

| | Study 1 | Study 2 |
|---|---|---|
| episodes of the study ÷ 192 | 14 | 29 |

So the study costs as much as tuning at 14 (or 29) separate conditions. For fewer
conditions than that, tuning each one is cheaper and, inside the range, scores the
same. The claim graph's advantage in cost begins only beyond that number, and it
covers five policy parameters where the grid covers two. Its other products (where
each claim stops holding, which explanations failed) have no counterpart in tuning
and are not priced here.

## B.9 Statistical significance, and what limits it

- **Unit of analysis.** Seeds. Each held-out comparison rests on 32 seeds; the
  intervals in B.3 and B.4 resample those. The earlier, pooled intervals are kept in
  the result files; no conclusion differs between the two except `pooled − reference`
  between array areas in study 2 (pooled interval [−0.008, +0.170], by seed
  [+0.019, +0.130]).
- **Multiplicity.** Six comparisons in each of five groups, 30 in all, and no
  correction. Under a Bonferroni correction (threshold 0.0017) every comparison
  reported with p = 0.0002 would stand. These would not: in study 1 outside the
  range, conditional − pooled (p = 0.03), grid search − conditional (0.02) and
  pooled − reference (0.004); in study 2, pooled − reference with the small array
  (0.09) and between areas (0.01), and the two differences of 0.017 outside the
  range (0.008).
- **Conditions are not a sample.** The held-out conditions were chosen by hand: 16
  in all. Nothing is inferred about other conditions.
- **One simulator, one task, one policy family.**
- **The method's own variability** is covered by B.5 and by nothing else.

## B.10 The comparisons that have not been run

No language model was called. The following are specified in full, run end to end
with a rule-based stand-in for the model (whose numbers mean nothing and are not
quoted), and wait for model access. Hypotheses H1 to H11, metrics, analysis and
reporting rules are fixed in
[`protocols/model-comparison.md`](protocols/model-comparison.md).

| Protocol | Arms | Tasks | Would establish |
|---|---|---|---|
| `protocols/scan_stepwise.json` | `no_memory`; `reasoningbank`; three ablations of it; `conditioned_retrieval`; `claim_memory`; `claim_memory` with a bank | 20 episodes × 3 repeats, two regimes alternating | whether ReasoningBank helps the paper's agent here; whether the adaptation and the extension improve on it |
| `protocols/scan_policy_agent.json` | the same, under the policy-writing agent | 30 episodes × 3 repeats | the same question for a much cheaper agent |
| `protocols/scan_scaling.json` | baseline; parallel MaTTS; its two controls; `restart` | 20 episodes, k = 3 | whether the paper's scaling results hold here |
| claim study with a model proposing hypotheses | one run against the recorded one | | whether a model proposes better comparisons than the ladder rule |

**Reported by the authors**, for orientation only (WebArena, success rate): no memory
40.5, ReasoningBank 48.8 with Gemini 2.5 Flash; 46.5 without failures against 49.7
with them on one subset; parallel MaTTS 49.7 to 55.1 at k = 5. These numbers say
what the method did on web tasks. They are not evidence about this task.

## B.11 Summary of findings

**Measured.**

1. Conditional claims beat the same evidence used without conditions, on every
   group of held-out conditions in both studies (+0.155 to +0.226 in score; intervals
   exclude zero).
2. Unconditional lessons from the reference spacecraft, applied everywhere, are
   worse than no lessons inside the studied ranges (−0.18 to −0.22) and lose two to
   three times as many spacecraft.
3. Inside the studied ranges the claim graph cannot be told apart from tuning on the
   held-out condition itself (differences within ±0.01, intervals include zero).
4. Outside the studied range it falls behind tuning (+0.102 in study 1), and in one
   group of study 2 it falls behind the unconditional lessons (−0.017).
5. The rule that withholds a claim when its nearest test disagrees lowers the
   held-out score where it applies.
6. A study costs as much as tuning at 14 to 29 conditions.

**Interpretation.**

- Findings 1 and 2 together suggest that what matters is *where* a lesson is
  applied, not how many lessons there are. This is the property ReasoningBank's
  items lack by design. It does not follow that ReasoningBank would fail in the same
  way: its lessons are filtered by a model at every step.
- Finding 4 is the expected behaviour of a method that abstains where it has no
  evidence. Whether abstaining is right depends on the cost of a lost spacecraft,
  which the score fixes at one episode of data.

**Hypotheses.** Everything about the six methods that need a language model.
