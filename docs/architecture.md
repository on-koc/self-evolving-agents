# Architecture

The code has two layers. A **shared layer** knows nothing about any method:
environments, agents, the model interface, the experiment runner, provenance. A
**methods layer** has one folder per method, each depending only on the shared layer
and on the methods it explicitly builds on.

```
src/self_evolving_agents/
│
│  shared layer: no method-specific behaviour
├── envs/            simulators as text plus named features
│     bsk_scan         Basilisk through BSK-RL
│     discoveryworld
│     toy              analytic imitation of bsk_scan, for tests and dry runs
│     scanning         task definition shared by bsk_scan and toy
├── agents/          StepwiseAgent (one model call per action),
│                    PolicyAgent (executes a given rule policy, no model)
├── policies.py      rule policies as JSON
├── llm/             request and response types, Claude backend, stand-ins,
│                    cache, budget guard
├── embeddings.py    hashing embedder (offline), Gemini embedder (the paper's)
├── experiments/     parallel cached episode runner; paired statistics
├── provenance/      SQLite store of everything that happened
├── tasks.py         building a task stream from regimes, seeds and an order
│
│  methods layer: one folder per method
├── methods/
│     stream.py        the loop every stream method runs in
│     registry.py      names each method and builds it
│     run.py           runs one method into a run directory
│     no_memory/  reasoningbank/  matts/  conditioned_retrieval/
│     policy_program/  claim_memory/  claim_graph/
├── compare.py       runs several methods on the same stream and reports
└── cli.py           the `sea` command
```

The methods, and which may import which, are described in
[`methods/README.md`](methods/README.md). `tests/test_methods.py` enforces those
dependencies by reading every import statement.

## The stream loop (`methods/stream.py`)

Every method that works through a stream of tasks is three parts handed to one loop:

```
for each task:
    retrieval = memory.retrieve(task)             # may be empty
    attempts  = scaling.attempts(agent, memory)   # one attempt, or several
    verdicts  = judge(trajectory)                 # a model, or the simulator as a control
    learned   = scaling.learn(...) → memory.learn_single(...)
    record(task, outcome, verdict, what was retrieved, what was learned)
```

| Part | Default | Replaced by |
|---|---|---|
| `Memory` | retrieves nothing, learns nothing (this *is* `no_memory`) | `reasoningbank`, `conditioned_retrieval`, `claim_memory` |
| `Scaling` | one attempt | `matts` |
| `Agent` | `StepwiseAgent` | `policy_program` |
| `Judge` | none | `LLMJudge` (the method), `EnvJudge` (a control) |

The loop refuses to run a memory that learns without a judge. It records, per task,
the simulator's outcome next to the judge's verdict; the outcome never reaches the
agent, the judge or the extractor.

`claim_graph` is not a stream method. It has its own loop (`claim_graph/loop.py`):
choose an experiment, run it, revise the graph.

## The environment contract (`envs/base.py`)

An adapter exposes a simulator as:

- `query`: the task statement. For ReasoningBank it is also the retrieval key;
- `spec`: handbook-style documentation: actions, observation fields, rules, how to
  write an action, what counts as success, and a `domain` name that the published
  prompts take in place of "web navigation". It states facts and gives no strategy
  advice;
- `reset() -> Observation` and `step(Action) -> StepResult`. An observation has
  `text` for a language model, `brief` (one line, for step histories) and `features`
  (named numbers, for rule policies). A step result adds a one-line `summary` of what
  the action did and an `event` for anything the agent must be told, in particular
  why the episode ended;
- `parse_action(text)` with error messages fit to show the model, and a harmless
  `fallback_action()`;
- `outcome() -> Outcome`: ground truth. Score, success, failure mode and metrics
  (defined in [`metrics.md`](metrics.md)).

`Outcome` is the only place ground truth lives.

### `bsk-scan`

The BSK-RL nadir-scanning spacecraft: four modes (`scan` 180 s, `charge` 120 s,
`downlink` 60 s, `desat` 60 s), a data buffer, a battery charged by a body-fixed
array, reaction wheels under a random disturbance torque, and a ground-station
network. Twelve operating conditions are exposed (`envs/scanning.py`: battery
capacity, panel area and efficiency, power draws, buffer size and data rates,
disturbance torque, wheel speed limit), with named single-factor regimes.

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
used by the tests and by dry runs. It runs in milliseconds. Nothing measured on it is
a statement about the real simulator.

## Rule policies (`policies.py`)

