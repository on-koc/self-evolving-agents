# ReasoningBank: fidelity of this implementation to the published method

This document compares the ReasoningBank baseline in this repository
(`methods/reasoningbank`, `methods/matts`) with the method as published, component by
component. Its purpose is to say exactly what can and cannot be claimed when the
baseline is called "ReasoningBank" in a paper.

## Sources

| | Source | Used for |
|---|---|---|
| P | Ouyang et al., *ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory*, arXiv:2509.25140v2 (16 March 2026), ICLR 2026. Sections 3 and 4.1, Appendices A to C and E. | the method as published; primary source |
| F | Figures 9 to 12 of P (the prompts), extracted as text from the figure PDFs in the arXiv LaTeX source | exact prompt wording |
| C | Reference code, `github.com/google-research/reasoning-bank`, commit `ed80611` (18 May 2026), Apache 2.0: `WebArena/` and the software-engineering port in `third_party/src/minisweagent/memory/` | details the paper leaves open |

Where P and C disagree, P is followed and the difference is listed. C was revised
after publication: its WebArena extraction and judge prompts are no longer the ones
printed in P (see rows E2 and J2).

## What the published method specifies

### Setting

| | Specification | Where |
|---|---|---|
| S1 | Test-time learning: task queries arrive as a stream and are completed one at a time, without access to later ones. | P 3.1 |
| S2 | The memory starts empty and persists for the run. | P 3.1, A.2 |
| S3 | No ground truth is available at test time. The agent learns from its own trajectories and its own verdict on them. | P 3.1 |

### Memory

| | Specification | Where |
|---|---|---|
| M1 | A memory item has three fields: a title (concise identifier of the strategy), a description (one-sentence summary), and content (distilled reasoning steps, rationales or insights). | P 3.2 |
| M2 | Storage: one entry per task, holding the task query, the original trajectory and the memory items extracted from it. Query embeddings are computed once and stored. | P A.2 |
| M3 | Consolidation: new items are appended. No pruning, merging or deduplication ("to highlight the contribution of ReasoningBank itself"). | P 3.2, A.2 |

### Retrieval and use

| | Specification | Where |
|---|---|---|
| R1 | The task query is embedded with `gemini-embedding-001`; similarity is cosine. | P A.2 |
| R2 | The memory items of the top-k most similar past **experiences** are retrieved, where an experience is one past task with all its items. Default k = 1. More experiences lowered the success rate in the paper's ablation (49.7, 46.0, 45.5, 44.4 for k = 1 to 4). | P A.2, C.1 |
| R3 | Stored vectors are embeddings of the plain query (task type `RETRIEVAL_DOCUMENT`, 3072 dimensions). The lookup vector is the embedding of `Instruct: <instruction>\nQuery: <query>`, with a one-sentence instruction describing the retrieval task. | C `memory_management.py` |
| R4 | A past task whose extraction produced nothing has an embedding but no entry; if it is the best match, nothing is retrieved for it. | C `select_memory` |
| R5 | Retrieved items are appended to the agent's **system** prompt, after the instruction: "Below are some memory items that I accumulated from past interaction from the environment that may be helpful to solve the task. You can use it when you feel it's relevant. In each step, please first explicitly discuss if you want to use each memory item or not, and then take action." | P A.2, C `agent.py` |
| R6 | Format of the injected items. P: "each item represented by its title and content". C: the extractor's Markdown is injected as generated, with title, description and content. | P A.2 against C `run.py` |

### Acting

| | Specification | Where |
|---|---|---|
| A1 | ReAct-style agent: at each step it produces its reasoning and one action, given the observation and the history of its earlier reasoning and actions. | P 4.1, B.1 |
| A2 | Decoding temperature 0.7. Step limit 30 on WebArena. | P B.1 |
| A3 | Backbones: Gemini 2.5 Flash, Gemini 2.5 Pro, Claude 3.7 Sonnet. Judge and extractor use the same model as the agent. | P B.1, A.2 |

### Judging

| | Specification | Where |
|---|---|---|
| J1 | An LLM labels each finished trajectory success or failure, without any ground-truth reference. Temperature 0.0. | P 3.2, A.2 |
| J2 | Input: the user's intent, the trajectory, the final state of the page, the agent's response. Output: two lines, `Thoughts:` and `Status: "success" or "failure"`. The system instruction describes three task types (F, Figure 10). C adds a block of strictness rules that is not in the published figure. | F Fig. 10, C `autoeval_prompts.py` |
| J3 | Reported judge accuracy against ground truth: 72.7% (WebArena-Shopping, Gemini 2.5 Flash). The method was reported robust between 70% and 90% simulated accuracy. | P 5 |

### Extraction

| | Specification | Where |
|---|---|---|
| E1 | Successful and failed trajectories are both used, with different system instructions: successes yield validated strategies, failures yield lessons and preventive strategies. Temperature 1.0. At most 3 items per trajectory. | P 3.2, A.1, A.2 |
| E2 | Wording of the two system instructions: F, Figure 9. C's WebArena prompts differ from the figure in one note ("Prefer concrete, actionable procedures ...") and in the description field ("when or when NOT to use"); C's software-engineering port matches the figure. | F Fig. 9, C |
| E3 | Input: `Query: <query>` and `Trajectory: <trajectory>`, where the trajectory is the agent's reasoning and action at each step. Observations are not included ("We use the thinking process ... as the approximation of [the observations] due to lengthy observation representations"). | P 3.1 footnote 1, F Fig. 9, C `induce_memory.py` |
| E4 | The judge's reasoning is appended to the extractor's input ("The task succeeded/failed because: ..."). | C `induce_memory.py` only |
| E5 | The extractor's output is stored as text split on blank lines. It is not parsed into fields. | C `induce_memory.py` only |

