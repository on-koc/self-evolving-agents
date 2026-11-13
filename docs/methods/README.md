# Methods

One folder per method under `src/self_evolving_agents/methods/`, one page per method
here. `sea methods` prints the same list; `sea methods --options` adds every option
and its default.

| Method | Origin | Page | What it is | Needs a model | Evidence in this repository |
|---|---|---|---|---|---|
| `no_memory` | reference point (the paper's vanilla agent) | [no_memory.md](no_memory.md) | the agent with no memory | yes | mechanics only |
| `reasoningbank` | paper | [reasoningbank.md](reasoningbank.md) | the published method | yes | mechanics only |
| `matts` | paper (parallel, no-aggregation); adaptation (`restart`) | [matts.md](matts.md) | several attempts per task | yes | mechanics only |
| `conditioned_retrieval` | adaptation | [conditioned_retrieval.md](conditioned_retrieval.md) | retrieval and extraction aware of operating conditions | yes | mechanics only |
| `policy_program` | adaptation | [policy_program.md](policy_program.md) | the model writes one executable policy per episode | yes | mechanics only |
| `claim_memory` | extension | [claim_memory.md](claim_memory.md) | tested claims shown to an agent as memory | yes | mechanics only |
| `claim_graph` | extension | [claim_graph.md](claim_graph.md) | conditional claims tested by chosen experiments | no | measured on Basilisk |

"Mechanics only" means: every code path is exercised by tests with scripted
stand-ins for the model, and no language model has been called. Nothing is known
about how these methods perform.

## How the folders depend on each other

```
shared, no method-specific behaviour
  agents/   envs/   llm/   experiments/   provenance/   policies.py   embeddings.py
  methods/stream.py        the stream loop; its default memory is "no memory"

methods/
  no_memory ───────────────► stream
  reasoningbank ───────────► stream                                  (the baseline)
  matts ───────────────────► stream, reasoningbank
  conditioned_retrieval ───► stream, reasoningbank
  policy_program ──────────► reasoningbank
  claim_graph ─────────────► (shared only)
  claim_memory ────────────► stream, reasoningbank, claim_graph
```

These are the only dependencies allowed. `tests/test_methods.py` reads every import
statement and fails if a method folder imports from one it is not listed with here,
if the baseline's folder mentions any adaptation, or if shared code imports a method.
The point is that the baseline cannot be changed by accident through an extension,
and that an extension's code states what it builds on.

## How a method is put together

A stream method is three parts handed to one loop (`methods/stream.py`):

| Part | Interface | The baseline's | Replaced by |
|---|---|---|---|
| agent | `Agent.run(env, memory, notes)` | `StepwiseAgent` | `policy_program` |
| memory | `Memory.retrieve`, `Memory.learn_single` | `ReasoningBankMemory` | `no_memory`, `conditioned_retrieval`, `claim_memory` |
| scaling | `Scaling.attempts`, `Scaling.learn` | one attempt | `matts` |

`methods/registry.py` names each combination and builds it; `methods/run.py` runs
one into a run directory; `compare.py` runs several on the same stream.

## Running and comparing

One method:

```bash
sea run --method reasoningbank --env toy-scan --seeds 0:3 --llm offline-demo --out runs/dry
```

Several methods on the same tasks, model and budget, with paired differences against
the baseline:

```bash
sea compare run --protocol protocols/toy_dry_run.json --out runs/dry-comparison
```

The protocols meant for a real model are described in
[`../protocols/model-comparison.md`](../protocols/model-comparison.md).

## Adding a method

1. A folder under `methods/` with a configuration dataclass and a `Memory`, a
   `Scaling` or an `Agent`.
2. An entry in `methods/registry.py` (`METHODS`, `config_class`, `build_stream`).
3. A page here, and the folder's allowed dependencies in `tests/test_methods.py`.
4. An arm in a protocol.
