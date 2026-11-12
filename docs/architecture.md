# Architecture

```
                        ┌──────────────────────────────────────────────┐
                        │  envs/        simulators as text + features  │
                        │   bsk_scan  (Basilisk via BSK-RL)            │
                        │   discoveryworld                             │
                        │   toy  (analytic surrogate, tests only)      │
                        └───────────────┬──────────────────────────────┘
                                        │ Observation / StepResult / Outcome
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
┌───────▼────────┐             ┌────────▼────────┐             ┌────────▼────────┐
│ agents/        │             │ policies.py     │             │ experiments/    │
│  StepwiseAgent │  writes     │  RulePolicy     │  executes   │  EpisodeRunner  │
│  PolicyProgram ├────────────►│  (JSON rules,   │◄────────────┤  (parallel,     │
│  PolicyAgent   │             │   named knobs)  │             │   cached)       │
└───────┬────────┘             └─────────────────┘             │  stats (paired) │
        │ Trajectory                                           └────────┬────────┘
┌───────▼─────────────────────────┐                    ┌────────────────▼─────────────────┐
│ reasoningbank/                  │                    │ claims/                          │
│  retrieve → act → judge →       │   claims rendered  │  Claim, Region, Evidence,        │
│  extract → consolidate          │◄───as memory───────┤  Mechanism                       │
│  MaTTS parallel / sequential    │                    │  ClaimTester (matched-seed A/B)  │
│  ReasoningBank (bank.jsonl)     │                    │  ClaimGraph (partition, revise)  │
└───────┬─────────────────────────┘                    │  Planner, ActiveLoop, proposers  │
        │                                              │  recommend, evaluate_transfer    │
        │                                              └────────────────┬─────────────────┘
        │              ┌──────────────────────────────────┐             │
        └─────────────►│ provenance/  SQLite graph, PROV  │◄────────────┘
                       └──────────────────────────────────┘
        llm/   LLMRequest → backend (Claude | scripted | offline-demo), wrapped by
               TrackedLLM: disk cache, budget guard, every call logged to provenance
```

## The environment contract (`envs/base.py`)

An adapter exposes a simulator as:

- `query` — the task statement (also the retrieval key);
- `spec` — handbook-style documentation: actions, observation fields, rules, how to
  write an action, what counts as success. It states facts and gives no strategy
  advice;
- `reset() -> Observation` and `step(Action) -> StepResult`. An observation has
  `text` for a language model, `brief` (one line, for step histories) and `features`
  (named numbers, for rule policies). A step result adds a one-line `summary` of what
  the action did and an `event` for anything the agent must be told, in particular
  why the episode ended;
- `parse_action(text)` with error messages fit to show the model, and a harmless
  `fallback_action()`;
- `outcome() -> Outcome` — ground truth: score, success, failure mode and metrics.

`Outcome` is the only place ground truth lives. Renderers for the judge and the
extractor take a `Trajectory` and never read its `outcome`.

### `bsk-scan`

The BSK-RL nadir-scanning spacecraft: four modes (`scan` 180 s, `charge` 120 s,
`downlink` 60 s, `desat` 60 s), a data buffer, a battery charged by a body-fixed
array, reaction wheels under a random disturbance torque, and a ground-station
network. Reward per step is seconds of data recorded divided by the episode length;
losing the spacecraft (battery flat, or a wheel over its speed limit) ends the
episode with -1. Twelve operating conditions are exposed (`envs/scanning.py`:
battery capacity, panel area and efficiency, power draws, buffer size and data
rates, disturbance torque, wheel speed limit), with named single-factor regimes.

BSK-RL seeds NumPy's global generator from the reset seed and draws every random
quantity from it, so an episode is exactly reproducible, and the same seed under
different policies or conditions starts from the same orbit, epoch and state
fractions. The test suite checks both.

### `discoveryworld`