An ordered list of `if condition then action` rules over the named features, with a
default action and named parameters. Plain JSON, evaluated without `eval`,
deterministic. `scanning_policy(**knobs)` builds the reference scanning policy: one
fixed rule structure with seven parameters. Rule policies are what make strategies
testable: the same policy can be rerun on the same seeds with one parameter changed.

## Agents

| Agent | Where | Model calls | Use |
|---|---|---|---|
| `StepwiseAgent` | `agents/stepwise.py` | one per action | the paper's setting: reasoning, then one action, at every step |
| `PolicyProgramAgent` | `methods/policy_program/` | one per episode, plus repairs | the model writes a rule policy, which is validated and executed |
| `PolicyAgent` | `agents/rule.py` | none | executes a given rule policy; used by every simulator experiment |

An agent receives a `MemoryBlock` (text for its prompt, and the ids of the items in
it) and returns a `Trajectory`: the task, every step (observation, reasoning, action,
reward, result), the outcome, the memory items it was given, and the id of the model
call behind each step. Agents import no method.

## The model layer (`llm/`)

`LLMRequest` carries a system prompt, messages, a `purpose` (act, judge, extract,
select, refine, policy, propose) and a `sample` index that distinguishes repeated
draws of the same prompt. A backend turns a request into text. `TrackedLLM` wraps any
backend with:

- a disk cache keyed by model, prompts and sample, so interrupted runs resume and
  reruns are free;
- a budget guard (estimated cost, uncached calls, or output tokens). A spent budget
  raises and stops the run; it is never swallowed by an agent;
- provenance logging of the full request and response of every call.

Backends: `AnthropicBackend` (official SDK), `ScriptedLLM` (test double) and
`OfflineDemoLLM` (a rule-based stand-in for dry runs; its outputs are not results).
The request carries the paper's decoding temperatures; the Claude backend omits them
for models that do not accept sampling parameters (see the fidelity document).

## Experiments (`experiments/`)

`EpisodeRunner` executes `(task, rule policy)` pairs across worker processes
(started with `spawn`; Basilisk does not survive `fork`), reusing one simulator per
configuration, and caches outcomes on disk under a hash of the task and the policy.
It counts both the episodes it had to simulate and the distinct episodes it was
asked for; budgets use the second, so they do not depend on what the cache held. A
finished study replays from its cache in seconds, which is how recorded results are
regenerated and checked after a change to the code.

`stats` holds the paired bootstrap interval, the sign-flip permutation test, the
interaction contrast and a rank trend test. All resampling is seeded.

## Provenance (`provenance/store.py`)

One SQLite file per run: `nodes` (trajectories, memory items, experiences, verdicts,
claims, evidence, experiments, model calls, agents, runs), `edges` (W3C PROV
relations plus `supports`, `contradicts`, `specializes`, `supersedes`), and two bulk
tables for step records and model calls. Edges point from the later thing to what it
depends on, so lineage is a walk in either direction.

```
memory_item --wasDerivedFrom--> trajectory --wasGeneratedBy--> run
     |                              |
     |--wasGeneratedBy--> llm_call  |--wasAssociatedWith--> agent
     |--wasDerivedFrom--> experience|--used--> memory_item (those it was given)
verdict --wasDerivedFrom--> trajectory, --wasGeneratedBy--> llm_call (the judge)
evidence --wasGeneratedBy--> experiment, --supports | contradicts--> claim
claim    --specializes | supersedes--> claim
```

`sea prov lineage RUN ID` answers "where did this item come from?" and, with
`--down`, "which episodes used it and how did they go?". `sea prov export` writes
PROV-JSON.

## Where the two families of methods meet

- `methods/claim_memory` renders the claims of a finished graph as memory items for
  a language-model agent.
- `claim_graph/hypotheses.py` has a proposer that lets a language model feed
  hypotheses into the claim graph (`sea claims study --llm ...`).
- A policy written by `policy_program` is a rule policy, the same object the claim
  graph experiments on.

## Run directories

```
sea run            runs/<run>/      config.json  summary.json  records.jsonl  bank.jsonl
                                    provenance.sqlite  llm_cache/
sea compare run    runs/<name>/     protocol.json  comparison.json  comparison.md
                                    <arm>/rep-<i>/   (each a `sea run` directory)
sea claims study   runs/<study>/    config.json  study.json  graph.json  experiments.jsonl
                                    transfer.json  composition.json  report.md
                                    episodes.sqlite  provenance.sqlite
sea claims replicate  runs/<name>/  replication.json  replication.md  episodes.sqlite
                                    seed-<base>/     (each a study directory)
```

`runs/` is git-ignored. Compact outputs of studies meant to be read are copied to
`results/`.
