# Evaluation metrics

Every number reported in this repository is one of the quantities below. Each entry
says what the metric is, how it is computed, which direction is better, why it is
reported, and what it cannot tell you.

Section 9 lists all of them in one table. Section 8 relates them to the two metrics
of the ReasoningBank paper.

## 1. Terms

| Term | Meaning |
|---|---|
| episode | one run of one agent or policy on one task: about three orbits of a simulated spacecraft |
| conditions | the properties of the spacecraft in an episode, e.g. battery capacity in Wh |
| seed | an integer that fixes everything random in an episode: orbit, epoch, initial battery charge, initial buffer fill, initial wheel speeds, disturbance torques |
| method | whatever decides the actions: a rule policy with given settings, or an agent with a given memory |
| held-out | conditions and seeds that no experiment used while the method was being built |

Two methods run on the same conditions and the same seed face exactly the same
situation. Every comparison in this repository is made that way.

All outcome metrics are computed by the simulator. No method sees them, with one
exception that is always marked as a control (`judge=env`).

The metrics are defined for the scanning task (`bsk-scan` on the Basilisk simulator;
`toy-scan` is a fast imitation with the same definitions, used for tests only).
Section 2.6 gives the DiscoveryWorld equivalents.

## 2. Metrics of one episode

### 2.1 Episode score

**Definition.** The fraction of the episode during which data was recorded, minus 1
if the spacecraft was lost.

**Formula.** With episode length T = 17,100 s, `rec_t` the seconds of data recorded
during step t, and `lost` equal to 1 if the spacecraft was lost and 0 otherwise:

```
score = (1/T) · Σ_t rec_t  −  lost
```

It is the sum of the step rewards of BSK-RL's `ScanningTimeReward` with its failure
penalty of −1, unchanged.

**Range and direction.** Higher is better. A surviving episode scores between 0 and
1; a lost one scores between −1 and 0. A negative score always means a lost
spacecraft.

**How to read a value.** 0.60 means data was recorded during 60% of the episode.
A score of 1 cannot be reached: charging, downlinking, unloading the reaction wheels
and turning between modes all take time, and the battery cannot carry the instrument
through every eclipse. In the recorded studies the best setting found by exhaustive
search scores about 0.6 on average over the battery sizes of the first study, and
about 0.35 with a small solar array. Scores should be compared with each other and
with that search, not with 1.

**Why it is reported.** It is the task's own objective: the quantity an agent in
this environment is asked to maximise.

**Limitations.**

1. *It mixes two things at a fixed exchange rate.* Losing the spacecraft costs
   exactly as much as a whole episode of perfect recording earns. That rate is
   BSK-RL's default, not a law. A mission that values the spacecraft more would rank
   cautious policies higher. The share of spacecraft lost (2.2) is therefore always
   reported next to the score.
2. *The mean of the score hides its shape.* Scores cluster in two groups, lost and
   survived. A mean of 0.30 can be "0.30 everywhere" or "0.60 with a fifth of the
   spacecraft lost".
3. *It counts data recorded on board, not data delivered.* Downlinking matters only
   because a full buffer stops recording.
4. *Nothing after the last step counts.* A policy that reaches the time limit with
   an almost empty battery is not penalised for it.
5. *A late loss scores higher than an early one*, since the data recorded before it
   still counts, although both lose the spacecraft.

### 2.2 Spacecraft lost

**Definition.** 1 if the episode ended early because the battery was fully depleted
(mode `battery`) or a reaction wheel exceeded its speed limit (mode `wheels`), 0
otherwise. Files call it `failure`, with the mode as its value.

**Direction.** Lower is better.

**Why it is reported.** A loss cannot be undone, and it is what moves the score
most. Of the 3,001 lost episodes among the 13,120 simulated for the two recorded
studies, 3,000 were battery depletions.

**Limitations.** It is binary: an episode that ended with 1% charge counts the same
as one that never went below 60%. The lowest battery level reached is recorded
separately (2.5).

### 2.3 Success

