# Charging, desaturation and eclipse strategies across battery size and solar-array area (Basilisk / BSK-RL)

157 experiments in 41 rounds, 5648 simulator episodes (budget 10000).

**8 comparisons, 35 claims** (1 retired, 8 superseded, 26 supported); 62 relations between claims.

## What the graph recommends, by condition

Settings that differ from the reference policy, in every region of conditions the supported claims tell apart. A dot keeps the reference value: either nothing was found to beat it there, or nothing could be established.

| panel_area_m2 | battery_capacity_wh | `charge_below` | `charge_margin` | `desat_above` | `precharge_below` | `precharge_window_s` |
|---|---|---|---|---|---|---|
| below 0.1581 | below 27.25 | 0.8 | · | · | · | · |
| below 0.1581 | 27.25 to 32.42 | 0.6 | 0.25 | 0.3 | · | · |
| below 0.1581 | 32.42 to 33.87 | 0.6 | 0.25 | 0.3 | 0.6 | 900 |
| below 0.1581 | 33.87 to 38.6 | 0.4 | 0.25 | 0.3 | 0.6 | 900 |
| below 0.1581 | 38.6 to 56.95 | 0.4 | · | 0.3 | · | · |
| below 0.1581 | 56.95 to 64.86 | · | · | 0.3 | · | · |
| below 0.1581 | 64.86 to 77.11 | · | 0.25 | 0.3 | · | · |
| below 0.1581 | 77.11 to 91.71 | · | · | 0.3 | · | · |
| below 0.1581 | 91.71 to 109.1 | · | · | · | · | · |
| below 0.1581 | 109.1 to 129.5 | · | · | 0.3 | · | · |
| below 0.1581 | 129.5 to 147.4 | 0.1 | · | 0.3 | · | · |
| below 0.1581 | 147.4 to 175.5 | · | · | 0.3 | · | · |
| below 0.1581 | 175.5 to 308.4 | 0.1 | · | 0.3 | · | · |
| below 0.1581 | 308.4 and above | 0.05 | · | · | · | · |
| 0.1581 and above | below 27.25 | 0.6 | 0.25 | · | 0.6 | 900 |
| 0.1581 and above | 27.25 to 32.42 | 0.6 | · | 0.3 | 0.6 | 900 |
| 0.1581 and above | 32.42 to 45.88 | 0.4 | 0.25 | 0.3 | 0.6 | 900 |
| 0.1581 and above | 45.88 to 54.54 | 0.4 | · | 0.3 | · | · |
| 0.1581 and above | 54.54 to 64.86 | · | · | 0.3 | 0.6 | 900 |
| 0.1581 and above | 64.86 to 87.82 | · | 0.25 | 0.3 | 0.6 | 900 |
| 0.1581 and above | 87.82 to 91.71 | · | 0.25 | · | 0.6 | 900 |
| 0.1581 and above | 91.71 to 109.1 | · | 0.25 | 0.3 | 0.6 | 900 |
| 0.1581 and above | 109.1 to 135.4 | · | 0.25 | · | 0.6 | 900 |
| 0.1581 and above | 135.4 to 147.4 | · | 0.25 | · | · | · |
| 0.1581 and above | 147.4 to 153.9 | · | 0.25 | 0.3 | · | · |
| 0.1581 and above | 153.9 to 175.5 | · | · | 0.3 | · | · |
| 0.1581 and above | 175.5 to 259.5 | 0.1 | · | 0.3 | · | · |
| 0.1581 and above | 259.5 to 366.6 | 0.1 | · | · | · | · |
| 0.1581 and above | 366.6 and above | 0.1 | · | 0.3 | · | · |

## Claims by comparison

### A lower charge threshold collects more data.

Proposed by: seed (hand-written). Compares `charge_below` = 0.1 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25, panel_area_m2=0.1 | no meaningful benefit | +0.013 | [+0.008, +0.017] | 16 | 16 / 16 |
| battery_capacity_wh=25, panel_area_m2=0.25 | no meaningful benefit | +0.003 | [-0.022, +0.017] | 16 | 16 / 16 |
| battery_capacity_wh=32.4, panel_area_m2=0.25 | no meaningful benefit | -0.091 | [-0.345, +0.015] | 16 | 16 / 15 |
| battery_capacity_wh=35.4, panel_area_m2=0.1 | no meaningful benefit | -0.121 | [-0.324, +0.017] | 16 | 16 / 14 |
| battery_capacity_wh=42, panel_area_m2=0.25 | baseline better | -0.534 | [-0.869, -0.216] | 16 | 16 / 10 |
| battery_capacity_wh=42.1, panel_area_m2=0.1 | baseline better | -0.440 | [-0.705, -0.179] | 16 | 16 / 9 |
| battery_capacity_wh=50, panel_area_m2=0.1 | baseline better | -0.876 | [-1.009, -0.676] | 16 | 16 / 2 |
| battery_capacity_wh=50, panel_area_m2=0.25 | baseline better | -1.010 | [-1.215, -0.745] | 16 | 16 / 3 |
| battery_capacity_wh=70.7, panel_area_m2=0.25 | baseline better | -1.130 | [-1.182, -1.075] | 16 | 16 / 0 |
| battery_capacity_wh=100, panel_area_m2=0.1 | baseline better | -0.557 | [-0.819, -0.289] | 16 | 10 / 0 |
| battery_capacity_wh=100, panel_area_m2=0.25 | baseline better | -0.344 | [-0.648, -0.059] | 16 | 6 / 0 |
| battery_capacity_wh=119, panel_area_m2=0.1 | baseline better | -0.169 | [-0.359, -0.008] | 32 | 8 / 0 |
| battery_capacity_wh=119, panel_area_m2=0.25 | baseline better | -0.168 | [-0.328, -0.031] | 48 | 11 / 0 |
| battery_capacity_wh=141, panel_area_m2=0.1 | intervention better | +0.102 | [+0.091, +0.113] | 16 | 0 / 0 |
| battery_capacity_wh=154, panel_area_m2=0.25 | unresolved (inconclusive at the maximum number of seeds) | +0.005 | [-0.105, +0.088] | 48 | 4 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.1 | intervention better | +0.146 | [+0.132, +0.161] | 16 | 0 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.25 | intervention better | +0.092 | [+0.062, +0.120] | 16 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.1 | intervention better | +0.115 | [+0.046, +0.192] | 16 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.25 | intervention better | +0.055 | [+0.009, +0.113] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh >= 175.499, use `charge_below` = 0.1 instead of 0.25.
- **supported** (reversed): where 38.559 <= battery_capacity_wh < 129.534, use `charge_below` = 0.25 instead of 0.1.
- **supported** (narrowed): where 129.534 <= battery_capacity_wh < 147.357, use `charge_below` = 0.1 instead of 0.25.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 38.559.
- Not established either way, so nothing is recommended, where: 147.357 <= battery_capacity_wh < 175.499.

Explanations (judged separately from the outcome):

- *less time is spent in charge mode* — **supported**
  - mediator test at battery_capacity_wh=200, panel_area_m2=0.25: supports. `time_charge_s`: 2636.25 with the intervention vs 4125 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400, panel_area_m2=0.1: supports. `time_charge_s`: 2010 with the intervention vs 3993.75 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=200, panel_area_m2=0.1: supports. `time_charge_s`: 6438.75 with the intervention vs 8992.5 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=141, panel_area_m2=0.1: supports. `time_charge_s`: 9232.5 with the intervention vs 10991.2 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400, panel_area_m2=0.25: supports. `time_charge_s`: 1267.5 with the intervention vs 2141.25 without, over 16 of 16 seed pairs

### Topping up the battery before each eclipse improves the score.

