# Condition-aware ReasoningBank (adaptation)

**Origin:** this project. **Code:** `methods/conditioned_retrieval/`.
**Evidence in this repository:** verified for correctness with scripted stand-ins;
never run with a language model. Its default settings are reasoned choices that have
not been tuned or evaluated.

## Motivation

ReasoningBank identifies a task by its query. A simulation family breaks that
assumption in a specific way: every episode can share one task statement and differ
only in operating conditions (a battery of 50 Wh instead of 200 Wh). Then

- all past queries look alike, so "the most similar experience" is an arbitrary one,
  and with exact ties it is always the oldest (see the baseline's page);
- a lesson that is right under one set of conditions can be wrong under another, and
  nothing in a free-text item says which conditions it came from.

The simulator-only study in this repository shows the second point is not
hypothetical: lessons that held for the reference spacecraft, applied to every
spacecraft, were worse than no lessons at all (`../comparison.md`).

## What it changes

Five mechanisms, each switched on its own, so that each can be ablated.

| Mechanism | Option | Default | What it does |
|---|---|---|---|
| Condition similarity in retrieval | `condition_weight` | 0.5 | relevance = (1 - w) x query similarity + w x similarity of the stored and current operating conditions (numeric conditions compared by ratio) |
| Item-level retrieval | `retrieval_mode`, `max_retrieved` | `item`, 6 | ranks single items instead of whole experiences; an item scores by how it reads against the query and by the relevance of the experience it came from |
| Diversity | `diversity` | 0.3 | greedy selection that penalises items similar to ones already chosen |
| Usage statistics | `utility_weight` | 0.0 (off) | bonus for items whose earlier uses scored above the bank's average, from the reward and verdict the agent itself observed |
| Duplicate filter | `dedup_threshold` | off | a new item at least this similar to an existing one is dropped |

And two changes to extraction:

| Mechanism | Option | Default | What it does |
|---|---|---|---|
| Condition notes | `condition_notes` | true | two instructions added to the published prompts: state the conditions under which an insight was observed and when not to apply it; mark explanations as hypotheses unless the trajectory demonstrates them |
| Richer trajectory | `observations` | true | the extractor also sees each step's observation summary and the feedback to each action, not only reasoning and action |

`tie_break` defaults to `newest` here.

## Implementation

| Module | Contents |
|---|---|
| `bank.py` | `ConditionedBank`, a subclass of the published bank: `retrieve_conditioned`, the duplicate filter, usage statistics (kept in each item's `meta`) |
| `method.py` | `ConditionedConfig`, `ConditionedExtractor` (the published extractor with the two added notes), `ConditionedMemory`, `build` |

It builds on `methods/reasoningbank` by subclassing and adds nothing to it: the
baseline's classes have no parameter of this method. With every mechanism switched
off (`condition_weight=0`, `retrieval_mode=experience`, `condition_notes=false`,
`observations=false`, `tie_break=oldest`) it behaves as the baseline, which a test
checks for the prompts.

## Differences from the ReasoningBank baseline

Everything in the two tables above. Judge, consolidation by appending, the memory
instruction, the item format and the loop are unchanged.

## Assumptions

- Tasks carry their operating conditions as named numbers (`Task.conditions`). An
  environment without them gains nothing from `condition_weight`.
- Similar conditions call for similar strategies. That is true far from a boundary
  and false near one; the claim graph exists because of the second case.
- The conditions an insight was *observed* under are the conditions it *holds*
  under. They are not: a lesson observed at 200 Wh may hold from 175 Wh upward or
  only near 200. Nothing in this method tests where a lesson stops being true.

## Running it

```bash
sea run --method conditioned_retrieval --env toy-scan --regime nominal,small_battery --order interleaved --seeds 0:3 --llm offline-demo --out runs/conditioned-dry
```

An ablation, for example condition weighting alone on top of the baseline:

```bash
sea run --method conditioned_retrieval --set retrieval_mode=experience --set condition_notes=false --set observations=false --env toy-scan --seeds 0:3 --llm offline-demo --out runs/conditioned-ablation
```

It is an arm of `protocols/scan_stepwise.json` and `protocols/scan_policy_agent.json`.

## Expected behaviour and limitations

Hypothesis: on a stream that alternates regimes, it should retrieve lessons from the
matching regime where the baseline retrieves an arbitrary or the oldest one, and so
lose the spacecraft less often in the regime whose lessons differ. Untested.

It adds complexity: seven switches against the baseline's none. Until the comparison
has been run there is no evidence that any of them earns its place, and several could
interact. Usage statistics in particular reward items for outcomes they may not have
caused.

What it cannot do is what the claim graph does: establish by experiment where a
lesson holds. It makes retrieval respect conditions; it does not make the lessons
conditional.
