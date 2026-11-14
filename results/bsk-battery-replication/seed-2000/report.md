# Charging, desaturation and eclipse strategies across battery sizes (Basilisk / BSK-RL)

75 experiments in 20 rounds, 2720 simulator episodes (budget 4500).

**8 comparisons, 22 claims** (1 refuted, 7 superseded, 14 supported); 34 relations between claims.

## What the graph recommends, by condition

Settings that differ from the reference policy, in every region of conditions the supported claims tell apart. A dot keeps the reference value: either nothing was found to beat it there, or nothing could be established.

| battery_capacity_wh | `charge_below` | `charge_margin` | `desat_above` | `precharge_below` | `precharge_window_s` |
|---|---|---|---|---|---|
| below 27.25 | 0.6 | 0.25 | · | · | · |
| 27.25 to 28.46 | 0.6 | 0.25 | · | 0.6 | 900 |
| 28.46 to 36.89 | 0.6 | 0.25 | 0.3 | 0.6 | 900 |
| 36.89 to 52.2 | 0.4 | 0.25 | 0.3 | 0.6 | 900 |
| 52.2 to 135.4 | · | 0.25 | 0.3 | 0.6 | 900 |
| 135.4 to 183.3 | 0.1 | 0.25 | 0.3 | 0.6 | 900 |
| 183.3 to 259.5 | 0.1 | 0.25 | 0.3 | · | · |
| 259.5 to 308.4 | 0.05 | 0.25 | 0.3 | · | · |
| 308.4 to 366.6 | 0.05 | · | 0.3 | · | · |
| 366.6 and above | 0.1 | · | 0.3 | · | · |

## Claims by comparison

### A lower charge threshold collects more data.

Proposed by: seed (hand-written). Compares `charge_below` = 0.1 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | -0.016 | [-0.044, +0.007] | 16 | 16 / 16 |
| battery_capacity_wh=32.4 | baseline better | -0.165 | [-0.409, -0.009] | 16 | 16 / 14 |
| battery_capacity_wh=42 | baseline better | -0.406 | [-0.727, -0.122] | 16 | 16 / 11 |
| battery_capacity_wh=50 | baseline better | -0.811 | [-1.077, -0.527] | 16 | 16 / 5 |
| battery_capacity_wh=70.7 | baseline better | -1.075 | [-1.116, -1.035] | 16 | 16 / 0 |
| battery_capacity_wh=100 | baseline better | -0.617 | [-0.903, -0.300] | 16 | 10 / 0 |
| battery_capacity_wh=119 | baseline better | -0.225 | [-0.432, -0.048] | 32 | 9 / 0 |
| battery_capacity_wh=154 | intervention better | +0.100 | [+0.075, +0.122] | 16 | 0 / 0 |
| battery_capacity_wh=200 | intervention better | +0.125 | [+0.097, +0.148] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.085 | [+0.026, +0.150] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh >= 135.374, use `charge_below` = 0.1 instead of 0.25.
- **supported** (reversed): where 28.4605 <= battery_capacity_wh < 135.374, use `charge_below` = 0.25 instead of 0.1.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 28.4605.

Explanations (judged separately from the outcome):

- *less time is spent in charge mode* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 3810 with the intervention vs 5816.25 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=154: supports. `time_charge_s`: 5321.25 with the intervention vs 6930 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400: supports. `time_charge_s`: 1147.5 with the intervention vs 2497.5 without, over 16 of 16 seed pairs

### Topping up the battery before each eclipse improves the score.

