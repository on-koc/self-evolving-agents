# Proteomics

Find the animal species that is not native: the one whose protein measurements are outliers when all species are clustered.

| | |
|---|---|
| Scenario name | `Proteomics` |
| Difficulties | Easy, Normal, Challenge |
| Step limit (paper) | Easy 100; Normal and Challenge 1000 |
| Benchmark seeds | 0 to 4 |
| Sub-goals | Easy 4, Normal 4, Challenge 4 |
| Critical questions per world | Easy 1, Normal 1, Challenge 1 |
| Action detectors | generic: measurements, distinct instruments and targets, candidates tested before the answer, premature commitment |

## The task

The agent is in a biological preserve with several animal species and a statue of each. With the proteomics meter it measures each species' proteins; one species' values lie apart from the cluster the others form. The task ends when the red flag is dropped beside the statue of that species (Easy: one square to the west of it). Dropping the flag at the wrong statue completes the task unsuccessfully.

## What changes with the difficulty

| | Easy | Normal | Challenge |
|---|---|---|---|
| What has to be found | the outlier among 3 species, all in the research building; values in 2 dimensions | the outlier among 5 species spread over 12 possible animal areas; values in 2 dimensions | as Normal, but the protein values have 3 dimensions, so the outlier can hide in a 2-dimensional view |
| Tools and instruments in the world | proteomics meter, flag | proteomics meter, flag | proteomics meter, flag |
| Teleport locations | Animal Area 1, Animal Area 2, Animal Area 3, Instrument Table, Statue of a echojelly, Statue of a spheroid, Statue of a vortisquid | Instrument Table, Possible Animal Area 1, Possible Animal Area 10, Possible Animal Area 11, Possible Animal Area 12, Possible Animal Area 2, Possible Animal Area 3, Possible Animal Area 4, Possible Animal Area 5, Possible Animal Area 6, Possible Animal Area 7, Possible Animal Area 8, Possible Animal Area 9, Statue of a animaplant, Statue of a echojelly, Statue of a prismatic beast, Statue of a spheroid, Statue of a vortisquid | Instrument Table, Possible Animal Area 1, Possible Animal Area 10, Possible Animal Area 11, Possible Animal Area 12, Possible Animal Area 2, Possible Animal Area 3, Possible Animal Area 4, Possible Animal Area 5, Possible Animal Area 6, Possible Animal Area 7, Possible Animal Area 8, Possible Animal Area 9, Statue of a animaplant, Statue of a echojelly, Statue of a prismatic beast, Statue of a spheroid, Statue of a vortisquid |

Task text shown to the agent at seed 0:

- **Easy.** You are in a biological preserve on Planet X, that has 3 different animal species. We suspect that one of these animal species is not native to the area, but migrated from an isolated island in the recent past. Your task is to use the proteomics meter to analyze the proteins of each of the 3 animal species, which can be found in the research building you're in, and determine which species is the anomoly. Once you have completed your task, drop the red flag directly beside (i.e. one square left/to the west) the statue of the animal species that is the anomoly.
- **Normal.** You are in a biological preserve on Planet X, that has 5 different animal species. We suspect that one of these animal species is not native to the area, but migrated from an isolated island in the recent past. Your task is to use the proteomics meter to analyze the proteins of each of the 5 animal species, which can be found throughout the environment away from the central statue area, and determine which species is the anomoly. Once you have completed your task, return to the statue area and drop the red flag directly beside the statue of the animal species that is the anomoly.
- **Challenge.** You are in a biological preserve on Planet X, that has 5 different animal species. We suspect that one of these animal species is not native to the area, but migrated from an isolated island in the recent past. Your task is to use the proteomics meter to analyze the proteins of each of the 5 animal species, which can be found throughout the environment away from the central statue area, and determine which species is the anomoly. Once you have completed your task, return to the statue area and drop the red flag directly beside the statue of the animal species that is the anomoly.

## Procedural progress: the sub-goals

The share of these that are reached is DiscoveryWorld's procedural score (`progress` in this repository's reports).

**Easy**

1. The proteomics meter has been in an agent's inventory
2. The flag has been in an agent's inventory
3. The proteomics meter has been used on each of the 3 different animal types
4. The flag has been moved to the correct location

**Normal**

1. The proteomics meter has been in an agent's inventory
2. The flag has been in an agent's inventory
3. The proteomics meter has been used on each of the 5 different animal types
4. The flag has been moved to the correct location

**Challenge**

1. The proteomics meter has been in an agent's inventory
2. The flag has been in an agent's inventory
3. The proteomics meter has been used on each of the 5 different animal types
4. The flag has been moved to the correct location

## Explanatory knowledge: the critical questions

A grader model answers each question about the agent's knowledge with DiscoveryWorld's own prompt (`discovery/knowledge.py`). At seed 0:

**Easy**

- Does it clearly state that the vortisquid has proteomics values that appear to be outliers compared to the other animals, whose proteomics values all cluster together?

**Normal**

- Does it clearly state that the spheroid has proteomics values that appear to be outliers compared to the other animals, whose proteomics values all cluster together?

**Challenge**

- Does it clearly state that the spheroid has proteomics values that appear to be outliers compared to the other animals, whose proteomics values all cluster together?

## What changes with the seed

The hidden answer, read from each world's critical questions:

| seed | Easy | Normal | Challenge |
|---|---|---|---|
| 0 | vortisquid | spheroid | spheroid |
| 1 | animaplant | echojelly | echojelly |
| 2 | prismatic beast | vortisquid | vortisquid |
| 3 | spheroid | animaplant | animaplant |
| 4 | echojelly | prismatic beast | prismatic beast |

Every seed hides a different answer at every difficulty.

## Measuring investigative behaviour here

Only the generic detectors apply: how many animals were measured before the flag was placed (alternatives tested before committing) and whether the flag was placed after at most one measurement (premature commitment). Controls, confounds and revision are left to the model coder.

## Notes

- Normal and Challenge show the same task text; the only difference is the dimensionality of the data (DiscoveryWorld's `scenarios/proteomics.py`).
- Animals wander, so their positions change from step to step; their wandering uses DiscoveryWorld's unseeded generator, which this repository seeds per world (see [`../README.md`](../README.md#determinism)).
- Seed 5 hides the same species as seed 0 at every difficulty; seeds above 4 are outside the benchmark.

## Run it

DiscoveryWorld's ReAct baseline on the five Easy worlds, with a local model:

```bash
sea run --method no_memory --agent react --env discoveryworld --scenario "Proteomics" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/proteomics-react
```

ReasoningBank on the same worlds with the Hypothesizer as the actor:

```bash
sea run --method reasoningbank --agent hypothesizer --env discoveryworld --scenario "Proteomics" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/proteomics-rb
```

Every agent and method, and which combinations work: [`../../agents.md`](../../agents.md). All scenarios: [`../README.md`](../README.md).
