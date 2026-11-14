# Investigation memory (extension)

**Origin:** this project. **Code:** `methods/investigation_memory/`.
**Evidence in this repository:** verified for correctness with scripted stand-ins
and an end-to-end dry run on DiscoveryWorld; never run with a language model.

## Motivation

The key distinction of the DiscoveryWorld study is between *remembering which
substance worked in a previous world* and *learning how to identify the effective
substance in a new world*. DiscoveryWorld varies the answer with the seed: in
Combinatorial Chemistry (Easy) the rust remover is Substance B in one world and
Substance D in the next. A memory of answers is useless there, or worse. A memory of
how the answer was found might carry over, and might carry over to other scientific
tasks.

ReasoningBank stores both kinds of lesson in one free-text item, with nothing that
says where a lesson was observed. This memory keeps them apart, and keeps track of
where each finding came from.

## The method

Three kinds of memory, linked into one graph:

| Kind | Example | Retrieved for |
|---|---|---|
| **evidence** | "Substance A left the key heavily rusted" | an earlier attempt in the same world only |
| **conditional hypothesis** | "Substance B removes rust" [supported], observed under: this shed; evidence for and against | the same world; other worlds of the same kind, with their conditions |
| **investigation strategy** | "Empty the container before each new test", applies when several candidates share one container; how it was put into practice; record of use | any task, ranked by relevance and by record |

Links: hypotheses to the evidence that supports or contradicts them; hypotheses and
strategies to the episodes they came from; strategies to the episodes where they were
used, with the assessment of each use; a revised strategy to the one it replaced.

After each episode one model call writes evidence, hypotheses and strategies from
the episode (actions, results, the agent's own notes, and the agent's verdict on the
outcome). If strategies had been shown at the start, the same call assesses each:
used or not, helped or not, and, if it did not help because it does not apply in
situations like this, a narrower revised version. The record of use enters the
ranking; a revised strategy replaces the old one.

Nothing in this method sees the simulator's score. Episodes are labelled by the same
model judge ReasoningBank uses.

## Variants (for the experiment)

| `mode` | What the agent is shown | Role |
|---|---|---|
| `full` | the method | the treatment |
| `answers` | supported hypotheses from worlds of this kind, as plain facts, without conditions, evidence or strategies | the foil: "remember which substance worked" |
| `placebo` | neutral sentences about the setting, of similar length, in the same place | controls for having text in the memory slot |
| `instructed` | no memory; a fixed text that prescribes the five investigative behaviours | the instruction-following reference |

`include` removes kinds of memory from what is shown. Applied to a frozen memory at
evaluation time, it is the lesion test: `include=["evidence","hypotheses"]` removes
strategies.

## What no prompt says

The experiment measures whether controls, testing alternatives, recognising
confounds, revisiting conclusions and transferring a strategy appear without being
asked for. So no prompt of this method names or describes them; a test checks the
texts for the words. The schema records support and contradiction between
hypotheses and evidence: that is how the memory is organised, stated in the
extraction prompt, and it is a design choice to keep in mind when interpreting
"revision". Only the `instructed` variant names the behaviours.

## Implementation

| Module | Contents |
|---|---|
| `schema.py` | `Evidence`, `Hypothesis`, `Strategy`, `InvestigationGraph` (one JSON file) |
| `prompts.py` | extraction and review prompts, headings, the instructed text, the placebo sentences |
| `memory.py` | `InvestigationMemory`: retrieval, extraction, review, provenance |
| `config.py` | `InvestigationMemoryConfig` |

It builds on the shared stream loop and takes ReasoningBank's judge
(`methods/reasoningbank`). Its default agent is the Hypothesizer.

## Parameters

| Option | Default | Meaning |
|---|---|---|
| `mode` | `full` | `full`, `answers`, `placebo`, `instructed` |
| `include` | all three kinds | kinds shown to the agent |
| `other_worlds` | `scoped` | hypotheses from other worlds of this kind: with their conditions, or `hide` |
| `max_strategies`, `max_hypotheses`, `max_evidence` | 6, 6, 8 | how many of each are shown |
| `review` | true | assess shown strategies after each episode |
| `judge` | `llm` | `env` uses the simulator's verdict (a control) |
| `extraction_temperature` | 0.0 | |

## Assumptions and dependencies

- A world can be identified (scenario, difficulty, seed). The memory records where
  each item came from; it uses no knowledge of whether the item is true.
- Strategy relevance is judged from text similarity. With the default `hashing`
  embedder that is word overlap; a semantic embedder (`--embedder hf:...`) is better.
- Needs a model that can write the extraction JSON.

## Running it

```bash
sea run --method investigation_memory --env discoveryworld --scenario "Combinatorial Chemistry" --difficulty Easy --seeds 0:3 --max-steps 100 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/inv
```

As part of the experiment:

```bash
sea discovery run --protocol protocols/discovery_pilot.json --out runs/discovery-pilot
```

## Expected behaviour (hypotheses, untested)

Better than answer memory on new worlds of a known kind and on new kinds of task;
no better than answer memory on a world seen before. Fewer stale answers (stating an
earlier world's answer) than ReasoningBank and answer memory. The investigative
behaviours more frequent than with the Hypothesizer alone, less frequent after the
strategies are removed. See [`../discoveryworld.md`](../discoveryworld.md).

## Limitations

- Strategies are free text; whether a strategy was actually followed is inferred
  from the agent's own review and from citation, not established.
- One extraction call per episode can produce poor notes; nothing checks a strategy
  except its later record of use.
- The record of use rests on the agent's own judgement of whether a strategy helped.