Wraps `DiscoveryWorldAPI`: the JSON observation is rendered as compact text (about
a sixth of the raw size; scenery tiles are dropped), actions are JSON as in
DiscoveryWorld itself, dialogs are handled, stdout is silenced and frame images go to
a temporary directory. Reward is always 0: the scorecard is oracle knowledge and is
only read into `Outcome`.

### `toy-scan`

A bookkeeping model with the same actions, features and conditions as `bsk-scan`,
used by the tests and by offline dry runs. It runs in milliseconds. Nothing measured
on it is a statement about the real simulator.

## Rule policies (`policies.py`)

An ordered list of `if condition then action` rules over the named features, with a
default action and named parameters. Plain JSON, evaluated without `eval`,
deterministic. `scanning_policy(**knobs)` builds the reference scanning policy: one
fixed rule structure with seven knobs. Rule policies are what make strategies
testable: the same policy can be rerun on the same seeds with one knob changed.

## Agents (`agents/`)

| Agent | Model calls | Use |
|---|---|---|
| `StepwiseAgent` | one per action | the paper's setting; reasoning recorded at every step |
| `PolicyProgramAgent` | one per episode (plus retries on invalid JSON) | the model writes a rule policy, which is validated and executed |
| `PolicyAgent` | none | executes a given rule policy; used by all experiments |

All return a `Trajectory`: the task, every step (observation, reasoning, action,
reward, result), the outcome, the memory items it was given, and the id of the model
call behind each step.

## The LLM layer (`llm/`)

`LLMRequest` carries a system prompt, messages, a `purpose` (act, judge, extract,
select, refine, policy, propose) and a `sample` index that distinguishes repeated
draws of the same prompt. A backend turns a request into text. `TrackedLLM` wraps any
backend with:

- a disk cache keyed by model, prompts and sample, so interrupted runs resume and
  reruns are free;
- a budget guard (estimated cost, uncached calls, or output tokens). A spent budget
  raises and stops the run; it is never swallowed by an agent;
- provenance logging of the full request and response of every call.

Backends: `AnthropicBackend` (official SDK; no sampling parameters, adaptive
thinking, optional effort, system prompt marked for prompt caching, refusal fallbacks
on the model families that support them), `ScriptedLLM` (test double) and
`OfflineDemoLLM` (a rule-based stand-in for dry runs).

## Provenance (`provenance/store.py`)

One SQLite file per run: `nodes` (trajectories, memory items, experiences, verdicts,
claims, evidence, experiments, model calls, agents, runs), `edges` (W3C PROV
relations plus `supports`, `contradicts`, `specializes`, `supersedes`), and two bulk
tables for step records and model calls. Edges point from the later thing to what it
depends on, so lineage is a recursive walk in either direction. `export_prov_json()`
writes PROV-JSON.

## Experiments (`experiments/`)

`EpisodeRunner` executes `(task, rule policy)` pairs across worker processes
(started with `spawn`; Basilisk does not survive `fork`), reusing one simulator per
configuration, and caches outcomes on disk under a hash of the task and the policy.
`stats` holds the paired bootstrap interval, the sign-flip permutation test, the
interaction contrast and a rank trend test.

## The two memory layers

- `reasoningbank/` — see `docs/reasoningbank-adaptation.md`.
- `claims/` — see `docs/claims.md`.

They meet in two places: `claims.report.claims_as_memory` renders applicable claims
as memory items for a language-model agent (`sea rb run --claims RUN`), and
`claims.hypotheses.LLMProposer` lets a language model feed hypotheses into the claim
graph.

## Run directories

```
runs/<rb-run>/     config.json  provenance.sqlite  bank.jsonl  records.jsonl
                   summary.json  llm_cache/
runs/<study>/      config.json  provenance.sqlite  episodes.sqlite  graph.json
                   experiments.jsonl  study.json  transfer.json  composition.json
                   report.md
```

`runs/` is git-ignored. Compact outputs of studies meant to be read are copied to
`results/`.
