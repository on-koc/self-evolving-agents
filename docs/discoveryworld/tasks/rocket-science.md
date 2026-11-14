# It's (not) Rocket Science!

Compute the orbital speed for a launch from measurements of an unfamiliar planet; at Challenge, also choose and dose the propellant.

| | |
|---|---|
| Scenario name | `It's (not) Rocket Science!` |
| Difficulties | Easy, Normal, Challenge |
| Step limit (paper) | Easy 100; Normal and Challenge 1000 |
| Benchmark seeds | 0 to 4 |
| Sub-goals | Easy 3, Normal 6, Challenge 9 |
| Critical questions per world | Easy 3, Normal 4, Challenge 8 |
| Action detectors | generic: measurements, distinct instruments and targets, candidates tested before the answer, premature commitment |

## The task

The agent must enter the orbital speed for a given altitude into the launch terminal; there is one rocket and one try. A rocketry book gives the formulas. At Easy the planet's radius and gravity are given in the task. At Normal they have to be measured: the radius from the angle of sunlight at two observation posts (with a speed square), gravity from the period of a 1-metre pendulum. At Challenge the agent also tests three propellants with the load cell, rules out one with too little thrust and one too light to fit in the tank, and enters the fuel type and amount.

## What changes with the difficulty

| | Easy | Normal | Challenge |
|---|---|---|---|
| What has to be found | the orbital speed at 400 km for a planet with given radius and gravity | the planet's radius (two sun angles) and gravity (pendulum), then the orbital speed | as Normal, plus which of 3 propellants to use and how much |
| Tools and instruments in the world | load cell wall, load cell, 1-meter pendulum, computer, rocketry book, speed square, load cell interface | load cell wall, load cell, 1-meter pendulum, computer, rocketry book, speed square, load cell interface | load cell wall, load cell, 1-meter pendulum, computer, rocketry book, speed square, load cell interface |
| Teleport locations | control room, northern observation post, rocket, southern observation post, thrust test site | control room, northern observation post, rocket, southern observation post, thrust test site | control room, northern observation post, rocket, southern observation post, thrust test site |

Task text shown to the agent at seed 0:

- **Easy.** You are at the new Launch Site on Planet X. To better monitor the weather patterns, you were tasked to send a new probe on orbit at 400 kilometers from the ground. You were told to simply punch in the target orbital speed needed for such an altitude in the launch terminal and the system will take care of the rest. There is only one single-stage rocket, and this is a very important mission, so we better get it right the first time! Thankfully, you know the planet's characteristics, such as its mass and radius, are exactly the same as Earth. Good thing, you brought your faithful rocketry book with you! Here are some additional helpful notes: 1. The grid cells on Planet X are 1-meter square. 2. You can assume air resistance is neglible. 3. Pay attention to the units in the formulas. 4. The formulas are simplifications and may not be 100% accurate. 5. Keep as much decimal places in your calculations.
- **Normal.** You are at the new Launch Site on Planet X. To better monitor the weather patterns, you were tasked to send a new probe on orbit at 8061 kilometers from the ground. You were told to simply punch in the target orbital speed needed for such an altitude in the launch terminal and the system will take care of the rest. There is only one single-stage rocket, and this is a very important mission, so we better get it right the first time! Good thing, you brought your faithful rocketry book with you! Here are some additional helpful notes: 1. The grid cells on Planet X are 1-meter square. 2. You can assume air resistance is neglible. 3. Pay attention to the units in the formulas. 4. The formulas are simplifications and may not be 100% accurate. 5. Keep as much decimal places in your calculations. 6. Look around for two observation posts to the north and south.
- **Challenge.** You are at the new Launch Site on Planet X. To better monitor the weather patterns, you were tasked to send a new probe on orbit at 8061 kilometers from the ground. You were told to simply punch in the target orbital speed needed for such an altitude in the launch terminal and the system will take care of the rest. There is only one single-stage rocket, and this is a very important mission, so we better get it right the first time! Upon arriving at the launch site, you realized the rocket hasn't been fueled yet. You will need to figure which one of the three types of propellant to use and how much to put in the rocket. The rocket can hold a maximum of 10,000 liters of fuel, and it's weight can be determined using the load cell. Good thing, you brought your faithful rocketry book with you! Here are some additional helpful notes: 1. The grid cells on Planet X are 1-meter square. 2. You can assume air resistance is neglible. 3. Pay attention to the units in the formulas. 4. The formulas are simplifications and may not be 100% accurate. 5. Keep as much decimal places in your calculations. 6. Look around for two observation posts to the north and south.

## Procedural progress: the sub-goals

The share of these that are reached is DiscoveryWorld's procedural score (`progress` in this repository's reports).

**Easy**

1. The agent has read the rocketry book.
2. The agent has seen the launch terminal interface.
3. The agent has entered the correct target orbital velocity.

**Normal**

1. The agent has read the rocketry book.
2. The agent has seen the launch terminal interface.
3. The agent has entered the correct target orbital velocity.
4. The agent has measured light angle at two locations.
5. Pendulum was activated.
6. The agent has read the pendulum.

