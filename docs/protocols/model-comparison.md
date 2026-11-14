# Language-model comparison: protocol

**Status: not run.** No language model has been called by any code in this
repository. This document fixes, before any run, what will be compared, on what, with
which metrics, and how each outcome will be read. It was written with no result in
hand.

The comparison is executable as it stands: each protocol below is a file in
`protocols/`, and one command runs all its arms on the same tasks.

## What has been checked without a model

| Part | How | What that does not show |
|---|---|---|
| Claude backend | the official `anthropic` SDK driven against a local stand-in for the API: request shape, reply parsing, refusals, error mapping | that the live API accepts the requests |
| Gemini embedder | the official `google-genai` SDK against a local stand-in | that the live service accepts them |
| Every method | scripted replies in the expected formats and in broken ones; tests per row of the fidelity audit | how a real model responds to the prompts |
| Each protocol | `--llm offline-demo`, a rule-based stand-in, end to end | anything about performance |

So the first real run may need adjustments. Any change made after seeing results has
to be listed with the results (see "Reporting").

## Setup

```bash
pip install -e ".[all,dev]"
```

```bash
export ANTHROPIC_API_KEY=...
```

A dry run of the whole comparison with the stand-in (free; its numbers mean nothing):

```bash
sea compare run --protocol protocols/toy_dry_run.json --out runs/dry-comparison
```

A small real run with a hard cap on spending, to see the prompts work:

```bash
sea run --method reasoningbank --agent policy_program --env bsk-scan --regime small_battery --seeds 0:2 --llm anthropic:claude-opus-5-5 --max-cost 1 --out runs/first
```

`--max-cost` stops a run when the locally estimated spend reaches the limit. Running
the same command again into the same directory replays recorded calls from
`llm_cache/` and pays only for what is missing.

For the Claude 5 family the backend asks the API to rerun a declined request on a
fallback model. Pass `refusal_fallback=False` to `AnthropicBackend` to keep one model
strictly.

## What is held fixed across arms

Within a protocol every arm has the same: task stream (environment, regimes, seeds,
order), agent and its settings, model and effort, embedder, budget cap per run, and
number of repeats. Each arm has its own memory, run directory and call cache. All of
it is written to each run's `config.json`.

Seeds fix the simulator, not the model. Repeats of an arm differ because the model
samples; they do not differ in the tasks.

**The embedder.** The protocols name the offline hashing embedder, which is not the
paper's. For the baseline on these streams the choice cannot change what is
retrieved: all episodes of a regime have the same query, so a same-regime experience
has similarity exactly 1 under any embedder and wins, and the tie among several is
broken by the tie rule, not by the embedder. It does matter for
`conditioned_retrieval`, which ranks single items by their text. A run that is to be
cited as ReasoningBank should set `"embedder": "gemini"` in the protocol (it needs a
Google API key) or state the embedder used.

## Metrics

Defined in [`../metrics.md`](../metrics.md). Primary: mean episode score. Secondary:
share of spacecraft lost, success rate, mean steps (all, successful, failed), judge
agreement with the simulator, and the mean score of the second half of the stream
against the first.

## Analysis

For each arm against the baseline arm: the paired difference per task (same task,
same seed; repeats averaged per task first), its 95% bootstrap interval and a
sign-flip permutation p-value, for score, lost and steps. The same split by regime.
A hypothesis counts as supported when the interval excludes zero in the predicted
direction. Seven comparisons are planned and no correction for multiplicity is
applied; all seven are reported whatever they show.

The number of tasks was chosen for cost, not from a power calculation: the variance
of the paired differences is unknown until the first run. The first run is therefore
exploratory, and should be described as such.

## Protocol 1: memory methods under the paper's agent

`protocols/scan_stepwise.json`. Basilisk scanning task, the reference spacecraft and
a small-battery one (50 Wh) alternating, 10 seeds each, 20 episodes. Step-by-step
agent. Three repeats.

The stream alternates two regimes on purpose: a lesson learned in one is tempting and
wrong in the other. The simulator-only study measured this for policy settings: the
lower charge threshold that helps at 200 Wh loses the spacecraft in every episode at
71 Wh.

| Arm | Method and options | Why it is there |
|---|---|---|
| `no_memory` | `no_memory` | the reference point |
| `reasoningbank` | published defaults | **the baseline** |
| `reasoningbank_newest_on_ties` | `tie_break=newest` | the stream repeats two queries, so ties are constant; see the method's page |
| `reasoningbank_success_only` | `include_failures=false` | the paper's ablation |
| `reasoningbank_env_judge` | `judge=env` | removes judge error; the gap to the baseline is what the judge costs |
| `conditioned_retrieval` | defaults | the retrieval adaptation |
| `claim_memory` | claims from `results/bsk-battery` | tested claims instead of learned items |
| `claim_memory_plus_reasoningbank` | the same, plus a bank | both together |

Hypotheses, stated in advance:

