# Charging, desaturation and eclipse strategies across battery sizes (Basilisk / BSK-RL)

71 experiments in 19 rounds, 2304 simulator episodes (budget 4500).

**8 comparisons, 21 claims** (1 refuted, 7 superseded, 13 supported); 30 relations between claims.

## What the graph recommends, by condition

Settings that differ from the reference policy, in every region of conditions the supported claims tell apart. A dot keeps the reference value: either nothing was found to beat it there, or nothing could be established.

| battery_capacity_wh | `charge_below` | `charge_margin` | `desat_above` | `precharge_below` | `precharge_window_s` |
|---|---|---|---|---|---|
| below 28.46 | 0.6 | 0.25 | · | 0.6 | 900 |
| 28.46 to 36.89 | 0.6 | 0.25 | 0.3 | 0.6 | 900 |
| 36.89 to 62.07 | 0.4 | 0.25 | 0.3 | 0.6 | 900 |
| 62.07 to 135.4 | · | 0.25 | 0.3 | 0.6 | 900 |
| 135.4 to 175.5 | 0.1 | 0.25 | 0.3 | 0.6 | 900 |
| 175.5 to 218.2 | 0.1 | 0.25 | 0.3 | · | · |
| 218.2 to 308.4 | 0.05 | 0.25 | 0.3 | · | · |
| 308.4 and above | 0.05 | · | 0.3 | · | · |

## Claims by comparison

### A lower charge threshold collects more data.

Proposed by: seed (hand-written). Compares `charge_below` = 0.1 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | +0.005 | [-0.012, +0.016] | 16 | 16 / 16 |
| battery_capacity_wh=32.4 | no meaningful benefit | -0.004 | [-0.032, +0.014] | 16 | 15 / 15 |
| battery_capacity_wh=42 | baseline better | -0.511 | [-0.872, -0.201] | 16 | 15 / 9 |
| battery_capacity_wh=50 | baseline better | -0.909 | [-1.168, -0.600] | 16 | 15 / 3 |
| battery_capacity_wh=70.7 | baseline better | -1.049 | [-1.152, -0.849] | 16 | 15 / 0 |
| battery_capacity_wh=100 | baseline better | -0.492 | [-0.808, -0.171] | 16 | 8 / 0 |
| battery_capacity_wh=119 | baseline better | -0.181 | [-0.348, -0.037] | 48 | 11 / 0 |
| battery_capacity_wh=154 | intervention better | +0.104 | [+0.083, +0.119] | 16 | 0 / 0 |
| battery_capacity_wh=200 | intervention better | +0.106 | [+0.076, +0.131] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.129 | [+0.058, +0.204] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh >= 135.374, use `charge_below` = 0.1 instead of 0.25.
- **supported** (reversed): where 36.889 <= battery_capacity_wh < 135.374, use `charge_below` = 0.25 instead of 0.1.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 36.889.

Explanations (judged separately from the outcome):

- *less time is spent in charge mode* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 4211.25 with the intervention vs 6015 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=154: supports. `time_charge_s`: 5373.75 with the intervention vs 7095 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400: supports. `time_charge_s`: 1530 with the intervention vs 3690 without, over 16 of 16 seed pairs

### Topping up the battery before each eclipse improves the score.