### Memory-aware test-time scaling (MaTTS)

| | Specification | Where |
|---|---|---|
| T1 | Scaling factor k: number of trajectories (parallel) or of refinement steps (sequential). k = 1 is no scaling. | P 3.3 |
| T2 | **Parallel.** k trajectories are generated for the same query under the same retrieved memory. One extraction over all of them with a self-contrast instruction, at most 5 items. The trajectories are given without success labels. | P 3.3, A.3, F Fig. 11 |
| T3 | **Sequential.** After the trajectory first completes, the agent re-examines it with a check instruction and may correct itself, in the same think/action format; then "Let's check again" for further rounds. The intermediate notes are used as memory signals. | P 3.3, A.3, F Fig. 11 |
| T4 | **Best-of-N.** For parallel scaling, an LLM is shown all N trajectories at once and selects the best one (F, Figure 12; JSON answer with an index and an analysis). Reported next to Pass@1, the score of one randomly chosen trajectory. | P 4.3, 4.4, A.3 |
| T5 | **Controls.** Vanilla TTS (no aggregation): each of the k trajectories is turned into memory on its own. Scaling without memory. | P 3.3, 4.3 |
| T6 | C contains the parallel pipeline (extraction temperature 0.7) and the sequential prompts, but no sequential pipeline and no Best-of-N code. Its parallel induction script reads the same trajectory k times. | C `pipeline_scaling.py`, `induce_scaling.py` |

### Comparison methods and metrics in the paper

| | Specification | Where |
|---|---|---|
| B1 | Baselines: no memory; Synapse (raw trajectories as memory); AWM (workflows as memory). They share retrieval and consolidation with ReasoningBank and differ only in what is extracted. Synapse and AWM use successful trajectories only. | P 4.1, B.1 |
| B2 | Metrics: success rate by the benchmark's own ground-truth evaluation, and the average number of steps per task. Token use per task is reported separately. | P B.1, C.2 |

## Results reported in the paper, for reference

These are the authors' numbers on their benchmarks. Nothing in this repository
reproduces them.

| Benchmark (model) | No memory | ReasoningBank | with MaTTS (parallel, k = 5) |
|---|---|---|---|
| WebArena overall success rate (Gemini 2.5 Flash) | 40.5 | 48.8 | 51.8 |
| WebArena overall success rate (Gemini 2.5 Pro) | 46.7 | 53.9 | 56.3 |
| WebArena overall success rate (Claude 3.7 Sonnet) | 41.7 | 46.3 | 48.8 |
| WebArena average steps (Gemini 2.5 Flash) | 9.7 | 8.3 | 7.9 |
| SWE-Bench-Verified resolve rate (Gemini 2.5 Flash) | 34.2 | 38.8 | |
| SWE-Bench-Verified resolve rate (Gemini 2.5 Pro) | 54.0 | 57.4 | |

Ablations on WebArena-Shopping with Gemini 2.5 Flash: memory from successes only
46.5 against 49.7 with failures included; parallel MaTTS 49.7 (k = 1) to 55.1
(k = 5), sequential 49.7 to 54.5, scaling without memory between 39.0 and 42.2.

## What the audit found

The implementation was compared with every row above. These are the places where the
baseline, as it stood before the audit, departed from the published method. Each was
either corrected or is listed under remaining deviations below.

| | Row | What the code did | Why it matters | Resolution |
|---|---|---|---|---|
| D1 | E1, E2 | The success and failure extraction prompts carried two instructions that are not in the paper: state the operating conditions under which an insight was observed, and mark explanations as hypotheses. | They change what the memory contains. A baseline with them is not ReasoningBank; it is ReasoningBank plus the first step of the extension it is compared with. | Corrected. The baseline uses the published wording. The added instructions moved to the `conditioned_retrieval` method. |
| D2 | E3 | The extractor was shown each step's observation summary and action feedback, the final state and the total reward, besides reasoning and action. | The published extractor sees the query and the reasoning and action of each step only. | Corrected. Reasoning and action only by default; the richer rendering is an option used by the adaptations. |
| D3 | E4 | The judge's reasoning was always appended to the extractor's input. | In the released code, not in the paper. | Now an option, off by default. |
| D4 | R6 | Injected memory items showed title, description and content. | The paper states title and content. | Corrected to title and content; the released code's form is an option. |
| D5 | J2 | The judge prompt was a rewrite: it included the released code's strictness rules, the environment's rules and a full step-by-step account with observations. | The published prompt has no strictness block, and the judge sees the intent, the action history, the final state and the response. | Restructured to the published frame. What counts as success in the environment replaces the three web task types (unavoidable: that part of the prompt is domain-specific). Strictness rules are an option. |
| D6 | T4 | Best-of-N used a prompt written for this project, with a different answer format. | The paper's selection prompt is Figure 12. | Corrected to the published prompt and its JSON answer. |
| D7 | T2 | The self-contrast prompt carried an added instruction about attempts starting from the same situation. | Not in the paper. | Corrected to the published wording. |
| D8 | T3 | "Sequential" scaling re-ran the task from the start with notes from earlier attempts. | The published procedure continues the same trajectory after it completes. That is a different procedure. | Not correctable in these environments (see below). Renamed `restart` and documented as an adaptation. |
| D9 | R1 | Retrieval used a hashing embedder that measures word overlap. | The paper uses a neural embedding model. | The paper's model is now available (`GeminiEmbedder`); the hashing embedder remains the offline default and is named in every run's configuration. |
| D10 | M3 | Deduplication, usage statistics and condition-weighted retrieval lived in the baseline's memory class, switched off by default. | Off by default, so behaviour was the paper's, but the baseline's code path contained the adaptations. | Moved out. The baseline class has no such parameters. |
