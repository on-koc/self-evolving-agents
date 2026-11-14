# Tutorial

A short guided scenario that DiscoveryWorld offers people before they play; it is not part of the benchmark and has no knowledge questions.

| | |
|---|---|
| Scenario name | `Tutorial` |
| Difficulty | Normal only |
| Seeds | one world (seed 0) |
| Step limit | not benchmarked; 100 by default here |
| Critical questions | none |

## The task

The agent wakes in a house and has to learn from the elder what is wanted (a key), get it and leave the room. It is useful as a quick check that an agent can talk, pick up and use doors.

Task text: Where am I?! You just wake up in a strange place... It's discovery time! Some helpful notes: 1. Feel free to explore your surroundings. 2. The elder knows the completion code for the tutorial.

Teleport locations: Front Door, Kitchen, Near Elder, Starting Location.

Sub-goals:

1. The agent has learned about the elder's request.
2. The key is in the agent's inventory.
3. The agent has left the roo  m.

## Run it

```bash
sea run --method no_memory --agent react --env discoveryworld --scenario Tutorial --seeds 0 --llm offline-demo --out runs/tutorial-dry
```