**Challenge**

1. The agent has read the rocketry book.
2. The agent has seen the launch terminal interface.
3. The agent has entered the correct target orbital velocity.
4. The agent has measured light angle at two locations.
5. Pendulum was activated.
6. The agent has read the pendulum.
7. The agent has seen the load cell interface.
8. The agent has tested the different fuel types with the load cell.
9. The agent has entered the correct fuel type and its amount.

## Explanatory knowledge: the critical questions

A grader model answers each question about the agent's knowledge with DiscoveryWorld's own prompt (`discovery/knowledge.py`). At seed 0:

**Easy**

- Does it clearly state the planet's radius is approximately 6371 km?
- Does it clearly state the planet's gravity is approximately 9.82 m/s^2?
- Does it clearly state the target orbit speed to reach an orbital height of 400 km is approximately 7672.7 m/s? (plus or minus 3 m/s)

**Normal**

- Does it clearly state the planet's radius is approximately 6711 km?
- Does it clearly state the planet's gravity is approximately 14.31 m/s^2?
- Does it clearly state the pendulum's period is approximately 1.66 seconds?
- Does it clearly state the target orbit speed to reach an orbital height of 8061 km is approximately 6605.9 m/s? (plus or minus 3 m/s)

**Challenge**

- Does it clearly state the planet's radius is approximately 6711 km?
- Does it clearly state the planet's gravity is approximately 14.31 m/s^2?
- Does it clearly state the pendulum's period is approximately 1.66 seconds?
- Does it clearly state the target orbit speed to reach an orbital height of 8061 km is approximately 6605.9 m/s? (plus or minus 3 m/s)
- Does it clearly eliminate fuel type C as it wouldn't generate enough thrust to liftoff the rocket (i.e., its thrust to weight ratio is lower or equal to 1 g)?
- Does it clearly eliminate fuel type B as its density is to low and would require more fuel than what the rocket can hold?
- Does it clearly state what fuel type to use A (between A,B,C)?
- Does it clearly state the amount needed of fuel type A is approximately 1667 liters? (plus or minus 2 liters)

## What changes with the seed

The hidden answer, read from each world's critical questions:

| seed | Easy | Normal | Challenge |
|---|---|---|---|
| 0 | radius 6371 km, g 9.82 m/s², orbital speed 7672.7 m/s | radius 6711 km, g 14.31 m/s², orbital speed 6605.9 m/s | radius 6711 km, g 14.31 m/s², orbital speed 6605.9 m/s; fuel A, 1667 l |
| 1 | radius 1737.5 km, g 1.62 m/s², orbital speed 1514.5 m/s | radius 2601 km, g 49.38 m/s², orbital speed 5760.9 m/s | radius 2601 km, g 49.38 m/s², orbital speed 5760.9 m/s; fuel C, 48 l |
| 2 | radius 3389.5 km, g 3.73 m/s², orbital speed 3361.9 m/s | radius 1326 km, g 317.77 m/s², orbital speed 9290.0 m/s | radius 1326 km, g 317.77 m/s², orbital speed 9290.0 m/s; fuel B, 2119 l |
| 3 | radius 1821.6 km, g 1.8 m/s², orbital speed 1638.1 m/s | radius 4298 km, g 21.96 m/s², orbital speed 5399.9 m/s | radius 4298 km, g 21.96 m/s², orbital speed 5399.9 m/s; fuel C, 65 l |
| 4 | radius 1560.8 km, g 1.32 m/s², orbital speed 1278.2 m/s | radius 4267 km, g 14.74 m/s², orbital speed 6233.8 m/s | radius 4267 km, g 14.74 m/s², orbital speed 6233.8 m/s; fuel A, 468 l |

Every seed hides a different answer at every difficulty.

## Measuring investigative behaviour here

Only the generic detectors apply. Measuring the sun angle at both posts and timing the pendulum are measurements; whether the agent checks its result before the single launch is left to the model coder.

## Notes

- DiscoveryWorld 0.0.2 cannot load this scenario on Python 3.12 or later (it passes float bounds to `randint`); this repository's adapter gives its world generator the Python 3.11 behaviour, which produces the same worlds from the same seeds ([`../../reproducibility.md`](../../reproducibility.md), section 9).
- Seeds also change the planet at Easy (seed 1 has a radius of 1737.5 km and gravity of 1.62 m/s²), so the task text matters.
- The launch is irreversible: entering a wrong speed completes the task unsuccessfully.

## Run it

DiscoveryWorld's ReAct baseline on the five Easy worlds, with a local model:

```bash
sea run --method no_memory --agent react --env discoveryworld --scenario "It's (not) Rocket Science!" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/rocket-science-react
```

ReasoningBank on the same worlds with the Hypothesizer as the actor:

```bash
sea run --method reasoningbank --agent hypothesizer --env discoveryworld --scenario "It's (not) Rocket Science!" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/rocket-science-rb
```

Every agent and method, and which combinations work: [`../../agents.md`](../../agents.md). All scenarios: [`../README.md`](../README.md).
