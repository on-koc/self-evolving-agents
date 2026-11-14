# Plant Nutrients

Find which soil nutrient, at which level or in which combination, makes the plants of Planet X grow.

| | |
|---|---|
| Scenario name | `Plant Nutrients` |
| Difficulties | Easy, Normal, Challenge |
| Step limit (paper) | Easy 100; Normal and Challenge 1000 |
| Benchmark seeds | 0 to 4 |
| Sub-goals | Easy 3, Normal 6, Challenge 6 |
| Critical questions per world | Easy 1, Normal 1, Challenge 1 |
| Action detectors | generic: measurements, distinct instruments and targets, candidates tested before the answer, premature commitment |

## The task

A botanical research station has a pilot field of soil plots, each with a different nutrient make-up, some already growing plants (mushrooms). With the soil nutrient meter the agent reads the plots; comparing plots with and without growth points to the nutrient. At Easy the answer is entered into the soil controller; at Normal and Challenge the agent sets the nutrients of experimental fields through their controllers, plants seeds with a shovel and grows at least two plants to maturity.

## What changes with the difficulty

| | Easy | Normal | Challenge |
|---|---|---|---|
| What has to be found | which of 5 nutrients must be present (6 plots) | which nutrient at which level, low, medium or high (12 plots) | a rule over one or two nutrients and their levels, such as "thorium at medium or potassium at high, but not both" (18 plots) |
| Tools and instruments in the world | soil nutrient controller, soil nutrient meter | soil nutrient controller (field #1), soil nutrient meter, shovel, seed jar, soil nutrient controller (field #2), soil nutrient controller (field #3) | soil nutrient controller (field #1), soil nutrient meter, shovel, seed jar, soil nutrient controller (field #2), soil nutrient controller (field #3) |
| Teleport locations | initial location | Experimental Field #1, Experimental Field #2, Experimental Field #3, Pilot Field, Storage Building | Experimental Field #1, Experimental Field #2, Experimental Field #3, Pilot Field, Storage Building |

Task text shown to the agent at seed 0:

- **Easy.** You are at a botanical research station on Planet X. The plants on Planet X only appear to grow in the presence of an unusual nutrient uncommon on Earth. Other scientists have narrowed down the nutrient to be one of the following: Potassium, Titanium, Lithium, Thorium, or Barium. Your task is to figure out which nutrient it is, and inter this answer into the Soil Controller computer. To support your research, a pilot field was set up with 6 plots of soil, each containing a randomly chosen nutrient. The research station is also equipped with a soil nutrient meter.
- **Normal.** You are at a botanical research station on Planet X. A species of plant has been identified that appears to grow very quickly in the presence of an unusual nutrient uncommon on Earth. Other scientists have narrowed down the nutrient to be one of the following: Potassium, Titanium, Lithium, Thorium, or Barium. Your task is to figure out which nutrient it is, and what specific amount of the nutrient (low, medium, or high) is required in the soil for the plant to grow. To support your work, a pilot field was set up with 12 plots of soil, each with a different combination of nutrients. The pilot field is located to the south west part of the research station. The research station is equipped with three test fields, where you can configure the nutrient levels in the field using the nearby soil nutrient controller. Once you configure the nutrients for a field, it *can't* be changed again. Under the right conditions, the plant tends to grow very quickly, so you should be able to see the results of your work within a few steps. Inside the storage facility are some tools that may be helpful for your work, including a soil nutrient meter, a jar of seeds, and a shovel. To plant the seeds, dig a hole in the soil, place a seed in the hole, then put the soil back into the hole. If the conditions are correct, the plant will grow from the seed. As part of your discovery process, you should grow at least 2 new plants to maturity.
- **Challenge.** You are at a botanical research station on Planet X. A species of plant has been identified that appears to grow very quickly in the presence of unusual nutrient(s) uncommon on Earth. Other scientists have narrowed down the nutrient list to include the following: Potassium, Titanium, Lithium, Thorium, or Barium. Your task is to figure out what nutrient or combination of nutrients make the plants grow, including what specific amount of the nutrient(s) (i.e. low, medium, or high) is required in the soil for the plant to grow. To support your work, a pilot field was set up with 18 plots of soil, each with a different combination of nutrients. The pilot field is located to the south west part of the research station. The research station is equipped with three test fields, where you can configure the nutrient levels in the field using the nearby soil nutrient controller. Once you configure the nutrients for a field, it *can't* be changed again. Under the right conditions, the plant tends to grow very quickly, so you should be able to see the results of your work within a few steps. Inside the storage facility are some tools that may be helpful for your work, including a soil nutrient meter, a jar of seeds, and a shovel. To plant the seeds, dig a hole in the soil, place a seed in the hole, then put the soil back into the hole. If the conditions are correct, the plant will grow from the seed. As part of your discovery process, you should grow at least 2 new plants to maturity.

## Procedural progress: the sub-goals

The share of these that are reached is DiscoveryWorld's procedural score (`progress` in this repository's reports).