**Definition.** The spacecraft survived to the time limit *and* recorded data during
at least 20% of the episode (`success_score = 0.2`).

**Direction.** Higher is better.

**Why it exists.** ReasoningBank needs a yes-or-no outcome in two places: its judge
labels each trajectory success or failure, and the paper's headline metric is the
success rate. This is the ground truth that the judge's label is checked against
(7.2), and the label the `judge=env` control uses.

**Limitations.** The 20% threshold was chosen in this repository; it is not part of
BSK-RL. It is not the same as survival: of the surviving episodes simulated for the
one-variable study, 6% recorded less than 20%; of those simulated only for the
two-variable study, which includes a small solar array, 38%. (These counts include
the deliberately poor settings that experiments try.) The claim graph does not use
this metric at all; it works with the score.

### 2.4 Steps

**Definition.** The number of decisions taken in the episode.

**Direction.** None in this task. This is the main difference from the paper, where
a web task ends when the agent answers and fewer steps mean a more efficient agent.
Here an episode lasts a fixed time and a step lasts as long as its mode (scan 180 s,
charge 120 s, downlink or unload 60 s). A surviving episode has between about 95
and 285 steps depending only on the mix of modes (97 to 146 for the rule policies in
the recorded studies); an early loss has few. Fewer steps can therefore mean "scanned
more" or "lost the spacecraft sooner".

**Why it is reported.** For correspondence with the paper, and because for an agent
that calls a model at every step it is the cost of the episode. It is reported for
all, for successful and for failed episodes separately, since the three mean
different things.

### 2.5 Diagnostic quantities

Recorded for every episode. They are not used to rank methods. The claim graph uses
them to test *explanations*: a claim that "a lower charge threshold helps because
less time is spent charging" predicts that `time_charge_s` goes down.

| Name | Meaning |
|---|---|
| `scan_fraction` | share of the episode with data recorded; equals the score of a surviving episode |
| `min_battery` | lowest battery level reached, as a fraction of capacity |
| `max_wheel_speed` | highest reaction-wheel speed reached, as a fraction of the limit |
| `time_scan_s`, `time_charge_s`, `time_downlink_s`, `time_desat_s` | time spent in each mode |
| `wasted_scan_s` | time in scan mode during which nothing was recorded (turning, settling, full buffer) |
| `dark_charge_s` | time in charge mode that began in eclipse, when the panels produce nothing |
| `mode_switches` | number of changes of mode |
| `failure:battery`, `failure:wheels` | 1 if the episode was lost in that way |

Quantities that accumulate over an episode are compared only on seeds where both
arms survived. Otherwise an arm that loses the spacecraft early would show "less
charging" merely because its episodes were shorter.

### 2.6 DiscoveryWorld

| Metric | Definition |
|---|---|
| score | the environment's normalised scorecard, the share of sub-goals reached, between 0 and 1 |
| success | the task was completed and marked as completed successfully |
| failure mode | `wrong_answer` (completed, not successfully) or `incomplete` (step limit reached) |
| steps | actions taken; here fewer steps among completed tasks do mean a more efficient agent |

No experiment reported in this repository uses DiscoveryWorld. The adapter is tested
for its mechanics only.

## 3. Metrics of a set of episodes

A method is evaluated on a set of episodes: every held-out condition with every
held-out seed. For the one-variable study that is 4 conditions × 32 seeds = 128
episodes inside the studied range and 2 × 32 = 64 outside it.

| Metric | Formula | Direction |
|---|---|---|
| **mean score** | mean of the episode scores over the set | higher |
| **spacecraft lost** (files: `failure_rate`) | lost episodes ÷ episodes | lower |
| **success rate** | successful episodes ÷ episodes | higher |
| **mean steps** | mean number of steps; also over successful and over failed episodes | none (2.4) |
| **losses by mode** | count per failure mode | lower |

**Limitations of the mean score over a set.**

- *It depends on which conditions are in the set.* Each condition has the same
  number of seeds and so the same weight. The mean is an average over the conditions
  that were chosen, not over any population of spacecraft. Every report therefore
  also gives the table per condition, and results inside and outside the studied
  range are never averaged together.