Proposed by: seed (hand-written). Compares `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25, panel_area_m2=0.1 | no meaningful benefit | -0.003 | [-0.007, +0.001] | 16 | 16 / 16 |
| battery_capacity_wh=25, panel_area_m2=0.25 | intervention better | +0.129 | [+0.002, +0.306] | 32 | 28 / 31 |
| battery_capacity_wh=29.7, panel_area_m2=0.1 | unresolved (inconclusive at the maximum number of seeds) | +0.042 | [-0.006, +0.131] | 48 | 44 / 46 |
| battery_capacity_wh=35.4, panel_area_m2=0.1 | intervention better | +0.221 | [+0.026, +0.442] | 32 | 21 / 28 |
| battery_capacity_wh=35.4, panel_area_m2=0.25 | intervention better | +0.291 | [+0.029, +0.625] | 16 | 9 / 12 |
| battery_capacity_wh=42.1, panel_area_m2=0.1 | unresolved (inconclusive at the maximum number of seeds) | +0.016 | [-0.110, +0.146] | 48 | 27 / 28 |
| battery_capacity_wh=42.1, panel_area_m2=0.25 | intervention better | +0.370 | [+0.099, +0.673] | 16 | 5 / 10 |
| battery_capacity_wh=50, panel_area_m2=0.1 | unresolved (inconclusive at the maximum number of seeds) | -0.072 | [-0.201, +0.056] | 48 | 19 / 16 |
| battery_capacity_wh=50, panel_area_m2=0.25 | unresolved (inconclusive at the maximum number of seeds) | +0.072 | [-0.068, +0.215] | 48 | 12 / 14 |
| battery_capacity_wh=59.5, panel_area_m2=0.1 | no meaningful benefit | -0.072 | [-0.264, +0.003] | 16 | 1 / 0 |
| battery_capacity_wh=59.5, panel_area_m2=0.25 | intervention better | +0.042 | [+0.014, +0.068] | 16 | 0 / 0 |
| battery_capacity_wh=70.7, panel_area_m2=0.1 | no meaningful benefit | -0.005 | [-0.015, +0.004] | 16 | 0 / 0 |
| battery_capacity_wh=70.7, panel_area_m2=0.25 | intervention better | +0.039 | [+0.010, +0.068] | 16 | 0 / 0 |
| battery_capacity_wh=100, panel_area_m2=0.1 | no meaningful benefit | -0.010 | [-0.023, +0.002] | 16 | 0 / 0 |
| battery_capacity_wh=100, panel_area_m2=0.25 | intervention better | +0.034 | [+0.006, +0.061] | 16 | 0 / 0 |
| battery_capacity_wh=119, panel_area_m2=0.25 | intervention better | +0.036 | [+0.011, +0.060] | 32 | 0 / 0 |
| battery_capacity_wh=154, panel_area_m2=0.25 | unresolved (inconclusive at the maximum number of seeds) | +0.009 | [-0.011, +0.029] | 48 | 0 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.1 | no meaningful benefit | -0.006 | [-0.023, +0.010] | 16 | 0 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.25 | no meaningful benefit | -0.003 | [-0.023, +0.017] | 48 | 0 / 0 |
| battery_capacity_wh=238, panel_area_m2=0.1 | no meaningful benefit | -0.013 | [-0.028, +0.002] | 16 | 0 / 0 |
| battery_capacity_wh=283, panel_area_m2=0.1 | baseline better | -0.026 | [-0.045, -0.007] | 16 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.1 | baseline better | -0.065 | [-0.117, -0.028] | 16 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.25 | no meaningful benefit | -0.039 | [-0.088, +0.001] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 45.8803 and panel_area_m2 >= 0.158114, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- **supported** (reversed): where battery_capacity_wh >= 259.526 and panel_area_m2 < 0.158114, use `precharge_below` = 0 instead of 0.6, `precharge_window_s` = 0 instead of 900.
- **supported** (narrowed): where 32.425 <= battery_capacity_wh < 38.6049 and panel_area_m2 < 0.158114, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- **supported** (narrowed): where 54.5436 <= battery_capacity_wh < 135.374 and panel_area_m2 >= 0.158114, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 27.2489 and panel_area_m2 < 0.158114; 54.5436 <= battery_capacity_wh < 175.499 and panel_area_m2 < 0.158114; 175.499 <= battery_capacity_wh < 259.526; battery_capacity_wh >= 259.526 and panel_area_m2 >= 0.158114.
- Not established either way, so nothing is recommended, where: 27.2489 <= battery_capacity_wh < 32.425 and panel_area_m2 < 0.158114; 38.6049 <= battery_capacity_wh < 54.5436 and panel_area_m2 < 0.158114; 45.8803 <= battery_capacity_wh < 54.5436 and panel_area_m2 >= 0.158114; 135.374 <= battery_capacity_wh < 175.499 and panel_area_m2 >= 0.158114.

Explanations (judged separately from the outcome):

- *the battery does not get as low* — **supported**
  - mediator test at battery_capacity_wh=25, panel_area_m2=0.25: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=70.7, panel_area_m2=0.25: supports. `min_battery`: 0.14246 with the intervention vs 0.09956 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=119, panel_area_m2=0.25: supports. `min_battery`: 0.19276 with the intervention vs 0.17195 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=35.4, panel_area_m2=0.1: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=35.4, panel_area_m2=0.25: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=59.5, panel_area_m2=0.25: supports. `min_battery`: 0.11991 with the intervention vs 0.07604 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42.1, panel_area_m2=0.25: supports. `min_battery`: 0.11848 with the intervention vs 0.04063 without, over 6 of 16 seed pairs
  - mediator test at battery_capacity_wh=100, panel_area_m2=0.25: supports. `min_battery`: 0.18141 with the intervention vs 0.1485 without, over 16 of 16 seed pairs
- *it prevents battery depletion* — **contested**
  - mediator test at battery_capacity_wh=25, panel_area_m2=0.25: inconclusive. `failure:battery`: 0.875 with the intervention vs 0.96875 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=70.7, panel_area_m2=0.25: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=119, panel_area_m2=0.25: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=35.4, panel_area_m2=0.1: supports. `failure:battery`: 0.65625 with the intervention vs 0.875 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=35.4, panel_area_m2=0.25: inconclusive. `failure:battery`: 0.5625 with the intervention vs 0.75 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=59.5, panel_area_m2=0.25: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42.1, panel_area_m2=0.25: supports. `failure:battery`: 0.3125 with the intervention vs 0.625 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100, panel_area_m2=0.25: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs

### Unloading the reaction wheels early improves the score.

Proposed by: seed (hand-written). Compares `desat_above` = 0.3 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25, panel_area_m2=0.1 | unresolved (inconclusive at the maximum number of seeds) | +0.056 | [-0.015, +0.152] | 48 | 43 / 46 |
| battery_capacity_wh=25, panel_area_m2=0.25 | unresolved (inconclusive at the maximum number of seeds) | +0.040 | [-0.022, +0.145] | 48 | 44 / 46 |
| battery_capacity_wh=29.7, panel_area_m2=0.1 | intervention better | +0.105 | [+0.013, +0.220] | 48 | 41 / 46 |
| battery_capacity_wh=32.4, panel_area_m2=0.25 | intervention better | +0.186 | [+0.016, +0.436] | 16 | 13 / 15 |
| battery_capacity_wh=35.4, panel_area_m2=0.1 | intervention better | +0.197 | [+0.004, +0.394] | 32 | 22 / 28 |
| battery_capacity_wh=42, panel_area_m2=0.25 | intervention better | +0.598 | [+0.233, +0.946] | 16 | 2 / 10 |
| battery_capacity_wh=50, panel_area_m2=0.1 | intervention better | +0.145 | [+0.012, +0.346] | 16 | 0 / 2 |
| battery_capacity_wh=50, panel_area_m2=0.25 | intervention better | +0.254 | [+0.037, +0.541] | 16 | 0 / 3 |
| battery_capacity_wh=70.7, panel_area_m2=0.1 | intervention better | +0.021 | [+0.011, +0.032] | 16 | 0 / 0 |
| battery_capacity_wh=70.7, panel_area_m2=0.25 | intervention better | +0.057 | [+0.017, +0.099] | 16 | 0 / 0 |
| battery_capacity_wh=84.1, panel_area_m2=0.1 | intervention better | +0.036 | [+0.008, +0.099] | 48 | 0 / 1 |
| battery_capacity_wh=100, panel_area_m2=0.1 | unresolved (inconclusive at the maximum number of seeds) | +0.018 | [+0.009, +0.027] | 48 | 0 / 0 |
| battery_capacity_wh=100, panel_area_m2=0.25 | intervention better | +0.056 | [+0.020, +0.093] | 16 | 0 / 0 |
| battery_capacity_wh=119, panel_area_m2=0.1 | intervention better | +0.020 | [+0.011, +0.030] | 48 | 0 / 0 |
| battery_capacity_wh=141, panel_area_m2=0.1 | intervention better | +0.023 | [+0.009, +0.038] | 16 | 0 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.1 | intervention better | +0.030 | [+0.012, +0.050] | 16 | 0 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.25 | intervention better | +0.048 | [+0.022, +0.080] | 16 | 0 / 0 |
| battery_capacity_wh=283, panel_area_m2=0.1 | intervention better | +0.033 | [+0.013, +0.053] | 16 | 0 / 0 |
| battery_capacity_wh=336, panel_area_m2=0.1 | unresolved (inconclusive at the maximum number of seeds) | +0.020 | [+0.005, +0.034] | 48 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.1 | no meaningful benefit | +0.003 | [-0.012, +0.016] | 32 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.25 | intervention better | +0.026 | [+0.005, +0.049] | 48 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where 27.2489 <= battery_capacity_wh < 91.7061, use `desat_above` = 0.3 instead of 0.6.
- **supported** (narrowed): where 109.087 <= battery_capacity_wh < 308.363, use `desat_above` = 0.3 instead of 0.6.
- **supported** (narrowed): where battery_capacity_wh >= 366.606 and panel_area_m2 >= 0.158114, use `desat_above` = 0.3 instead of 0.6.
- **supported** (narrowed): where 91.7061 <= battery_capacity_wh < 109.087 and panel_area_m2 >= 0.158114, use `desat_above` = 0.3 instead of 0.6.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh >= 366.606 and panel_area_m2 < 0.158114.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 27.2489; 91.7061 <= battery_capacity_wh < 109.087 and panel_area_m2 < 0.158114; 308.363 <= battery_capacity_wh < 366.606.

Explanations (judged separately from the outcome):

- *it prevents the wheels from reaching their speed limit* — **refuted**
  - mediator test at battery_capacity_wh=200, panel_area_m2=0.25: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=70.7, panel_area_m2=0.25: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42, panel_area_m2=0.25: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=32.4, panel_area_m2=0.25: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=200, panel_area_m2=0.1: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=141, panel_area_m2=0.1: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=283, panel_area_m2=0.1: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=119, panel_area_m2=0.1: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=50, panel_area_m2=0.1: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=35.4, panel_area_m2=0.1: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=70.7, panel_area_m2=0.1: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400, panel_area_m2=0.25: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=29.7, panel_area_m2=0.1: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=84.1, panel_area_m2=0.1: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=100, panel_area_m2=0.25: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50, panel_area_m2=0.25: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
- *slower wheels draw less power, so less time is spent charging* — **supported**
  - mediator test at battery_capacity_wh=200, panel_area_m2=0.25: supports. `time_charge_s`: 3318.75 with the intervention vs 4125 without, over 16 of 16 seed pairs
  - moderator test at battery_capacity_wh=200, panel_area_m2=0.25: supports. effect by `max_wheel_speed_rpm`: 1500 -> -0.070, 3000 -> +0.006, 6000 -> +0.041
  - mediator test at battery_capacity_wh=70.7, panel_area_m2=0.25: supports. `time_charge_s`: 7080 with the intervention vs 8058.75 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42, panel_area_m2=0.25: inconclusive. `time_charge_s`: 7680 with the intervention vs 8020 without, over 6 of 16 seed pairs
  - mediator test at battery_capacity_wh=32.4, panel_area_m2=0.25: inconclusive. `time_charge_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=200, panel_area_m2=0.1: supports. `time_charge_s`: 8358.75 with the intervention vs 8992.5 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=141, panel_area_m2=0.1: supports. `time_charge_s`: 10507.5 with the intervention vs 10991.2 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=283, panel_area_m2=0.1: supports. `time_charge_s`: 5475 with the intervention vs 6116.25 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=119, panel_area_m2=0.1: supports. `time_charge_s`: 11458.8 with the intervention vs 12005 without, over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=50, panel_area_m2=0.1: supports. `time_charge_s`: 13902.9 with the intervention vs 14275.7 without, over 14 of 16 seed pairs
  - mediator test at battery_capacity_wh=35.4, panel_area_m2=0.1: inconclusive. `time_charge_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=70.7, panel_area_m2=0.1: supports. `time_charge_s`: 13102.5 with the intervention vs 13571.2 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400, panel_area_m2=0.25: supports. `time_charge_s`: 1981.25 with the intervention vs 2523.75 without, over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=29.7, panel_area_m2=0.1: inconclusive. `time_charge_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=84.1, panel_area_m2=0.1: supports. `time_charge_s`: 12690.6 with the intervention vs 13159.1 without, over 47 of 48 seed pairs
  - mediator test at battery_capacity_wh=100, panel_area_m2=0.25: supports. `time_charge_s`: 6228.75 with the intervention vs 7188.75 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50, panel_area_m2=0.25: supports. `time_charge_s`: 7818.46 with the intervention vs 8649.23 without, over 13 of 16 seed pairs

