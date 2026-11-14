# DiscoveryWorld in this repository

[DiscoveryWorld](https://github.com/allenai/discoveryworld) (Jansen et al., NeurIPS 2024)
is a simulated planet on which an agent completes scientific investigations: it chooses
instruments, takes measurements, talks to colonists and runs experiments. This page lists
every scenario it offers, how each is run here, and what holds for all of them. The
memory experiment built on it is described in [`../discoveryworld.md`](../discoveryworld.md).

## Scenarios

Every scenario and difficulty loads, steps and reports its scorecard here; a test does
this for all 35 combinations (`test_every_scenario_loads_and_steps`), and every
combination was also loaded at seeds 0 to 5.

| Scenario | Difficulties | Step limit (paper) | Seeds | Knowledge questions | Page |
|---|---|---|---|---|---|
| Proteomics | Easy, Normal, Challenge | 100 / 1000 / 1000 | 0-4 | 1 | [proteomics](tasks/proteomics.md) |
| Combinatorial Chemistry | Easy, Normal, Challenge | 100 / 1000 / 1000 | 0-4 | 1 | [combinatorial-chemistry](tasks/combinatorial-chemistry.md) |
| Archaeology Dating | Easy, Normal, Challenge | 100 / 1000 / 1000 | 0-4 | 2 / 2 / 4 | [archaeology-dating](tasks/archaeology-dating.md) |
| Plant Nutrients | Easy, Normal, Challenge | 100 / 1000 / 1000 | 0-4 | 1 | [plant-nutrients](tasks/plant-nutrients.md) |
| Reactor Lab | Easy, Normal, Challenge | 100 / 1000 / 1000 | 0-4 | 2 | [reactor-lab](tasks/reactor-lab.md) |
| Lost in Translation | Easy, Normal, Challenge | 100 / 1000 / 1000 | 0-4 | 1 / 2 / 4 | [lost-in-translation](tasks/lost-in-translation.md) |
| Space Sick | Easy, Normal, Challenge | 100 / 1000 / 1000 | 0-4 | 2 / 3 / 1 | [space-sick](tasks/space-sick.md) |
| It's (not) Rocket Science! | Easy, Normal, Challenge | 100 / 1000 / 1000 | 0-4 | 3 / 4 / 8 | [rocket-science](tasks/rocket-science.md) |
| Small Skills (10 unit tests) | Normal | 100 | 0-4 | none | [unit-tests](tasks/unit-tests.md) |
| Tutorial | Normal | not benchmarked (100 here) | 0 | none | [tutorial](tasks/tutorial.md) |

Each theme page gives the task, what changes with the difficulty, the sub-goals behind
the procedural score, the critical questions behind the knowledge score, the hidden
answer at every seed, which behaviour detectors apply, and commands to run it. The tables
there were produced from the worlds themselves.

```bash
sea envs
```

lists the scenarios with their difficulties and step limits.

## Running any scenario

A task is a scenario, a difficulty and a seed:

```bash
sea run --method no_memory --agent react --env discoveryworld --scenario "Space Sick" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/space-sick-react
```

- `--scenario` takes several names separated by `;`, and `themes` or `unit-tests` for
  the eight themes or the ten unit tests; `--difficulty` takes several separated by
  commas. `--order interleaved` alternates between them seed by seed.
- Without `--max-steps` a task gets the paper's limit: 100 for Easy and the unit tests,
  1000 for Normal and Challenge.
- `--agent` chooses who plays: DiscoveryWorld's own baselines (`hypothesizer`, `react`,
  `plan_execute`, `random`) or this repository's `stepwise` agent. `--method` chooses the
  memory: `no_memory` for a baseline as released, or `reasoningbank`, `matts`,
  `conditioned_retrieval`, `investigation_memory` on top of any agent that reads memory.
  Which combinations work, and why some do not: [`../agents.md`](../agents.md).
- `--agent-option NAME=VALUE` passes an option to the agent, for example
  `--agent-option observation=text` to the Hypothesizer.

## What the scores are

| Score | Source | In reports |
|---|---|---|
| task completion | the scorecard's `completedSuccessfully` | `completion` |
| procedural progress | the share of the scenario's sub-goals reached (`scoreNormalized`) | `progress` |
| explanatory knowledge | a grader model answers each critical question about the agent's knowledge, with DiscoveryWorld's own prompt | `knowledge` (`sea discovery grade`) |

Unit tests and the tutorial have no critical questions, so no knowledge score. The
episode also records how it ended (`ended_by`: the task marked complete, the agent
submitted, the step limit, or the agent's model-call limit).

## Seeds

DiscoveryWorld's benchmark uses seeds 0 to 4 (its README and the Hypothesizer and random
agent runners; its scenario catalogue numbers them 1 to 5 and the runners subtract one).
Its ReAct and Plan-and-Execute configurations iterate over the catalogue's numbers
directly, i.e. seeds 1 to 5. Seed 5 is outside the vetted range, and in several themes it
hides the same answer as seed 0 (Proteomics at every difficulty; Combinatorial
Chemistry, Plant Nutrients and Space Sick at Easy). This repository uses 0 to 4.

Within the benchmark seeds, a few pairs hide the same answer; each theme page lists them
(Combinatorial Chemistry Easy seeds 2 and 4, Normal seeds 3 and 4; Archaeology Dating
Challenge seeds 2 and 4; Plant Nutrients Normal seeds 1 and 3; Space Sick Challenge at
every seed). `sea discovery check PROTOCOL` refuses a memory experiment whose
"new world" hides an answer an experience world hides.

## Determinism

DiscoveryWorld seeds its world generator, but every object also gets its own generator
seeded by the operating system, and characters wander using Python's global generator.
In DiscoveryWorld 0.0.2 mushroom colours, plant sprouting and growth times, the background
of radiation readings, some sprites and the paths of wandering characters therefore
differ between processes for the same scenario and seed (observed: the same mushroom was
green, pink or yellow in three runs). The adapter gives DiscoveryWorld generators that
are seeded from the world when DiscoveryWorld leaves them unseeded
(`envs/discoveryworld.py`, `install_python312_compat`). The draws come from the same
distributions; the same world and the same actions now give the same observations in
every process (`test_worlds_are_the_same_in_every_process`), which is also what lets a
run be replayed from its model-call cache. Generators DiscoveryWorld seeds itself (the
world generator, object ids) give exactly the numbers they gave before, so the hidden
answers are unchanged.

## Other adaptations

- **Python 3.12 and later.** "It's (not) Rocket Science!" passes float bounds to
  `randint`, which Python 3.12 rejects; the same shim converts integral floats as Python
  3.11 did.
- **Output.** DiscoveryWorld prints verbosely and writes a picture of every observation;
  both are redirected (to nothing and to a temporary directory).
- **What the agent sees.** The observation as DiscoveryWorld's API returns it, without
  the images (for DiscoveryWorld's agents), or a compact text rendering (for the
  `stepwise` agent). The scorecard is never shown to an agent.
- **Ending an episode.** `SUBMIT` (ReAct, Plan-and-Execute) ends the episode without
  calling the simulator and without charging the step limit, as in DiscoveryWorld's
  runner.
