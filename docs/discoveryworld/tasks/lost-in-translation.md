# Lost in Translation

Learn words of an unknown language from signs and from what villagers do, well enough to carry out a request.

| | |
|---|---|
| Scenario name | `Lost in Translation` |
| Difficulties | Easy, Normal, Challenge |
| Step limit (paper) | Easy 100; Normal and Challenge 1000 |
| Benchmark seeds | 0 to 4 |
| Sub-goals | Easy 2, Normal 3, Challenge 9 |
| Critical questions per world | Easy 1, Normal 2, Challenge 4 |
| Action detectors | generic: measurements, distinct instruments and targets, candidates tested before the answer, premature commitment |

## The task

Villagers speak a language the agent does not know. At Easy one villager, Gail, asks for an object by an unknown word; at Normal and Challenge the village elder makes a request that needs a word for an object, and at Challenge also words for a colour and a number, which the agent can learn at the paint shop and from the counting computer at the school. Signs and shops pair words with objects. The task is complete when the requested objects are in the elder's (Gail's) inventory.

## What changes with the difficulty

| | Easy | Normal | Challenge |
|---|---|---|---|
| What has to be found | what one word refers to (one of the objects on the table) | that 'Womple' means 'bring me', and the word for the requested object | as Normal, plus the words for a colour and a number (the request names how many, of which colour) |
| Tools and instruments in the world | rock (glowing), microscope, thermometer | shovel, flag, jar, measuring tape, computer | shovel, flag, jar, measuring tape, computer |
| Teleport locations | initial location | general store, key shop, paint shop, school, town square | general store, key shop, paint shop, school, town square |

Task text shown to the agent at seed 0:

- **Easy.** Your task is to talk to Gail and follow their instructions.
- **Normal.** You find yourself venturing into a small village of Planet X where everyone speaks a dialect unknown to you. An elder (at the center of the village) is trying to tell you something that seems very important. You need to figure out what the older is saying. Some helpful notes: 1. Even though you don't understand them, you can still interact with the inhabitants. 2. Look for signs to read, you might be able to decipher some words from them.
- **Challenge.** You find yourself venturing into a small village of Planet X where everyone speaks a dialect unknown to you. An elder (at the center of the village) is trying to tell you something that seems very important. You need to figure out what the older is saying. Some helpful notes: 1. Even though you don't understand them, you can still interact with the inhabitants. 2. Look for signs to read, you might be able to decipher some words from them.

## Procedural progress: the sub-goals

The share of these that are reached is DiscoveryWorld's procedural score (`progress` in this repository's reports).

**Easy**

1. Pick up the fertilizer bag.
2. Give the fertilizer bag to Gail.

**Normal**

1. The agent has learned about the elder's request.
2. Needed objects are in agent's inventory.
3. Needed objects are in elder's inventory.

**Challenge**

1. The agent has learned about the elder's request.
2. Needed objects are in agent's inventory.
3. Needed objects are in elder's inventory.
4. The agent visited the paint shop to learn about color.
5. The paint sign associated to the color has been read.
6. The agent visited the school to learn how to count.
7. The counting computer has been used.
8. The reset card was used on the computer.
9. The measuring tape has been used on the flagpole.

## Explanatory knowledge: the critical questions

A grader model answers each question about the agent's knowledge with DiscoveryWorld's own prompt (`discovery/knowledge.py`). At seed 0:

**Easy**

- Does it clearly state the word `Plork` refers to the `fertilizer bag`?

**Normal**

- Does it clearly state that: The word 'Womple' means something like 'bring me'?
- Does it clearly state that: The word 'blonk' means 'stick'?

**Challenge**

- Does it clearly state that: The word 'gleep' means 'orange'?
- Does it clearly state that: The word 'squarp' means 'four'?
- Does it clearly state that: The word 'Womple' means something like 'bring me'?
- Does it clearly state that: The word 'nushblort' means 'mushroom'?

## What changes with the seed

The hidden answer, read from each world's critical questions:

| seed | Easy | Normal | Challenge |
|---|---|---|---|
| 0 | Plork = fertilizer bag | Womple = bring me; blonk = stick | gleep = orange; squarp = four; Womple = bring me; nushblort = mushroom |
| 1 | Flubergast = microscope | Womple = bring me; nushblort = mushroom | flib = green; zorp = five; Womple = bring me; florpt = flower |
| 2 | Grundle = thermometer | Womple = bring me; florpt = flower | gleep = orange; blip = one; Womple = bring me; squibble = key |
| 3 | Froznak = radiation meter | Womple = bring me; squibble = key | flib = green; zorp = five; Womple = bring me; nushblort = mushroom |
| 4 | Blorpnik = mushroom | Womple = bring me; blurf = shovel | flib = green; blorp = three; Womple = bring me; florpt = flower |

Every seed hides a different answer at every difficulty.

## Measuring investigative behaviour here

Mostly dialog and reading; only the generic detectors apply. Testing an interpretation (offering an object, reading another sign) before committing to it is left to the model coder.

## Notes

- The dialog options are numbered; the action is `{"chosen_dialog_option_int": n}`.
- Normal seeds 0 and 4 share their task text and their first question ('Womple' = 'bring me'); the object word differs.

## Run it

DiscoveryWorld's ReAct baseline on the five Easy worlds, with a local model:

```bash
sea run --method no_memory --agent react --env discoveryworld --scenario "Lost in Translation" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/lost-in-translation-react
```

ReasoningBank on the same worlds with the Hypothesizer as the actor:

```bash
sea run --method reasoningbank --agent hypothesizer --env discoveryworld --scenario "Lost in Translation" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/lost-in-translation-rb
```

Every agent and method, and which combinations work: [`../../agents.md`](../../agents.md). All scenarios: [`../README.md`](../README.md).