### Charging in longer blocks improves the score.

Proposed by: seed (hand-written). Compares `charge_margin` = 0.25 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25, panel_area_m2=0.1 | no meaningful benefit | +0.003 | [-0.003, +0.009] | 16 | 16 / 16 |
| battery_capacity_wh=25, panel_area_m2=0.25 | intervention better | +0.024 | [+0.001, +0.075] | 16 | 16 / 16 |
| battery_capacity_wh=29.7, panel_area_m2=0.1 | intervention better | +0.049 | [+0.001, +0.137] | 48 | 44 / 46 |
| battery_capacity_wh=35.4, panel_area_m2=0.1 | intervention better | +0.261 | [+0.007, +0.524] | 16 | 10 / 14 |
| battery_capacity_wh=35.4, panel_area_m2=0.25 | intervention better | +0.233 | [+0.020, +0.472] | 32 | 20 / 25 |
| battery_capacity_wh=42.1, panel_area_m2=0.1 | unresolved (inconclusive at the maximum number of seeds) | +0.141 | [-0.003, +0.295] | 48 | 22 / 28 |
| battery_capacity_wh=42.1, panel_area_m2=0.25 | intervention better | +0.344 | [+0.116, +0.635] | 16 | 6 / 10 |
| battery_capacity_wh=50, panel_area_m2=0.1 | unresolved (inconclusive at the maximum number of seeds) | +0.034 | [-0.093, +0.160] | 48 | 15 / 16 |
| battery_capacity_wh=50, panel_area_m2=0.25 | unresolved (inconclusive at the maximum number of seeds) | +0.095 | [-0.022, +0.223] | 48 | 13 / 14 |
| battery_capacity_wh=59.5, panel_area_m2=0.1 | unresolved (inconclusive at the maximum number of seeds) | -0.027 | [-0.168, +0.102] | 48 | 10 / 8 |
| battery_capacity_wh=59.5, panel_area_m2=0.25 | unresolved (inconclusive at the maximum number of seeds) | +0.056 | [-0.048, +0.152] | 48 | 7 / 6 |
| battery_capacity_wh=70.7, panel_area_m2=0.1 | intervention better | +0.051 | [+0.009, +0.145] | 32 | 0 / 1 |
| battery_capacity_wh=70.7, panel_area_m2=0.25 | intervention better | +0.059 | [+0.012, +0.110] | 16 | 0 / 0 |
| battery_capacity_wh=84.1, panel_area_m2=0.1 | no meaningful benefit | -0.030 | [-0.114, +0.019] | 48 | 3 / 1 |
| battery_capacity_wh=100, panel_area_m2=0.1 | no meaningful benefit | +0.001 | [-0.014, +0.018] | 16 | 0 / 0 |
| battery_capacity_wh=100, panel_area_m2=0.25 | intervention better | +0.048 | [+0.003, +0.104] | 16 | 0 / 0 |
| battery_capacity_wh=141, panel_area_m2=0.25 | intervention better | +0.039 | [+0.001, +0.075] | 48 | 0 / 0 |
| battery_capacity_wh=168, panel_area_m2=0.25 | unresolved (inconclusive at the maximum number of seeds) | +0.027 | [-0.009, +0.062] | 48 | 0 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.1 | no meaningful benefit | -0.012 | [-0.036, +0.002] | 16 | 0 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.25 | unresolved (inconclusive at the maximum number of seeds) | +0.028 | [-0.011, +0.062] | 48 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.1 | no meaningful benefit | -0.030 | [-0.112, +0.001] | 16 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.25 | unresolved (inconclusive at the maximum number of seeds) | -0.001 | [-0.039, +0.031] | 48 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 27.2489 and panel_area_m2 >= 0.158114, use `charge_margin` = 0.25 instead of 0.
- **supported** (narrowed): where 27.2489 <= battery_capacity_wh < 38.6049, use `charge_margin` = 0.25 instead of 0.
- **supported** (narrowed): where 64.8587 <= battery_capacity_wh < 77.1095 and panel_area_m2 < 0.158114, use `charge_margin` = 0.25 instead of 0.
- **supported** (narrowed): where 64.8587 <= battery_capacity_wh < 153.909 and panel_area_m2 >= 0.158114, use `charge_margin` = 0.25 instead of 0.
- **retired** (narrowed): where 38.6049 <= battery_capacity_wh < 45.8803 and panel_area_m2 >= 0.158114, use `charge_margin` = 0.25 instead of 0.
- **supported** (narrowed): where 38.6049 <= battery_capacity_wh < 45.8803 and panel_area_m2 >= 0.158114, use `charge_margin` = 0.25 instead of 0.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 27.2489 and panel_area_m2 < 0.158114; battery_capacity_wh >= 77.1095 and panel_area_m2 < 0.158114.
- Not established either way, so nothing is recommended, where: 38.6049 <= battery_capacity_wh < 45.8803 and panel_area_m2 < 0.158114; 45.8803 <= battery_capacity_wh < 64.8587; battery_capacity_wh >= 153.909 and panel_area_m2 >= 0.158114.

Explanations (judged separately from the outcome):

- *fewer mode switches waste less scan time on slewing and settling* — **supported**
  - mediator test at battery_capacity_wh=25, panel_area_m2=0.25: inconclusive. `wasted_scan_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=35.4, panel_area_m2=0.25: supports. `wasted_scan_s`: 603.333 with the intervention vs 1201.67 without, over 6 of 32 seed pairs
  - mediator test at battery_capacity_wh=35.4, panel_area_m2=0.1: inconclusive. `wasted_scan_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=70.7, panel_area_m2=0.1: inconclusive. `wasted_scan_s`: 477.968 with the intervention vs 504.548 without, over 31 of 32 seed pairs
  - mediator test at battery_capacity_wh=42.1, panel_area_m2=0.25: supports. `wasted_scan_s`: 350.833 with the intervention vs 881.667 without, over 6 of 16 seed pairs
  - mediator test at battery_capacity_wh=100, panel_area_m2=0.25: supports. `wasted_scan_s`: 371.625 with the intervention vs 837.188 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=70.7, panel_area_m2=0.25: supports. `wasted_scan_s`: 388.625 with the intervention vs 895.562 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=141, panel_area_m2=0.25: supports. `wasted_scan_s`: 482.583 with the intervention vs 859.375 without, over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=29.7, panel_area_m2=0.1: inconclusive. `wasted_scan_s`: too few seeds on which both arms completed the episode