- *Small counts.* With 32 seeds per condition one lost spacecraft is 3.1 percentage
  points. An observed share of 0 of 128 is compatible with a true share of up to
  2.8%; 2 of 128 (1.6%) with 0.2% to 5.5%; 25 of 128 (19.5%) with 13% to 27% (exact
  binomial 95% intervals, treating the episodes as independent).

## 4. Comparing two methods

### 4.1 Paired difference

**Definition.** Methods A and B are run on the same set of (conditions, seed) pairs.
For pair i the difference is `d_i = x_i(A) − x_i(B)`, where x is the score (or 1 if
lost, for the share lost). The reported difference is the mean of the `d_i`.

**Direction.** Positive favours A for the score; negative favours A for the share
lost. Reports always name the order ("conditional minus pooled").

**Why paired.** Episodes differ far more by seed (a different orbit, a different
starting charge) than by method. Subtracting within a pair removes that variation,
so much smaller differences can be detected with the same number of episodes.

### 4.2 Interval

A 95% bootstrap percentile interval for the mean difference: the differences are
resampled with replacement 5,000 times and the 2.5th and 97.5th percentiles of the
resampled means are reported. The random generator is seeded, so the same data
always give the same interval.

Two versions are reported for comparisons that span several conditions:

| Version | What is resampled | Assumes |
|---|---|---|
| pooled (files: `score`) | the individual (condition, seed) pairs | the pairs are independent |
| by seed (files: `score_by_seed`) | whole seeds, after averaging each seed's differences over the conditions | the seeds are independent |

Every condition reuses the same seeds, and episodes that share a seed share an orbit
and an initial state, so the pairs are not independent. **The interval by seed is the
one to use.** In the recorded studies it is narrower than the pooled one in most
comparisons, because the pooled version also counts the differences *between
conditions* as noise although the conditions are fixed. The pooled interval is kept
because results recorded before the correction quoted it.

**What the interval covers.** The uncertainty of the mean difference *for these
conditions*, over the seeds that could have been drawn for the evaluation.

**What it does not cover.**

- Other conditions. Nothing is inferred about spacecraft that were not evaluated.
- Another run of the study. Had the experiments drawn other training seeds, the
  method itself (the claim graph) could have come out different. That variability is
  measured separately by replication (5.6).

### 4.3 p-value

A two-sided sign-flip permutation test of the hypothesis "the differences are
symmetric about zero": the signs of the `d_i` are flipped at random 5,000 times, and
p is the share of flipped data sets whose mean is at least as far from zero as the
observed one (counting the observed one). The smallest value it can report is
1/5001 = 0.0002; "p = 0.0002" means no flipped data set was as extreme. If all
differences are identical, the exact sign-test value is used.

### 4.4 Reading several comparisons together

Each evaluation reports six paired comparisons per group of conditions, and no
correction for multiple comparisons is applied. A p-value near 0.05 is weak evidence
here; with a Bonferroni correction for six comparisons the threshold would be 0.008.
Reports give the interval and p for every comparison so that a reader can apply
their own.

A difference is called *distinguishable* when its interval by seed excludes zero,
and *not distinguishable* otherwise. "Not distinguishable" is not "equal": it means
this evaluation could not tell.

## 5. Metrics of the claim graph

The claim graph (`methods/claim_graph`) holds claims of the form "under conditions
C, setting A scores at least `min_effect` better than setting B", tests them in the
simulator, and narrows or splits them. These are its own metrics.

### 5.1 Effect and label of one test

**Definition.** A test runs settings A and B on the same n training seeds at one
point of condition space. Its *effect* is the paired difference in score (4.1), with
an interval at the confidence level of 5.2. Its label follows from the interval
`[low, high]`, the mean and the claim's `min_effect` (0.02 unless stated):

