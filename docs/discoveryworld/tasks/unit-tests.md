# Unit tests (Small Skills)

Ten short tasks that test one skill each: talking, carrying, giving, measuring, doors, keys, navigation, search, reading the Discovery Feed and finding moving characters. DiscoveryWorld reports them separately from the discovery themes, as a check that an agent can operate the game at all.

| | |
|---|---|
| Difficulty | Normal only |
| Step limit (paper) | 100 |
| Benchmark seeds | 0 to 4 |
| Critical questions | none: these tasks test skills, not discoveries, so there is no knowledge score |
| Action detectors | the generic ones only (measurements, targets, premature commitment); the investigative behaviours do not apply |

| Test | Skill | Sub-goals | Seed variation |
|---|---|---|---|
| [Dialog Test](#small-skills-dialog-test) | following a dialog tree | 4 | the requested answer |
| [Pick and Place Test](#small-skills-pick-and-place-test) | picking up an object and putting it in a container | 2 | the object (microscope, spectrometer, ...) |
| [Pick and Give Test](#small-skills-pick-and-give-test) | giving an object to a character | 2 | the object and the character |
| [Instrument Measurement Test](#small-skills-instrument-measurement-test) | measuring with an instrument and acting on the reading | 3 | the object, the instrument and the decision rule |
| [Doors Test](#small-skills-doors-test) | opening doors on the way through a building | 2 | the layout |
| [Doors with Keys Test](#small-skills-doors-with-keys-test) | collecting keys and unlocking doors | 3 | the layout and key placement |
| [Navigation in a House Test](#small-skills-navigation-in-a-house-test) | finding a named place in a house | 2 | the layout |
| [Search Test](#small-skills-search-test) | finding an object somewhere in the world | 1 | where the flag is |
| [Discovery Feed Test](#small-skills-discovery-feed-test) | reading the Discovery Feed and following one poster | 2 | which poster to follow, and the object |
| [Moving Agents Test](#small-skills-moving-agents-test) | reaching characters who move | 1 | where the characters walk |

## Small Skills: Dialog Test

Sally asks the agent to choose a particular option at each of several stages of a dialog; choosing wrongly does not advance it. The character is reached by teleporting to it and turning to face it, then `TALK`.

Task text at seed 0: Your task is to follow the instructions of the other person in the room.

Sub-goals:

1. The agent has talked to the other person.
2. The agent has reached the second stage of the dialog tree.
3. The agent has reached the third stage of the dialog tree.
4. The agent has completed going through the dialog tree successfully.

## Small Skills: Pick and Place Test

One object on a table has to go into the pot.

Task text at seed 0: Your task is to pick up the `microscope` and place it in the `pot`.

At seed 1: Your task is to pick up the `spectrometer` and place it in the `pot`.

Sub-goals:

1. Pick up the microscope.
2. Place the microscope in the pot.

## Small Skills: Pick and Give Test

One object has to be given to one of three characters (`PUT` with the character as the second argument).

Task text at seed 0: Your task is to give Gail the `microscope`.

At seed 1: Your task is to give Yugo the `spectrometer`.

Sub-goals:

1. Pick up the microscope.
2. Give the microscope to Gail.

## Small Skills: Instrument Measurement Test

Measure an object with the named instrument and put it into one of four pots according to the reading (for example, spectrum channel 3 below 2.5 goes into pot A). The reading is a high-importance message: DiscoveryWorld's ReAct runs never show it as `extended_action_message`, because their logging reads the observation first (see [`../../agents.md`](../../agents.md)).

Task text at seed 0: Your task is measure the spectrum (on channel 3) of the `seed`, and place it in a specific container depending on the measured value. If the value is less than 2.5, place it in pot A. If the value is between 2.5 and 5.0, place it in pot B. If the value is between 5.0 and 7.5, place it in pot C. If the value is greater than 7.5, place it in pot D.

At seed 1: Your task is measure the microscopic description of the `fertilizer bag`, and place it in a specific container depending on the measured value. If the object has a rough surface, place it in pot A. If the object has a smooth surface, place it in pot B. If the object has a bumpy surface, place it in pot C. If the object has any other kind of surface, place it in pot D.

Sub-goals:

1. Pick up the seed.
2. Measure the seed with the spectrometer.
3. Place the seed in pot B.

## Small Skills: Doors Test

Go through a building, opening every door, to a flag, and pick it up.

Task text at seed 0: Your task is to enter the building, and go through all the doors until you reach a flag. When you see the flag, pick it up to complete the task. Note that for the task to be considered complete, all the doors must be opened, too.

Sub-goals:

1. Pick up the flag.
2. Open all doors in the building.

## Small Skills: Doors with Keys Test

As the Doors Test, but doors need keys that lie in the building.

Task text at seed 0: Your task is to enter the building, and go through all the doors until you reach a flag. When you see the flag, pick it up to complete the task. Note that for the task to be considered complete, all the doors must be opened, too.

Sub-goals:

1. Pick up the flag.
2. Open all doors in the building.
3. Collect all keys in the building.

## Small Skills: Navigation in a House Test

Drop the flag inside a named room or area of a furnished house.

Task text at seed 0: Your task is to drop the flag inside the following location: `soil plot`.

Sub-goals:

1. Be inside the soil plot.
2. Drop the flag in the soil plot.

## Small Skills: Search Test

A flag lies somewhere in the world; find it and pick it up.

Task text at seed 0: Your task is to find the flag (located somewhere in the environment) and pick it up.

Sub-goals:

1. Have the flag in your inventory.

## Small Skills: Discovery Feed Test

Several posters on the Discovery Feed give conflicting instructions; follow the named one (which is a pick-and-place).

Task text at seed 0: Your task is to read the Discovery Feed, and follow the instructions posted by `Dors`, while ignoring the instructions by the other posters.

At seed 1: Your task is to read the Discovery Feed, and follow the instructions posted by `Arkady`, while ignoring the instructions by the other posters.

Sub-goals:

1. Pick up the microscope.
2. Place the microscope in the pot.

## Small Skills: Moving Agents Test

Talk to three characters who walk around and warn each that it is about to rain.

Task text at seed 0: Your task is to talk to each of the 3 other characters in this environment, and warn each that it's about to rain.

Sub-goals:

1. The agent has talked to all other characters.

## Run them

All ten unit tests, five seeds each, with DiscoveryWorld's ReAct baseline:

```bash
sea run --method no_memory --agent react --env discoveryworld --scenario unit-tests --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/unit-tests-react
```

The unit tests exist at Normal difficulty only; `--difficulty` defaults to Normal. Every agent: [`../../agents.md`](../../agents.md).
