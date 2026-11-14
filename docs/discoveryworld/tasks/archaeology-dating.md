# Archaeology Dating

Date artifacts with a radiometric instrument and mark the oldest; at Challenge, first work out which channel of an unfamiliar instrument dates anything at all.

| | |
|---|---|
| Scenario name | `Archaeology Dating` |
| Difficulties | Easy, Normal, Challenge |
| Step limit (paper) | Easy 100; Normal and Challenge 1000 |
| Benchmark seeds | 0 to 4 |
| Sub-goals | Easy 4, Normal 6, Challenge 7 |
| Critical questions per world | Easy 2, Normal 2, Challenge 4 |
| Action detectors | Challenge: controls (the known-age reference artifacts measured); all: the generic ones |

## The task

The agent dates ancient artifacts with a radiocarbon meter (Easy, Normal) or a multi-channel radioisotope meter (Challenge) and places a red flag beside the oldest artifact (Easy) or beside the sign of the dig site with the oldest artifact (Normal, Challenge). At Normal and Challenge the artifacts first have to be dug up with a shovel. At Challenge three artifacts of known relative age (a stone hammer, a bronze chisel, iron tongs) lie uncovered: only by measuring these references can the agent find the channel whose values fall with age.

## What changes with the difficulty

| | Easy | Normal | Challenge |
|---|---|---|---|
| What has to be found | the oldest of 3 artifacts in a store room (direct radiocarbon ages) | the dig site, of 3, with the oldest artifact (excavate, then date) | which radioisotope channel tracks age, from 3 reference artifacts; then the oldest of 3 unknown artifacts at 6 dig sites |
| Tools and instruments in the world | radiocarbon meter, flag | shovel, flag, radiocarbon meter | shovel, flag, radioisotope meter |
| Teleport locations | starting location | base camp, dig site 1, dig site 2, dig site 3 | base camp, dig site 1, dig site 2, dig site 3, dig site 4, dig site 5, dig site 6 |

Task text shown to the agent at seed 0:

- **Easy.** You are in archaeological dig store room on Planet X. 3 ancient artifacts have been found. Your task is to date the artifacts with the radiocarbon meter. Then, once completed, place the red flag directly beside (i.e. one square right/to the west) of the artifact with the oldest age.
- **Normal.** You are on an archaeological dig on Planet X. 3 ancient sites have been found. Your task is to excavate the sites, and date any artifacts with the radiocarbon meter. Then, once completed, place the red flag beside the sign of the dig site with the oldest artifact.
- **Challenge.** You are on an archaeological dig on Planet X. 6 sites of suspected ancient artifacts have been found, 3 of which have already been uncovered. It's not clear how or if radioisotope dating works on Planet X, or how it would differ from Earth, but your task is to figure out if it can be used. Your task is to excavate the remaining sites, and figure out a way to use the radioisotope meter to approximately date the artifacts. Then, once completed, place the red flag beside the sign of the dig site with the oldest artifact.

## Procedural progress: the sub-goals

The share of these that are reached is DiscoveryWorld's procedural score (`progress` in this repository's reports).

**Easy**

1. The radiocarbon meter has been in an agent's inventory
2. The flag has been in an agent's inventory
3. The artifacts have been dated with the radiocarbon meter
4. The flag has been placed in the correct location

**Normal**

1. The radiocarbon meter has been in an agent's inventory
2. The shovel has been in an agent's inventory
3. The flag has been in an agent's inventory
4. The artifacts have been uncovered
5. The artifacts have been dated with the radiocarbon meter
6. The flag has been placed in the correct location

**Challenge**

1. The radioisotope meter has been in an agent's inventory
2. The shovel has been in an agent's inventory
3. The flag has been in an agent's inventory
4. 3 unknown artifacts have been uncovered
5. The radioisotope meter has been used on 3 seed artifacts
6. The radioisotope meter has been used on 3 unknown artifacts
7. The flag has been moved to the correct location

## Explanatory knowledge: the critical questions

A grader model answers each question about the agent's knowledge with DiscoveryWorld's own prompt (`discovery/knowledge.py`). At seed 0:

**Easy**

- Does it clearly state that the artifact with age 675000 years is the oldest?
- Does it clearly state the ages of the other younger artifacts (in years), which are: `150000, 500000`?

**Normal**

- Does it clearly state that the artifact at Dig Site #2 is the oldest, because it's age is 675000 years?
- Does it clearly state the ages of the other younger artifacts (in years), which are: `150000, 500000`?

**Challenge**

- Does it clearly make the realization (or assumption) that the known artifacts are from the `stone age`, `bronze age`, and `iron age`, or otherwise assume that the stone artifact is the oldest, the bronze artifact is the middle, and the iron artifact is the youngest?
- Does it clearly state that with radioisotope dating, artifacts that are younger should have higher radioisotope values, and/or older artifacts should have lower values?
- Does it clearly state that Radioisotope Channel 3 shows a pattern where the (1) stone artifact has the lowest value, (2) bronze artifact has a medium value, and (3) iron artifact has the highest value, making it likely useful for radioisotope dating?
- Does it clearly state that the artifact at Dig Site #6 has the lowest Radioisotope Channel 3 value, signifying that it is the oldest of the 3 unknown artifacts?

## What changes with the seed

The hidden answer, read from each world's critical questions:

| seed | Easy | Normal | Challenge |
|---|---|---|---|
| 0 | oldest 675000 y; others 150000, 500000 | site #2, 675000 y; others 150000, 500000 | channel 3; oldest at site #6 |
| 1 | oldest 725000 y; others 230000, 370000 | site #2, 725000 y; others 230000, 370000 | channel 3; oldest at site #5 |
| 2 | oldest 890000 y; others 410000, 150000 | site #2, 890000 y; others 410000, 150000 | channel 2; oldest at site #4 |
| 3 | oldest 890000 y; others 675000, 230000 | site #3, 890000 y; others 675000, 230000 | channel 2; oldest at site #5 |
| 4 | oldest 890000 y; others 725000, 150000 | site #1, 890000 y; others 725000, 150000 | channel 2; oldest at site #4 |

Seeds that hide the same answer (a memory of answers is not tested by moving between them): Challenge: seeds 2, 4 hide the same answer.

## Measuring investigative behaviour here

At Challenge the detector records whether the reference artifacts were measured before the answer (a control: a case where the answer is known) and how many reference measurements were taken. Elsewhere only the generic detectors apply (artifacts dated before the flag was placed).

## Notes

- At Easy, seeds 2, 3 and 4 all have their oldest artifact at 890,000 years (the younger ones differ), so they share one of their two critical questions. The main protocol (Easy) therefore uses seeds 2 to 4 for experience and 0 and 1 as new worlds (`protocols/discovery_main.json`); `sea discovery check` reports such overlaps.
- The Challenge knowledge questions ask for the reasoning (that younger artifacts should read higher, which channel shows the pattern), not only the site.

## Run it

DiscoveryWorld's ReAct baseline on the five Easy worlds, with a local model:

```bash
sea run --method no_memory --agent react --env discoveryworld --scenario "Archaeology Dating" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/archaeology-dating-react
```

ReasoningBank on the same worlds with the Hypothesizer as the actor:

```bash
sea run --method reasoningbank --agent hypothesizer --env discoveryworld --scenario "Archaeology Dating" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/archaeology-dating-rb
```

Every agent and method, and which combinations work: [`../../agents.md`](../../agents.md). All scenarios: [`../README.md`](../README.md).