Proposed by: seed (hand-written). Compares `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | unresolved (inconclusive at the maximum number of seeds) | +0.071 | [-0.005, +0.176] | 48 | 44 / 47 |
| battery_capacity_wh=29.7 | intervention better | +0.181 | [+0.029, +0.368] | 32 | 24 / 29 |
| battery_capacity_wh=35.4 | intervention better | +0.366 | [+0.074, +0.696] | 16 | 9 / 14 |
| battery_capacity_wh=50 | intervention better | +0.356 | [+0.086, +0.639] | 16 | 0 / 5 |
| battery_capacity_wh=100 | intervention better | +0.027 | [+0.013, +0.040] | 48 | 0 / 0 |
| battery_capacity_wh=141 | intervention better | +0.022 | [+0.003, +0.039] | 32 | 0 / 0 |
| battery_capacity_wh=168 | intervention better | +0.022 | [+0.006, +0.037] | 48 | 0 / 0 |
| battery_capacity_wh=200 | unresolved (inconclusive at the maximum number of seeds) | +0.009 | [-0.010, +0.027] | 48 | 0 / 0 |
| battery_capacity_wh=238 | no meaningful benefit | -0.010 | [-0.034, +0.016] | 32 | 0 / 0 |
| battery_capacity_wh=283 | no meaningful benefit | -0.023 | [-0.060, +0.016] | 16 | 0 / 0 |
| battery_capacity_wh=336 | baseline better | -0.042 | [-0.070, -0.013] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.057 | [-0.098, -0.018] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where 27.2489 <= battery_capacity_wh < 183.303, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- **supported** (reversed): where battery_capacity_wh >= 308.363, use `precharge_below` = 0 instead of 0.6, `precharge_window_s` = 0 instead of 900.
- No meaningful benefit, so nothing is recommended, where: 218.174 <= battery_capacity_wh < 308.363.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 27.2489; 183.303 <= battery_capacity_wh < 218.174.

Explanations (judged separately from the outcome):

- *the battery does not get as low* — **supported**
  - mediator test at battery_capacity_wh=50: supports. `min_battery`: 0.09738 with the intervention vs 0.05206 without, over 11 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `min_battery`: 0.1689 with the intervention vs 0.14227 without, over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=35.4: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=141: supports. `min_battery`: 0.20143 with the intervention vs 0.18392 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=29.7: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=168: supports. `min_battery`: 0.22073 with the intervention vs 0.19518 without, over 48 of 48 seed pairs
- *it prevents battery depletion* — **contested**
  - mediator test at battery_capacity_wh=50: supports. `failure:battery`: 0 with the intervention vs 0.3125 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=35.4: supports. `failure:battery`: 0.5625 with the intervention vs 0.875 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=141: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=29.7: supports. `failure:battery`: 0.75 with the intervention vs 0.90625 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=168: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 48 of 48 seed pairs

### Unloading the reaction wheels early improves the score.

Proposed by: seed (hand-written). Compares `desat_above` = 0.3 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | unresolved (inconclusive at the maximum number of seeds) | +0.075 | [-0.006, +0.182] | 48 | 44 / 47 |
| battery_capacity_wh=32.4 | intervention better | +0.174 | [+0.012, +0.353] | 48 | 37 / 42 |
| battery_capacity_wh=42 | intervention better | +0.707 | [+0.287, +1.078] | 16 | 2 / 11 |
| battery_capacity_wh=50 | intervention better | +0.356 | [+0.103, +0.665] | 16 | 1 / 5 |
| battery_capacity_wh=70.7 | intervention better | +0.105 | [+0.063, +0.149] | 16 | 0 / 0 |
| battery_capacity_wh=100 | intervention better | +0.100 | [+0.063, +0.144] | 16 | 0 / 0 |
| battery_capacity_wh=200 | intervention better | +0.088 | [+0.056, +0.125] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.034 | [+0.003, +0.072] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh >= 28.4605, use `desat_above` = 0.3 instead of 0.6.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 28.4605.

Explanations (judged separately from the outcome):

- *it prevents the wheels from reaching their speed limit* — **refuted**
  - mediator test at battery_capacity_wh=200: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=70.7: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=32.4: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=400: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
- *slower wheels draw less power, so less time is spent charging* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 4158.75 with the intervention vs 5816.25 without, over 16 of 16 seed pairs
  - moderator test at battery_capacity_wh=200: inconclusive. effect by `max_wheel_speed_rpm`: 1500 -> -0.001, 3000 -> +0.010, 6000 -> +0.066
  - mediator test at battery_capacity_wh=70.7: supports. `time_charge_s`: 7608.75 with the intervention vs 9375 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42: inconclusive. `time_charge_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=32.4: inconclusive. `time_charge_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=400: supports. `time_charge_s`: 1747.5 with the intervention vs 2497.5 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `time_charge_s`: 6720 with the intervention vs 8501.25 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: supports. `time_charge_s`: 8094.55 with the intervention vs 9501.82 without, over 11 of 16 seed pairs

### Charging in longer blocks improves the score.

Proposed by: seed (hand-written). Compares `charge_margin` = 0.25 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.057 | [+0.010, +0.161] | 32 | 30 / 31 |
| battery_capacity_wh=50 | intervention better | +0.255 | [+0.057, +0.473] | 32 | 6 / 11 |
| battery_capacity_wh=100 | intervention better | +0.109 | [+0.050, +0.174] | 16 | 0 / 0 |
| battery_capacity_wh=200 | intervention better | +0.060 | [+0.005, +0.118] | 16 | 0 / 0 |
| battery_capacity_wh=283 | intervention better | +0.032 | [+0.001, +0.068] | 32 | 0 / 0 |
| battery_capacity_wh=336 | unresolved (inconclusive at the maximum number of seeds) | +0.011 | [-0.009, +0.037] | 48 | 0 / 0 |
| battery_capacity_wh=400 | unresolved (inconclusive at the maximum number of seeds) | +0.008 | [-0.016, +0.040] | 48 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 308.363, use `charge_margin` = 0.25 instead of 0.
- Not established either way, so nothing is recommended, where: battery_capacity_wh >= 308.363.

Explanations (judged separately from the outcome):

- *fewer mode switches waste less scan time on slewing and settling* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `wasted_scan_s`: 484.312 with the intervention vs 943.438 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=25: inconclusive. `wasted_scan_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=50: supports. `wasted_scan_s`: 496.15 with the intervention vs 1169.85 without, over 20 of 32 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `wasted_scan_s`: 449.938 with the intervention vs 1121.38 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=283: supports. `wasted_scan_s`: 508.781 with the intervention vs 819.312 without, over 32 of 32 seed pairs

