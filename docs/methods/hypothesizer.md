# DiscoveryWorld Hypothesizer (baseline)

**Origin:** the Hypothesizer agent of DiscoveryWorld (Jansen et al., *DiscoveryWorld: A
Virtual Environment for Developing and Evaluating Automated Scientific Discovery
Agents*, NeurIPS 2024 Datasets and Benchmarks), released in
`agents/HypothesizerAgent.py` of https://github.com/allenai/discoveryworld (commit
`fd59132`). **Code:** `methods/hypothesizer/`.
**Evidence in this repository:** its prompts are byte-identical to the original's
(checked by a test); never run with a language model here.

## Motivation

DiscoveryWorld's own strongest baseline. It already keeps hypotheses and evidence, so
any claim that a memory "makes an agent keep track of hypotheses" has to beat it. It
remembers within an episode only: every episode starts with an empty store. That
makes it the right reference for a memory that works *across* episodes.

## The method

Each step makes two model calls.

1. **Act.** The model sees the observation (DiscoveryWorld's JSON), the list of
   actions, its last three actions with their explanations and results, and its
   current scientific knowledge. It answers with a JSON action plus an
   `explanation`, a `memory` note and its `running_hypotheses`.
2. **Reflect.** With the same context, the model adds measurements and hypotheses to
   its knowledge store. Hypotheses are IF statements with a status (pending,
   confirmed, rejected) and supporting evidence.

Every ten steps a third call consolidates the store to at most 40 entries and 2,000
tokens. Temperature 0.1 for all calls; 800 reply tokens for acting, 3,000 for
reflecting and consolidating.

## Implementation

| Module | Contents |
|---|---|
| `prompts.py` | the original prompt texts, quoted unchanged |
| `agent.py` | `HypothesizerAgent`: the act-reflect loop on this repository's agent interface |
| `config.py` | `HypothesizerConfig` |

As a method (`sea run --method hypothesizer`) it is the agent with no memory across
episodes. As an agent (`--agent hypothesizer`) it can be paired with a memory method;
the DiscoveryWorld experiment pairs it with ReasoningBank and with the investigation
memory, so that the arms differ only in their memory. It imports from no other method.

## Fidelity to the released agent

The port was run side by side with the original `GPT4HypothesizerOneStep` and
`consolidateKnowledgeStep` on the same worlds, with the same scripted replies: every
prompt was identical, byte for byte, along with its temperature and reply limit (31
calls over two worlds, covering an ordinary step, an unreadable reply, a reply
missing keys, a dialog, and a consolidation). Fingerprints of those prompts are in
`tests/data/hypothesizer_reference_prompts.json`, and a test regenerates them.

Kept as released, although they look like mistakes:

| Quirk | Effect |
|---|---|
| The prompt describes an image | no image is sent, as in the original run with `includeImages=False`; the models used here read text |
| The dialog addition overwrites itself | only the reply format survives; the dialog is not shown. `fixed_dialog_prompt=true` shows it |
| The reflection prompt is the decision's context | knowledge recorded at a step does not yet include that step's result; it is seen one step later |
| "Only the last code block will be parsed" | the parser reads the first code block, as the original's does |

Differences:

| Difference | Why |
|---|---|
| Unreadable replies and unknown actions become a no-op action that advances the world | the original passes the reply to the game, which refuses it and ticks; the effect is the same |
| The knowledge-base size in the consolidation prompt is estimated as characters / 4 when tiktoken's data cannot be downloaded | tiktoken fetches its tokenizer on first use; the run records which counter was used |
| `observation="text"` (option) shows this repository's compact observation instead of the JSON | for models with small context windows; a deviation, off by default |
| Cross-episode memory, when a method provides it, is placed between the knowledge and the output instructions | the original has no cross-episode memory; with none the prompt is unchanged |
| Runs end at the step limit or when the task is marked complete | as in the original's main loop |

## Parameters

| Option | Default | Meaning |
|---|---|---|
| `observation` | `json` | `json` as released; `text` for small context windows |
| `temperature` | 0.1 | of every call |
| `consolidate_every` | 10 | steps between consolidations |
| `fixed_dialog_prompt` | false | show the dialog in the dialog addition |
| `judge` | `none` | judge episodes anyway, to measure judge agreement (`llm`, `env`) |

## Assumptions and dependencies

Needs the DiscoveryWorld environment (it reads the API's own observation, actions and
teleport locations) and a language model. A model that cannot fit about 7,000 tokens
of prompt needs `observation=text`.

## Running it

```bash
sea run --method hypothesizer --env discoveryworld --scenario "Combinatorial Chemistry" --difficulty Easy --seeds 0:1 --max-steps 100 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/hyp
```

## Expected behaviour

From the DiscoveryWorld paper: the strongest of its baselines, completing a minority
of the discovery tasks (most on Easy). Not measured here.

## Limitations

- Cost: two calls per step, each with about 7,000 prompt tokens in `json` mode; a
  100-step episode is about 1.5 million prompt tokens.
- The knowledge store is per episode by design.
