# Combinatorial Chemistry

Find the substance, or the mixture of substances in the right proportions, that removes rust from a key, then use the key to leave the shed.

| | |
|---|---|
| Scenario name | `Combinatorial Chemistry` |
| Difficulties | Easy, Normal, Challenge |
| Step limit (paper) | Easy 100; Normal and Challenge 1000 |
| Benchmark seeds | 0 to 4 |
| Sub-goals | Easy 7, Normal 8, Challenge 8 |
| Critical questions per world | Easy 1, Normal 1, Challenge 1 |
| Action detectors | chemistry tests (what the jar held each time the key went in; cleaning between tests; repeated failed tests) and the generic ones |

## The task

The agent is locked in a storage shed with a rusted key, a mixing jar, a bottle cleaner and chemical dispensers labelled only Substance A, B, C (and D). It fills the jar from dispensers, puts the key in and sees how much rust is removed. The jar keeps whatever was put in it until it is cleaned, so testing a second substance without cleaning tests a mixture. The task is complete when the agent is outside the shed.

## What changes with the difficulty

| | Easy | Normal | Challenge |
|---|---|---|---|
| What has to be found | which one of 4 substances removes rust | a mixture of at least 2 of 3 substances, 3 or 4 parts in all, in exact proportions | a mixture of at least 2 of 4 substances, 3 or 4 parts in all, in exact proportions; a larger shed |
| Tools and instruments in the world | jar, Dispenser (Substance A), Dispenser (Substance B), Dispenser (Substance C), Dispenser (Substance D), bottle cleaner | jar, Dispenser (Substance A), Dispenser (Substance B), Dispenser (Substance C), bottle cleaner | jar, Dispenser (Substance A), Dispenser (Substance B), Dispenser (Substance C), Dispenser (Substance D), bottle cleaner |
| Teleport locations | shed | shed | shed |

Task text shown to the agent at seed 0:

- **Easy.** You were venturing into the wilderness of Planet X to a storage shed to fetch some supplies. The shed door locked behind you, and your key appears too rusted to work in the lock. You remember one of the other colonists mentioning that one of the chemicals in the shed is a rust remover, but unfortunately the chemicals you see are all unlabelled.You need to figure out which is a rust remover, and use it to remove the rust from the key. Then, use the key to open the shed door, and make your way back to the colony. You have no means of communication with the other colonists, and must figure this out on your own. Some helpful notes: 1. The rusted key is in the shed. 2. The shed door is locked, and will only open using a non-rusted key. 3. You can add chemicals to the jar. Just use a chemical dispenser on the jar to add chemicals to the jar. 4. The solution is only a single chemical, and should not require mixing chemicals. If you add multiple chemicals into the same jar, they will automatically mix, having different properties than any single chemical. 5. Placing the rusted key into the jar will automatically apply the chemical in that jar to the key. If the chemical is correct, the rust will be removed, though it may up to 2 steps for this to happen. 6. If you need to clean the jar of chemicals to try a new chemical, use the bottle washer on the jar. 7. When you have successfully derusted the key and opened the door, please leave the shed.
- **Normal.** You were venturing into the wilderness of Planet X to a storage shed to fetch some supplies. The shed door locked behind you, and your key appears too rusted to work in the lock. You remember one of the other colonists mentioning that some combination of the chemicals in the shed could make a rust remover, but you can't remember the details. You need to figure out a way to remove the rust from the key, and use it to open the shed door, and make your way back to the colony. You have no means of communication with the other colonists, and must figure this out on your own. Some helpful notes: 1. The rusted key is in the shed. 2. The shed door is locked, and will only open using a non-rusted key. 3. You can mix chemicals in the jar. Just use a chemical dispenser on the jar to add chemicals to the jar. 4. Chemicals placed in the same jar will automatically mix, though it may take up to 2 steps for this to happen. 5. Placing the rusted key into the jar will automatically apply the chemicals to the key. If the chemical mixture is correct, the rust will be removed, though it may up to 2 steps for this to happen. 6. If you need to clean the jar of chemicals to try a new combination, use the bottle washer on the jar. 7. When you have successfully derusted the key and opened the door, please leave the shed.
- **Challenge.** You were venturing into the wilderness of Planet X to a storage shed to fetch some supplies. The shed door locked behind you, and your key appears too rusted to work in the lock. You remember one of the other colonists mentioning that some combination of the chemicals in the shed could make a rust remover, but you can't remember the details. You need to figure out a way to remove the rust from the key, and use it to open the shed door, and make your way back to the colony. You have no means of communication with the other colonists, and must figure this out on your own. Some helpful notes: 1. The rusted key is in the shed. 2. The shed door is locked, and will only open using a non-rusted key. 3. You can mix chemicals in the jar. Just use a chemical dispenser on the jar to add chemicals to the jar. 4. Chemicals placed in the same jar will automatically mix, though it may take a step or two for this to happen. 5. Placing the rusted key into the jar will automatically apply the chemicals to the key. If the chemical mixture is correct, the rust will be removed, though it may take a step or two. 6. If you need to clean the jar of chemicals to try a new combination, use the bottle washer on the jar. 7. When you have successfully derusted the key and opened the door, please leave the shed.