### Going further in the direction that helped keeps helping: charge_below=0.05 beats charge_below=0.1.

Proposed by: program. Compares `charge_below` = 0.05 instead of 0.1.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | +0.003 | [+0.000, +0.007] | 16 | 16 / 16 |
| battery_capacity_wh=50 | no meaningful benefit | -0.009 | [-0.039, +0.012] | 16 | 16 / 16 |
| battery_capacity_wh=59.5 | no meaningful benefit | +0.003 | [-0.021, +0.018] | 16 | 16 / 16 |
| battery_capacity_wh=70.7 | baseline better | -0.038 | [-0.077, -0.003] | 16 | 16 / 16 |
| battery_capacity_wh=100 | baseline better | -0.403 | [-0.721, -0.118] | 16 | 16 / 10 |
| battery_capacity_wh=141 | baseline better | -0.641 | [-0.912, -0.363] | 16 | 10 / 0 |
| battery_capacity_wh=168 | baseline better | -0.547 | [-0.816, -0.232] | 16 | 10 / 1 |
| battery_capacity_wh=200 | no meaningful benefit | -0.219 | [-0.483, +0.012] | 16 | 4 / 0 |
| battery_capacity_wh=238 | unresolved (inconclusive at the maximum number of seeds) | -0.014 | [-0.094, +0.035] | 48 | 2 / 0 |
| battery_capacity_wh=283 | intervention better | +0.023 | [+0.009, +0.039] | 16 | 0 / 0 |
| battery_capacity_wh=336 | intervention better | +0.025 | [+0.004, +0.049] | 16 | 0 / 0 |
| battery_capacity_wh=400 | unresolved (inconclusive at the maximum number of seeds) | +0.014 | [+0.004, +0.025] | 48 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (reversed): where 64.8587 <= battery_capacity_wh < 183.303, use `charge_below` = 0.1 instead of 0.05.
- **supported** (narrowed): where 259.526 <= battery_capacity_wh < 366.606, use `charge_below` = 0.05 instead of 0.1.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 64.8587; 183.303 <= battery_capacity_wh < 218.174.
- Not established either way, so nothing is recommended, where: 218.174 <= battery_capacity_wh < 259.526; battery_capacity_wh >= 366.606.

