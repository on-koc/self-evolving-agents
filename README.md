# self-evolving-agents

Agents that get better at a simulation by learning from their own runs, with a
record of where every lesson came from.

Two memory layers, on two simulators:

1. **ReasoningBank for simulations.** An adaptation of
   [ReasoningBank](https://arxiv.org/abs/2509.25140) (Ouyang et al., ICLR 2026;
   [reference code](https://github.com/google-research/reasoning-bank)): retrieve
   memory items, act, judge the episode, distil new items from successes *and*
   failures, consolidate. Includes memory-aware test-time scaling (MaTTS).
2. **Conditional claims tested in simulation.** A lesson has to say where it applies,
   survive a matched-seed experiment there, and have its *explanation* checked
   separately from its outcome. When evidence disagrees across conditions, the claim
   is narrowed or reversed and the counterexamples are kept.

Environments: [BSK-RL](https://github.com/AVSLab/bsk_rl) spacecraft tasking on the
Basilisk simulator (nadir scanning with battery, data buffer, reaction wheels and
ground stations) and [DiscoveryWorld](https://github.com/allenai/discoveryworld).
Everything that happens is written to a provenance store.

## What has been verified, and how

| Part | Verified with | Status |
|---|---|---|
| `bsk-scan` adapter, rule policies, experiment runner | real Basilisk 2.12 / BSK-RL 1.3.11 | exact per-seed reproducibility, matched initial conditions, physics sanity check, all in the test suite |
| `discoveryworld` adapter | real DiscoveryWorld 0.0.2 | scripted solutions complete the task on seeds 0-4; oracle scorecard never reaches the agent |
| Claim graph, active experimentation, transfer evaluation | real Basilisk, two studies, about 13,000 episodes | results below and in `results/` |
| Claude backend | the real `anthropic` SDK against a local fake server | request shape and reply handling only; **never called the live API** |
| ReasoningBank loop, MaTTS, LLM agents, LLM hypothesis proposer | scripted stand-ins for the model | mechanics only; **no real language model has run yet** |

So the simulator-side results are real, and the language-model side is implemented
and tested for mechanics but has produced no findings. `docs/running-llm-experiments.md`
has the commands to run it with a key and says where the first real run is most
likely to need tuning.

## Results so far (simulator only)

One study on Basilisk: charging, eclipse and wheel-unloading strategies for
spacecraft with batteries from 25 to 400 Wh. Four hypotheses written by hand, four
more from a simple rule, and 77 matched-seed experiments (2,688 episodes, about an
hour of CPU) chosen by the planner.

- **None of the four hypotheses held as stated; all four are now claims with
  boundaries.** "A lower charge threshold collects more data" is true for the
  reference spacecraft (+0.09 score at 200 Wh) and loses the spacecraft in 16
  episodes of 16 at 71 Wh. The planner found that with its second experiment after
  the claim was first supported, and located both edges with four more.
- **One explanation was refuted although its claim holds.** Unloading the reaction
  wheels early helps almost everywhere, but not by keeping them from their speed
  limit: no wheel was lost in either arm in any seed. It saves power.
- **The result transfers.** On four battery sizes that appear in no experiment, with
  seeds that were never used:

  | | mean score | spacecraft lost |
  |---|---|---|
  | untuned reference policy | +0.305 | 19.5% |
  | lessons from the reference spacecraft, applied everywhere | +0.103 | 43.0% |
  | best single setting given all the evidence | +0.443 | 1.6% |
  | **conditional claims** | **+0.598** | **1.6%** |
  | grid search at each test condition (yardstick) | +0.607 | 0.0% |

  Conditional claims beat the same evidence used without conditions by +0.155 (95%
  interval +0.128 to +0.185) and are within 0.009 of tuning on the test conditions
  themselves (-0.019 to +0.043).

![Held-out scores by method and battery size](results/bsk-battery/transfer.png)

Outside the studied range (18 and 600 Wh) the claims still beat every baseline, but
fall short of tuning (0.377 against 0.479), and one claim was applied past the point
where it holds. `docs/results-bsk-battery.md` has the full account, including what
went wrong and every revision of the decision rules.

A second study varies the solar-array area as well (157 experiments, 5,648 episodes).
The same pattern holds at eight untested combinations inside the studied range, in
two groups of four: conditional claims score +0.348 and +0.452, tuning on the test
conditions +0.347 and +0.457, the same evidence without conditions +0.121 and +0.261.
At two array areas outside the range, where no spacecraft is lost, the unconditional
lessons do slightly better than the claims (0.604 against 0.587). The study also
turned "top up before each eclipse" from a lesson about battery size into one about
battery size and array area: with the small array it helps at one battery size and
costs score on large ones.

## Install

```bash
pip install -e ".[all,dev]"
```

Extras: `bsk` (Basilisk + BSK-RL), `discoveryworld`, `anthropic`, `plots`, `dev`.
Python 3.10 or newer. On first use Basilisk downloads about 116 MB of SPICE kernels
from `naif.jpl.nasa.gov`.

```bash
pytest
```

Tests that need Basilisk or DiscoveryWorld are skipped when those are not installed.

## Try it

A dry run of the whole ReasoningBank loop with a rule-based stand-in for the model
(free, no credentials; it exercises the pipeline and its numbers mean nothing):

```bash
sea rb run --env toy-scan --regime small_battery --seeds 0:4 --llm offline-demo --retrieval item --out runs/dry
```

```bash
sea rb show runs/dry
```

Trace a memory item back to the episode it came from, or forward to the episodes
that used it:

```bash
sea prov lineage runs/dry <item-id>
```

```bash
sea prov lineage runs/dry <item-id> --down
```

Run a rule policy on real Basilisk, no model involved:

```bash
sea policy run --env bsk-scan --regime small_battery --seeds 0:8 --set charge_below=0.4
```

Reproduce the first claim study (about 30 minutes on 4 cores):

```bash
sea claims study --config studies/bsk_battery.json --out runs/bsk-battery --workers 4
```

Ask the resulting graph what it recommends for a spacecraft it has never seen:

```bash
sea claims recommend results/bsk-battery --condition battery_capacity_wh=70
```

With an Anthropic API key, the same loop with a real model:

```bash
sea rb run --env bsk-scan --regime nominal,small_battery --order interleaved --seeds 0:10 --agent policy --llm anthropic:claude-opus-5-5 --max-cost 5 --out runs/first
```

## Documentation

| | |
|---|---|
| `docs/architecture.md` | modules, the environment contract, provenance model |
| `docs/reasoningbank-adaptation.md` | what follows the paper, what was changed and why |
| `docs/claims.md` | the claim layer: evidence, revision, planning, limits |
| `docs/results-bsk-battery.md` | the two Basilisk studies, with interpretation and what went wrong |
| `docs/running-llm-experiments.md` | commands, cost estimates and protocols for the model experiments |

## Layout

```
src/self_evolving_agents/
  envs/           bsk_scan, discoveryworld, toy, shared scanning task definition
  agents/         StepwiseAgent, PolicyProgramAgent, PolicyAgent
  policies.py     JSON rule policies
  llm/            request/response types, tracking wrapper, Claude backend, stand-ins
  reasoningbank/  schema, prompts, bank, judge + extractor, pipeline with MaTTS
  claims/         schema, testing, graph, planner + loop, policy assembly, evaluation
  experiments/    parallel cached episode runner, paired statistics
  provenance/     SQLite store, lineage, PROV-JSON export
studies/          study configurations
results/          compact outputs of studies run on real Basilisk
tests/            212 tests
```

## Limits

- No real language model has been run. Prompt quality, judge accuracy and whether
  memory helps are all open.
- Claims are about parameters of an executable rule policy. Free-text strategies for
  a step-by-step agent (DiscoveryWorld) can be stored and retrieved but not tested by
  the experiment machinery.
- Each claim family is tested against the reference policy, one change at a time;
  interactions are only caught afterwards by a composition check.
- The default embedder measures lexical overlap, not meaning.
- DiscoveryWorld's discovery-knowledge score (LLM-graded) is not implemented.

More in `docs/claims.md` and `docs/running-llm-experiments.md`.

## Attribution

Prompts in `reasoningbank/prompts.py` are adapted from the ReasoningBank reference
implementation (Apache 2.0, Google LLC). See `THIRD_PARTY_NOTICES.md`. This
repository is MIT licensed.