### Going further in the direction that helped keeps helping: charge_below=0.05 beats charge_below=0.1.

Proposed by: program. Compares `charge_below` = 0.05 instead of 0.1.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25, panel_area_m2=0.1 | no meaningful benefit | +0.002 | [-0.005, +0.007] | 16 | 16 / 16 |
| battery_capacity_wh=25, panel_area_m2=0.25 | no meaningful benefit | -0.014 | [-0.044, +0.005] | 16 | 16 / 16 |
| battery_capacity_wh=50, panel_area_m2=0.1 | no meaningful benefit | +0.007 | [+0.001, +0.013] | 16 | 16 / 16 |
| battery_capacity_wh=50, panel_area_m2=0.25 | no meaningful benefit | -0.010 | [-0.043, +0.014] | 16 | 16 / 16 |
| battery_capacity_wh=70.7, panel_area_m2=0.1 | no meaningful benefit | +0.014 | [+0.009, +0.019] | 16 | 16 / 16 |
| battery_capacity_wh=70.7, panel_area_m2=0.25 | no meaningful benefit | -0.010 | [-0.041, +0.014] | 16 | 16 / 16 |
| battery_capacity_wh=84.1, panel_area_m2=0.1 | no meaningful benefit | +0.011 | [+0.000, +0.019] | 16 | 16 / 16 |
| battery_capacity_wh=91.7, panel_area_m2=0.25 | baseline better | -0.424 | [-0.768, -0.127] | 16 | 16 / 10 |
| battery_capacity_wh=100, panel_area_m2=0.1 | baseline better | -0.368 | [-0.634, -0.108] | 16 | 16 / 10 |
| battery_capacity_wh=100, panel_area_m2=0.25 | baseline better | -0.562 | [-0.877, -0.256] | 16 | 14 / 6 |
| battery_capacity_wh=119, panel_area_m2=0.25 | baseline better | -0.865 | [-1.084, -0.584] | 16 | 15 / 2 |
| battery_capacity_wh=141, panel_area_m2=0.1 | baseline better | -0.854 | [-0.987, -0.657] | 16 | 14 / 0 |
| battery_capacity_wh=168, panel_area_m2=0.1 | baseline better | -0.649 | [-0.902, -0.393] | 16 | 11 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.1 | no meaningful benefit | -0.140 | [-0.300, +0.011] | 32 | 6 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.25 | baseline better | -0.144 | [-0.309, -0.012] | 32 | 5 / 0 |
| battery_capacity_wh=238, panel_area_m2=0.1 | no meaningful benefit | -0.083 | [-0.200, +0.008] | 48 | 6 / 0 |
| battery_capacity_wh=238, panel_area_m2=0.25 | unresolved (inconclusive at the maximum number of seeds) | -0.034 | [-0.119, +0.027] | 48 | 3 / 0 |
| battery_capacity_wh=283, panel_area_m2=0.1 | unresolved (inconclusive at the maximum number of seeds) | -0.062 | [-0.168, +0.025] | 48 | 5 / 0 |
| battery_capacity_wh=283, panel_area_m2=0.25 | unresolved (inconclusive at the maximum number of seeds) | +0.003 | [-0.059, +0.032] | 48 | 1 / 0 |
| battery_capacity_wh=336, panel_area_m2=0.1 | intervention better | +0.034 | [+0.010, +0.061] | 16 | 0 / 0 |
| battery_capacity_wh=336, panel_area_m2=0.25 | unresolved (inconclusive at the maximum number of seeds) | +0.019 | [+0.009, +0.030] | 48 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.1 | intervention better | +0.023 | [+0.005, +0.047] | 16 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.25 | no meaningful benefit | +0.006 | [+0.000, +0.018] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (reversed): where 87.8178 <= battery_capacity_wh < 183.303, use `charge_below` = 0.1 instead of 0.05.
- **supported** (narrowed): where battery_capacity_wh >= 308.363 and panel_area_m2 < 0.158114, use `charge_below` = 0.05 instead of 0.1.
- **supported** (reversed): where 183.303 <= battery_capacity_wh < 218.174 and panel_area_m2 >= 0.158114, use `charge_below` = 0.1 instead of 0.05.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 87.8178; 183.303 <= battery_capacity_wh < 218.174 and panel_area_m2 < 0.158114; 218.174 <= battery_capacity_wh < 259.526 and panel_area_m2 < 0.158114; battery_capacity_wh >= 366.606 and panel_area_m2 >= 0.158114.
- Not established either way, so nothing is recommended, where: 218.174 <= battery_capacity_wh < 259.526 and panel_area_m2 >= 0.158114; 259.526 <= battery_capacity_wh < 308.363; 308.363 <= battery_capacity_wh < 366.606 and panel_area_m2 >= 0.158114.

### Neither tested setting is acceptable here; a setting further out does better: charge_below=0.4 beats charge_below=0.25.

Proposed by: program. Compares `charge_below` = 0.4 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25, panel_area_m2=0.1 | intervention better | +0.390 | [+0.127, +0.660] | 16 | 10 / 16 |
| battery_capacity_wh=25, panel_area_m2=0.25 | intervention better | +0.489 | [+0.160, +0.842] | 16 | 10 / 16 |
| battery_capacity_wh=42, panel_area_m2=0.1 | intervention better | +0.481 | [+0.216, +0.749] | 16 | 0 / 8 |
| battery_capacity_wh=50, panel_area_m2=0.1 | intervention better | +0.187 | [+0.030, +0.374] | 32 | 0 / 7 |
| battery_capacity_wh=50, panel_area_m2=0.25 | intervention better | +0.167 | [+0.014, +0.349] | 32 | 0 / 6 |
| battery_capacity_wh=54.5, panel_area_m2=0.1 | intervention better | +0.155 | [+0.028, +0.304] | 48 | 1 / 10 |
| battery_capacity_wh=59.5, panel_area_m2=0.25 | baseline better | -0.044 | [-0.084, -0.016] | 16 | 0 / 0 |
| battery_capacity_wh=70.7, panel_area_m2=0.1 | baseline better | -0.048 | [-0.059, -0.035] | 16 | 0 / 0 |
| battery_capacity_wh=70.7, panel_area_m2=0.25 | baseline better | -0.058 | [-0.101, -0.034] | 16 | 0 / 0 |
| battery_capacity_wh=100, panel_area_m2=0.1 | baseline better | -0.077 | [-0.087, -0.065] | 16 | 0 / 0 |
| battery_capacity_wh=100, panel_area_m2=0.25 | baseline better | -0.066 | [-0.081, -0.049] | 16 | 0 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.1 | baseline better | -0.135 | [-0.155, -0.112] | 16 | 0 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.25 | baseline better | -0.123 | [-0.145, -0.100] | 16 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.1 | baseline better | -0.182 | [-0.258, -0.104] | 16 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.25 | baseline better | -0.103 | [-0.171, -0.039] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 56.9451, use `charge_below` = 0.4 instead of 0.25.
- **supported** (reversed): where battery_capacity_wh >= 56.9451, use `charge_below` = 0.25 instead of 0.4.

### Going further in the direction that helped keeps helping: charge_below=0.6 beats charge_below=0.4.

Proposed by: program. Compares `charge_below` = 0.6 instead of 0.4.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25, panel_area_m2=0.1 | intervention better | +0.493 | [+0.226, +0.807] | 16 | 2 / 10 |
| battery_capacity_wh=25, panel_area_m2=0.25 | intervention better | +0.468 | [+0.145, +0.830] | 16 | 4 / 10 |
| battery_capacity_wh=29.7, panel_area_m2=0.25 | intervention better | +0.521 | [+0.189, +0.883] | 16 | 1 / 8 |
| battery_capacity_wh=32.4, panel_area_m2=0.1 | intervention better | +0.296 | [+0.044, +0.606] | 16 | 0 / 5 |
| battery_capacity_wh=35.4, panel_area_m2=0.25 | no meaningful benefit | -0.020 | [-0.036, -0.006] | 16 | 0 / 0 |
| battery_capacity_wh=42, panel_area_m2=0.1 | baseline better | -0.031 | [-0.042, -0.022] | 16 | 0 / 0 |
| battery_capacity_wh=42.1, panel_area_m2=0.25 | no meaningful benefit | -0.017 | [-0.026, -0.006] | 16 | 0 / 0 |
| battery_capacity_wh=50, panel_area_m2=0.1 | baseline better | -0.039 | [-0.050, -0.028] | 16 | 0 / 0 |
| battery_capacity_wh=50, panel_area_m2=0.25 | baseline better | -0.030 | [-0.041, -0.018] | 16 | 0 / 0 |
| battery_capacity_wh=70.7, panel_area_m2=0.1 | baseline better | -0.054 | [-0.067, -0.041] | 16 | 0 / 0 |
| battery_capacity_wh=100, panel_area_m2=0.1 | baseline better | -0.079 | [-0.095, -0.060] | 16 | 0 / 0 |
| battery_capacity_wh=100, panel_area_m2=0.25 | baseline better | -0.087 | [-0.116, -0.063] | 16 | 0 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.1 | baseline better | -0.168 | [-0.199, -0.129] | 16 | 0 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.25 | baseline better | -0.163 | [-0.192, -0.129] | 16 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.1 | baseline better | -0.306 | [-0.371, -0.224] | 16 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.25 | baseline better | -0.223 | [-0.287, -0.157] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 33.8668, use `charge_below` = 0.6 instead of 0.4.
- **supported** (reversed): where 33.8668 <= battery_capacity_wh < 45.8803 and panel_area_m2 < 0.158114, use `charge_below` = 0.4 instead of 0.6.
- **supported** (reversed): where battery_capacity_wh >= 45.8803, use `charge_below` = 0.4 instead of 0.6.
- No meaningful benefit, so nothing is recommended, where: 33.8668 <= battery_capacity_wh < 45.8803 and panel_area_m2 >= 0.158114.