### Neither tested setting is acceptable here; a setting further out does better: charge_below=0.4 beats charge_below=0.25.

Proposed by: program. Compares `charge_below` = 0.4 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.705 | [+0.399, +1.012] | 16 | 7 / 16 |
| battery_capacity_wh=42 | intervention better | +0.739 | [+0.439, +1.019] | 16 | 0 / 11 |
| battery_capacity_wh=50 | intervention better | +0.321 | [+0.083, +0.564] | 32 | 1 / 11 |
| battery_capacity_wh=54.5 | baseline better | -0.025 | [-0.039, -0.011] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.046 | [-0.068, -0.026] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.066 | [-0.082, -0.051] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.123 | [-0.147, -0.096] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.144 | [-0.211, -0.070] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 52.2015, use `charge_below` = 0.4 instead of 0.25.
- **supported** (reversed): where battery_capacity_wh >= 52.2015, use `charge_below` = 0.25 instead of 0.4.

### Going further in the direction that helped keeps helping: charge_below=0.6 beats charge_below=0.4.

Proposed by: program. Compares `charge_below` = 0.6 instead of 0.4.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.390 | [+0.106, +0.716] | 16 | 1 / 7 |
| battery_capacity_wh=32.4 | intervention better | +0.158 | [+0.015, +0.334] | 32 | 1 / 6 |
| battery_capacity_wh=42 | baseline better | -0.034 | [-0.048, -0.018] | 16 | 0 / 0 |
| battery_capacity_wh=50 | unresolved (inconclusive at the maximum number of seeds) | -0.010 | [-0.046, +0.066] | 48 | 0 / 1 |
| battery_capacity_wh=59.5 | baseline better | -0.044 | [-0.066, -0.019] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.048 | [-0.064, -0.032] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.066 | [-0.094, -0.038] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.151 | [-0.180, -0.114] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.272 | [-0.349, -0.188] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 36.889, use `charge_below` = 0.6 instead of 0.4.
- **supported** (reversed): where 36.889 <= battery_capacity_wh < 45.8258, use `charge_below` = 0.4 instead of 0.6.
- **supported** (reversed): where battery_capacity_wh >= 54.5436, use `charge_below` = 0.4 instead of 0.6.
- Not established either way, so nothing is recommended, where: 45.8258 <= battery_capacity_wh < 54.5436.

### Going further in the direction that helped keeps helping: charge_below=0.8 beats charge_below=0.6.

Proposed by: program. Compares `charge_below` = 0.8 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | unresolved (inconclusive at the maximum number of seeds) | +0.081 | [-0.007, +0.195] | 48 | 2 / 6 |
| battery_capacity_wh=32.4 | baseline better | -0.029 | [-0.051, -0.013] | 16 | 0 / 0 |
| battery_capacity_wh=42 | baseline better | -0.026 | [-0.051, -0.003] | 16 | 0 / 0 |
| battery_capacity_wh=50 | baseline better | -0.031 | [-0.059, -0.010] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.043 | [-0.071, -0.018] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.061 | [-0.104, -0.027] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.097 | [-0.130, -0.063] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.193 | [-0.263, -0.125] | 16 | 0 / 0 |

**Original claim: refuted.** Did not hold anywhere it was tested.

- **supported** (reversed): where battery_capacity_wh >= 28.4605, use `charge_below` = 0.6 instead of 0.8.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 28.4605.

## Revision history