## Procedural progress: the sub-goals

The share of these that are reached is DiscoveryWorld's procedural score (`progress` in this repository's reports).

**Easy**

1. The key has been in an agent's inventory
2. The mixing jar has been in an agent's inventory
3. Each chemical dispenser has been used
4. The bottle cleaner has been used
5. The key has been placed in the jar at least once
6. The key is not rusted (includes levels for reduced amounts of rust)
7. The agent is outside the shed

**Normal**

1. The key has been in an agent's inventory
2. The mixing jar has been in an agent's inventory
3. Each chemical dispenser has been used
4. The bottle cleaner has been used
5. The jar contains a mixture of chemicals
6. The key has been placed in the jar at least once
7. The key is not rusted (includes levels for reduced amounts of rust)
8. The agent is outside the shed

**Challenge**

1. The key has been in an agent's inventory
2. The mixing jar has been in an agent's inventory
3. Each chemical dispenser has been used
4. The bottle cleaner has been used
5. The jar contains a mixture of chemicals
6. The key has been placed in the jar at least once
7. The key is not rusted (includes levels for reduced amounts of rust)
8. The agent is outside the shed

## Explanatory knowledge: the critical questions

A grader model answers each question about the agent's knowledge with DiscoveryWorld's own prompt (`discovery/knowledge.py`). At seed 0:

**Easy**

- Does it clearly state the rust remover compound is this compound: `Substance B`?

**Normal**

- Does it clearly state the rust remover compound is a mixture of exactly these compounds in exactly these proportions: `1 part Substance A, and 2 parts Substance C`?

**Challenge**

- Does it clearly state the rust remover compound is a mixture of exactly these compounds in exactly these proportions: `1 part Substance B, and 2 parts Substance C`?

## What changes with the seed

The hidden answer, read from each world's critical questions:

| seed | Easy | Normal | Challenge |
|---|---|---|---|
| 0 | Substance B | 1 part Substance A, and 2 parts Substance C | 1 part Substance B, and 2 parts Substance C |
| 1 | Substance D | 1 part Substance B, and 2 parts Substance C | 2 parts Substance B, and 2 parts Substance C |
| 2 | Substance C | 2 parts Substance A, and 1 part Substance C | 1 part Substance A, and 2 parts Substance C |
| 3 | Substance A | 1 part Substance A, 1 part Substance B, and 1 part Substance C | 2 parts Substance B, 1 part Substance C, and 1 part Substance D |
| 4 | Substance C | 1 part Substance A, 1 part Substance B, and 1 part Substance C | 3 parts Substance A, and 1 part Substance D |

Seeds that hide the same answer (a memory of answers is not tested by moving between them): Easy: seeds 2, 4 hide the same answer; Normal: seeds 3, 4 hide the same answer.

## Measuring investigative behaviour here

The best-instrumented theme. From the actions alone (`discovery/behaviours.py`): the contents of every test, so alternatives tested before the answer; whether the jar was cleaned before a test with different contents (confounds); whether a failed test was followed by a different one rather than repeated (revision); contaminated tests; repeated failed tests; and whether the first test used an earlier world's answer (`first_test_old_answer`).

## Notes

- Easy has only four possible answers and five seeds, so two seeds share one (seeds 2 and 4, Substance C); the main protocol therefore uses different seeds for this theme (`protocols/discovery_main.json`).
- The rust level of the key is reported by later observations ("key (no rust)"), which is how the detectors tell a working test from a failed one.
- Seed 5 hides the same substance as seed 0 at Easy.

## Run it

DiscoveryWorld's ReAct baseline on the five Easy worlds, with a local model:

```bash
sea run --method no_memory --agent react --env discoveryworld --scenario "Combinatorial Chemistry" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/combinatorial-chemistry-react
```

ReasoningBank on the same worlds with the Hypothesizer as the actor:

```bash
sea run --method reasoningbank --agent hypothesizer --env discoveryworld --scenario "Combinatorial Chemistry" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/combinatorial-chemistry-rb
```

Every agent and method, and which combinations work: [`../../agents.md`](../../agents.md). All scenarios: [`../README.md`](../README.md).
