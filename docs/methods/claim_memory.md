# Claims as memory (extension)

**Origin:** this project. **Code:** `methods/claim_memory/`.
**Evidence in this repository:** verified for correctness with scripted stand-ins;
never run with a language model.

## Motivation

A ReasoningBank item is a lesson a model wrote after one episode. Nothing checks it,
and nothing says where it stops being true. The claim graph (`claim_graph.md`)
produces lessons of a different kind: each was tested by a controlled experiment,
has a scope outside which it is known not to hold, and carries its evidence. This
method puts those in front of a language-model agent, in the place where
ReasoningBank would put its items.

## The method

Before an episode, the claims that apply under the task's operating conditions are
looked up in a claim graph built beforehand. A claim applies when its scope contains
the conditions and the nearest test of its comparison agrees with it. Each
applicable claim is rendered as a memory item:

- **title:** the claim's statement (or "Here the opposite of this holds: ..." for a
  claim that reverses the hypothesis it came from);
- **description:** the scope ("Applies where battery_capacity_wh >= 175.5") and how
  far the task's conditions are from the nearest supporting test ("tested under
  exactly these conditions", or "treat it as an extrapolation");
- **content:** what to set, the strongest supporting result with its interval and
  number of seeds, conditions outside the scope where it was found not to hold, and
  the status of each explanation ("is supported", "is refuted").

The items are shown with the published memory instruction. The agent's own episodes
add nothing to the claims.

With `with_reasoningbank=true` the items of a ReasoningBank follow the claims, and
that bank keeps learning from the agent's episodes as usual.

## Implementation

| Module | Contents |
|---|---|
| `render.py` | `claims_as_memory(graph, conditions)` |
| `method.py` | `ClaimMemory` (the loop's memory interface), `ClaimMemoryConfig` |

It depends on `methods/claim_graph` (to read a graph) and on
`methods/reasoningbank` (the item format and, optionally, a bank).

## Differences from the ReasoningBank baseline

| | ReasoningBank | Claims as memory |
|---|---|---|
| Where items come from | the agent's own trajectories, written by a model | simulator experiments run beforehand; no model |
| What decides relevance | similarity of the task query | the task's operating conditions against each claim's tested scope |
| Does it learn during the stream | yes | no (unless combined with a bank) |
| What an item carries | advice | advice, scope, evidence, counterexamples, status of explanations |
| Item format shown | title and content | title, description and content: the scope is in the description |

## Parameters

| Option | Default | Meaning |
|---|---|---|
| `claims` | (required) | run directory of a finished claim study, holding `graph.json` |
| `max_claims` | 8 | cap on claims shown |
| `with_reasoningbank` | false | also retrieve from and learn into a ReasoningBank |

## Assumptions and dependencies

Depends on a finished claim study (`methods/claim_graph`), on the item format of
`methods/reasoningbank` (and optionally its bank), on the shared loop and on a
language model.

- A claim graph exists for the task family and its conditions. Building one costs
  simulator time, not model calls (`claim_graph.md`).
- Claims are about parameters of the reference rule policy (`charge_below = 0.1`). A
  step-by-step agent has to translate "use charge_below = 0.25 instead of 0.1" into
  behaviour; a policy-writing agent can use it almost directly. Whether models do
  either is untested.
- The task's conditions are the ones the graph was built over. Under other
  conditions no claim applies and the agent gets nothing.

## Running it

```bash
sea run --method claim_memory --set claims=results/bsk-battery --env toy-scan --regime small_battery --seeds 0:2 --llm offline-demo --out runs/claims-dry
```

```bash
sea run --method claim_memory --set claims=results/bsk-battery --set with_reasoningbank=true --agent policy_program --env toy-scan --regime small_battery --seeds 0:2 --llm offline-demo --out runs/claims-both-dry
```

Both are arms of `protocols/scan_stepwise.json` and `protocols/scan_policy_agent.json`.

## Expected behaviour and limitations

Hypothesis: an agent given tested, scoped claims should avoid the failure that
unconditional lessons cause (applying a large-battery lesson to a small battery),
because each item says where it applies. The simulator-only study shows that the
*claims* have that property when applied mechanically. Whether a language model
reads and follows them is a separate question and has not been run.

It is not a like-for-like competitor of ReasoningBank: its knowledge was bought with
thousands of simulator episodes before the stream begins, and ReasoningBank's with
none. A comparison has to report that cost next to the scores.