- `propose` claim_c6b81cc412b0: proposed
- `propose` claim_fc6ed5afacdb: proposed
- `propose` claim_b17a3cc7229e: proposed
- `propose` claim_f9867c7df577: proposed
- `support` claim_c6b81cc412b0: hypothesis -> supported: 1 decisive test(s), all in favour
- `support` claim_b17a3cc7229e: hypothesis -> supported: 1 decisive test(s), all in favour
- `support` claim_f9867c7df577: hypothesis -> supported: 1 decisive test(s), all in favour
- `propose` claim_ee1d538aed53: keep-going rule, from claim_c6b81cc412b0, along the charge_below ladder
- `refute` claim_ee1d538aed53: hypothesis -> refuted: 1 decisive test(s), none in favour
- `supersede` claim_c6b81cc412b0: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_c452ceebbd2b: narrowed from claim_c6b81cc412b0: battery_capacity_wh >= 70.7107
- `support` claim_c452ceebbd2b: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_ecd3d2432e5e: nothing-works-here rule, from claim_c6b81cc412b0, along the charge_below ladder
- `support` claim_ecd3d2432e5e: hypothesis -> supported: 1 decisive test(s), all in favour
- `specialize` claim_3a8e293e88f9: reversed from claim_c6b81cc412b0: 42.0416 <= battery_capacity_wh < 118.912
- `support` claim_3a8e293e88f9: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_c452ceebbd2b: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 118.912]
- `supersede` claim_b17a3cc7229e: supported -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_b56541d3254d: narrowed from claim_b17a3cc7229e: battery_capacity_wh >= 70.7107
- `support` claim_b56541d3254d: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_9b879caf9c39: keep-going rule, from claim_ecd3d2432e5e, along the charge_below ladder
- `support` claim_9b879caf9c39: hypothesis -> supported: 1 decisive test(s), all in favour
- `rescope` claim_b56541d3254d: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_3a8e293e88f9: scope changed from [42.0416 <= battery_capacity_wh < 118.912] to [42.0416 <= battery_capacity_wh < 154.272]
- `rescope` claim_c452ceebbd2b: scope changed from [battery_capacity_wh >= 118.912] to [battery_capacity_wh >= 154.272]
- `rescope` claim_3a8e293e88f9: scope changed from [42.0416 <= battery_capacity_wh < 154.272] to [32.4037 <= battery_capacity_wh < 154.272]
- `propose` claim_0efc298fc0dd: keep-going rule, from claim_9b879caf9c39, along the charge_below ladder
- `rescope` claim_b56541d3254d: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `rescope` claim_3a8e293e88f9: scope changed from [32.4037 <= battery_capacity_wh < 154.272] to [32.4037 <= battery_capacity_wh < 135.374]
- `rescope` claim_c452ceebbd2b: scope changed from [battery_capacity_wh >= 154.272] to [battery_capacity_wh >= 135.374]
- `rescope` claim_3a8e293e88f9: scope changed from [32.4037 <= battery_capacity_wh < 135.374] to [28.4605 <= battery_capacity_wh < 135.374]
- `rescope` claim_b56541d3254d: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 28.4605]
- `supersede` claim_ecd3d2432e5e: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_33d045066679: narrowed from claim_ecd3d2432e5e: battery_capacity_wh < 70.7107
- `support` claim_33d045066679: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_34e45e3382e0: reversed from claim_ecd3d2432e5e: battery_capacity_wh >= 70.7107
- `support` claim_34e45e3382e0: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_33d045066679: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_34e45e3382e0: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `supersede` claim_9b879caf9c39: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_7705fe8e2885: narrowed from claim_9b879caf9c39: battery_capacity_wh < 70.7107
- `support` claim_7705fe8e2885: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_485c1742ff03: reversed from claim_9b879caf9c39: battery_capacity_wh >= 70.7107
- `support` claim_485c1742ff03: hypothesis -> supported: 1 decisive test(s) in its region
- `refute` claim_0efc298fc0dd: hypothesis -> refuted: 1 decisive test(s), none in favour
- `specialize` claim_94081de0302b: reversed from claim_0efc298fc0dd: battery_capacity_wh >= 70.7107
- `support` claim_94081de0302b: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_7705fe8e2885: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_485c1742ff03: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_94081de0302b: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_33d045066679: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 54.4922]
- `rescope` claim_34e45e3382e0: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 54.4922]
- `rescope` claim_7705fe8e2885: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 32.4037]
- `rescope` claim_485c1742ff03: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `rescope` claim_94081de0302b: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `rescope` claim_33d045066679: scope changed from [battery_capacity_wh < 54.4922] to [battery_capacity_wh < 47.8435]
- `rescope` claim_34e45e3382e0: scope changed from [battery_capacity_wh >= 54.4922] to [battery_capacity_wh >= 47.8435]
- `supersede` claim_fc6ed5afacdb: hypothesis -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_268a956f0584: narrowed from claim_fc6ed5afacdb: 35.3553 <= battery_capacity_wh < 100
- `support` claim_268a956f0584: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_268a956f0584: scope changed from [35.3553 <= battery_capacity_wh < 100] to [35.3553 <= battery_capacity_wh < 141.421]
- `rescope` claim_268a956f0584: scope changed from [35.3553 <= battery_capacity_wh < 141.421] to [29.7489 <= battery_capacity_wh < 141.421]
- `rescope` claim_7705fe8e2885: scope changed from [battery_capacity_wh < 32.4037] to [battery_capacity_wh < 36.889]
- `rescope` claim_485c1742ff03: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 36.889]
- `rescope` claim_94081de0302b: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 28.4605]
- `rescope` claim_268a956f0584: scope changed from [29.7489 <= battery_capacity_wh < 141.421] to [29.7489 <= battery_capacity_wh < 167.929]
- `rescope` claim_268a956f0584: scope changed from [29.7489 <= battery_capacity_wh < 167.929] to [27.2489 <= battery_capacity_wh < 167.929]
- `specialize` claim_fd251d9e42c1: reversed from claim_fc6ed5afacdb: battery_capacity_wh >= 282.843
- `support` claim_fd251d9e42c1: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_fd251d9e42c1: scope changed from [battery_capacity_wh >= 282.843] to [battery_capacity_wh >= 336.452]
- `rescope` claim_268a956f0584: scope changed from [27.2489 <= battery_capacity_wh < 167.929] to [27.2489 <= battery_capacity_wh < 183.303]
- `rescope` claim_fd251d9e42c1: scope changed from [battery_capacity_wh >= 336.452] to [battery_capacity_wh >= 308.363]
- `supersede` claim_f9867c7df577: supported -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_2db24fbc0828: narrowed from claim_f9867c7df577: battery_capacity_wh < 282.843
- `support` claim_2db24fbc0828: hypothesis -> supported: 4 decisive test(s) in its region
- `rescope` claim_2db24fbc0828: scope changed from [battery_capacity_wh < 282.843] to [battery_capacity_wh < 336.452]
- `specialize` claim_5d8fbb454498: reversed from claim_ee1d538aed53: 70.7107 <= battery_capacity_wh < 141.421
- `support` claim_5d8fbb454498: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_5d8fbb454498: scope changed from [70.7107 <= battery_capacity_wh < 141.421] to [59.4559 <= battery_capacity_wh < 141.421]
- `rescope` claim_5d8fbb454498: scope changed from [59.4559 <= battery_capacity_wh < 141.421] to [59.4559 <= battery_capacity_wh < 167.929]
- `supersede` claim_ee1d538aed53: refuted -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_846616fc9fa0: narrowed from claim_ee1d538aed53: battery_capacity_wh >= 237.908
- `contest` claim_846616fc9fa0: hypothesis -> contested: the 2 test(s) in its region disagree and could not be separated
- `rescope` claim_2db24fbc0828: scope changed from [battery_capacity_wh < 336.452] to [battery_capacity_wh < 308.363]
- `rescope` claim_5d8fbb454498: scope changed from [59.4559 <= battery_capacity_wh < 167.929] to [59.4559 <= battery_capacity_wh < 183.303]
- `rescope` claim_846616fc9fa0: scope changed from [battery_capacity_wh >= 237.908] to [259.526 <= battery_capacity_wh < 336.452]
- `support` claim_846616fc9fa0: contested -> supported: 1 decisive test(s) in its region
- `rescope` claim_5d8fbb454498: scope changed from [59.4559 <= battery_capacity_wh < 183.303] to [64.8587 <= battery_capacity_wh < 183.303]
- `rescope` claim_846616fc9fa0: scope changed from [259.526 <= battery_capacity_wh < 336.452] to [battery_capacity_wh >= 218.174]
- `contest` claim_846616fc9fa0: supported -> contested: the 3 test(s) in its region disagree and could not be separated
- `rescope` claim_846616fc9fa0: scope changed from [battery_capacity_wh >= 218.174] to [259.526 <= battery_capacity_wh < 366.606]
- `support` claim_846616fc9fa0: contested -> supported: 2 decisive test(s) in its region
- `rescope` claim_485c1742ff03: scope changed from [battery_capacity_wh >= 36.889] to [36.889 <= battery_capacity_wh < 45.8258]
- `specialize` claim_4dd0cf73762c: reversed from claim_9b879caf9c39: battery_capacity_wh >= 59.4559
- `support` claim_4dd0cf73762c: hypothesis -> supported: 4 decisive test(s) in its region
- `rescope` claim_4dd0cf73762c: scope changed from [battery_capacity_wh >= 59.4559] to [battery_capacity_wh >= 54.5436]
- `rescope` claim_33d045066679: scope changed from [battery_capacity_wh < 47.8435] to [battery_capacity_wh < 52.2015]
- `rescope` claim_34e45e3382e0: scope changed from [battery_capacity_wh >= 47.8435] to [battery_capacity_wh >= 52.2015]

