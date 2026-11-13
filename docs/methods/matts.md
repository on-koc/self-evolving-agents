# Memory-aware test-time scaling (MaTTS)

**Origin:** section 3.3 of the ReasoningBank paper. **Code:** `methods/matts/`.
**Evidence in this repository:** verified for correctness with scripted stand-ins;
never run with a language model.

Two of the three variants here follow the paper. The third does not, and is named
differently so that it cannot be mistaken for the paper's.

## Motivation

Spending more computation on a task at test time usually helps. The paper's point is
that it helps more when there is a memory: several attempts at the same task are not
only several chances to succeed, they are a contrast from which better memory items
can be distilled, and better memory in turn steers later attempts.

## The variants

`scaling_k` is the scaling factor k: the number of attempts per task. k = 1 is the
baseline.

| `scaling` | From the paper? | What happens for each task |
|---|---|---|
| `parallel` | yes (MaTTS, parallel) | k trajectories under the same retrieved memory. **One** extraction over all of them with the self-contrast instruction, at most 5 items; the trajectories are given without success labels. The task's result is the trajectory a model picks when shown all of them (Best-of-N). |
| `vanilla` | yes ("MaTTS w/o aggregation") | k trajectories, each judged and turned into memory on its own, so a task adds up to k experiences. Result by Best-of-N. |
| either, with `memory=false` | yes ("MaTTS w/o memory") | scaling with no memory at all |
| `restart` | **no** | see below |

### Why there is no sequential MaTTS here

In the paper's sequential scaling the agent finishes its trajectory, is then told to
re-examine it ("Let's carefully re-examine the previous trajectory ... If you find
inconsistencies, correct them"), and goes on acting in the same episode, k times in
all. That presupposes a task whose answer can still be revised after it has been
given.

No environment here is like that. A scanning episode ends when the time limit is
reached or the spacecraft is lost; there is nothing left to act on. The published
check instructions are kept in `matts/prompts.py` for reference and are not used.

`restart` is what can be done instead: after an attempt the agent is shown its
attempts so far, asked to re-examine them and write notes, and the task is started
again from the same initial state with the notes in the system prompt. The last
attempt is the result; one extraction is made over the whole series and the notes.
It keeps the idea of self-refinement and changes the procedure: k full episodes
instead of one extended trajectory, and a second chance at the same episode that the
published procedure does not give. **It should not be reported as the paper's
sequential MaTTS.**

## Implementation

| Module | Contents |
|---|---|
| `prompts.py` | the published self-contrast and Best-of-N prompts (figures 11 and 12); the published check instructions, unused; the `restart` prompts |
| `scaling.py` | `ParallelScaling`, `VanillaScaling`, `RestartScaling`, `select_best` |
| `config.py` | `MattsConfig` |

Each strategy is a `Scaling` for the shared stream loop: it decides how many
attempts are made and how they become memory. It builds on `methods/reasoningbank`
(the bank, the extractor, the judge) and on nothing else.

## Differences from the ReasoningBank baseline

More than one attempt per task; a different extraction prompt over several
trajectories (parallel, restart); an extra model call per task to select the result
(parallel, vanilla) or to write notes (restart).

Details of this implementation that the paper leaves open:

- In parallel scaling only the selected trajectory is judged, for the record. The
  published self-contrast does not use the judge. (The reference code runs no judge
  in its scaling pipeline either.)
- The self-contrast extraction uses the extractor's temperature (1.0). The reference
  code uses 0.7 for this call; the paper states 1.0 for extraction in general.
- Attempts differ by sampling. The paper relies on a decoding temperature of 0.7 for
  that; with a model that accepts no temperature, variety comes from the model's
  default sampling.

## Parameters

All of the baseline's, plus:

| Option | Default | Meaning |
|---|---|---|
| `scaling` | `parallel` | `parallel`, `vanilla` or `restart` |
| `scaling_k` | 5 | attempts per task; the paper's headline result uses 5, its figure 4 varies 1 to 5 |
| `memory` | true | false scales without memory |

## What is reported

`mean_score` and `success_rate` are of the selected attempt (the paper's Best-of-N).
`mean_first_attempt_score` and `first_attempt_success_rate` are of one attempt (the
paper's Pass@1, which takes one at random; attempts are exchangeable, so the first is
one at random). `mean_best_attempt_score` and `any_attempt_success_rate` use the
simulator's ground truth to pick the best attempt: an upper bound no selector can
exceed, not something the method achieves.

## Running it

```bash
sea run --method matts --set scaling_k=3 --env toy-scan --regime small_battery --seeds 0:3 --llm offline-demo --out runs/matts-dry
```

```bash
sea compare run --protocol protocols/scan_scaling.json --out runs/scan-scaling
```

## Expected behaviour and limitations

From the paper, on WebArena-Shopping with Gemini 2.5 Flash: 49.7 to 55.1 with
parallel k = 5, 49.7 to 54.5 with sequential, 52.4 without aggregation, and between
39.0 and 42.2 without memory. None of this has been measured here.

Cost grows linearly with k: each attempt is a full episode. In a simulator an
attempt is also k times the environment interaction, on the same initial state,
which the paper's web tasks only approximate.

A point specific to seeded simulators: all k attempts start from the same state, so
differences between them are due to the agent alone. That makes the contrast cleaner
than on a live website. It also means Best-of-N selects among attempts at the *same*
episode, which flatters the result compared with a single attempt.