Proposed by: seed (hand-written). Compares `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.177 | [+0.001, +0.481] | 16 | 14 / 16 |
| battery_capacity_wh=50 | intervention better | +0.108 | [+0.024, +0.299] | 16 | 2 / 3 |
| battery_capacity_wh=70.7 | intervention better | +0.045 | [+0.017, +0.072] | 16 | 0 / 0 |
| battery_capacity_wh=100 | intervention better | +0.034 | [+0.008, +0.059] | 16 | 0 / 0 |
| battery_capacity_wh=119 | intervention better | +0.045 | [+0.020, +0.070] | 16 | 0 / 0 |
| battery_capacity_wh=154 | intervention better | +0.044 | [+0.017, +0.072] | 16 | 0 / 0 |
| battery_capacity_wh=200 | unresolved (inconclusive at the maximum number of seeds) | +0.011 | [-0.007, +0.028] | 48 | 0 / 0 |
| battery_capacity_wh=238 | no meaningful benefit | +0.001 | [-0.018, +0.019] | 48 | 0 / 0 |
| battery_capacity_wh=283 | no meaningful benefit | -0.011 | [-0.030, +0.009] | 48 | 0 / 0 |
| battery_capacity_wh=400 | no meaningful benefit | -0.009 | [-0.035, +0.018] | 32 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 175.499, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh >= 218.174.
- Not established either way, so nothing is recommended, where: 175.499 <= battery_capacity_wh < 218.174.

Explanations (judged separately from the outcome):

- *the battery does not get as low* — **supported**
  - mediator test at battery_capacity_wh=25: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=70.7: supports. `min_battery`: 0.14924 with the intervention vs 0.11427 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=119: supports. `min_battery`: 0.21237 with the intervention vs 0.19645 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=154: supports. `min_battery`: 0.23386 with the intervention vs 0.22069 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: supports. `min_battery`: 0.10005 with the intervention vs 0.06708 without, over 13 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `min_battery`: 0.19203 with the intervention vs 0.17199 without, over 16 of 16 seed pairs
- *it prevents battery depletion* — **refuted**
  - mediator test at battery_capacity_wh=25: inconclusive. `failure:battery`: 0.875 with the intervention vs 1 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=70.7: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=119: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=154: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: inconclusive. `failure:battery`: 0.125 with the intervention vs 0.1875 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs

### Unloading the reaction wheels early improves the score.

Proposed by: seed (hand-written). Compares `desat_above` = 0.3 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | -0.001 | [-0.011, +0.009] | 16 | 16 / 16 |
| battery_capacity_wh=32.4 | intervention better | +0.170 | [+0.020, +0.365] | 32 | 26 / 30 |
| battery_capacity_wh=42 | intervention better | +0.568 | [+0.239, +0.901] | 16 | 2 / 9 |
| battery_capacity_wh=50 | intervention better | +0.208 | [+0.019, +0.489] | 16 | 1 / 3 |
| battery_capacity_wh=70.7 | intervention better | +0.076 | [+0.039, +0.116] | 16 | 0 / 0 |
| battery_capacity_wh=100 | intervention better | +0.074 | [+0.037, +0.114] | 16 | 0 / 0 |
| battery_capacity_wh=200 | intervention better | +0.060 | [+0.027, +0.101] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.049 | [+0.011, +0.094] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh >= 28.4605, use `desat_above` = 0.3 instead of 0.6.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 28.4605.

Explanations (judged separately from the outcome):

- *it prevents the wheels from reaching their speed limit* — **refuted**
  - mediator test at battery_capacity_wh=200: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=70.7: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=32.4: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=400: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
- *slower wheels draw less power, so less time is spent charging* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 4935 with the intervention vs 6015 without, over 16 of 16 seed pairs
  - moderator test at battery_capacity_wh=200: inconclusive. effect by `max_wheel_speed_rpm`: 1500 -> +0.031, 3000 -> +0.016, 6000 -> +0.070
  - mediator test at battery_capacity_wh=70.7: supports. `time_charge_s`: 7740 with the intervention vs 9007.5 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42: supports. `time_charge_s`: 7928.57 with the intervention vs 8511.43 without, over 7 of 16 seed pairs
  - mediator test at battery_capacity_wh=32.4: inconclusive. `time_charge_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=400: supports. `time_charge_s`: 2895 with the intervention vs 3690 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `time_charge_s`: 7068.75 with the intervention vs 8295 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: supports. `time_charge_s`: 7864.62 with the intervention vs 8833.85 without, over 13 of 16 seed pairs

### Charging in longer blocks improves the score.