| Label | Rule | Counts as |
|---|---|---|
| intervention better | `low > 0` and `mean ≥ min_effect` | support |
| baseline better | `high < 0` and `mean ≤ −min_effect` | contradiction |
| no meaningful benefit | `high < min_effect` | contradiction: the claimed gain is ruled out, without showing a loss |
| unresolved | anything else | neither |

**Why a minimum effect.** With enough seeds any difference becomes "significant".
0.02 is two percentage points of recording time, a little under two scan steps per
episode. Below that a change of setting is not worth a claim.

**Limitations.** The labels are decisions at a threshold. An effect of 0.019 and one
of 0.021 get different labels from nearly the same evidence. The effect and its
interval are always stored with the label.

### 5.2 Confidence per look

A test starts with 16 seeds and adds 16 at a time, up to 48, stopping as soon as the
label is not "unresolved". Looking at data several times and stopping at the first
decisive look raises the chance of a false finding. To keep the overall two-sided
error rate of one test near 5%, each look uses a stricter level: the Pocock value
for three looks, 0.0221, that is a 97.79% interval per look (files:
`confidence_per_look = 0.9779`).

**Limitation.** This controls the error of *one test*. A study makes many (77 and
157 in the recorded ones), and no correction is applied across them. Some verdicts
are expected to be wrong; replication (5.6) measures how often they disagree.

### 5.3 Status of a claim

Derived from the decisive tests inside the claim's scope, never set by hand.

| Status | Meaning |
|---|---|
| supported | every decisive test inside its scope agreed with it |
| refuted | every decisive test inside its scope disagreed |
| contested | decisive tests inside its scope disagree with each other |
| superseded | replaced by more specific claims that divide its scope |
| hypothesis | no decisive test yet |
| retired | withdrawn because the pooled evidence no longer supports its region; kept so that its counterexamples stay retrievable |

The counts by status describe a graph; they are not a quality score. More supported
claims is not better: a study that splits one claim into five narrow ones has more
supported claims and the same knowledge.

### 5.4 Verdicts on explanations

A claim can carry explanations, each naming a *mediator* (a diagnostic quantity that
should move) and optionally a *moderator* (a condition that should change the size of
the effect).

| Test | Supported if | Contradicted if |
|---|---|---|
| mediator | the mediator moves in the predicted direction (interval excludes zero) in an experiment where the effect appeared | it moves the other way, or is identical in both arms for every seed |
| moderator | the effect differs between the highest and the lowest level of the moderator in the predicted direction | it differs in the other direction, or the difference is confined within ±`min_effect` |

**Limitation.** A mediator test shows that a quantity moved together with the
effect. It does not show that the quantity *caused* the effect. "Supported" here
means "not ruled out by this check", which is weaker than it sounds.

### 5.5 Held-out comparison of ways to use the evidence

The same evidence can be used in different ways. Each is evaluated on the same
held-out conditions and seeds, with the metrics of section 3 and the comparisons of
section 4.

| Name in reports | Settings used at a held-out condition | Role |
|---|---|---|
| `reference` | the untuned policy | the floor |
| `flat` | every change that held at the reference conditions, applied everywhere | what a store of unconditional lessons amounts to |
| `pooled` | the single best setting over all tests, applied everywhere | same evidence as `conditional`, no conditions: isolates the value of conditioning |
| `conditional` | each supported claim applied only inside its scope | the claim graph |
| `oracle` (grid search) | the best of a grid of settings *for that very condition*, chosen on 16 separate tuning seeds | a reference for what was attainable, not a competitor |

Held-out conditions are grouped as **inside the studied range** (between tested
values) and **outside it**, and reported separately. These are what the documents
call interpolation and extrapolation.

**Limitations.**

- The grid search is given what no other method has: experiments at the held-out
  condition itself. A method matching it has lost nothing by generalising. It is not
  an upper bound either: it picks its setting on 16 seeds and can pick wrongly, and
  its grid is finite. `conditional` can score above it.
- All methods choose among settings of one rule policy. The comparison says nothing
  about policies of another form.

### 5.6 Composition finding

Claims are tested one change at a time. At each held-out condition the reference
policy, the assembled policy and each recommended change on its own are run on the
same seeds, and the result is labelled:

