# ReasoningBank (baseline)

**Origin:** Ouyang et al., *ReasoningBank: Scaling Agent Self-Evolving with Reasoning
Memory*, ICLR 2026 (arXiv:2509.25140). **Code:** `methods/reasoningbank/`.
**Evidence in this repository:** verified for correctness with scripted stand-ins;
never run with a language model.

This page describes the method. How closely the implementation follows the
publication, row by row, is in [`../reasoningbank-fidelity.md`](../reasoningbank-fidelity.md).

## Motivation

An agent that meets a stream of tasks and treats each one as new repeats its
mistakes and rediscovers what it already found. Earlier agent memories stored raw
trajectories or workflows taken from successful runs. ReasoningBank stores something
more abstract, and from more sources: short strategy-level items distilled from the
agent's own trajectories, successful and failed, labelled by the agent itself because
no ground truth is available at test time.

## The method

Tasks arrive one at a time. The memory starts empty. For each task:

```
query ──► retrieve ──► act ──► judge ──► extract ──► consolidate
            ▲                                            │
            └────────────── memory bank ◄────────────────┘
```

1. **Retrieve.** The task query is embedded. Past experiences (one per earlier task)
   are ranked by cosine similarity of their queries, and all memory items of the top
   k experiences are taken. k = 1.
2. **Act.** The items are appended to the agent's system prompt after a fixed
   instruction ("Below are some memory items that I accumulated ..."), each shown by
   its title and content. The agent works step by step: reasoning, then one action.
3. **Judge.** A language model labels the finished trajectory success or failure from
   the task, the action history and the final state. No ground truth.
4. **Extract.** A language model distils at most three memory items from the
   trajectory. A successful trajectory is read for why it worked; a failed one for
   what went wrong and how to prevent it. The extractor sees the query and the
   agent's reasoning and action at each step.
5. **Consolidate.** The new experience (query, trajectory, items) is appended to the
   bank. Nothing is merged, pruned or de-duplicated.

A memory item has a title, a one-sentence description and the content.

The authors keep retrieval and consolidation deliberately minimal "so as to highlight
the contribution of ReasoningBank itself". This implementation keeps them minimal for
the same reason: anything beyond them is a different method with its own folder.

## Implementation

| Module | Contents |
|---|---|
| `schema.py` | `MemoryItem`, `Experience`, the parser for the extractor's Markdown |
| `prompts.py` | the published prompts, with the environment's domain substituted |
| `render.py` | trajectory as reasoning and action per step; the memory block; the judge's inputs |
| `bank.py` | `ReasoningBank`: append-only store, top-k experience retrieval |
| `judge.py` | `LLMJudge` |
| `extraction.py` | `MemoryExtractor` |
| `method.py` | `ReasoningBankMemory` (the loop's memory interface), `ReasoningBankConfig`, `build` |

The loop itself (`methods/stream.py`) and the step-by-step agent
(`agents/stepwise.py`) are shared with every other method and contain nothing
specific to this one. A test (`tests/test_methods.py`) fails if this folder imports
from any other method folder.

## Parameters

Defaults are the published values (`ReasoningBankConfig`; `sea methods --options`).

| Option | Default | Meaning | Source |
|---|---|---|---|
| `retrieve_k` | 1 | experiences retrieved per task | Appendix A.2; C.1 found 1 best |
| `max_items` | 3 | items extracted per trajectory at most | Appendix A.2 |
| `include_failures` | true | learn from failed trajectories; false is the paper's success-only ablation | Section 5 |
| `judge` | `llm` | `llm`: the method. `env`: the simulator's own criterion, a control without judge error | Section 5 (100% accuracy setting) |
| `judge_temperature` | 0.0 | | Appendix A.2 |
| `extraction_temperature` | 1.0 | | Appendix A.2 |
| `tie_break` | `oldest` | which experience wins an exact tie in similarity | reference code (see below) |

Five more options reproduce details of the reference code that are not in the paper.
All are off by default: `inject_description`, `extractor_sees_judge_rationale`,
`revised_prompts`, `judge_strict`, `query_instruction`.

Chosen outside the method: the model (`--llm`), the agent (`--agent stepwise` is the
paper's) and the embedder (`--embedder gemini` is the paper's `gemini-embedding-001`;
the default `hashing` works offline and measures word overlap, not meaning).

## Differences from the published method

This is the baseline, so there is no baseline to differ from. What matters instead
is how it differs from the system the paper evaluated. In short: the procedure and
the prompts are the published ones with the domain substituted; the environments,
the models and their decoding settings are not; the default embedder is an offline
stand-in unless the paper's is selected; sequential test-time scaling is not
reproduced. The full list, row by row, with what was corrected after an audit, is in
[`../reasoningbank-fidelity.md`](../reasoningbank-fidelity.md). Equivalence with the
published system is not claimed.

## Dependencies

The shared stream loop and step-by-step agent, a language model (for acting, judging
and extracting), and an embedder. It imports from no other method.

## Assumptions the method makes, and where they bite here

- **A task is identified by its query.** Retrieval looks at nothing else. On the
  paper's benchmarks every task has its own query. In a simulation family many
  episodes share one task statement. Here the scanning task's query includes the
  spacecraft's data sheet, so two regimes do have different queries, but all episodes
  of one regime have the *same* query.
- **Ties do not matter.** With identical queries, similarity ties are the normal
  case. The reference code's sort keeps the oldest of equally similar experiences, so
  with k = 1 a repeated task is given the items of its *first* episode forever, and
  nothing learned later is ever retrieved for it. `tie_break=newest` returns the
  latest instead. Neither is a published design decision; the protocols run both.
- **A lesson's scope is whatever the model wrote down.** Items are free text. Nothing
  checks under which conditions an item holds. An item learned with a large battery
  can be retrieved for a small one if the queries are similar enough.
- **The judge is good enough.** The paper measured 72.7% judge accuracy and found the
  method robust between 70% and 90%. Whether a judge can tell success from failure in
  these environments from the action history and the final state is unmeasured; the
  `judge_agreement` metric measures it in every run.

## Running it

A dry run with the stand-in model (free; its numbers mean nothing):

```bash
sea run --method reasoningbank --env toy-scan --regime nominal,small_battery --order interleaved --seeds 0:3 --llm offline-demo --out runs/rb-dry
```

```bash
sea show runs/rb-dry
```

With a model, on Basilisk:

```bash
sea run --method reasoningbank --env bsk-scan --regime nominal,small_battery --order interleaved --seeds 0:10 --llm anthropic:claude-opus-5-5 --max-cost 30 --out runs/rb
```

As one arm of the pre-registered comparison (with the no-memory reference, the
ablations and the other methods on the same stream):

```bash
sea compare run --protocol protocols/scan_stepwise.json --out runs/scan-stepwise
```

## Expected behaviour

From the paper, on its own benchmarks: higher success rate than no memory (+4.6 to
+8.3 points on WebArena across three models), fewer steps, and a gain from including
failures (46.5 to 49.7 on one subset). None of that has been measured here. What one
would look for in these environments: a higher mean score and fewer lost spacecraft in
the second half of a stream than in the first, relative to the no-memory arm.

## Known limitations

- Not run with a language model in this repository. No claim about its performance
  on these environments is supported by data.
- Not equivalent to the published system in three respects that cannot be removed
  here: the environments and their prompts are different; the models available
  through the Claude backend do not accept the published decoding temperatures; and
  the default embedder is not the published one unless `--embedder gemini` is used.
  See the fidelity document.
- The paper's own stated limits apply: retrieval and consolidation are minimal by
  design, and the memory's quality depends on the judge.
