# Charging, desaturation and eclipse strategies across battery sizes (Basilisk / BSK-RL)

79 experiments in 21 rounds, 2608 simulator episodes (budget 4500).

**8 comparisons, 21 claims** (1 contested, 1 refuted, 7 superseded, 12 supported); 30 relations between claims.

## What the graph recommends, by condition

Settings that differ from the reference policy, in every region of conditions the supported claims tell apart. A dot keeps the reference value: either nothing was found to beat it there, or nothing could be established.

| battery_capacity_wh | `charge_below` | `charge_margin` | `desat_above` | `precharge_below` | `precharge_window_s` |
|---|---|---|---|---|---|
| below 28.46 | 0.6 | · | · | · | · |
| 28.46 to 36.89 | 0.6 | 0.25 | 0.3 | · | · |
| 36.89 to 54.54 | 0.4 | 0.25 | 0.3 | · | · |
| 54.54 to 62.07 | 0.4 | 0.25 | 0.3 | 0.6 | 900 |
| 62.07 to 135.4 | · | 0.25 | 0.3 | 0.6 | 900 |
| 135.4 to 175.5 | 0.1 | 0.25 | 0.3 | 0.6 | 900 |
| 175.5 to 218.2 | 0.1 | 0.25 | 0.3 | · | · |
| 218.2 to 259.5 | 0.05 | 0.25 | 0.3 | · | · |
| 259.5 and above | 0.05 | · | 0.3 | · | · |

## Claims by comparison

### A lower charge threshold collects more data.

Proposed by: seed (hand-written). Compares `charge_below` = 0.1 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | -0.157 | [-0.401, +0.010] | 16 | 16 / 14 |
| battery_capacity_wh=32.4 | baseline better | -0.319 | [-0.638, -0.047] | 16 | 16 / 12 |
| battery_capacity_wh=42 | baseline better | -0.450 | [-0.815, -0.135] | 16 | 16 / 10 |
| battery_capacity_wh=50 | baseline better | -0.889 | [-1.155, -0.575] | 16 | 16 / 4 |
| battery_capacity_wh=70.7 | baseline better | -0.801 | [-1.043, -0.495] | 16 | 13 / 1 |
| battery_capacity_wh=100 | baseline better | -0.494 | [-0.827, -0.191] | 16 | 8 / 0 |
| battery_capacity_wh=119 | baseline better | -0.198 | [-0.407, -0.018] | 32 | 8 / 0 |
| battery_capacity_wh=154 | intervention better | +0.113 | [+0.095, +0.131] | 16 | 0 / 0 |
| battery_capacity_wh=200 | intervention better | +0.128 | [+0.104, +0.155] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.075 | [+0.023, +0.138] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh >= 135.374, use `charge_below` = 0.1 instead of 0.25.
- **supported** (reversed): where 28.4605 <= battery_capacity_wh < 135.374, use `charge_below` = 0.25 instead of 0.1.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 28.4605.

Explanations (judged separately from the outcome):

- *less time is spent in charge mode* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 3176.25 with the intervention vs 5227.5 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=154: supports. `time_charge_s`: 4788.75 with the intervention vs 6570 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400: supports. `time_charge_s`: 945 with the intervention vs 2171.25 without, over 16 of 16 seed pairs

### Topping up the battery before each eclipse improves the score.

