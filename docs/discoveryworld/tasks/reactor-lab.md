# Reactor Lab

Find which instrument reading determines a quantum crystal's resonance frequency, and the formula, from crystals whose frequencies are known.

| | |
|---|---|
| Scenario name | `Reactor Lab` |
| Difficulties | Easy, Normal, Challenge |
| Step limit (paper) | Easy 100; Normal and Challenge 1000 |
| Benchmark seeds | 0 to 4 |
| Sub-goals | Easy 5, Normal 7, Challenge 7 |
| Critical questions per world | Easy 2, Normal 2, Challenge 2 |
| Action detectors | controls (the crystals with known frequencies measured) and the generic ones |

## The task

Quantum crystals power a reactor only when their reactors are tuned to the crystal's resonance frequency. The frequencies of some crystals are known (they sit in working reactors). Measuring the known crystals with the instruments and relating one instrument's reading to the known frequencies gives the formula, which predicts the frequency of each unknown crystal. The agent sets the unknown reactors to the predicted frequencies and installs the crystals.

## What changes with the difficulty

| | Easy | Normal | Challenge |
|---|---|---|---|
| What has to be found | a proportional formula, frequency = a × reading, for 1 unknown crystal; one instrument is provided | which of 5 instruments matters and a linear formula with an offset, for 2 unknown crystals | which instrument matters and a quadratic formula, for 2 unknown crystals (3 known) |
| Tools and instruments in the world | microscope | radiation meter, microscope, spectrometer, densitometer, thermometer | radiation meter, microscope, spectrometer, densitometer, thermometer |
| Teleport locations | start location | reactor lab, science lab (crystal bench), science lab (instruments) | reactor lab, science lab (crystal bench), science lab (instruments) |

Task text shown to the agent at seed 0:

- **Easy.** You are at the Quantum Reactor Lab on Planet X. Quantum Crystals offer the potential to generate a great deal of power, but require their respective crystal reactors to be tuned to a specific frequency that appears unique for each crystal. Through great effort, a previous research scientist manually stumbled upon the correct frequencies for Crystal 1 and Crystal 2, which are in their respective reactors. Your task is to use science to figure out the correct frequency for Crystal 3, set it's reactor to the appropriate frequency, and install the crystal. Once all three crystals are installed, the reactor will be able to generate a great deal of power. To support your task, a scientific instrument is available in the lab.
- **Normal.** You are at the Quantum Reactor Lab on Planet X. Quantum Crystals offer the potential to generate a great deal of power, but require their respective crystal reactors to be tuned to a specific frequency that appears unique for each crystal. Through great effort, a previous research scientist manually stumbled upon the correct frequencies for Crystal 1 and Crystal 2, which are in their respective reactors. Your task is to use science to figure out the correct frequency for Crystal 3 and Crystal 4, set their reactors to the appropriate frequency, and install the crystals. Once all four crystals are installed, the reactor will be able to generate a great deal of power. To support your task, a number of scientific instruments are available in the lab.
- **Challenge.** You are at the Quantum Reactor Lab on Planet X. Quantum Crystals offer the potential to generate a great deal of power, but require their respective crystal reactors to be tuned to a specific frequency that appears unique for each crystal. Through great effort, a previous research scientist manually stumbled upon the correct frequencies for Crystal 1, Crystal 2, and Crystal 3, which are in their respective reactors. Your task is to use science to figure out the correct frequency for Crystal 4 and Crystal 5, set their reactors to the appropriate frequency, and install the crystals. Once all four crystals are installed, the reactor will be able to generate a great deal of power. To support your task, a number of scientific instruments are available in the lab.

## Procedural progress: the sub-goals

The share of these that are reached is DiscoveryWorld's procedural score (`progress` in this repository's reports).

**Easy**

1. The quantum crystals have each been in an agent's inventory
2. Each crystal has been examined by the critical instrument
3. The resonance frequency of the unknown reactors have been changed
4. The resonance frequency of the unknown reactors is correct
5. The reactors have been successfully activated