### Going further in the direction that helped keeps helping: charge_below=0.8 beats charge_below=0.6.

Proposed by: program. Compares `charge_below` = 0.8 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25, panel_area_m2=0.1 | intervention better | +0.178 | [+0.054, +0.325] | 48 | 3 / 12 |
| battery_capacity_wh=25, panel_area_m2=0.25 | unresolved (inconclusive at the maximum number of seeds) | +0.143 | [-0.028, +0.324] | 48 | 3 / 9 |
| battery_capacity_wh=29.7, panel_area_m2=0.25 | no meaningful benefit | -0.013 | [-0.036, +0.005] | 16 | 1 / 1 |
| battery_capacity_wh=32.4, panel_area_m2=0.1 | no meaningful benefit | -0.015 | [-0.027, -0.003] | 16 | 0 / 0 |
| battery_capacity_wh=35.4, panel_area_m2=0.25 | no meaningful benefit | -0.015 | [-0.027, -0.001] | 16 | 0 / 0 |
| battery_capacity_wh=42, panel_area_m2=0.1 | no meaningful benefit | -0.019 | [-0.030, -0.009] | 16 | 0 / 0 |
| battery_capacity_wh=42.1, panel_area_m2=0.25 | baseline better | -0.024 | [-0.033, -0.014] | 16 | 0 / 0 |
| battery_capacity_wh=50, panel_area_m2=0.1 | baseline better | -0.022 | [-0.032, -0.013] | 16 | 0 / 0 |
| battery_capacity_wh=50, panel_area_m2=0.25 | baseline better | -0.027 | [-0.042, -0.012] | 16 | 0 / 0 |
| battery_capacity_wh=54.5, panel_area_m2=0.1 | baseline better | -0.030 | [-0.046, -0.016] | 16 | 0 / 0 |
| battery_capacity_wh=70.7, panel_area_m2=0.1 | baseline better | -0.032 | [-0.044, -0.019] | 16 | 0 / 0 |
| battery_capacity_wh=100, panel_area_m2=0.1 | baseline better | -0.051 | [-0.074, -0.029] | 16 | 0 / 0 |
| battery_capacity_wh=100, panel_area_m2=0.25 | baseline better | -0.074 | [-0.126, -0.034] | 16 | 0 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.1 | baseline better | -0.096 | [-0.146, -0.049] | 16 | 0 / 0 |
| battery_capacity_wh=200, panel_area_m2=0.25 | baseline better | -0.139 | [-0.185, -0.094] | 16 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.1 | baseline better | -0.174 | [-0.273, -0.079] | 16 | 0 / 0 |
| battery_capacity_wh=400, panel_area_m2=0.25 | baseline better | -0.255 | [-0.317, -0.190] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 27.2489 and panel_area_m2 < 0.158114, use `charge_below` = 0.8 instead of 0.6.
- **supported** (reversed): where battery_capacity_wh >= 42.05, use `charge_below` = 0.6 instead of 0.8.
- No meaningful benefit, so nothing is recommended, where: 27.2489 <= battery_capacity_wh < 42.05.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 27.2489 and panel_area_m2 >= 0.158114.

## Revision history