Proposed by: seed (hand-written). Compares `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.247 | [+0.003, +0.565] | 16 | 11 / 14 |
| battery_capacity_wh=29.7 | intervention better | +0.299 | [+0.007, +0.632] | 16 | 10 / 14 |
| battery_capacity_wh=35.4 | unresolved (inconclusive at the maximum number of seeds) | +0.144 | [-0.011, +0.315] | 48 | 29 / 34 |
| battery_capacity_wh=50 | unresolved (inconclusive at the maximum number of seeds) | +0.024 | [-0.160, +0.207] | 48 | 11 / 11 |
| battery_capacity_wh=59.5 | intervention better | +0.107 | [+0.022, +0.272] | 16 | 0 / 1 |
| battery_capacity_wh=70.7 | intervention better | +0.116 | [+0.031, +0.297] | 16 | 0 / 1 |
| battery_capacity_wh=100 | intervention better | +0.040 | [+0.009, +0.069] | 16 | 0 / 0 |
| battery_capacity_wh=119 | intervention better | +0.028 | [+0.004, +0.054] | 32 | 0 / 0 |
| battery_capacity_wh=154 | intervention better | +0.035 | [+0.001, +0.070] | 16 | 0 / 0 |
| battery_capacity_wh=200 | unresolved (inconclusive at the maximum number of seeds) | +0.017 | [-0.002, +0.036] | 48 | 0 / 0 |
| battery_capacity_wh=238 | no meaningful benefit | -0.008 | [-0.031, +0.014] | 48 | 0 / 0 |
| battery_capacity_wh=283 | no meaningful benefit | -0.034 | [-0.084, +0.015] | 16 | 0 / 0 |
| battery_capacity_wh=400 | no meaningful benefit | -0.036 | [-0.074, +0.004] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **contested** (narrowed): where battery_capacity_wh < 54.5436, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- **supported** (narrowed): where 54.5436 <= battery_capacity_wh < 175.499, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh >= 218.174.
- Not established either way, so nothing is recommended, where: 175.499 <= battery_capacity_wh < 218.174.

Explanations (judged separately from the outcome):

- *the battery does not get as low* — **supported**
  - mediator test at battery_capacity_wh=25: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=70.7: supports. `min_battery`: 0.13561 with the intervention vs 0.09824 without, over 15 of 16 seed pairs
  - mediator test at battery_capacity_wh=119: supports. `min_battery`: 0.17925 with the intervention vs 0.16316 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=154: supports. `min_battery`: 0.21542 with the intervention vs 0.18531 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=59.5: supports. `min_battery`: 0.11071 with the intervention vs 0.07713 without, over 15 of 16 seed pairs
  - mediator test at battery_capacity_wh=29.7: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=100: inconclusive. `min_battery`: 0.16963 with the intervention vs 0.1536 without, over 16 of 16 seed pairs
- *it prevents battery depletion* — **refuted**
  - mediator test at battery_capacity_wh=25: inconclusive. `failure:battery`: 0.6875 with the intervention vs 0.875 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=70.7: inconclusive. `failure:battery`: 0 with the intervention vs 0.0625 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=119: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=154: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=59.5: inconclusive. `failure:battery`: 0 with the intervention vs 0.0625 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=29.7: inconclusive. `failure:battery`: 0.625 with the intervention vs 0.875 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs

### Unloading the reaction wheels early improves the score.

Proposed by: seed (hand-written). Compares `desat_above` = 0.3 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | unresolved (inconclusive at the maximum number of seeds) | +0.060 | [-0.001, +0.159] | 48 | 42 / 44 |
| battery_capacity_wh=32.4 | intervention better | +0.186 | [+0.013, +0.445] | 16 | 10 / 12 |
| battery_capacity_wh=42 | intervention better | +0.672 | [+0.288, +1.053] | 16 | 2 / 10 |
| battery_capacity_wh=50 | intervention better | +0.377 | [+0.106, +0.700] | 16 | 0 / 4 |
| battery_capacity_wh=70.7 | intervention better | +0.152 | [+0.054, +0.351] | 16 | 0 / 1 |
| battery_capacity_wh=100 | intervention better | +0.076 | [+0.045, +0.104] | 16 | 0 / 0 |
| battery_capacity_wh=200 | intervention better | +0.074 | [+0.043, +0.104] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.031 | [+0.001, +0.069] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh >= 28.4605, use `desat_above` = 0.3 instead of 0.6.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 28.4605.

Explanations (judged separately from the outcome):

- *it prevents the wheels from reaching their speed limit* — **refuted**
  - mediator test at battery_capacity_wh=200: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=70.7: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=32.4: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
- *slower wheels draw less power, so less time is spent charging* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 3881.25 with the intervention vs 5227.5 without, over 16 of 16 seed pairs
  - moderator test at battery_capacity_wh=200: supports. effect by `max_wheel_speed_rpm`: 1500 -> -0.074, 3000 -> +0.013, 6000 -> +0.076
  - mediator test at battery_capacity_wh=70.7: supports. `time_charge_s`: 7588 with the intervention vs 9064 without, over 15 of 16 seed pairs
  - mediator test at battery_capacity_wh=42: inconclusive. `time_charge_s`: 7890 with the intervention vs 8560 without, over 6 of 16 seed pairs
  - mediator test at battery_capacity_wh=32.4: inconclusive. `time_charge_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=400: supports. `time_charge_s`: 1552.5 with the intervention vs 2171.25 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `time_charge_s`: 6825 with the intervention vs 8167.5 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: supports. `time_charge_s`: 8115 with the intervention vs 9280 without, over 12 of 16 seed pairs