**Normal**

1. The quantum crystals have each been in an agent's inventory
2. Each scientific instrument has been used with at least one crystal
3. Each crystal has been examined by at least one instrument
4. Each crystal has been examined by the critical instrument
5. The resonance frequency of the unknown reactors have been changed
6. The resonance frequency of the unknown reactors is correct
7. The reactors have been successfully activated

**Challenge**

1. The quantum crystals have each been in an agent's inventory
2. Each scientific instrument has been used with at least one crystal
3. Each crystal has been examined by at least one instrument
4. Each crystal has been examined by the critical instrument
5. The resonance frequency of the unknown reactors have been changed
6. The resonance frequency of the unknown reactors is correct
7. The reactors have been successfully activated

## Explanatory knowledge: the critical questions

A grader model answers each question about the agent's knowledge with DiscoveryWorld's own prompt (`discovery/knowledge.py`). At seed 0:

**Easy**

- Does it clearly state that the resonance frequency of the crystals is dependent upon the microscope reading?
- Does it clearly state that the relationship is linear, with the crystal resonance frequency = (59 * microscope reading)  (i.e. a slope of 59, and no offset)?

**Normal**

- Does it clearly state that the resonance frequency of the crystals is dependent upon the densitometer reading?
- Does it clearly state that the relationship is linear, with the crystal resonance frequency = (96 * densitometer reading) + 102 (i.e. a slope of 96 and an offset of 102)?

**Challenge**

- Does it clearly state that the resonance frequency of the crystals is dependent upon the thermometer reading?
- Does it clearly state that the relationship is quadratic, with the crystal resonance frequency = (13 * thermometer reading)^2 + (32 * thermometer reading) + 189 (i.e. `y = a*x^2 + b*x + c`, with `a` = 13, `b` = 32, and `c` = 189)?

## What changes with the seed

The hidden answer, read from each world's critical questions:

| seed | Easy | Normal | Challenge |
|---|---|---|---|
| 0 | (59 * microscope reading) | (96 * densitometer reading) + 102 | (13 * thermometer reading)^2 + (32 * thermometer reading) + 189 |
| 1 | (78 * densitometer reading) | (108 * thermometer reading) + 97 | (19 * densitometer reading)^2 + (27 * densitometer reading) + 199 |
| 2 | (66 * spectrometer reading) | (101 * microscope reading) + 94 | (15 * microscope reading)^2 + (24 * microscope reading) + 39 |
| 3 | (74 * thermometer reading) | (106 * radiation meter reading) + 95 | (18 * spectrometer reading)^2 + (25 * spectrometer reading) + 513 |
| 4 | (59 * radiation meter reading) | (96 * spectrometer reading) + 102 | (13 * radiation meter reading)^2 + (32 * radiation meter reading) + 627 |

Every seed hides a different answer at every difficulty.

## Measuring investigative behaviour here

The detector records whether the crystals whose frequencies are known were measured (`controls`) and how many such reference measurements were made: without them the formula cannot be fitted. Trying several instruments on the same crystal counts as testing alternatives.

## Notes

- At Easy, seeds 0 and 4 share the slope 59 but with different instruments (microscope, radiation meter), so their critical questions differ.
- Readings of the radiation meter include a random background that DiscoveryWorld draws from an unseeded generator; this repository seeds it per world.
- Reactor Lab is a `new_theme` world in the main protocol.

## Run it

DiscoveryWorld's ReAct baseline on the five Easy worlds, with a local model:

```bash
sea run --method no_memory --agent react --env discoveryworld --scenario "Reactor Lab" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/reactor-lab-react
```

ReasoningBank on the same worlds with the Hypothesizer as the actor:

```bash
sea run --method reasoningbank --agent hypothesizer --env discoveryworld --scenario "Reactor Lab" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/reactor-lab-rb
```

Every agent and method, and which combinations work: [`../../agents.md`](../../agents.md). All scenarios: [`../README.md`](../README.md).