- `propose` claim_ff958825da44: proposed
- `propose` claim_fddf7a5791ad: proposed
- `propose` claim_45238d1aefab: proposed
- `propose` claim_36d8437489e9: proposed
- `support` claim_ff958825da44: hypothesis -> supported: 1 decisive test(s), all in favour
- `refute` claim_fddf7a5791ad: hypothesis -> refuted: 1 decisive test(s), none in favour
- `support` claim_45238d1aefab: hypothesis -> supported: 1 decisive test(s), all in favour
- `propose` claim_9842fe544ff3: keep-going rule, from claim_ff958825da44, along the charge_below ladder
- `refute` claim_9842fe544ff3: hypothesis -> refuted: 1 decisive test(s), none in favour
- `specialize` claim_fd3a88a86f68: reversed from claim_9842fe544ff3: all tested conditions
- `support` claim_fd3a88a86f68: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_ff958825da44: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_861b5bb11574: narrowed from claim_ff958825da44: battery_capacity_wh >= 70.7107
- `support` claim_861b5bb11574: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_f9d4216c1b37: nothing-works-here rule, from claim_ff958825da44, along the charge_below ladder
- `support` claim_f9d4216c1b37: hypothesis -> supported: 1 decisive test(s), all in favour
- `specialize` claim_baa580394953: reversed from claim_ff958825da44: 42.0416 <= battery_capacity_wh < 118.912
- `support` claim_baa580394953: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_861b5bb11574: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 118.912]
- `supersede` claim_fddf7a5791ad: refuted -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_bbb3ef5ff705: narrowed from claim_fddf7a5791ad: battery_capacity_wh < 70.7107 and panel_area_m2 >= 0.158114
- `support` claim_bbb3ef5ff705: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_b8a55e06dd39: keep-going rule, from claim_f9d4216c1b37, along the charge_below ladder
- `support` claim_b8a55e06dd39: hypothesis -> supported: 1 decisive test(s), all in favour
- `rescope` claim_bbb3ef5ff705: scope changed from [battery_capacity_wh < 70.7107 and panel_area_m2 >= 0.158114] to [battery_capacity_wh < 118.912 and panel_area_m2 >= 0.158114]
- `rescope` claim_baa580394953: scope changed from [42.0416 <= battery_capacity_wh < 118.912] to [42.0416 <= battery_capacity_wh < 154.272]
- `rescope` claim_861b5bb11574: scope changed from [battery_capacity_wh >= 118.912] to [battery_capacity_wh >= 154.272]
- `rescope` claim_baa580394953: scope changed from [42.0416 <= battery_capacity_wh < 154.272] to [32.4037 <= battery_capacity_wh < 154.272]
- `propose` claim_4fbb9d04d0b6: keep-going rule, from claim_b8a55e06dd39, along the charge_below ladder
- `support` claim_4fbb9d04d0b6: hypothesis -> supported: 1 decisive test(s), all in favour
- `rescope` claim_bbb3ef5ff705: scope changed from [battery_capacity_wh < 118.912 and panel_area_m2 >= 0.158114] to [battery_capacity_wh < 154.272 and panel_area_m2 >= 0.158114]
- `rescope` claim_baa580394953: scope changed from [32.4037 <= battery_capacity_wh < 154.272] to [32.4037 <= battery_capacity_wh < 135.374]
- `rescope` claim_861b5bb11574: scope changed from [battery_capacity_wh >= 154.272] to [battery_capacity_wh >= 175.499]
- `rescope` claim_baa580394953: scope changed from [32.4037 <= battery_capacity_wh < 135.374] to [36.889 <= battery_capacity_wh < 135.374]
- `rescope` claim_bbb3ef5ff705: scope changed from [battery_capacity_wh < 154.272 and panel_area_m2 >= 0.158114] to [battery_capacity_wh < 135.374 and panel_area_m2 >= 0.158114]
- `supersede` claim_45238d1aefab: supported -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_cf56ecb3bf5a: narrowed from claim_45238d1aefab: battery_capacity_wh >= 70.7107
- `support` claim_cf56ecb3bf5a: hypothesis -> supported: 1 decisive test(s) in its region
- `refute` claim_36d8437489e9: hypothesis -> refuted: 1 decisive test(s), none in favour
- `rescope` claim_cf56ecb3bf5a: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_fd3a88a86f68: scope changed from [all tested conditions] to [battery_capacity_wh >= 70.7107]
- `supersede` claim_f9d4216c1b37: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_eea71940b239: narrowed from claim_f9d4216c1b37: battery_capacity_wh < 70.7107
- `support` claim_eea71940b239: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_025573179cdf: reversed from claim_f9d4216c1b37: battery_capacity_wh >= 70.7107
- `support` claim_025573179cdf: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_fd3a88a86f68: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 118.912]
- `rescope` claim_eea71940b239: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_025573179cdf: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_cf56ecb3bf5a: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `supersede` claim_b8a55e06dd39: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_c7b559a020ee: narrowed from claim_b8a55e06dd39: battery_capacity_wh < 70.7107
- `support` claim_c7b559a020ee: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_7df2eca041b2: reversed from claim_b8a55e06dd39: battery_capacity_wh >= 70.7107
- `support` claim_7df2eca041b2: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_c7b559a020ee: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_7df2eca041b2: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_fd3a88a86f68: scope changed from [battery_capacity_wh >= 118.912] to [battery_capacity_wh >= 91.724]
- `rescope` claim_eea71940b239: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 54.4922]
- `rescope` claim_025573179cdf: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 54.4922]
- `rescope` claim_cf56ecb3bf5a: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 28.4605]
- `rescope` claim_c7b559a020ee: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 32.4037]
- `rescope` claim_7df2eca041b2: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `rescope` claim_eea71940b239: scope changed from [battery_capacity_wh < 54.4922] to [battery_capacity_wh < 62.0737]
- `rescope` claim_025573179cdf: scope changed from [battery_capacity_wh >= 54.4922] to [battery_capacity_wh >= 62.0737]
- `rescope` claim_fd3a88a86f68: scope changed from [battery_capacity_wh >= 91.724] to [battery_capacity_wh >= 80.5183]
- `supersede` claim_4fbb9d04d0b6: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_ce514d49f6d3: narrowed from claim_4fbb9d04d0b6: battery_capacity_wh < 70.7107
- `support` claim_ce514d49f6d3: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_5aa8efa3e3af: reversed from claim_4fbb9d04d0b6: battery_capacity_wh >= 70.7107
- `support` claim_5aa8efa3e3af: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_ce514d49f6d3: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_5aa8efa3e3af: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_c7b559a020ee: scope changed from [battery_capacity_wh < 32.4037] to [battery_capacity_wh < 36.889]
- `rescope` claim_7df2eca041b2: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 36.889]
- `specialize` claim_9c0dc06c6eda: reversed from claim_fddf7a5791ad: battery_capacity_wh >= 282.843
- `support` claim_9c0dc06c6eda: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_9c0dc06c6eda: scope changed from [battery_capacity_wh >= 282.843] to [battery_capacity_wh >= 200 and panel_area_m2 < 0.158114]
- `rescope` claim_ce514d49f6d3: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 32.4037]
- `rescope` claim_5aa8efa3e3af: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 54.4922]
- `rescope` claim_cf56ecb3bf5a: scope changed from [battery_capacity_wh >= 28.4605] to [28.4605 <= battery_capacity_wh < 282.843]
- `rescope` claim_cf56ecb3bf5a: scope changed from [28.4605 <= battery_capacity_wh < 282.843] to [battery_capacity_wh >= 28.4605 and panel_area_m2 >= 0.158114]
- `rescope` claim_9c0dc06c6eda: scope changed from [battery_capacity_wh >= 200 and panel_area_m2 < 0.158114] to [battery_capacity_wh >= 282.843 and panel_area_m2 < 0.158114]
- `specialize` claim_9d31536f963b: narrowed from claim_45238d1aefab: 141.421 <= battery_capacity_wh < 282.843 and panel_area_m2 < 0.158114
- `support` claim_9d31536f963b: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_cf56ecb3bf5a: scope changed from [battery_capacity_wh >= 28.4605 and panel_area_m2 >= 0.158114] to [28.4605 <= battery_capacity_wh < 282.843 and panel_area_m2 >= 0.158114]
- `rescope` claim_baa580394953: scope changed from [36.889 <= battery_capacity_wh < 135.374] to [38.559 <= battery_capacity_wh < 135.374]
- `rescope` claim_baa580394953: scope changed from [38.559 <= battery_capacity_wh < 135.374] to [38.559 <= battery_capacity_wh < 129.534]
- `specialize` claim_0277b9d6bb79: narrowed from claim_ff958825da44: 129.534 <= battery_capacity_wh < 147.357
- `support` claim_0277b9d6bb79: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_9c0dc06c6eda: scope changed from [battery_capacity_wh >= 282.843 and panel_area_m2 < 0.158114] to [battery_capacity_wh >= 237.908]
- `rescope` claim_9d31536f963b: scope changed from [141.421 <= battery_capacity_wh < 282.843 and panel_area_m2 < 0.158114] to [118.743 <= battery_capacity_wh < 282.843 and panel_area_m2 < 0.158114]
- `rescope` claim_cf56ecb3bf5a: scope changed from [28.4605 <= battery_capacity_wh < 282.843 and panel_area_m2 >= 0.158114] to [28.4605 <= battery_capacity_wh < 84.0833]
- `rescope` claim_9d31536f963b: scope changed from [118.743 <= battery_capacity_wh < 282.843 and panel_area_m2 < 0.158114] to [118.743 <= battery_capacity_wh < 336.452]
- `rescope` claim_5aa8efa3e3af: scope changed from [battery_capacity_wh >= 54.4922] to [battery_capacity_wh >= 47.8435]
- `rescope` claim_ce514d49f6d3: scope changed from [battery_capacity_wh < 32.4037] to [battery_capacity_wh < 28.4605]
- `rescope` claim_9c0dc06c6eda: scope changed from [battery_capacity_wh >= 237.908] to [battery_capacity_wh >= 259.526]
- `rescope` claim_9d31536f963b: scope changed from [118.743 <= battery_capacity_wh < 336.452] to [118.743 <= battery_capacity_wh < 308.363]
- `rescope` claim_9d31536f963b: scope changed from [118.743 <= battery_capacity_wh < 308.363] to [109.087 <= battery_capacity_wh < 308.363]
- `supersede` claim_9842fe544ff3: refuted -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `rescope` claim_fd3a88a86f68: scope changed from [battery_capacity_wh >= 80.5183] to [80.5183 <= battery_capacity_wh < 282.843]
- `specialize` claim_368c165cd7e2: narrowed from claim_9842fe544ff3: battery_capacity_wh >= 282.843
- `support` claim_368c165cd7e2: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_fd3a88a86f68: scope changed from [80.5183 <= battery_capacity_wh < 282.843] to [80.5183 <= battery_capacity_wh < 154.272]
- `specialize` claim_f6aebf262179: reversed from claim_9842fe544ff3: 154.272 <= battery_capacity_wh < 282.843 and panel_area_m2 >= 0.158114
- `support` claim_f6aebf262179: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_fd3a88a86f68: scope changed from [80.5183 <= battery_capacity_wh < 154.272] to [80.5183 <= battery_capacity_wh < 167.929]
- `rescope` claim_f6aebf262179: scope changed from [154.272 <= battery_capacity_wh < 282.843 and panel_area_m2 >= 0.158114] to [167.929 <= battery_capacity_wh < 282.843 and panel_area_m2 >= 0.158114]
- `rescope` claim_f6aebf262179: scope changed from [167.929 <= battery_capacity_wh < 282.843 and panel_area_m2 >= 0.158114] to [167.929 <= battery_capacity_wh < 237.908 and panel_area_m2 >= 0.158114]
- `rescope` claim_368c165cd7e2: scope changed from [battery_capacity_wh >= 282.843] to [battery_capacity_wh >= 336.452]
- `rescope` claim_fd3a88a86f68: scope changed from [80.5183 <= battery_capacity_wh < 167.929] to [80.5183 <= battery_capacity_wh < 183.303]
- `rescope` claim_f6aebf262179: scope changed from [167.929 <= battery_capacity_wh < 237.908 and panel_area_m2 >= 0.158114] to [183.303 <= battery_capacity_wh < 237.908 and panel_area_m2 >= 0.158114]
- `rescope` claim_f6aebf262179: scope changed from [183.303 <= battery_capacity_wh < 237.908 and panel_area_m2 >= 0.158114] to [183.303 <= battery_capacity_wh < 259.526 and panel_area_m2 >= 0.158114]
- `rescope` claim_fd3a88a86f68: scope changed from [80.5183 <= battery_capacity_wh < 183.303] to [87.8178 <= battery_capacity_wh < 183.303]
- `rescope` claim_f6aebf262179: scope changed from [183.303 <= battery_capacity_wh < 259.526 and panel_area_m2 >= 0.158114] to [183.303 <= battery_capacity_wh < 218.174 and panel_area_m2 >= 0.158114]
- `rescope` claim_368c165cd7e2: scope changed from [battery_capacity_wh >= 336.452] to [battery_capacity_wh >= 308.363]
- `rescope` claim_5aa8efa3e3af: scope changed from [battery_capacity_wh >= 47.8435] to [battery_capacity_wh >= 45.8258]
- `specialize` claim_295a6075249b: narrowed from claim_fddf7a5791ad: 29.7489 <= battery_capacity_wh < 42.0714 and panel_area_m2 < 0.158114
- `support` claim_295a6075249b: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_c7b559a020ee: scope changed from [battery_capacity_wh < 36.889] to [battery_capacity_wh < 33.8668]
- `rescope` claim_7df2eca041b2: scope changed from [battery_capacity_wh >= 36.889] to [battery_capacity_wh >= 38.559]
- `rescope` claim_295a6075249b: scope changed from [29.7489 <= battery_capacity_wh < 42.0714 and panel_area_m2 < 0.158114] to [32.425 <= battery_capacity_wh < 42.0714 and panel_area_m2 < 0.158114]
- `rescope` claim_eea71940b239: scope changed from [battery_capacity_wh < 62.0737] to [battery_capacity_wh < 56.9451]
- `rescope` claim_025573179cdf: scope changed from [battery_capacity_wh >= 62.0737] to [battery_capacity_wh >= 56.9451]
- `rescope` claim_295a6075249b: scope changed from [32.425 <= battery_capacity_wh < 42.0714 and panel_area_m2 < 0.158114] to [32.425 <= battery_capacity_wh < 38.6049 and panel_area_m2 < 0.158114]
- `rescope` claim_7df2eca041b2: scope changed from [battery_capacity_wh >= 38.559] to [33.8668 <= battery_capacity_wh < 45.8803 and panel_area_m2 < 0.158114]
- `specialize` claim_505a91c782be: reversed from claim_b8a55e06dd39: battery_capacity_wh >= 45.8803
- `support` claim_505a91c782be: hypothesis -> supported: 5 decisive test(s) in its region
- `rescope` claim_9c0dc06c6eda: scope changed from [battery_capacity_wh >= 259.526] to [battery_capacity_wh >= 259.526 and panel_area_m2 < 0.158114]
- `specialize` claim_69a48df822d3: narrowed from claim_45238d1aefab: battery_capacity_wh >= 366.606 and panel_area_m2 >= 0.158114
- `support` claim_69a48df822d3: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_36d8437489e9: refuted -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_8e04a9a97fb4: narrowed from claim_36d8437489e9: battery_capacity_wh < 35.3553 and panel_area_m2 >= 0.158114
- `support` claim_8e04a9a97fb4: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_8e04a9a97fb4: scope changed from [battery_capacity_wh < 35.3553 and panel_area_m2 >= 0.158114] to [battery_capacity_wh < 42.0714 and panel_area_m2 >= 0.158114]
- `rescope` claim_cf56ecb3bf5a: scope changed from [28.4605 <= battery_capacity_wh < 84.0833] to [27.2489 <= battery_capacity_wh < 84.0833]
- `rescope` claim_cf56ecb3bf5a: scope changed from [27.2489 <= battery_capacity_wh < 84.0833] to [27.2489 <= battery_capacity_wh < 91.7061]
- `rescope` claim_8e04a9a97fb4: scope changed from [battery_capacity_wh < 42.0714 and panel_area_m2 >= 0.158114] to [battery_capacity_wh < 29.7489 and panel_area_m2 >= 0.158114]
- `specialize` claim_b4a689db233b: narrowed from claim_36d8437489e9: 29.7489 <= battery_capacity_wh < 42.0714
- `support` claim_b4a689db233b: hypothesis -> supported: 2 decisive test(s) in its region
- `specialize` claim_d6a4da424382: narrowed from claim_36d8437489e9: 59.4559 <= battery_capacity_wh < 84.0833
- `support` claim_d6a4da424382: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_b4a689db233b: scope changed from [29.7489 <= battery_capacity_wh < 42.0714] to [29.7489 <= battery_capacity_wh < 45.8803]
- `specialize` claim_9198690b1cf7: narrowed from claim_36d8437489e9: 84.0833 <= battery_capacity_wh < 141.421 and panel_area_m2 >= 0.158114
- `support` claim_9198690b1cf7: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_b4a689db233b: scope changed from [29.7489 <= battery_capacity_wh < 45.8803] to [29.7489 <= battery_capacity_wh < 42.0714 and panel_area_m2 < 0.158114]
- `rescope` claim_d6a4da424382: scope changed from [59.4559 <= battery_capacity_wh < 84.0833] to [59.4559 <= battery_capacity_wh < 84.0833 and panel_area_m2 < 0.158114]
- `rescope` claim_8e04a9a97fb4: scope changed from [battery_capacity_wh < 29.7489 and panel_area_m2 >= 0.158114] to [battery_capacity_wh < 45.8803 and panel_area_m2 >= 0.158114]
- `rescope` claim_9198690b1cf7: scope changed from [84.0833 <= battery_capacity_wh < 141.421 and panel_area_m2 >= 0.158114] to [59.4559 <= battery_capacity_wh < 141.421 and panel_area_m2 >= 0.158114]
- `rescope` claim_9198690b1cf7: scope changed from [59.4559 <= battery_capacity_wh < 141.421 and panel_area_m2 >= 0.158114] to [59.4559 <= battery_capacity_wh < 167.929 and panel_area_m2 >= 0.158114]
- `rescope` claim_b4a689db233b: scope changed from [29.7489 <= battery_capacity_wh < 42.0714 and panel_area_m2 < 0.158114] to [27.2489 <= battery_capacity_wh < 42.0714 and panel_area_m2 < 0.158114]
- `rescope` claim_d6a4da424382: scope changed from [59.4559 <= battery_capacity_wh < 84.0833 and panel_area_m2 < 0.158114] to [59.4559 <= battery_capacity_wh < 77.1095 and panel_area_m2 < 0.158114]
- `rescope` claim_9198690b1cf7: scope changed from [59.4559 <= battery_capacity_wh < 167.929 and panel_area_m2 >= 0.158114] to [59.4559 <= battery_capacity_wh < 153.909 and panel_area_m2 >= 0.158114]
- `rescope` claim_8e04a9a97fb4: scope changed from [battery_capacity_wh < 45.8803 and panel_area_m2 >= 0.158114] to [battery_capacity_wh < 27.2489 and panel_area_m2 >= 0.158114]
- `rescope` claim_b4a689db233b: scope changed from [27.2489 <= battery_capacity_wh < 42.0714 and panel_area_m2 < 0.158114] to [27.2489 <= battery_capacity_wh < 45.8803]
- `rescope` claim_d6a4da424382: scope changed from [59.4559 <= battery_capacity_wh < 77.1095 and panel_area_m2 < 0.158114] to [64.8587 <= battery_capacity_wh < 77.1095 and panel_area_m2 < 0.158114]
- `rescope` claim_9198690b1cf7: scope changed from [59.4559 <= battery_capacity_wh < 153.909 and panel_area_m2 >= 0.158114] to [64.8587 <= battery_capacity_wh < 153.909 and panel_area_m2 >= 0.158114]
- `rescope` claim_b4a689db233b: scope changed from [27.2489 <= battery_capacity_wh < 45.8803] to [27.2489 <= battery_capacity_wh < 38.6049]
- `specialize` claim_b0ffbb5895eb: narrowed from claim_36d8437489e9: 38.6049 <= battery_capacity_wh < 45.8803 and panel_area_m2 >= 0.158114
- `support` claim_b0ffbb5895eb: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_b4a689db233b: scope changed from [27.2489 <= battery_capacity_wh < 38.6049] to [27.2489 <= battery_capacity_wh < 38.6049 and panel_area_m2 < 0.158114]
- `rescope` claim_8e04a9a97fb4: scope changed from [battery_capacity_wh < 27.2489 and panel_area_m2 >= 0.158114] to [battery_capacity_wh < 45.8803 and panel_area_m2 >= 0.158114]
- `retire` claim_b0ffbb5895eb: supported -> retired: its region is no longer supported by the pooled evidence
- `rescope` claim_8e04a9a97fb4: scope changed from [battery_capacity_wh < 45.8803 and panel_area_m2 >= 0.158114] to [battery_capacity_wh < 27.2489 and panel_area_m2 >= 0.158114]
- `rescope` claim_b4a689db233b: scope changed from [27.2489 <= battery_capacity_wh < 38.6049 and panel_area_m2 < 0.158114] to [27.2489 <= battery_capacity_wh < 38.6049]
- `specialize` claim_2ca3bdc2bc6e: narrowed from claim_36d8437489e9: 38.6049 <= battery_capacity_wh < 45.8803 and panel_area_m2 >= 0.158114
- `support` claim_2ca3bdc2bc6e: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_f6aebf262179: scope changed from [183.303 <= battery_capacity_wh < 218.174 and panel_area_m2 >= 0.158114] to [183.303 <= battery_capacity_wh < 259.526 and panel_area_m2 >= 0.158114]
- `rescope` claim_368c165cd7e2: scope changed from [battery_capacity_wh >= 308.363] to [battery_capacity_wh >= 308.363 and panel_area_m2 < 0.158114]
- `rescope` claim_f6aebf262179: scope changed from [183.303 <= battery_capacity_wh < 259.526 and panel_area_m2 >= 0.158114] to [183.303 <= battery_capacity_wh < 218.174 and panel_area_m2 >= 0.158114]
- `rescope` claim_ce514d49f6d3: scope changed from [battery_capacity_wh < 28.4605] to [battery_capacity_wh < 28.4605 and panel_area_m2 < 0.158114]
- `specialize` claim_a51fc29d5605: narrowed from claim_45238d1aefab: 91.7061 <= battery_capacity_wh < 109.087 and panel_area_m2 >= 0.158114
- `support` claim_a51fc29d5605: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_ce514d49f6d3: scope changed from [battery_capacity_wh < 28.4605 and panel_area_m2 < 0.158114] to [battery_capacity_wh < 27.2489 and panel_area_m2 < 0.158114]
- `rescope` claim_5aa8efa3e3af: scope changed from [battery_capacity_wh >= 45.8258] to [battery_capacity_wh >= 42.05]
- `rescope` claim_bbb3ef5ff705: scope changed from [battery_capacity_wh < 135.374 and panel_area_m2 >= 0.158114] to [battery_capacity_wh < 27.2489 and panel_area_m2 >= 0.158114]
- `rescope` claim_295a6075249b: scope changed from [32.425 <= battery_capacity_wh < 38.6049 and panel_area_m2 < 0.158114] to [32.425 <= battery_capacity_wh < 38.6049]
- `specialize` claim_7ea935cbc2f1: narrowed from claim_fddf7a5791ad: 54.5436 <= battery_capacity_wh < 135.374 and panel_area_m2 >= 0.158114
- `support` claim_7ea935cbc2f1: hypothesis -> supported: 2 decisive test(s) in its region
- `rescope` claim_295a6075249b: scope changed from [32.425 <= battery_capacity_wh < 38.6049] to [32.425 <= battery_capacity_wh < 38.6049 and panel_area_m2 < 0.158114]
- `rescope` claim_bbb3ef5ff705: scope changed from [battery_capacity_wh < 27.2489 and panel_area_m2 >= 0.158114] to [battery_capacity_wh < 42.0714 and panel_area_m2 >= 0.158114]
- `rescope` claim_bbb3ef5ff705: scope changed from [battery_capacity_wh < 42.0714 and panel_area_m2 >= 0.158114] to [battery_capacity_wh < 45.8803 and panel_area_m2 >= 0.158114]