## Transfer: interpolation (inside the studied range)

4 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | spacecraft lost | success rate |
|---|---|---|---|
| reference | +0.3050 | 19.5% | 78.1% |
| flat | +0.2589 | 29.7% | 69.5% |
| pooled | +0.5313 | 1.6% | 96.9% |
| conditional | +0.6209 | 1.6% | 97.7% |
| oracle | +0.6070 | 0.0% | 95.3% |

Success: the spacecraft survived and recorded data for at least 20% of the episode (`docs/metrics.md`, 2.3).

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.0896 [+0.0684, +0.1130], p = 0.0002; resampling whole seeds: [+0.0696, +0.1104], p = 0.0002
- conditional minus flat: +0.3620 [+0.2658, +0.4610], p = 0.0002; resampling whole seeds: [+0.2993, +0.4235], p = 0.0002
- conditional minus reference: +0.3159 [+0.2337, +0.4020], p = 0.0002; resampling whole seeds: [+0.2456, +0.3822], p = 0.0002
- pooled minus reference: +0.2264 [+0.1331, +0.3190], p = 0.0002; resampling whole seeds: [+0.1601, +0.2869], p = 0.0002
- flat minus reference: -0.0461 [-0.1219, +0.0290], p = 0.2360; resampling whole seeds: [-0.1150, +0.0269], p = 0.2106
- oracle minus conditional: -0.0139 [-0.0403, +0.0200], p = 0.4091; resampling whole seeds: [-0.0413, +0.0184], p = 0.3873

