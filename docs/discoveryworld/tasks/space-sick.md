# Space Sick

Find what makes colonists ill from the food, and how to detect it.

| | |
|---|---|
| Scenario name | `Space Sick` |
| Difficulties | Easy, Normal, Challenge |
| Step limit (paper) | Easy 100; Normal and Challenge 1000 |
| Benchmark seeds | 0 to 4 |
| Sub-goals | Easy 4, Normal 5, Challenge 7 |
| Critical questions per world | Easy 2, Normal 3, Challenge 1 |
| Action detectors | generic: measurements, distinct instruments and targets, candidates tested before the answer, premature commitment |

## The task

Some food on Planet X makes people mildly ill. At Easy, one of three mushrooms is contaminated, and only one of five instruments detects the pathogen; the contaminated mushroom goes into the jar. At Normal and Challenge the agent has to make colonists eat 10 mushrooms in a row without falling ill, with the help of the chef, the farmer and the science lab: some mushrooms carry mould, which the microscope shows directly and the spectrometer indirectly, and at Challenge a glowing rock becomes luminous near harmful mushrooms.

## What changes with the difficulty

| | Easy | Normal | Challenge |
|---|---|---|---|
| What has to be found | which instrument detects the pathogen, and so which mushroom is contaminated | that mould makes people ill, how to see it, and which mushroom colour(s) carry it | that the glowing rock detects harmful mushrooms (the same at every seed) |
| Tools and instruments in the world | radiation meter, densitometer, microscope, PH meter, spectrometer, jar | rock (glowing), shovel, microscope, petri dish, sampler, spectrometer, PH meter, radiation meter, thermometer, seed jar | rock (glowing), shovel, microscope, petri dish, sampler, spectrometer, PH meter, radiation meter, thermometer, seed jar |
| Teleport locations | initial location | barracks, cafeteria, cave, farm, farmers field, infirmary, science lab, town square | barracks, cafeteria, cave, farm, farmers field, infirmary, science lab, town square |

Task text shown to the agent at seed 0:

- **Easy.** Some of the food on Planet X has been contaminated with a pathogen that is causing mild stomach illness. You must determine which of the 3 mushrooms is contaminated, then place the contaminated mushroom in the jar for further analysis and disposal.
- **Normal.** The only food on this planet are local mushrooms, but after eating them, the colonist sometimes have upset stomachs. Your task is to figure out why people are feeling ill, and to prevent it. You must demonstrate this by having colonists successfully eat 10 mushrooms in a row without eventually feeling sick. Since the food causes only mild illness, and getting the colony established is important, the colonists have volunteered to be test subjects. The Chef in the Cafeteria can help you collect mushrooms, serve mushrooms from the cafeteria pot to the tables, and let the colonists know a meal is ready to eat, when you're ready. The colonists may post their status (like if they're feeling unwell) on the Discovery Feed (use 'v' to display it).After a colonist eats a mushroom, it will be automatically monitored by DiscoveryWorld for 50 turns to see if it gets sick. (Note: If it successfully eats another mushroom within that 50 turns, assuming both are good, it will still only count as a single good case.)
- **Challenge.** The only food on this planet are local mushrooms, but after eating them, the colonist sometimes have upset stomachs. Your task is to figure out why people are feeling ill, and to prevent it. You must demonstrate this by having colonists successfully eat 10 mushrooms in a row without eventually feeling sick. Since the food causes only mild illness, and getting the colony established is important, the colonists have volunteered to be test subjects. The Chef in the Cafeteria can help you collect mushrooms, serve mushrooms from the cafeteria pot to the tables, and let the colonists know a meal is ready to eat, when you're ready. The colonists may post their status (like if they're feeling unwell) on the Discovery Feed (use 'v' to display it).After a colonist eats a mushroom, it will be automatically monitored by DiscoveryWorld for 50 turns to see if it gets sick. (Note: If it successfully eats another mushroom within that 50 turns, assuming both are good, it will still only count as a single good case.)