| Finding | Rule (`tolerance = 0.01`) |
|---|---|
| consistent | the combination scores at least as well as its best single change, within the tolerance |
| unhelpful change | it scores below its best single change, and at least one change scores below the reference on its own: a claim is being applied where it does not hold |
| negative interaction | it scores below its best single change although every change is at least as good as the reference on its own |

**Limitation.** It is a screen, not a test: it compares means, and the best single
change is picked on the same seeds it is then compared on, which favours it. The
paired interval of "combination minus best single change" is reported next to it.

### 5.7 Run-to-run variability (replication)

**Definition.** The whole study is repeated with different training seeds; every
replicate is evaluated on the same held-out conditions and seeds. Reported over the
replicates:

| Quantity | Meaning |
|---|---|
| mean, sample standard deviation, minimum, maximum of each method's held-out mean score and share lost | how much the outcome of the *procedure* varies |
| the same for each paired difference, and the number of replicates whose own interval excludes zero | whether a conclusion holds in every replicate |
| settings recommended at each held-out condition, by number of replicates | whether the replicates end up recommending the same thing |
| verdict agreement | of the tests that every replicate made at the same conditions, the share on which all replicates reached the same label |

**Why.** The intervals of section 4 take the claim graph as given. Replication is
the only measure here of how much the graph itself depends on chance.

**Limitations.** Five replicates give a rough standard deviation and say nothing
reliable about rare outcomes. The reference policy and the grid search do not depend
on the training seeds; their spread is zero by construction, not a finding.

### 5.8 Cost

| Quantity (file key) | Definition |
|---|---|
| experiments | number of A/B tests made |
| episodes used (`episodes_used`) | distinct simulator episodes those tests needed; does not depend on what was already cached |
| episodes simulated | how many of them had to be run now and were not in the cache; 0 when a recorded study is replayed |
| simulation time (`simulation_core_s`) | sum of the wall-clock time of those episodes on one core, as measured when each was first simulated |
| evaluation episodes | distinct episodes the held-out evaluation needed, the grid search included |

**Direction.** Lower is better at equal result.

**Limitations.** Core-seconds depend on the machine and on what else it was doing.
Episodes are the portable unit. The budget of a study is counted in episodes used.

## 6. Robustness, defined

"Robust" is used in these documents in three specific senses, each tied to a metric:

| Sense | Measured by |
|---|---|
| over evaluation seeds | the interval by seed (4.2) |
| over the training seeds of the study | replication (5.7) |
| over operating conditions | the per-condition table, and the separation of results inside and outside the studied range (5.5) |

## 7. Metrics of the stream methods (methods that need a language model)

These apply to `no_memory`, `reasoningbank`, `matts`, `conditioned_retrieval`,
`policy_program` and `claim_memory`: an agent works through a stream of tasks, and
the methods with memory learn from earlier tasks. **None of these metrics has been
measured with a language model in this repository.** They are defined here because
the comparison protocols report them.

### 7.1 Outcome over a stream

The metrics of section 3 over the tasks of the stream, plus:

| Metric | Definition | Reading |
|---|---|---|
| first-half and second-half mean score | mean score over the first and the second half of the stream | a memory that learns should gain in the second half; the no-memory arm should not. Confounded if the two halves differ in difficulty, which is why streams alternate regimes |
| paired difference against the baseline arm | per task (same position, regime and seed), repeats averaged first; interval and p as in section 4 | positive favours the arm |
| the same within each regime | the paired difference restricted to one regime's tasks | needed when a hypothesis is about one regime |
| per-repeat mean score | the mean score of each repeat of an arm | repeats differ only because the model samples |

**Limitation.** Tasks of a stream are not independent for a method with memory: what
happens at task 5 changes what is retrieved at task 6. The paired interval treats
tasks as independent units and is too narrow by an unknown amount. Repeats of the
whole stream are the honest unit; with three repeats they give a range, not an
interval.

### 7.2 Judge quality