| | Prediction | Read as refuted if |
|---|---|---|
| H1 | `reasoningbank` scores above `no_memory`, mainly in the second half of the stream | the interval includes zero or lies below it |
| H2 | `reasoningbank_newest_on_ties` scores above `reasoningbank` | no difference: the oldest-experience behaviour does no harm on this stream |
| H3 | `reasoningbank` scores above `reasoningbank_success_only` | failures do not help here, unlike in the paper |
| H4 | `reasoningbank_env_judge` scores at least as well as `reasoningbank` | the baseline is clearly better, which would mean judge errors help |
| H5 | `conditioned_retrieval` scores above `reasoningbank`, the gain concentrated in the small-battery regime | no gain, or a gain equal in both regimes |
| H6 | `claim_memory` scores above `no_memory` and loses fewer spacecraft at 50 Wh than `reasoningbank` | the agent does not make use of the claims |
| H7 | `claim_memory_plus_reasoningbank` scores at least as well as the better of its two parts | it is worse than either |

One outcome is predicted as possible and would be a finding, not a fault:
`reasoningbank` scoring *below* `no_memory` in the small-battery regime, if lessons
from the reference spacecraft are retrieved for it.

```bash
sea compare run --protocol protocols/scan_stepwise.json --out runs/scan-stepwise
```

Cost: about 105 model calls per episode, so about 2,100 per run and 50,000 for the
whole protocol. Estimated from prompt sizes measured with the stand-in (about 1,400
input and 150 output tokens per step, before thinking tokens): of the order of a
dollar per episode with Opus 5.5 and a few cents with Haiku 5.5. Treat these as
lower bounds. `--arms` and `--repeats` run a subset.

## Protocol 2: the same comparison under the policy-writing agent

`protocols/scan_policy_agent.json`. Same arms, 15 seeds per regime, 30 episodes, one
model call per episode. Roughly a fiftieth of the cost of protocol 1.

It answers a narrower question: which memory helps an agent that writes one policy
per episode. Its results do not carry over to the paper's agent. In particular the
arm named `reasoningbank` is not the published method here, because an agent without
step-by-step reasoning forces the extractor to be shown observations instead.

The hypotheses are H1 to H7 again, with one addition:

| | Prediction | Read as refuted if |
|---|---|---|
| H8 | claims help this agent more than they help the step-by-step agent, since a claim names a policy parameter and this agent sets parameters | the gain of `claim_memory` over `no_memory` is not larger than in protocol 1 |

```bash
sea compare run --protocol protocols/scan_policy_agent.json --out runs/scan-policy-agent
```

## Protocol 3: test-time scaling

`protocols/scan_scaling.json`. Policy-writing agent, 10 seeds per regime, scaling
factor 3 (the paper's headline uses 5; 3 keeps the cost at three times the baseline).

| Arm | Why |
|---|---|
| `reasoningbank` | the baseline, no scaling |
| `matts_parallel_k3` | the paper's parallel MaTTS |
| `no_aggregation_k3` | the paper's control: scaling without self-contrast |
| `scaling_without_memory_k3` | the paper's control: scaling without memory |
| `restart_k3` | the adaptation that stands in for sequential scaling |
| `no_memory` | the reference point |

| | Prediction (the paper's findings, restated for this setting) | Read as refuted if |
|---|---|---|
| H9 | `matts_parallel_k3` scores above `reasoningbank` | no gain from three attempts |
| H10 | `matts_parallel_k3` scores above `no_aggregation_k3` | self-contrast adds nothing over separate extraction |
| H11 | `scaling_without_memory_k3` gains less over `no_memory` than `matts_parallel_k3` gains over `reasoningbank` | scaling helps as much without memory |

Under scaling the reported score is that of the selected attempt. The first-attempt
score and the best-attempt score are reported next to it; the last uses ground truth
and is an upper bound, not a result of the method.

```bash
sea compare run --protocol protocols/scan_scaling.json --out runs/scan-scaling
```

## A language model as the source of hypotheses

Separate from the protocols above: the claim study with a model proposing hypotheses
every third round, to be compared with the recorded run that used a ladder rule.

```bash
sea claims study --config studies/bsk_battery.json --out runs/bsk-battery-llm --workers 4 --llm anthropic:claude-opus-5-5
```

Prediction: a model proposes comparisons the ladder rule cannot (other parameters,
combinations), some of which are supported, and the held-out score is at least that
of the recorded run. Refuted if its proposals are mostly invalid or redundant.

## Reporting

Whatever the outcome:

- every arm and every hypothesis is reported, including those that fail;
- `comparison.md` and `comparison.json` of each protocol are kept as produced;
- any change to a prompt, a default or a protocol made after the first results is
  listed with the date and the results before and after;
- runs that stopped on the budget cap are reported as incomplete, with the number of
  tasks completed.

## If a real run misbehaves

1. `sea prov lineage RUN ITEM_ID` and the `llm_calls` table of `provenance.sqlite`
   hold every prompt and reply.
2. **Unparsable actions.** Steps with `info.parse_error` or `info.fallback` in the
   stored trajectories. The agent retries once with the error message, then takes the
   environment's fallback action.
3. **A judge that never says success.** Look at `judge_agreement`,
   `judge_false_success` and `judge_false_failure`. The judge sees the action history
   and the final state only; if that is not enough to tell here, that is a finding
   about the published judge in this environment. `history="steps"` on `LLMJudge`
   shows it more.
4. **Memory items that restate the data sheet.** That is the published extraction
   prompt at work on a task whose query contains a data sheet; compare with the
   `conditioned_retrieval` arm.
5. **Cost.** The memory instruction asks the model to discuss every item at every
   step, as in the paper. Use protocol 2 first.