## Transfer: interpolation: untested battery sizes at the small array

4 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | failure rate |
|---|---|---|
| reference | +0.0824 | 21.1% |
| flat | -0.0933 | 46.1% |
| pooled | +0.1212 | 1.6% |
| conditional | +0.3477 | 2.3% |
| oracle | +0.3470 | 1.6% |

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.2264 [+0.1878, +0.2650], p = 0.0002
- conditional minus flat: +0.4410 [+0.3554, +0.5280], p = 0.0002
- conditional minus reference: +0.2653 [+0.2021, +0.3303], p = 0.0002
- pooled minus reference: +0.0388 [-0.0452, +0.1218], p = 0.3815
- flat minus reference: -0.1757 [-0.2584, -0.0975], p = 0.0002
- oracle minus conditional: -0.0007 [-0.0272, +0.0289], p = 0.9904

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=35, panel_area_m2=0.1 | -0.719 (81%) reference | -0.877 (97%) charge_below=0.1, desat_above=0.3 | +0.026 (6%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.017 (9%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.001 (6%) charge_below=0.6, desat_above=0.6 |
| battery_capacity_wh=70, panel_area_m2=0.1 | +0.151 (3%) reference | -0.659 (88%) charge_below=0.1, desat_above=0.3 | +0.104 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.210 (0%) charge_margin=0.25, desat_above=0.3 | +0.192 (0%) charge_below=0.25, desat_above=0.3 |
| battery_capacity_wh=140, panel_area_m2=0.1 | +0.314 (0%) reference | +0.443 (0%) charge_below=0.1, desat_above=0.3 | +0.139 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.443 (0%) charge_below=0.1, desat_above=0.3 | +0.443 (0%) charge_below=0.1, desat_above=0.3 |
| battery_capacity_wh=280, panel_area_m2=0.1 | +0.584 (0%) reference | +0.720 (0%) charge_below=0.1, desat_above=0.3 | +0.215 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.720 (0%) charge_below=0.1, desat_above=0.3 | +0.752 (0%) charge_below=0.05, desat_above=0.3 |

## Transfer: interpolation: array areas between the two studied

4 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | failure rate |
|---|---|---|
| reference | +0.1837 | 20.3% |
| flat | -0.0335 | 47.7% |
| pooled | +0.2608 | 1.6% |
| conditional | +0.4490 | 1.6% |
| oracle | +0.4567 | 0.8% |

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.1882 [+0.1588, +0.2204], p = 0.0002
- conditional minus flat: +0.4825 [+0.3847, +0.5809], p = 0.0002
- conditional minus reference: +0.2654 [+0.1923, +0.3467], p = 0.0002
- pooled minus reference: +0.0772 [-0.0082, +0.1696], p = 0.0962
- flat minus reference: -0.2172 [-0.3087, -0.1314], p = 0.0002
- oracle minus conditional: +0.0077 [-0.0256, +0.0421], p = 0.6817

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=35, panel_area_m2=0.16 | -0.597 (75%) reference | -0.842 (97%) charge_below=0.1, desat_above=0.3 | +0.170 (6%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.206 (6%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.165 (0%) charge_below=0.6, desat_above=0.6 |
| battery_capacity_wh=70, panel_area_m2=0.13 | +0.170 (6%) reference | -0.665 (91%) charge_below=0.1, desat_above=0.3 | +0.185 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.295 (0%) charge_margin=0.25, desat_above=0.3 | +0.262 (0%) charge_below=0.25, desat_above=0.3 |
| battery_capacity_wh=140, panel_area_m2=0.2 | +0.498 (0%) reference | +0.604 (3%) charge_below=0.1, desat_above=0.3 | +0.369 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.525 (0%) charge_margin=0.25 | +0.604 (3%) charge_below=0.1, desat_above=0.3 |
| battery_capacity_wh=280, panel_area_m2=0.16 | +0.663 (0%) reference | +0.770 (0%) charge_below=0.1, desat_above=0.3 | +0.319 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.770 (0%) charge_below=0.1, desat_above=0.3 | +0.796 (0%) charge_below=0.05, desat_above=0.3 |

## Transfer: extrapolation: array areas outside the studied range

2 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | failure rate |
|---|---|---|
| reference | +0.5230 | 0.0% |
| flat | +0.6042 | 0.0% |
| pooled | +0.3868 | 0.0% |
| conditional | +0.5829 | 0.0% |
| oracle | +0.6042 | 0.0% |

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.1961 [+0.1655, +0.2267], p = 0.0002
- conditional minus flat: -0.0213 [-0.0357, -0.0046], p = 0.0072
- conditional minus reference: +0.0599 [+0.0422, +0.0771], p = 0.0002
- pooled minus reference: -0.1362 [-0.1608, -0.1116], p = 0.0002
- flat minus reference: +0.0811 [+0.0608, +0.0998], p = 0.0002
- oracle minus conditional: +0.0213 [+0.0046, +0.0357], p = 0.0072

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=140, panel_area_m2=0.07 | +0.270 (0%) reference | +0.381 (0%) charge_below=0.1, desat_above=0.3 | +0.080 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.381 (0%) charge_below=0.1, desat_above=0.3 | +0.381 (0%) charge_below=0.1, desat_above=0.3 |
| battery_capacity_wh=140, panel_area_m2=0.4 | +0.776 (0%) reference | +0.827 (0%) charge_below=0.1, desat_above=0.3 | +0.693 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.784 (0%) charge_margin=0.25 | +0.827 (0%) charge_below=0.1, desat_above=0.3 |

## Do the recommended settings still work together?

Every family was tested with only its own change. Here the reference policy, each recommended change on its own, and all of them together run on the same held-out seeds.

| conditions | reference | each change alone | all together | together minus reference | finding |
|---|---|---|---|---|---|
| battery_capacity_wh=35, panel_area_m2=0.1 | -0.719 | `precharge_below,precharge_window_s` -0.653; `desat_above` -0.562; `charge_margin` -0.482; `charge_below` -0.163 | +0.017 | +0.736 [+0.573, +0.893] | consistent |
| battery_capacity_wh=70, panel_area_m2=0.1 | +0.151 | `desat_above` +0.192; `charge_margin` +0.190 | +0.210 | +0.059 [+0.021, +0.125] | consistent |
| battery_capacity_wh=140, panel_area_m2=0.1 | +0.314 | `charge_below` +0.386; `desat_above` +0.335 | +0.443 | +0.129 [+0.112, +0.147] | consistent |
| battery_capacity_wh=280, panel_area_m2=0.1 | +0.584 | `charge_below` +0.722; `desat_above` +0.600 | +0.720 | +0.136 [+0.092, +0.175] | consistent |
| battery_capacity_wh=35, panel_area_m2=0.16 | -0.597 | `precharge_below,precharge_window_s` -0.410; `desat_above` -0.457; `charge_margin` -0.477; `charge_below` -0.006 | +0.206 | +0.803 [+0.617, +0.983] | consistent |
| battery_capacity_wh=70, panel_area_m2=0.13 | +0.170 | `desat_above` +0.262; `charge_margin` +0.264 | +0.295 | +0.125 [+0.054, +0.225] | consistent |
| battery_capacity_wh=140, panel_area_m2=0.2 | +0.498 | `charge_margin` +0.525 | +0.525 | +0.027 [+0.001, +0.053] | consistent |
| battery_capacity_wh=280, panel_area_m2=0.16 | +0.663 | `charge_below` +0.768; `desat_above` +0.681 | +0.770 | +0.106 [+0.055, +0.153] | consistent |
| battery_capacity_wh=140, panel_area_m2=0.07 | +0.270 | `charge_below` +0.308; `desat_above` +0.276 | +0.381 | +0.111 [+0.099, +0.124] | consistent |
| battery_capacity_wh=140, panel_area_m2=0.4 | +0.776 | `charge_margin` +0.784 | +0.784 | +0.008 [-0.013, +0.032] | consistent |