ReasoningBank labels its own trajectories. Because the simulator knows the truth
(2.3), the label can be checked, which the paper could do only on a sample.

| Metric | Definition | Direction |
|---|---|---|
| judge agreement | share of judged tasks where the judge's label equals the simulator's success | higher |
| false success | tasks judged successful that were not | lower |
| false failure | tasks judged failed that were successful | lower |

The two error counts matter differently: a false success turns a failed trajectory
into a lesson about "what worked". With `judge=env` agreement is 1 by construction.

### 7.3 Test-time scaling

With k attempts per task (`matts`):

| Metric | Definition | Uses ground truth to choose? |
|---|---|---|
| mean score (selected attempt) | the score of the attempt the method selected as its answer | no; **this is the method's result** |
| first-attempt mean score, first-attempt success rate | the first attempt only | no; what one attempt would have given |
| best-attempt mean score, any-attempt success rate | the best of the k attempts | **yes**: an upper bound on what selection could reach, not a result of the method |

The paper reports its Best-of-N numbers as the success rate of the selected
trajectory; the first row is the corresponding quantity.

### 7.4 Memory and cost

| Metric | Definition |
|---|---|
| new items | memory items added during the stream |
| model calls, input tokens, output tokens per run | counted by the model layer; replies replayed from the cache are counted as calls but cost nothing |
| estimated cost in USD | tokens × list prices stored in `llm/base.py`; `n/a` if the model's prices are not known there |

**Limitation.** The cost is an estimate from a price table in the code. It is used
for the budget cap, and should be checked against the provider's invoice.

## 8. Relation to the metrics of the ReasoningBank paper

| Paper | Here | Same quantity? |
|---|---|---|
| success rate (SR): share of tasks solved, by the benchmark's own checker | success rate (section 3) | same kind of quantity; the criterion is this repository's (2.3), so values are not comparable with the paper's |
| average steps (AS): mean steps per task, lower is better | mean steps | **not the same meaning**: episodes have a fixed duration here (2.4) |
| — | mean score, spacecraft lost | not in the paper; the primary metrics here, because the task has a graded objective and an irreversible failure |
| judge accuracy (72.7%, measured on a labelled sample) | judge agreement (7.2), over every task | same quantity, measured exhaustively |

No number in this repository should be set beside a number from the paper as if both
measured the same thing. The paper's numbers are quoted only to say what the method
achieved on its own benchmarks.

## 9. All metrics in one table

| Metric | Level | Range | Better | Section |
|---|---|---|---|---|
| episode score | episode | −1 to 1 | higher | 2.1 |
| spacecraft lost, failure mode | episode | 0 or 1 | lower | 2.2 |
| success | episode | 0 or 1 | higher | 2.3 |
| steps | episode | 1 to 285 | none | 2.4 |
| diagnostic quantities | episode | various | not ranked | 2.5 |
| mean score | set | −1 to 1 | higher | 3 |
| share of spacecraft lost | set | 0 to 1 | lower | 3 |
| success rate | set | 0 to 1 | higher | 3 |
| mean steps (all, successful, failed) | set | | none | 3 |
| paired difference, interval, p | comparison | | named order | 4 |
| effect and label of a test | claim test | | | 5.1 |
| confidence per look | claim test | 0.9779 | fixed by design | 5.2 |
| claims by status | claim graph | counts | not ranked | 5.3 |
| mediator and moderator verdicts | explanation | | | 5.4 |
| reference / flat / pooled / conditional / grid search | held-out comparison | | | 5.5 |
| composition finding | held-out condition | three labels | consistent | 5.6 |
| spread over replicates, verdict agreement | procedure | | smaller spread, higher agreement | 5.7 |
| experiments, episodes used, core-seconds | cost | | lower | 5.8 |
| first-half and second-half mean score | stream | −1 to 1 | second above first | 7.1 |
| judge agreement, false success, false failure | stream | | higher, lower, lower | 7.2 |
| selected, first and best attempt | scaling | | | 7.3 |
| new items, model calls, tokens, estimated cost | stream | | lower cost | 7.4 |