**Easy**

1. The soil nutrient meter has been in an agent's inventory
2. The soil nutrient meter has been used on at least 2 squares of soil from the pilot field
3. The correct nutrient has been selected

**Normal**

1. The soil nutrient meter has been in an agent's inventory
2. The shovel has been in an agent's inventory
3. The seed jar has been in an agent's inventory
4. The soil nutrient meter has been used on at least 2 squares of soil from the pilot field
5. At least 2 seeds have been planted in the test fields
6. At least two new plants (mushrooms) have been grown to maturity in the test fields

**Challenge**

1. The soil nutrient meter has been in an agent's inventory
2. The shovel has been in an agent's inventory
3. The seed jar has been in an agent's inventory
4. The soil nutrient meter has been used on at least 2 squares of soil from the pilot field
5. At least 2 seeds have been planted in the test fields
6. At least two new plants (mushrooms) have been grown to maturity in the test fields

## Explanatory knowledge: the critical questions

A grader model answers each question about the agent's knowledge with DiscoveryWorld's own prompt (`discovery/knowledge.py`). At seed 0:

**Easy**

- Does it clearly state that if a seed is placed in soil with the `potassium` nutrient present, then it will grow?

**Normal**

- Does it clearly state that if a seed is placed in soil with the `thorium` nutrient level of `medium`, then it will grow?

**Challenge**

- Does it clearly state something equivalent to the following rule: `The seed will grow if either thorium is present at a medium level, or potassium is present at a high level, but not both.`?

## What changes with the seed

The hidden answer, read from each world's critical questions:

| seed | Easy | Normal | Challenge |
|---|---|---|---|
| 0 | potassium | thorium at medium | either thorium is present at a medium level, or potassium is present at a high level, but not both |
| 1 | thorium | titanium at high | both titanium is present at a low level, and barium is present at a medium level |
| 2 | titanium | potassium at low | either potassium is present at a low level, or lithium is present at a high level |
| 3 | lithium | titanium at high | titanium is NOT present at a high level |
| 4 | barium | titanium at medium | either titanium is present at a low level, or lithium is present at a high level, but not both |

Seeds that hide the same answer (a memory of answers is not tested by moving between them): Normal: seeds 1, 3 hide the same answer.

## Measuring investigative behaviour here

Only the generic detectors apply (plots measured before the answer; premature commitment). Growing plants in fields set to candidate nutrient levels is an experiment with a control in all but name; recognising it is left to the model coder.

## Notes

- Plants take a number of steps to sprout and grow; at Normal and Challenge this makes the task long (the paper allows 1000 steps).
- Sprouting and growth times come from DiscoveryWorld's unseeded per-object generators; this repository seeds them per world, so the same actions give the same growth in every run.
- Plant Nutrients is a `new_theme` world in the main protocol: no experience world teaches it.

## Run it

DiscoveryWorld's ReAct baseline on the five Easy worlds, with a local model:

```bash
sea run --method no_memory --agent react --env discoveryworld --scenario "Plant Nutrients" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/plant-nutrients-react
```

ReasoningBank on the same worlds with the Hypothesizer as the actor:

```bash
sea run --method reasoningbank --agent hypothesizer --env discoveryworld --scenario "Plant Nutrients" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/plant-nutrients-rb
```

Every agent and method, and which combinations work: [`../../agents.md`](../../agents.md). All scenarios: [`../README.md`](../README.md).