### Charging in longer blocks improves the score.

Proposed by: seed (hand-written). Compares `charge_margin` = 0.25 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | unresolved (inconclusive at the maximum number of seeds) | +0.049 | [-0.056, +0.163] | 48 | 43 / 44 |
| battery_capacity_wh=32.4 | intervention better | +0.121 | [+0.011, +0.326] | 16 | 11 / 12 |
| battery_capacity_wh=42 | intervention better | +0.364 | [+0.105, +0.692] | 16 | 6 / 10 |
| battery_capacity_wh=50 | intervention better | +0.284 | [+0.079, +0.496] | 32 | 5 / 10 |
| battery_capacity_wh=70.7 | intervention better | +0.189 | [+0.074, +0.398] | 16 | 0 / 1 |
| battery_capacity_wh=100 | intervention better | +0.092 | [+0.039, +0.151] | 16 | 0 / 0 |
| battery_capacity_wh=200 | intervention better | +0.038 | [+0.004, +0.073] | 32 | 0 / 0 |
| battery_capacity_wh=238 | intervention better | +0.035 | [+0.009, +0.063] | 48 | 0 / 0 |
| battery_capacity_wh=283 | unresolved (inconclusive at the maximum number of seeds) | +0.025 | [-0.001, +0.052] | 48 | 0 / 0 |
| battery_capacity_wh=400 | unresolved (inconclusive at the maximum number of seeds) | +0.009 | [-0.019, +0.033] | 48 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where 28.4605 <= battery_capacity_wh < 259.526, use `charge_margin` = 0.25 instead of 0.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 28.4605; battery_capacity_wh >= 259.526.

Explanations (judged separately from the outcome):

