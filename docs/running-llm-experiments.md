# Running the language-model experiments

No real language model has been called by this code yet. Everything that needs one
was written against the reference implementation and the Claude API documentation,
and checked with stand-ins:

| Part | How it was checked | What that does *not* show |
|---|---|---|
| Claude backend (`llm/anthropic_backend.py`) | the real `anthropic` SDK (2.8.0) driven against a local fake server: request shape, absence of removed parameters, reply parsing, refusals, error mapping | that the live API accepts the request |
| Step-by-step agent, policy-writing agent | scripted replies: well-formed, malformed, truncated, refusals, exhausted budget | how a real model responds to these prompts |
| Judge, extractor, MaTTS, best-of-N | scripted replies in the expected formats and in broken ones | judgement quality, extraction quality |
| LLM hypothesis proposer | scripted JSON, valid and invalid | whether a model proposes useful hypotheses |
| Whole pipeline, all modes | `--llm offline-demo`, a rule-based stand-in | anything about whether memory helps |

So expect the first real run to need some prompt tuning. The list at the end says
where to look first.

## Setup

```bash
pip install -e ".[all,dev]"        # or: uv pip install -e ".[all,dev]"
export ANTHROPIC_API_KEY=...       # or `ant auth login`
```

Start with a dry run (free, no credentials) to see what a run produces:

```bash
sea rb run --env toy-scan --regime small_battery --seeds 0:4 --llm offline-demo --out runs/dry
```

```bash
sea rb show runs/dry
```

Then a very small real run with a hard spending cap:

```bash
sea rb run --env bsk-scan --regime small_battery --seeds 0:2 --agent policy --llm anthropic:claude-opus-5-5 --max-cost 1 --out runs/first
```

`--max-cost` stops the run when the locally estimated spend reaches the limit;
`--max-calls` caps uncached calls instead. Re-running the same command into the same
directory replays recorded calls from `llm_cache/` and only pays for what is missing.

The default model is `claude-opus-5-5`. For that model family the backend asks the
API to rerun a declined request on a fallback model (`fallbacks="default"`, beta
`server-side-fallback-2026-07-01`); pass `refusal_fallback=False` to
`AnthropicBackend` to turn it off. Choose the model with `--llm anthropic:<model-id>`
and the thinking depth with `--effort`.

## What a run costs (estimates)

Measured prompt sizes with the stand-in: about 1,400 input tokens per step of the
step-by-step agent on the scanning task, and a three-orbit episode is about 105
steps. With list prices and roughly 150 output tokens per step:

| Agent | Calls per episode | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|---|
| `--agent stepwise` | ~105 + judge + extract | ~$0.03 | ~$0.5 | ~$1 |
| `--agent policy` | 1-3 + judge + extract | < $0.01 | ~$0.03 | ~$0.06 |

These exclude thinking tokens, which are billed as output and depend on `--effort`,
so treat them as lower bounds and let `--max-cost` enforce the limit. DiscoveryWorld
observations are two to four times longer per step.

## Experiment 1: does reasoning memory help on BSK-RL?

A stream of episodes that alternates between two regimes, so that a lesson learned
in one is tempting and wrong in the other. Same seeds in every arm.

```bash
COMMON="--env bsk-scan --regime nominal,small_battery --order interleaved --seeds 0:15 --llm anthropic:claude-opus-5-5 --max-cost 40"
```

```bash
sea rb run $COMMON --memory none --out runs/e1-none
```

```bash
sea rb run $COMMON --memory reasoningbank --out runs/e1-paper
```

```bash
sea rb run $COMMON --memory reasoningbank --retrieval item --condition-weight 0.5 --out runs/e1-item
```

```bash
sea rb run $COMMON --memory none --claims results/bsk-battery --out runs/e1-claims
```

```bash
sea rb run $COMMON --memory reasoningbank --retrieval item --condition-weight 0.5 --claims results/bsk-battery --out runs/e1-both
```

What to read in each `summary.json`:

- `mean_score` and `failures_by_mode` over the stream, and the same split by regime
  from `records.jsonl`. The paper's two metrics map to score/success rate and
  `mean_steps_successful` vs `mean_steps_failed`.
- **Learning curve.** Score against position in the stream. Memory should make later
  episodes better than earlier ones; the no-memory arm should be flat.
- `judge_agreement`: how often the LLM judge matched the simulator's own criterion.
  The paper measured 72.7% on WebArena and found the method robust between 70% and
  90%.
- For the interleaved design specifically: does the paper's top-1 retrieval carry a
  nominal-regime lesson ("a low charge threshold collects more data") into the
  small-battery episodes? The simulator study in `docs/results-bsk-battery.md` shows
  that lesson loses the spacecraft there.

Add `--agent policy` to all arms for a version that costs cents; add
`--scaling parallel --k 3` for MaTTS.

Because the per-episode variation between seeds is large, compare arms seed by seed
(a paired difference), not by their means alone:
`experiments.stats.paired_compare(scores_a, scores_b)`.

## Experiment 2: DiscoveryWorld

```bash
sea rb run --env discoveryworld --scenario "Small Skills: Pick and Place Test;Small Skills: Instrument Measurement Test;Small Skills: Doors with Keys Test" --seeds 0:5 --max-steps 60 --order interleaved --llm anthropic:claude-opus-5-5 --max-cost 30 --out runs/dw-skills
```

Then a discovery theme at Easy difficulty, for example `--scenario "Proteomics"
--difficulty Easy --max-steps 100`. The interesting question is the one raised for
this project: do the items extracted here read like transferable experimental
strategy ("vary one factor at a time", "measure before deciding") or like a
particular task's answer? Retrieval is by task-text similarity, so running one theme
and then another shows what carries over.

Not implemented: DiscoveryWorld's *discovery knowledge* score, which grades the
agent's explanatory notes against the scenario's critical questions with an LLM.
Only task completion and the normalised procedural score are reported.

## Experiment 3: a language model as the hypothesis source

```bash
sea claims study --config studies/bsk_battery.json --out runs/bsk-battery-llm --workers 4 --llm anthropic:claude-opus-5-5
```

Every third round the model is shown the graph and asked for new hypotheses with
checkable mechanisms. Compare the resulting graph and its held-out transfer score
with the ladder-only run in `results/bsk-battery/`. Rejected proposals and the
reasons are kept on the proposer object; the calls are in `provenance.sqlite`.

## Where to look first if a real run misbehaves

1. `sea prov lineage RUN ITEM_ID` and the `llm_calls` table of `provenance.sqlite`
   hold every prompt and reply.
2. **Unparsable actions.** Steps with `info.parse_error` or `info.fallback` in the
   stored trajectories. The agent retries once with the error message, then takes the
   environment's fallback action (`charge`).
3. **A judge that never says success.** The judge prompt resolves uncertainty to
   failure. On the scanning task "a substantial share of the episode" is deliberately
   vague; if agreement with the simulator is poor, tighten `success_doc` in
   `envs/scanning.py` or pass reference statistics to `LLMJudge.judge(reference=...)`.
4. **Memory items that restate the data sheet or give no conditions.** That is the
   extraction prompt's job; see `reasoningbank/prompts.py`.
5. **Cost.** The memory instruction asks the model to discuss every item at every
   step, as in the paper. With many items that is a lot of output; pass a shorter
   `memory_instruction` to `StepwiseAgent`, or use `--agent policy`.
