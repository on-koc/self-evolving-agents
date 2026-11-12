# ReasoningBank, adapted to simulation environments

This page maps the paper (Ouyang et al., ICLR 2026, arXiv:2509.25140) and its
reference implementation (`google-research/reasoning-bank`) onto this repository,
and lists every place where the adaptation departs from them and why.

## What was kept as is

| Paper / reference code | Here |
|---|---|
| Memory item = title, description, content | `reasoningbank.schema.MemoryItem` |
| Each bank entry = task query, trajectory, items; stored as JSON | `Experience`, one JSON line per entry in `bank.jsonl`; trajectories live in the provenance store and are referenced by id |
| Retrieval: embed the task query, cosine similarity to past queries, items of the top-k experiences, k = 1 | `ReasoningBank.retrieve(mode="experience", k=1)` (the default) |
| Items injected into the system prompt after a fixed instruction | `StepwiseAgent.system_prompt`; the instruction text is quoted verbatim (`prompts.MEMORY_INSTRUCTION`) |
| LLM-as-a-judge labels success or failure with no ground truth; "Thoughts:/Status:" format; when uncertain, fail | `induction.LLMJudge` |
| `--criteria gt` alternative | `induction.EnvJudge` (`--judge env`) |
| Separate extraction prompts for successful and failed trajectories, at most 3 items | `induction.MemoryExtractor.extract` |
| The judge's reasoning is appended to the trajectory before extraction | `render.render_for_extraction` |
| Consolidation = append, no pruning | `ReasoningBank.add` |
| MaTTS parallel: k rollouts, self-contrast extraction (at most 5 items), best-of-N by the model | `--scaling parallel --k K` |
| Vanilla TTS ("MaTTS w/o aggregation"): k rollouts extracted independently | `--scaling vanilla --k K` |
| "Success only" ablation | `--success-only` |
| Streaming test-time learning: tasks arrive one at a time, memory starts empty | `ReasoningBankPipeline.run_stream` |

## What was changed, and why

### 1. Prompts name the conditions and mark explanations as hypotheses

On the web a task is identified by its query. In a simulator the *same* task runs
under different operating regimes (a 25 Wh battery, a 400 Wh battery), and a rule
that holds in one can be fatal in another. The extraction prompts therefore ask that
the description state the conditions under which an insight was observed, and when
it should not be applied. They also ask that explanations of *why* something worked
be marked as hypotheses, because a trajectory shows what happened and rarely why.
The task statement shown to the agent includes a data sheet of the spacecraft so
that these conditions are available to quote.

### 2. A second retrieval mode for homogeneous task families

With one task statement shared by every episode, all past queries look alike. The
paper's top-1 *experience* retrieval then returns the at-most-three items of a single
(the most recent) episode, so a lesson learned three episodes ago is displaced by
whatever was learned last. `--retrieval item` scores individual items instead, can
weigh in how close the stored operating conditions are to the current ones
(`--condition-weight`), can prefer items whose past uses went well
(`--utility-weight`), and diversifies the selection so that near-duplicates do not
crowd out a different lesson. The paper's mode remains the default.

Whether item retrieval actually helps a real model here is an open empirical
question; see `docs/running-llm-experiments.md` for the comparison to run.

### 3. Usage statistics use only what the agent can see

Each item records how often it was retrieved and how those episodes went. The
numbers come from the reward the agent itself received and from the *judged*
outcome, never from simulator ground truth, so using them for retrieval does not
leak labels into test-time learning.

### 4. Sequential scaling re-attempts instead of re-checking

In the paper, sequential scaling has the agent re-examine a finished trajectory and
possibly correct its final answer. A simulated episode cannot be amended after the
fact. Here the agent re-examines the attempt, writes notes, and plays the same task
again from the same initial state with those notes in its prompt; the notes and all
attempts go to the extractor. `k` counts attempts.

### 5. The best-of-N prompt is new

The paper describes it (Figure 12) but the released code does not contain it.
`prompts.selection_system` was written for this repository.

### 6. Sampling temperatures cannot be set on current Claude models

The paper judges at temperature 0 and extracts at temperature 1. The Claude Messages
API no longer accepts `temperature`, `top_p` or `top_k`. The request object still
carries the paper's values as hints for backends that accept them; the Claude backend
drops them. Reproducibility comes from the response cache instead: a rerun replays
recorded calls.

### 7. Two ways to put the model in charge

`--agent stepwise` is the paper's setting: one model call per action. A three-orbit
scanning episode is 95-285 steps, so `--agent policy` is offered as a cheaper
alternative: one call per episode writes a rule policy (JSON, validated, with the
errors fed back if it is malformed) which is then executed. The strategy is explicit,
the extractor sees exactly which rule produced which behaviour, and the same strategy
can be rerun on other seeds.

### 8. Embeddings

The paper uses `gemini-embedding-001`. The default here is a dependency-free hashing
embedder (words, word bigrams, character trigrams) so that retrieval works offline.
It measures lexical overlap, not meaning. Anything with an `embed(texts)` method can
be passed to `ReasoningBank(embedder=...)`.

## What "success" means in each environment

| Environment | Ground truth (`Outcome.success`) | What the LLM judge sees |
|---|---|---|
| `bsk-scan`, `toy-scan` | survived to the time limit and recorded for at least 20% of the episode | task statement, rules, the step record with per-step rewards, the end-of-episode message, the total reward |
| `discoveryworld` | the scenario's own `completedSuccessfully` | task statement, rules, the step record, the final observation including "task status: complete / not complete" |

The scorecard of DiscoveryWorld (sub-goal progress, normalised score) is oracle
knowledge. It is read only into `Outcome` for reporting and is never placed in an
observation, a step record, or anything a model is shown.

## Provenance

Every run writes a SQLite store (`provenance.sqlite`) holding a small property graph:

```
memory_item --wasDerivedFrom--> trajectory --wasGeneratedBy--> run
     |                              |
     |--wasGeneratedBy--> llm_call  |--wasAssociatedWith--> agent
     |--wasDerivedFrom--> experience|--used--> memory_item (those it was given)
verdict --wasDerivedFrom--> trajectory, --wasGeneratedBy--> llm_call (the judge)
```

`sea prov lineage RUN ID` walks it in either direction ("where did this item come
from?", "which episodes used it and how did they go?"), and `sea prov export` writes
W3C PROV-JSON. Every model call is stored with its full request and response.