- *fewer mode switches waste less scan time on slewing and settling* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `wasted_scan_s`: 501.406 with the intervention vs 840.25 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=70.7: supports. `wasted_scan_s`: 350.133 with the intervention vs 1031.73 without, over 15 of 16 seed pairs
  - mediator test at battery_capacity_wh=42: supports. `wasted_scan_s`: 458.167 with the intervention vs 1135.5 without, over 6 of 16 seed pairs
  - mediator test at battery_capacity_wh=32.4: inconclusive. `wasted_scan_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=238: supports. `wasted_scan_s`: 538.812 with the intervention vs 880.438 without, over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `wasted_scan_s`: 455.125 with the intervention vs 1003.94 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: supports. `wasted_scan_s`: 449.619 with the intervention vs 1081.14 without, over 21 of 32 seed pairs

### Going further in the direction that helped keeps helping: charge_below=0.05 beats charge_below=0.1.

Proposed by: program. Compares `charge_below` = 0.05 instead of 0.1.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | -0.014 | [-0.045, +0.004] | 16 | 16 / 16 |
| battery_capacity_wh=42 | no meaningful benefit | +0.004 | [-0.004, +0.010] | 16 | 16 / 16 |
| battery_capacity_wh=50 | no meaningful benefit | +0.002 | [-0.009, +0.010] | 16 | 16 / 16 |
| battery_capacity_wh=54.5 | no meaningful benefit | -0.013 | [-0.045, +0.010] | 16 | 16 / 16 |
| battery_capacity_wh=70.7 | baseline better | -0.244 | [-0.523, -0.027] | 16 | 16 / 13 |
| battery_capacity_wh=100 | baseline better | -0.543 | [-0.836, -0.237] | 16 | 16 / 8 |
| battery_capacity_wh=200 | baseline better | -0.260 | [-0.459, -0.088] | 32 | 9 / 0 |
| battery_capacity_wh=238 | intervention better | +0.032 | [+0.012, +0.056] | 16 | 0 / 0 |
| battery_capacity_wh=283 | intervention better | +0.023 | [+0.007, +0.043] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.024 | [+0.010, +0.041] | 32 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (reversed): where 62.0737 <= battery_capacity_wh < 218.174, use `charge_below` = 0.1 instead of 0.05.
- **supported** (narrowed): where battery_capacity_wh >= 218.174, use `charge_below` = 0.05 instead of 0.1.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 62.0737.

### Neither tested setting is acceptable here; a setting further out does better: charge_below=0.4 beats charge_below=0.25.

Proposed by: program. Compares `charge_below` = 0.4 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.305 | [+0.057, +0.633] | 16 | 10 / 14 |
| battery_capacity_wh=42 | intervention better | +0.641 | [+0.277, +0.969] | 16 | 1 / 10 |
| battery_capacity_wh=50 | intervention better | +0.259 | [+0.012, +0.575] | 16 | 0 / 4 |
| battery_capacity_wh=54.5 | intervention better | +0.219 | [+0.043, +0.411] | 32 | 0 / 7 |
| battery_capacity_wh=70.7 | unresolved (inconclusive at the maximum number of seeds) | +0.007 | [-0.042, +0.094] | 48 | 0 / 2 |
| battery_capacity_wh=91.7 | baseline better | -0.063 | [-0.084, -0.040] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.073 | [-0.094, -0.048] | 16 | 0 / 0 |
| battery_capacity_wh=119 | baseline better | -0.086 | [-0.108, -0.065] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.139 | [-0.161, -0.118] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.139 | [-0.208, -0.069] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 62.0737, use `charge_below` = 0.4 instead of 0.25.
- **supported** (reversed): where battery_capacity_wh >= 80.5183, use `charge_below` = 0.25 instead of 0.4.
- Not established either way, so nothing is recommended, where: 62.0737 <= battery_capacity_wh < 80.5183.

### Going further in the direction that helped keeps helping: charge_below=0.6 beats charge_below=0.4.

Proposed by: program. Compares `charge_below` = 0.6 instead of 0.4.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.507 | [+0.211, +0.825] | 16 | 3 / 10 |
| battery_capacity_wh=32.4 | intervention better | +0.333 | [+0.037, +0.673] | 16 | 0 / 5 |
| battery_capacity_wh=42 | unresolved (inconclusive at the maximum number of seeds) | +0.071 | [-0.022, +0.189] | 48 | 0 / 4 |
| battery_capacity_wh=50 | baseline better | -0.037 | [-0.052, -0.019] | 16 | 0 / 0 |
| battery_capacity_wh=54.5 | baseline better | -0.035 | [-0.056, -0.014] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.044 | [-0.061, -0.025] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.061 | [-0.081, -0.039] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.142 | [-0.171, -0.111] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.266 | [-0.331, -0.200] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 36.889, use `charge_below` = 0.6 instead of 0.4.
- **supported** (reversed): where battery_capacity_wh >= 45.8258, use `charge_below` = 0.4 instead of 0.6.
- Not established either way, so nothing is recommended, where: 36.889 <= battery_capacity_wh < 45.8258.

### Going further in the direction that helped keeps helping: charge_below=0.8 beats charge_below=0.6.

Proposed by: program. Compares `charge_below` = 0.8 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | unresolved (inconclusive at the maximum number of seeds) | +0.085 | [-0.011, +0.204] | 48 | 4 / 8 |
| battery_capacity_wh=32.4 | no meaningful benefit | -0.008 | [-0.024, +0.011] | 16 | 0 / 0 |
| battery_capacity_wh=42 | baseline better | -0.024 | [-0.047, -0.005] | 16 | 0 / 0 |
| battery_capacity_wh=50 | baseline better | -0.024 | [-0.050, -0.002] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.043 | [-0.063, -0.025] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.067 | [-0.090, -0.043] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.124 | [-0.151, -0.096] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.244 | [-0.309, -0.179] | 16 | 0 / 0 |

**Original claim: refuted.** Did not hold anywhere it was tested.

- **supported** (reversed): where battery_capacity_wh >= 36.889, use `charge_below` = 0.6 instead of 0.8.
- No meaningful benefit, so nothing is recommended, where: 28.4605 <= battery_capacity_wh < 36.889.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 28.4605.

## Revision history

- `propose` claim_f0f050c80d08: proposed
- `propose` claim_a8c27512692d: proposed
- `propose` claim_949ef79aa71a: proposed
- `propose` claim_a20f92a935ba: proposed
- `support` claim_f0f050c80d08: hypothesis -> supported: 1 decisive test(s), all in favour
- `support` claim_949ef79aa71a: hypothesis -> supported: 1 decisive test(s), all in favour
- `support` claim_a20f92a935ba: hypothesis -> supported: 1 decisive test(s), all in favour
- `propose` claim_bbd1b9b3334f: keep-going rule, from claim_f0f050c80d08, along the charge_below ladder
- `refute` claim_bbd1b9b3334f: hypothesis -> refuted: 1 decisive test(s), none in favour
- `specialize` claim_57f2e1c09825: reversed from claim_bbd1b9b3334f: all tested conditions
- `support` claim_57f2e1c09825: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_f0f050c80d08: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_7d88f67ca3e1: narrowed from claim_f0f050c80d08: battery_capacity_wh >= 70.7107
- `support` claim_7d88f67ca3e1: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_a8c27512692d: hypothesis -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_ee00ab7ab54b: narrowed from claim_a8c27512692d: battery_capacity_wh < 70.7107
- `support` claim_ee00ab7ab54b: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_d88deef3a9cb: nothing-works-here rule, from claim_f0f050c80d08, along the charge_below ladder
- `support` claim_d88deef3a9cb: hypothesis -> supported: 1 decisive test(s), all in favour
- `specialize` claim_bfa216011f2c: reversed from claim_f0f050c80d08: 42.0416 <= battery_capacity_wh < 118.912
- `support` claim_bfa216011f2c: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_7d88f67ca3e1: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 118.912]
- `rescope` claim_ee00ab7ab54b: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 118.912]
- `supersede` claim_949ef79aa71a: supported -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_8db9e06feee9: narrowed from claim_949ef79aa71a: battery_capacity_wh >= 70.7107
- `support` claim_8db9e06feee9: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_299bfa459613: keep-going rule, from claim_d88deef3a9cb, along the charge_below ladder
- `support` claim_299bfa459613: hypothesis -> supported: 1 decisive test(s), all in favour
- `rescope` claim_8db9e06feee9: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_bfa216011f2c: scope changed from [42.0416 <= battery_capacity_wh < 118.912] to [42.0416 <= battery_capacity_wh < 154.272]
- `rescope` claim_7d88f67ca3e1: scope changed from [battery_capacity_wh >= 118.912] to [battery_capacity_wh >= 154.272]
- `rescope` claim_ee00ab7ab54b: scope changed from [battery_capacity_wh < 118.912] to [battery_capacity_wh < 154.272]
- `propose` claim_be82ada2b47e: keep-going rule, from claim_299bfa459613, along the charge_below ladder
- `rescope` claim_bfa216011f2c: scope changed from [42.0416 <= battery_capacity_wh < 154.272] to [32.4037 <= battery_capacity_wh < 154.272]
- `rescope` claim_8db9e06feee9: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `rescope` claim_bfa216011f2c: scope changed from [32.4037 <= battery_capacity_wh < 154.272] to [32.4037 <= battery_capacity_wh < 135.374]
- `rescope` claim_7d88f67ca3e1: scope changed from [battery_capacity_wh >= 154.272] to [battery_capacity_wh >= 135.374]
- `rescope` claim_ee00ab7ab54b: scope changed from [battery_capacity_wh < 154.272] to [battery_capacity_wh < 175.499]
- `rescope` claim_bfa216011f2c: scope changed from [32.4037 <= battery_capacity_wh < 135.374] to [28.4605 <= battery_capacity_wh < 135.374]
- `rescope` claim_8db9e06feee9: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 28.4605]
- `supersede` claim_a20f92a935ba: supported -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_284fbe420cc6: narrowed from claim_a20f92a935ba: battery_capacity_wh >= 70.7107
- `support` claim_284fbe420cc6: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_284fbe420cc6: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_57f2e1c09825: scope changed from [all tested conditions] to [battery_capacity_wh >= 70.7107]
- `supersede` claim_d88deef3a9cb: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_8e60848f240e: narrowed from claim_d88deef3a9cb: battery_capacity_wh < 70.7107
- `support` claim_8e60848f240e: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_8b38a9085de1: reversed from claim_d88deef3a9cb: battery_capacity_wh >= 70.7107
- `support` claim_8b38a9085de1: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_57f2e1c09825: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_8e60848f240e: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_8b38a9085de1: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 118.912]
- `rescope` claim_284fbe420cc6: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `supersede` claim_299bfa459613: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_91fa6bbeb67d: narrowed from claim_299bfa459613: battery_capacity_wh < 70.7107
- `support` claim_91fa6bbeb67d: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_5d646bb8cde4: reversed from claim_299bfa459613: battery_capacity_wh >= 70.7107
- `support` claim_5d646bb8cde4: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_91fa6bbeb67d: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_5d646bb8cde4: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_8b38a9085de1: scope changed from [battery_capacity_wh >= 118.912] to [battery_capacity_wh >= 91.724]
- `rescope` claim_57f2e1c09825: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 54.4922]
- `rescope` claim_8e60848f240e: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 54.4922]
- `rescope` claim_91fa6bbeb67d: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 32.4037]
- `rescope` claim_5d646bb8cde4: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 54.4922]
- `rescope` claim_57f2e1c09825: scope changed from [battery_capacity_wh >= 54.4922] to [battery_capacity_wh >= 62.0737]
- `rescope` claim_8e60848f240e: scope changed from [battery_capacity_wh < 54.4922] to [battery_capacity_wh < 62.0737]
- `rescope` claim_8b38a9085de1: scope changed from [battery_capacity_wh >= 91.724] to [battery_capacity_wh >= 80.5183]
- `rescope` claim_5d646bb8cde4: scope changed from [battery_capacity_wh >= 54.4922] to [battery_capacity_wh >= 47.8435]
- `rescope` claim_284fbe420cc6: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 28.4605]
- `rescope` claim_91fa6bbeb67d: scope changed from [battery_capacity_wh < 32.4037] to [battery_capacity_wh < 36.889]
- `refute` claim_be82ada2b47e: hypothesis -> refuted: 1 decisive test(s), none in favour
- `specialize` claim_290fd9dd1bd8: reversed from claim_be82ada2b47e: battery_capacity_wh >= 70.7107
- `support` claim_290fd9dd1bd8: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_290fd9dd1bd8: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_290fd9dd1bd8: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `rescope` claim_284fbe420cc6: scope changed from [battery_capacity_wh >= 28.4605] to [28.4605 <= battery_capacity_wh < 282.843]
- `supersede` claim_bbd1b9b3334f: refuted -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `rescope` claim_57f2e1c09825: scope changed from [battery_capacity_wh >= 62.0737] to [62.0737 <= battery_capacity_wh < 282.843]
- `specialize` claim_93c17adaf5a0: narrowed from claim_bbd1b9b3334f: battery_capacity_wh >= 282.843
- `support` claim_93c17adaf5a0: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_284fbe420cc6: scope changed from [28.4605 <= battery_capacity_wh < 282.843] to [28.4605 <= battery_capacity_wh < 237.908]
- `rescope` claim_57f2e1c09825: scope changed from [62.0737 <= battery_capacity_wh < 282.843] to [62.0737 <= battery_capacity_wh < 237.908]
- `rescope` claim_93c17adaf5a0: scope changed from [battery_capacity_wh >= 282.843] to [battery_capacity_wh >= 237.908]
- `rescope` claim_290fd9dd1bd8: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 36.889]
- `rescope` claim_284fbe420cc6: scope changed from [28.4605 <= battery_capacity_wh < 237.908] to [28.4605 <= battery_capacity_wh < 259.526]
- `rescope` claim_57f2e1c09825: scope changed from [62.0737 <= battery_capacity_wh < 237.908] to [62.0737 <= battery_capacity_wh < 218.174]
- `rescope` claim_93c17adaf5a0: scope changed from [battery_capacity_wh >= 237.908] to [battery_capacity_wh >= 218.174]
- `rescope` claim_ee00ab7ab54b: scope changed from [battery_capacity_wh < 175.499] to [battery_capacity_wh < 59.4559]
- `contest` claim_ee00ab7ab54b: supported -> contested: the 2 test(s) in its region disagree and could not be separated
- `specialize` claim_70ba15b98078: narrowed from claim_a8c27512692d: 59.4559 <= battery_capacity_wh < 175.499
- `support` claim_70ba15b98078: hypothesis -> supported: 3 decisive test(s) in its region
- `rescope` claim_ee00ab7ab54b: scope changed from [battery_capacity_wh < 59.4559] to [battery_capacity_wh < 54.5436]
- `rescope` claim_70ba15b98078: scope changed from [59.4559 <= battery_capacity_wh < 175.499] to [54.5436 <= battery_capacity_wh < 175.499]
- `rescope` claim_5d646bb8cde4: scope changed from [battery_capacity_wh >= 47.8435] to [battery_capacity_wh >= 45.8258]

## Transfer: interpolation (inside the studied range)

4 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | spacecraft lost | success rate |
|---|---|---|---|
| reference | +0.3050 | 19.5% | 78.1% |
| flat | +0.2589 | 29.7% | 69.5% |
| pooled | +0.4426 | 1.6% | 93.0% |
| conditional | +0.6220 | 1.6% | 97.7% |
| oracle | +0.6070 | 0.0% | 95.3% |

Success: the spacecraft survived and recorded data for at least 20% of the episode (`docs/metrics.md`, 2.3).

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.1794 [+0.1495, +0.2120], p = 0.0002; resampling whole seeds: [+0.1536, +0.2031], p = 0.0002
- conditional minus flat: +0.3631 [+0.2666, +0.4615], p = 0.0002; resampling whole seeds: [+0.3001, +0.4242], p = 0.0002
- conditional minus reference: +0.3170 [+0.2346, +0.4032], p = 0.0002; resampling whole seeds: [+0.2467, +0.3834], p = 0.0002
- pooled minus reference: +0.1376 [+0.0400, +0.2350], p = 0.0050; resampling whole seeds: [+0.0714, +0.2010], p = 0.0010
- flat minus reference: -0.0461 [-0.1219, +0.0290], p = 0.2360; resampling whole seeds: [-0.1150, +0.0269], p = 0.2106
- oracle minus conditional: -0.0150 [-0.0414, +0.0190], p = 0.3755; resampling whole seeds: [-0.0426, +0.0179], p = 0.3605

The first interval treats every (condition, seed) episode pair as independent. The second averages over the conditions first and resamples the 32 seeds, because every condition reuses the same seeds.

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=35 | -0.535 (75%) reference | -0.745 (94%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.357 (6%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.357 (6%) charge_below=0.6, charge_margin=0.25, desat_above=0.3 | +0.348 (0%) charge_below=0.6, desat_above=0.6 |
| battery_capacity_wh=70 | +0.424 (3%) reference | +0.260 (25%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.460 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.575 (0%) charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.517 (0%) charge_below=0.25, desat_above=0.3 |
| battery_capacity_wh=140 | +0.584 (0%) reference | +0.704 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.465 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.711 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.718 (0%) charge_below=0.1, desat_above=0.3 |
| battery_capacity_wh=280 | +0.747 (0%) reference | +0.817 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.489 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.846 (0%) charge_below=0.05, desat_above=0.3 | +0.846 (0%) charge_below=0.05, desat_above=0.3 |

## Transfer: extrapolation (outside the studied range)

2 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | spacecraft lost | success rate |
|---|---|---|---|
| reference | -0.0167 | 48.4% | 51.6% |
| flat | -0.0296 | 50.0% | 50.0% |
| pooled | +0.2168 | 17.2% | 65.6% |
| conditional | +0.3598 | 20.3% | 73.4% |
| oracle | +0.4790 | 9.4% | 82.8% |

Success: the spacecraft survived and recorded data for at least 20% of the episode (`docs/metrics.md`, 2.3).

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.1429 [-0.0147, +0.2989], p = 0.0898; resampling whole seeds: [-0.0235, +0.3000], p = 0.0982
- conditional minus flat: +0.3894 [+0.2502, +0.5346], p = 0.0002; resampling whole seeds: [+0.2805, +0.4954], p = 0.0002
- conditional minus reference: +0.3765 [+0.2394, +0.5199], p = 0.0002; resampling whole seeds: [+0.2697, +0.4806], p = 0.0002
- pooled minus reference: +0.2336 [+0.0523, +0.4253], p = 0.0168; resampling whole seeds: [+0.0892, +0.3713], p = 0.0038
- flat minus reference: -0.0129 [-0.0614, +0.0276], p = 0.6869; resampling whole seeds: [-0.0641, +0.0269], p = 0.6995
- oracle minus conditional: +0.1192 [+0.0217, +0.2261], p = 0.0354; resampling whole seeds: [+0.0229, +0.2175], p = 0.0314

The first interval treats every (condition, seed) episode pair as independent. The second averages over the conditions first and resamples the 32 seeds, because every condition reuses the same seeds.

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=18 | -0.877 (97%) reference | -0.933 (100%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | -0.065 (34%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | -0.158 (41%) charge_below=0.6 | +0.080 (19%) charge_below=0.8, desat_above=0.6 |
| battery_capacity_wh=600 | +0.843 (0%) reference | +0.874 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.499 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.878 (0%) charge_below=0.05, desat_above=0.3 | +0.878 (0%) charge_below=0.05, desat_above=0.3 |

## Do the recommended settings still work together?

Every family was tested with only its own change. Here the reference policy, each recommended change on its own, and all of them together run on the same held-out seeds.

| conditions | reference | each change alone | all together | together minus reference | finding |
|---|---|---|---|---|---|
| battery_capacity_wh=35 | -0.535 | `charge_below` +0.348; `desat_above` -0.393; `charge_margin` -0.358 | +0.357 | +0.892 [+0.677, +1.097] | consistent |
| battery_capacity_wh=70 | +0.424 | `precharge_below,precharge_window_s` +0.493; `desat_above` +0.517; `charge_margin` +0.511 | +0.575 | +0.151 [+0.082, +0.245] | consistent |
| battery_capacity_wh=140 | +0.584 | `charge_below` +0.540; `precharge_below,precharge_window_s` +0.607; `desat_above` +0.636; `charge_margin` +0.598 | +0.711 | +0.126 [+0.080, +0.169] | consistent |
| battery_capacity_wh=280 | +0.747 | `charge_below` +0.847; `desat_above` +0.760 | +0.846 | +0.099 [+0.039, +0.156] | consistent |
| battery_capacity_wh=18 | -0.877 | `charge_below` -0.158 | -0.158 | +0.719 [+0.500, +0.927] | consistent |
| battery_capacity_wh=600 | +0.843 | `charge_below` +0.903; `desat_above` +0.830 | +0.878 | +0.034 [-0.016, +0.091] | unhelpful change |

- battery_capacity_wh=600: on its own, `desat_above` (+0.830 against +0.843) scores below the reference here, so the claim behind it is being applied where it does not hold. All together is -0.025 [-0.050, -0.007] against `charge_below` alone.