Proposed by: seed (hand-written). Compares `charge_margin` = 0.25 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.045 | [+0.002, +0.158] | 32 | 31 / 32 |
| battery_capacity_wh=50 | intervention better | +0.179 | [+0.053, +0.330] | 48 | 10 / 15 |
| battery_capacity_wh=100 | intervention better | +0.057 | [+0.012, +0.107] | 16 | 0 / 0 |
| battery_capacity_wh=200 | intervention better | +0.049 | [+0.009, +0.094] | 32 | 0 / 0 |
| battery_capacity_wh=283 | intervention better | +0.034 | [+0.004, +0.068] | 32 | 0 / 0 |
| battery_capacity_wh=336 | unresolved (inconclusive at the maximum number of seeds) | +0.010 | [-0.015, +0.035] | 48 | 0 / 0 |
| battery_capacity_wh=400 | unresolved (inconclusive at the maximum number of seeds) | +0.007 | [-0.021, +0.034] | 48 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 308.363, use `charge_margin` = 0.25 instead of 0.
- Not established either way, so nothing is recommended, where: battery_capacity_wh >= 308.363.

Explanations (judged separately from the outcome):

- *fewer mode switches waste less scan time on slewing and settling* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `wasted_scan_s`: 528.656 with the intervention vs 810.781 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=25: inconclusive. `wasted_scan_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=50: supports. `wasted_scan_s`: 388.875 with the intervention vs 836.406 without, over 32 of 48 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `wasted_scan_s`: 485.188 with the intervention vs 818.312 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=283: supports. `wasted_scan_s`: 533.812 with the intervention vs 764.781 without, over 32 of 32 seed pairs

### Going further in the direction that helped keeps helping: charge_below=0.05 beats charge_below=0.1.

Proposed by: program. Compares `charge_below` = 0.05 instead of 0.1.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | -0.012 | [-0.042, +0.005] | 16 | 16 / 16 |
| battery_capacity_wh=50 | no meaningful benefit | -0.022 | [-0.057, +0.004] | 16 | 15 / 15 |
| battery_capacity_wh=70.7 | no meaningful benefit | -0.016 | [-0.052, +0.014] | 16 | 15 / 15 |
| battery_capacity_wh=91.7 | baseline better | -0.297 | [-0.593, -0.068] | 16 | 15 / 11 |
| battery_capacity_wh=100 | baseline better | -0.510 | [-0.841, -0.217] | 16 | 15 / 8 |
| battery_capacity_wh=119 | baseline better | -0.808 | [-1.056, -0.518] | 16 | 15 / 3 |
| battery_capacity_wh=200 | baseline better | -0.302 | [-0.577, -0.042] | 16 | 5 / 0 |
| battery_capacity_wh=238 | intervention better | +0.036 | [+0.019, +0.053] | 16 | 0 / 0 |
| battery_capacity_wh=283 | intervention better | +0.028 | [+0.012, +0.046] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.031 | [+0.007, +0.058] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (reversed): where 80.5183 <= battery_capacity_wh < 218.174, use `charge_below` = 0.1 instead of 0.05.
- **supported** (narrowed): where battery_capacity_wh >= 218.174, use `charge_below` = 0.05 instead of 0.1.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 80.5183.

### Neither tested setting is acceptable here; a setting further out does better: charge_below=0.4 beats charge_below=0.25.

Proposed by: program. Compares `charge_below` = 0.4 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.408 | [+0.104, +0.740] | 16 | 11 / 16 |
| battery_capacity_wh=42 | intervention better | +0.633 | [+0.280, +0.951] | 16 | 0 / 9 |
| battery_capacity_wh=50 | intervention better | +0.196 | [+0.031, +0.401] | 32 | 0 / 6 |
| battery_capacity_wh=54.5 | intervention better | +0.161 | [+0.028, +0.312] | 48 | 0 / 8 |
| battery_capacity_wh=70.7 | baseline better | -0.031 | [-0.053, -0.014] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.053 | [-0.071, -0.034] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.116 | [-0.144, -0.084] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.150 | [-0.218, -0.082] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 62.0737, use `charge_below` = 0.4 instead of 0.25.
- **supported** (reversed): where battery_capacity_wh >= 62.0737, use `charge_below` = 0.25 instead of 0.4.

### Going further in the direction that helped keeps helping: charge_below=0.6 beats charge_below=0.4.

Proposed by: program. Compares `charge_below` = 0.6 instead of 0.4.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.683 | [+0.306, +1.017] | 16 | 2 / 11 |
| battery_capacity_wh=32.4 | intervention better | +0.196 | [+0.029, +0.389] | 32 | 1 / 7 |
| battery_capacity_wh=42 | baseline better | -0.034 | [-0.048, -0.021] | 16 | 0 / 0 |
| battery_capacity_wh=50 | baseline better | -0.026 | [-0.037, -0.014] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.043 | [-0.057, -0.029] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.063 | [-0.084, -0.042] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.131 | [-0.163, -0.096] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.201 | [-0.259, -0.136] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 36.889, use `charge_below` = 0.6 instead of 0.4.
- **supported** (reversed): where battery_capacity_wh >= 36.889, use `charge_below` = 0.4 instead of 0.6.

### Going further in the direction that helped keeps helping: charge_below=0.8 beats charge_below=0.6.

Proposed by: program. Compares `charge_below` = 0.8 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | unresolved (inconclusive at the maximum number of seeds) | +0.077 | [-0.014, +0.198] | 48 | 5 / 9 |
| battery_capacity_wh=32.4 | baseline better | -0.027 | [-0.049, -0.007] | 16 | 0 / 0 |
| battery_capacity_wh=42 | no meaningful benefit | -0.013 | [-0.031, +0.005] | 16 | 0 / 0 |
| battery_capacity_wh=50 | baseline better | -0.025 | [-0.038, -0.013] | 16 | 0 / 0 |
| battery_capacity_wh=54.5 | baseline better | -0.029 | [-0.042, -0.015] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.048 | [-0.068, -0.028] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.056 | [-0.071, -0.042] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.094 | [-0.131, -0.059] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.194 | [-0.263, -0.128] | 16 | 0 / 0 |

**Original claim: refuted.** Did not hold anywhere it was tested.

- **supported** (reversed): where battery_capacity_wh >= 45.8258, use `charge_below` = 0.6 instead of 0.8.
- **supported** (reversed): where 28.4605 <= battery_capacity_wh < 36.889, use `charge_below` = 0.6 instead of 0.8.
- No meaningful benefit, so nothing is recommended, where: 36.889 <= battery_capacity_wh < 45.8258.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 28.4605.

## Revision history

- `propose` claim_ac01cd9f0014: proposed
- `propose` claim_0472c686b940: proposed
- `propose` claim_bbca943a2c7a: proposed
- `propose` claim_689262d8ad8d: proposed
- `support` claim_ac01cd9f0014: hypothesis -> supported: 1 decisive test(s), all in favour
- `support` claim_bbca943a2c7a: hypothesis -> supported: 1 decisive test(s), all in favour
- `support` claim_689262d8ad8d: hypothesis -> supported: 1 decisive test(s), all in favour
- `propose` claim_792285901eda: keep-going rule, from claim_ac01cd9f0014, along the charge_below ladder
- `refute` claim_792285901eda: hypothesis -> refuted: 1 decisive test(s), none in favour
- `specialize` claim_bddee8424b24: reversed from claim_792285901eda: all tested conditions
- `support` claim_bddee8424b24: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_ac01cd9f0014: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_212859f64bba: narrowed from claim_ac01cd9f0014: battery_capacity_wh >= 70.7107
- `support` claim_212859f64bba: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_0472c686b940: hypothesis -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_a6e40c8a9b9c: narrowed from claim_0472c686b940: battery_capacity_wh < 70.7107
- `support` claim_a6e40c8a9b9c: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_084b0a99bb89: nothing-works-here rule, from claim_ac01cd9f0014, along the charge_below ladder
- `support` claim_084b0a99bb89: hypothesis -> supported: 1 decisive test(s), all in favour
- `specialize` claim_aef649652f79: reversed from claim_ac01cd9f0014: 42.0416 <= battery_capacity_wh < 118.912
- `support` claim_aef649652f79: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_212859f64bba: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 118.912]
- `rescope` claim_a6e40c8a9b9c: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 118.912]
- `supersede` claim_bbca943a2c7a: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_4f8fd440a2fd: narrowed from claim_bbca943a2c7a: battery_capacity_wh >= 70.7107
- `support` claim_4f8fd440a2fd: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_077663adb44e: keep-going rule, from claim_084b0a99bb89, along the charge_below ladder
- `support` claim_077663adb44e: hypothesis -> supported: 1 decisive test(s), all in favour
- `rescope` claim_4f8fd440a2fd: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_aef649652f79: scope changed from [42.0416 <= battery_capacity_wh < 118.912] to [42.0416 <= battery_capacity_wh < 154.272]
- `rescope` claim_212859f64bba: scope changed from [battery_capacity_wh >= 118.912] to [battery_capacity_wh >= 154.272]
- `rescope` claim_a6e40c8a9b9c: scope changed from [battery_capacity_wh < 118.912] to [battery_capacity_wh < 154.272]
- `propose` claim_d211de4a8c71: keep-going rule, from claim_077663adb44e, along the charge_below ladder
- `rescope` claim_aef649652f79: scope changed from [42.0416 <= battery_capacity_wh < 154.272] to [32.4037 <= battery_capacity_wh < 154.272]
- `rescope` claim_4f8fd440a2fd: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `rescope` claim_aef649652f79: scope changed from [32.4037 <= battery_capacity_wh < 154.272] to [32.4037 <= battery_capacity_wh < 135.374]
- `rescope` claim_212859f64bba: scope changed from [battery_capacity_wh >= 154.272] to [battery_capacity_wh >= 135.374]
- `rescope` claim_a6e40c8a9b9c: scope changed from [battery_capacity_wh < 154.272] to [battery_capacity_wh < 175.499]
- `rescope` claim_aef649652f79: scope changed from [32.4037 <= battery_capacity_wh < 135.374] to [36.889 <= battery_capacity_wh < 135.374]
- `rescope` claim_4f8fd440a2fd: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 28.4605]
- `rescope` claim_bddee8424b24: scope changed from [all tested conditions] to [battery_capacity_wh >= 70.7107]
- `supersede` claim_084b0a99bb89: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_788161104928: narrowed from claim_084b0a99bb89: battery_capacity_wh < 70.7107
- `support` claim_788161104928: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_7bb3d4ce023d: reversed from claim_084b0a99bb89: battery_capacity_wh >= 70.7107
- `support` claim_7bb3d4ce023d: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_077663adb44e: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_cfbc20ec609c: narrowed from claim_077663adb44e: battery_capacity_wh < 70.7107
- `support` claim_cfbc20ec609c: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_90acf40e1557: reversed from claim_077663adb44e: battery_capacity_wh >= 70.7107
- `support` claim_90acf40e1557: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_bddee8424b24: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 118.912]
- `rescope` claim_788161104928: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_7bb3d4ce023d: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_cfbc20ec609c: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_90acf40e1557: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `refute` claim_d211de4a8c71: hypothesis -> refuted: 1 decisive test(s), none in favour
- `specialize` claim_f0074b66069c: reversed from claim_d211de4a8c71: battery_capacity_wh >= 70.7107
- `support` claim_f0074b66069c: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_f0074b66069c: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_bddee8424b24: scope changed from [battery_capacity_wh >= 118.912] to [battery_capacity_wh >= 91.724]
- `rescope` claim_788161104928: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 54.4922]
- `rescope` claim_7bb3d4ce023d: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 54.4922]
- `rescope` claim_cfbc20ec609c: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 32.4037]
- `rescope` claim_90acf40e1557: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `rescope` claim_f0074b66069c: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 54.4922]
- `rescope` claim_788161104928: scope changed from [battery_capacity_wh < 54.4922] to [battery_capacity_wh < 62.0737]
- `rescope` claim_7bb3d4ce023d: scope changed from [battery_capacity_wh >= 54.4922] to [battery_capacity_wh >= 62.0737]
- `rescope` claim_bddee8424b24: scope changed from [battery_capacity_wh >= 91.724] to [battery_capacity_wh >= 80.5183]
- `rescope` claim_cfbc20ec609c: scope changed from [battery_capacity_wh < 32.4037] to [battery_capacity_wh < 36.889]
- `rescope` claim_90acf40e1557: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 36.889]
- `rescope` claim_f0074b66069c: scope changed from [battery_capacity_wh >= 54.4922] to [battery_capacity_wh >= 47.8435]
- `specialize` claim_ef5eb636e74d: reversed from claim_d211de4a8c71: 28.4605 <= battery_capacity_wh < 36.889
- `support` claim_ef5eb636e74d: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_689262d8ad8d: supported -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_cc800ceba566: narrowed from claim_689262d8ad8d: battery_capacity_wh < 282.843
- `support` claim_cc800ceba566: hypothesis -> supported: 4 decisive test(s) in its region
- `supersede` claim_792285901eda: refuted -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `rescope` claim_bddee8424b24: scope changed from [battery_capacity_wh >= 80.5183] to [80.5183 <= battery_capacity_wh < 282.843]
- `specialize` claim_23c1ebf92061: narrowed from claim_792285901eda: battery_capacity_wh >= 282.843
- `support` claim_23c1ebf92061: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_cc800ceba566: scope changed from [battery_capacity_wh < 282.843] to [battery_capacity_wh < 336.452]
- `rescope` claim_bddee8424b24: scope changed from [80.5183 <= battery_capacity_wh < 282.843] to [80.5183 <= battery_capacity_wh < 237.908]
- `rescope` claim_23c1ebf92061: scope changed from [battery_capacity_wh >= 282.843] to [battery_capacity_wh >= 237.908]
- `rescope` claim_bddee8424b24: scope changed from [80.5183 <= battery_capacity_wh < 237.908] to [80.5183 <= battery_capacity_wh < 218.174]
- `rescope` claim_23c1ebf92061: scope changed from [battery_capacity_wh >= 237.908] to [battery_capacity_wh >= 218.174]
- `rescope` claim_cc800ceba566: scope changed from [battery_capacity_wh < 336.452] to [battery_capacity_wh < 308.363]
- `rescope` claim_f0074b66069c: scope changed from [battery_capacity_wh >= 47.8435] to [battery_capacity_wh >= 45.8258]

## Transfer: interpolation (inside the studied range)

4 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | spacecraft lost | success rate |
|---|---|---|---|
| reference | +0.3050 | 19.5% | 78.1% |
| flat | +0.2589 | 29.7% | 69.5% |
| pooled | +0.4426 | 1.6% | 93.0% |
| conditional | +0.6209 | 1.6% | 97.7% |
| oracle | +0.6070 | 0.0% | 95.3% |

Success: the spacecraft survived and recorded data for at least 20% of the episode (`docs/metrics.md`, 2.3).

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.1784 [+0.1488, +0.2104], p = 0.0002; resampling whole seeds: [+0.1527, +0.2017], p = 0.0002
- conditional minus flat: +0.3620 [+0.2658, +0.4610], p = 0.0002; resampling whole seeds: [+0.2993, +0.4235], p = 0.0002
- conditional minus reference: +0.3159 [+0.2337, +0.4020], p = 0.0002; resampling whole seeds: [+0.2456, +0.3822], p = 0.0002
- pooled minus reference: +0.1376 [+0.0400, +0.2350], p = 0.0050; resampling whole seeds: [+0.0714, +0.2010], p = 0.0010
- flat minus reference: -0.0461 [-0.1219, +0.0290], p = 0.2360; resampling whole seeds: [-0.1150, +0.0269], p = 0.2106
- oracle minus conditional: -0.0139 [-0.0403, +0.0200], p = 0.4091; resampling whole seeds: [-0.0413, +0.0184], p = 0.3873

The first interval treats every (condition, seed) episode pair as independent. The second averages over the conditions first and resamples the 32 seeds, because every condition reuses the same seeds.

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=35 | -0.535 (75%) reference | -0.745 (94%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.357 (6%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.357 (6%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.348 (0%) charge_below=0.6, desat_above=0.6 |
| battery_capacity_wh=70 | +0.424 (3%) reference | +0.260 (25%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.460 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.575 (0%) charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.517 (0%) charge_below=0.25, desat_above=0.3 |
| battery_capacity_wh=140 | +0.584 (0%) reference | +0.704 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.465 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.711 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.718 (0%) charge_below=0.1, desat_above=0.3 |
| battery_capacity_wh=280 | +0.747 (0%) reference | +0.817 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.489 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.842 (0%) charge_below=0.05, charge_margin=0.25, desat_above=0.3 | +0.846 (0%) charge_below=0.05, desat_above=0.3 |

## Transfer: extrapolation (outside the studied range)

2 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | spacecraft lost | success rate |
|---|---|---|---|
| reference | -0.0167 | 48.4% | 51.6% |
| flat | -0.0296 | 50.0% | 50.0% |
| pooled | +0.2168 | 17.2% | 65.6% |
| conditional | +0.3772 | 20.3% | 79.7% |
| oracle | +0.4790 | 9.4% | 82.8% |

Success: the spacecraft survived and recorded data for at least 20% of the episode (`docs/metrics.md`, 2.3).

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.1603 [+0.0174, +0.2984], p = 0.0272; resampling whole seeds: [+0.0193, +0.2997], p = 0.0318
- conditional minus flat: +0.4068 [+0.2631, +0.5561], p = 0.0002; resampling whole seeds: [+0.2958, +0.5140], p = 0.0002
- conditional minus reference: +0.3939 [+0.2508, +0.5397], p = 0.0002; resampling whole seeds: [+0.2817, +0.5009], p = 0.0002
- pooled minus reference: +0.2336 [+0.0523, +0.4253], p = 0.0168; resampling whole seeds: [+0.0892, +0.3713], p = 0.0038
- flat minus reference: -0.0129 [-0.0614, +0.0276], p = 0.6869; resampling whole seeds: [-0.0641, +0.0269], p = 0.6995
- oracle minus conditional: +0.1018 [+0.0186, +0.1956], p = 0.0202; resampling whole seeds: [+0.0218, +0.1916], p = 0.0184

The first interval treats every (condition, seed) episode pair as independent. The second averages over the conditions first and resamples the 32 seeds, because every condition reuses the same seeds.

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=18 | -0.877 (97%) reference | -0.933 (100%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | -0.065 (34%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | -0.123 (41%) charge_below=0.6, charge_margin=0.25, precharge_below=0.6, precharge_window_s=900 | +0.080 (19%) charge_below=0.8, desat_above=0.6 |
| battery_capacity_wh=600 | +0.843 (0%) reference | +0.874 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3 | +0.499 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.878 (0%) charge_below=0.05, desat_above=0.3 | +0.878 (0%) charge_below=0.05, desat_above=0.3 |

## Do the recommended settings still work together?

Every family was tested with only its own change. Here the reference policy, each recommended change on its own, and all of them together run on the same held-out seeds.

| conditions | reference | each change alone | all together | together minus reference | finding |
|---|---|---|---|---|---|
| battery_capacity_wh=35 | -0.535 | `precharge_below,precharge_window_s` -0.318; `desat_above` -0.393; `charge_margin` -0.358; `charge_below` +0.348 | +0.357 | +0.892 [+0.677, +1.097] | consistent |
| battery_capacity_wh=70 | +0.424 | `precharge_below,precharge_window_s` +0.493; `desat_above` +0.517; `charge_margin` +0.511 | +0.575 | +0.151 [+0.082, +0.245] | consistent |
| battery_capacity_wh=140 | +0.584 | `charge_below` +0.540; `precharge_below,precharge_window_s` +0.607; `desat_above` +0.636; `charge_margin` +0.598 | +0.711 | +0.126 [+0.080, +0.169] | consistent |
| battery_capacity_wh=280 | +0.747 | `charge_below` +0.847; `desat_above` +0.760; `charge_margin` +0.761 | +0.842 | +0.095 [+0.037, +0.150] | consistent |
| battery_capacity_wh=18 | -0.877 | `precharge_below,precharge_window_s` -0.881; `charge_margin` -0.869; `charge_below` -0.158 | -0.123 | +0.753 [+0.527, +0.971] | consistent |
| battery_capacity_wh=600 | +0.843 | `charge_below` +0.903; `desat_above` +0.830 | +0.878 | +0.034 [-0.016, +0.091] | unhelpful change |

- battery_capacity_wh=600: on its own, `desat_above` (+0.830 against +0.843) scores below the reference here, so the claim behind it is being applied where it does not hold. All together is -0.025 [-0.050, -0.007] against `charge_below` alone.