The first interval treats every (condition, seed) episode pair as independent. The second averages over the conditions first and resamples the 32 seeds, because every condition reuses the same seeds.

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=35 | -0.535 (75%) reference | -0.745 (94%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.388 (6%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.357 (6%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.348 (0%) charge_below=0.6, desat_above=0.6 |
| battery_capacity_wh=70 | +0.424 (3%) reference | +0.260 (25%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.531 (0%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.575 (0%) charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.517 (0%) charge_below=0.25, desat_above=0.3 |
| battery_capacity_wh=140 | +0.584 (0%) reference | +0.704 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.546 (0%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.711 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.718 (0%) charge_below=0.1, desat_above=0.3 |
| battery_capacity_wh=280 | +0.747 (0%) reference | +0.817 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.660 (0%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.842 (0%) charge_below=0.05, charge_margin=0.25, desat_above=0.3 | +0.846 (0%) charge_below=0.05, desat_above=0.3 |

## Transfer: extrapolation (outside the studied range)

2 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | spacecraft lost | success rate |
|---|---|---|---|
| reference | -0.0167 | 48.4% | 51.6% |
| flat | -0.0296 | 50.0% | 50.0% |
| pooled | +0.0308 | 40.6% | 57.8% |
| conditional | +0.3768 | 20.3% | 79.7% |
| oracle | +0.4790 | 9.4% | 82.8% |

Success: the spacecraft survived and recorded data for at least 20% of the episode (`docs/metrics.md`, 2.3).

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.3459 [+0.2242, +0.4728], p = 0.0002; resampling whole seeds: [+0.2355, +0.4590], p = 0.0002
- conditional minus flat: +0.4064 [+0.2625, +0.5557], p = 0.0002; resampling whole seeds: [+0.2952, +0.5139], p = 0.0002
- conditional minus reference: +0.3935 [+0.2505, +0.5385], p = 0.0002; resampling whole seeds: [+0.2811, +0.5006], p = 0.0002
- pooled minus reference: +0.0476 [-0.0436, +0.1585], p = 0.3837; resampling whole seeds: [-0.0420, +0.1475], p = 0.3261
- flat minus reference: -0.0129 [-0.0614, +0.0276], p = 0.6869; resampling whole seeds: [-0.0641, +0.0269], p = 0.6995
- oracle minus conditional: +0.1022 [+0.0189, +0.1964], p = 0.0198; resampling whole seeds: [+0.0223, +0.1920], p = 0.0182

The first interval treats every (condition, seed) episode pair as independent. The second averages over the conditions first and resamples the 32 seeds, because every condition reuses the same seeds.

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=18 | -0.877 (97%) reference | -0.933 (100%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | -0.640 (81%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | -0.123 (41%) charge_below=0.6, charge_margin=0.25 | +0.080 (19%) charge_below=0.8, desat_above=0.6 |
| battery_capacity_wh=600 | +0.843 (0%) reference | +0.874 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.702 (0%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.877 (0%) charge_below=0.1, desat_above=0.3 | +0.878 (0%) charge_below=0.05, desat_above=0.3 |

## Do the recommended settings still work together?

Every family was tested with only its own change. Here the reference policy, each recommended change on its own, and all of them together run on the same held-out seeds.

| conditions | reference | each change alone | all together | together minus reference | finding |
|---|---|---|---|---|---|
| battery_capacity_wh=35 | -0.535 | `charge_below` +0.348; `precharge_below,precharge_window_s` -0.318; `desat_above` -0.393; `charge_margin` -0.358 | +0.357 | +0.892 [+0.677, +1.097] | consistent |
| battery_capacity_wh=70 | +0.424 | `precharge_below,precharge_window_s` +0.493; `desat_above` +0.517; `charge_margin` +0.511 | +0.575 | +0.151 [+0.082, +0.245] | consistent |
| battery_capacity_wh=140 | +0.584 | `charge_below` +0.540; `precharge_below,precharge_window_s` +0.607; `desat_above` +0.636; `charge_margin` +0.598 | +0.711 | +0.126 [+0.080, +0.169] | consistent |
| battery_capacity_wh=280 | +0.747 | `charge_below` +0.847; `desat_above` +0.760; `charge_margin` +0.761 | +0.842 | +0.095 [+0.037, +0.150] | consistent |
| battery_capacity_wh=18 | -0.877 | `charge_margin` -0.869; `charge_below` -0.158 | -0.123 | +0.753 [+0.527, +0.971] | consistent |
| battery_capacity_wh=600 | +0.843 | `charge_below` +0.899; `desat_above` +0.830 | +0.877 | +0.034 [-0.016, +0.089] | unhelpful change |

- battery_capacity_wh=600: on its own, `desat_above` (+0.830 against +0.843) scores below the reference here, so the claim behind it is being applied where it does not hold. All together is -0.022 [-0.048, -0.003] against `charge_below` alone.