## Procedural progress: the sub-goals

The share of these that are reached is DiscoveryWorld's procedural score (`progress` in this repository's reports).

**Easy**

1. Pick up the mushroom.
2. Use each measurement device with at least one food item.
3. Use the critical measurement device on the contaminated food item.
4. Place the infected food in the jar.

**Normal**

1. Collect at least one of each of the 4 different colors of mushrooms
2. Use each of the scientific instruments on an object
3. Use each of the scientific instruments on a mushroom
4. Have at least 10 mushrooms eaten by colonists
5. Have 10 mushrooms eaten by colonists without them getting sick

**Challenge**

1. Collect at least one of each of the 4 different colors of mushrooms
2. Use each of the scientific instruments on an object
3. Use each of the scientific instruments on a mushroom
4. Collect at least one of the glowing rocks
5. Have a glowing rock turn luminous
6. Have at least 10 mushrooms eaten by colonists
7. Have 10 mushrooms eaten by colonists without them getting sick

## Explanatory knowledge: the critical questions

A grader model answers each question about the agent's knowledge with DiscoveryWorld's own prompt (`discovery/knowledge.py`). At seed 0:

**Easy**

- Does it clearly state that one of the food items is contaminated with a pathogen (`Bacterium Species 138`)?
- Does it clearly state that the pathogen can be measured/detected with the densitometer?

**Normal**

- Does it clearly state that the mushrooms that make people ill have mold on them?
- Does it clearly state either that (1) the mold can be directly observed with the microscope, AND/OR (2) that the mold can be indirectly observed by elevated spectrometer readings, particularly with a value of 1.0 on Channel 5 of the spectrometer?
- Does it clearly state that the mushrooms that make people ill have the following color(s): `red`?

**Challenge**

- Does it clearly state that the glowing rock can be used as an instrument to detect harmful mushrooms, by becoming luminous when it is near a harmful mushroom?

## What changes with the seed

The hidden answer, read from each world's critical questions:

| seed | Easy | Normal | Challenge |
|---|---|---|---|
| 0 | Bacterium Species 138, detected with the densitometer | mould; ill-making colour(s): red | the glowing rock detects harmful mushrooms |
| 1 | Virus Strain 12, detected with the spectrometer | mould; ill-making colour(s): green | the glowing rock detects harmful mushrooms |
| 2 | Fungus Species 3, detected with the PH meter | mould; ill-making colour(s): yellow | the glowing rock detects harmful mushrooms |
| 3 | Parasite Species 7, detected with the microscope | mould; ill-making colour(s): pink | the glowing rock detects harmful mushrooms |
| 4 | Prion Strain 2, detected with the radiation meter | mould; ill-making colour(s): red and pink | the glowing rock detects harmful mushrooms |

Seeds that hide the same answer (a memory of answers is not tested by moving between them): Challenge: seeds 0, 1, 2, 3, 4 hide the same answer.

## Measuring investigative behaviour here

Only the generic detectors apply (instruments and items measured before the answer). Using every instrument on a known-good item is a control the action detectors do not read; the model coder does.

## Notes

- Space Sick Challenge is the one combination whose answer is the same at every seed: a memory of the answer and a memory of the method cannot be told apart there.
- Mushroom colours are drawn from DiscoveryWorld's unseeded per-object generators where a scenario does not set them, and illness timers from its global generator; this repository seeds both per world.
- Seed 5 repeats seed 0's answer at Easy and Normal.

## Run it

DiscoveryWorld's ReAct baseline on the five Easy worlds, with a local model:

```bash
sea run --method no_memory --agent react --env discoveryworld --scenario "Space Sick" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/space-sick-react
```

ReasoningBank on the same worlds with the Hypothesizer as the actor:

```bash
sea run --method reasoningbank --agent hypothesizer --env discoveryworld --scenario "Space Sick" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/space-sick-rb
```

Every agent and method, and which combinations work: [`../../agents.md`](../../agents.md). All scenarios: [`../README.md`](../README.md).
