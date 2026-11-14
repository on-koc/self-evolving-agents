# Battery study with a passive design: fixed nine-point grid, no boundary probes (Basilisk / BSK-RL)

73 experiments in 20 rounds, 2224 simulator episodes (budget 7200).

**8 comparisons, 23 claims** (1 contested, 2 refuted, 1 retired, 6 superseded, 13 supported); 34 relations between claims.

## What the graph recommends, by condition

Settings that differ from the reference policy, in every region of conditions the supported claims tell apart. A dot keeps the reference value: either nothing was found to beat it there, or nothing could be established.

| battery_capacity_wh | `charge_below` | `charge_margin` | `desat_above` | `precharge_below` | `precharge_window_s` |
|---|---|---|---|---|---|
| below 29.75 | 0.6 | 0.25 | · | 0.6 | 900 |
| 29.75 to 42.07 | 0.4 | 0.25 | 0.3 | 0.6 | 900 |
| 42.07 to 59.46 | 0.4 | · | 0.3 | · | · |
| 59.46 to 167.9 | · | 0.25 | 0.3 | · | · |
| 167.9 and above | 0.1 | · | 0.3 | · | · |

## Claims by comparison

### A lower charge threshold collects more data.

Proposed by: seed (hand-written). Compares `charge_below` = 0.1 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | +0.003 | [-0.022, +0.017] | 16 | 16 / 16 |
| battery_capacity_wh=35.4 | baseline better | -0.325 | [-0.663, -0.063] | 16 | 16 / 12 |
| battery_capacity_wh=50 | baseline better | -1.010 | [-1.215, -0.745] | 16 | 16 / 3 |
| battery_capacity_wh=70.7 | baseline better | -1.130 | [-1.182, -1.075] | 16 | 16 / 0 |
| battery_capacity_wh=100 | baseline better | -0.344 | [-0.648, -0.059] | 16 | 6 / 0 |
| battery_capacity_wh=141 | unresolved (inconclusive at the maximum number of seeds) | -0.066 | [-0.193, +0.045] | 48 | 7 / 0 |
| battery_capacity_wh=200 | intervention better | +0.092 | [+0.062, +0.120] | 16 | 0 / 0 |
| battery_capacity_wh=283 | intervention better | +0.070 | [+0.024, +0.121] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.055 | [+0.009, +0.113] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh >= 167.929, use `charge_below` = 0.1 instead of 0.25.
- **supported** (reversed): where 29.7489 <= battery_capacity_wh < 118.743, use `charge_below` = 0.25 instead of 0.1.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 29.7489.
- Not established either way, so nothing is recommended, where: 118.743 <= battery_capacity_wh < 167.929.

Explanations (judged separately from the outcome):

- *less time is spent in charge mode* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 2636.25 with the intervention vs 4125 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400: supports. `time_charge_s`: 1267.5 with the intervention vs 2141.25 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=283: supports. `time_charge_s`: 1755 with the intervention vs 2857.5 without, over 16 of 16 seed pairs

### Topping up the battery before each eclipse improves the score.

Proposed by: seed (hand-written). Compares `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.129 | [+0.002, +0.306] | 32 | 28 / 31 |
| battery_capacity_wh=35.4 | intervention better | +0.291 | [+0.029, +0.625] | 16 | 9 / 12 |
| battery_capacity_wh=50 | unresolved (inconclusive at the maximum number of seeds) | +0.072 | [-0.068, +0.215] | 48 | 12 / 14 |
| battery_capacity_wh=70.7 | intervention better | +0.039 | [+0.010, +0.068] | 16 | 0 / 0 |
| battery_capacity_wh=100 | intervention better | +0.034 | [+0.006, +0.061] | 16 | 0 / 0 |
| battery_capacity_wh=141 | unresolved (inconclusive at the maximum number of seeds) | +0.017 | [-0.000, +0.035] | 48 | 0 / 0 |
| battery_capacity_wh=200 | no meaningful benefit | -0.003 | [-0.023, +0.017] | 48 | 0 / 0 |
| battery_capacity_wh=283 | baseline better | -0.045 | [-0.105, -0.000] | 16 | 0 / 0 |
| battery_capacity_wh=400 | no meaningful benefit | -0.039 | [-0.088, +0.001] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 42.0714, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- **retired** (narrowed): where battery_capacity_wh >= 237.908, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- **contested** (narrowed): where 42.0714 <= battery_capacity_wh < 118.743, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- **supported** (reversed): where 237.908 <= battery_capacity_wh < 336.452, use `precharge_below` = 0 instead of 0.6, `precharge_window_s` = 0 instead of 900.
- No meaningful benefit, so nothing is recommended, where: 167.929 <= battery_capacity_wh < 237.908; battery_capacity_wh >= 336.452.
- Not established either way, so nothing is recommended, where: 118.743 <= battery_capacity_wh < 167.929.

Explanations (judged separately from the outcome):

- *the battery does not get as low* — **supported**
  - mediator test at battery_capacity_wh=25: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=70.7: supports. `min_battery`: 0.14246 with the intervention vs 0.09956 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=35.4: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=100: supports. `min_battery`: 0.18141 with the intervention vs 0.1485 without, over 16 of 16 seed pairs
- *it prevents battery depletion* — **refuted**
  - mediator test at battery_capacity_wh=25: inconclusive. `failure:battery`: 0.875 with the intervention vs 0.96875 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=70.7: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=35.4: inconclusive. `failure:battery`: 0.5625 with the intervention vs 0.75 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs

### Unloading the reaction wheels early improves the score.

Proposed by: seed (hand-written). Compares `desat_above` = 0.3 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | unresolved (inconclusive at the maximum number of seeds) | +0.040 | [-0.022, +0.145] | 48 | 44 / 46 |
| battery_capacity_wh=35.4 | intervention better | +0.339 | [+0.091, +0.598] | 32 | 17 / 25 |
| battery_capacity_wh=50 | intervention better | +0.254 | [+0.037, +0.541] | 16 | 0 / 3 |
| battery_capacity_wh=70.7 | intervention better | +0.057 | [+0.017, +0.099] | 16 | 0 / 0 |
| battery_capacity_wh=100 | intervention better | +0.056 | [+0.020, +0.093] | 16 | 0 / 0 |
| battery_capacity_wh=141 | intervention better | +0.047 | [+0.020, +0.076] | 16 | 0 / 0 |
| battery_capacity_wh=200 | intervention better | +0.048 | [+0.022, +0.080] | 16 | 0 / 0 |
| battery_capacity_wh=283 | intervention better | +0.025 | [+0.002, +0.053] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.026 | [+0.005, +0.049] | 48 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh >= 29.7489, use `desat_above` = 0.3 instead of 0.6.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 29.7489.

Explanations (judged separately from the outcome):

- *it prevents the wheels from reaching their speed limit* — **refuted**
  - mediator test at battery_capacity_wh=200: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=70.7: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=141: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=35.4: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=283: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
- *slower wheels draw less power, so less time is spent charging* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 3318.75 with the intervention vs 4125 without, over 16 of 16 seed pairs
  - moderator test at battery_capacity_wh=200: supports. effect by `max_wheel_speed_rpm`: 1500 -> -0.070, 3000 -> +0.006, 6000 -> +0.041
  - mediator test at battery_capacity_wh=70.7: supports. `time_charge_s`: 7080 with the intervention vs 8058.75 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400: supports. `time_charge_s`: 1981.25 with the intervention vs 2523.75 without, over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=141: supports. `time_charge_s`: 4920 with the intervention vs 5797.5 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=35.4: inconclusive. `time_charge_s`: 7700 with the intervention vs 8590 without, over 6 of 32 seed pairs
  - mediator test at battery_capacity_wh=283: supports. `time_charge_s`: 2385 with the intervention vs 2857.5 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: supports. `time_charge_s`: 7818.46 with the intervention vs 8649.23 without, over 13 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `time_charge_s`: 6228.75 with the intervention vs 7188.75 without, over 16 of 16 seed pairs

### Charging in longer blocks improves the score.

Proposed by: seed (hand-written). Compares `charge_margin` = 0.25 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.024 | [+0.001, +0.075] | 16 | 16 / 16 |
| battery_capacity_wh=35.4 | intervention better | +0.233 | [+0.020, +0.472] | 32 | 20 / 25 |
| battery_capacity_wh=50 | unresolved (inconclusive at the maximum number of seeds) | +0.095 | [-0.022, +0.223] | 48 | 13 / 14 |
| battery_capacity_wh=70.7 | intervention better | +0.059 | [+0.012, +0.110] | 16 | 0 / 0 |
| battery_capacity_wh=100 | intervention better | +0.048 | [+0.003, +0.104] | 16 | 0 / 0 |
| battery_capacity_wh=141 | intervention better | +0.039 | [+0.001, +0.075] | 48 | 0 / 0 |
| battery_capacity_wh=200 | unresolved (inconclusive at the maximum number of seeds) | +0.028 | [-0.011, +0.062] | 48 | 0 / 0 |
| battery_capacity_wh=283 | unresolved (inconclusive at the maximum number of seeds) | -0.001 | [-0.040, +0.032] | 48 | 0 / 0 |
| battery_capacity_wh=400 | unresolved (inconclusive at the maximum number of seeds) | -0.001 | [-0.039, +0.031] | 48 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 42.0714, use `charge_margin` = 0.25 instead of 0.
- **supported** (narrowed): where 59.4559 <= battery_capacity_wh < 167.929, use `charge_margin` = 0.25 instead of 0.
- Not established either way, so nothing is recommended, where: 42.0714 <= battery_capacity_wh < 59.4559; battery_capacity_wh >= 167.929.

Explanations (judged separately from the outcome):

- *fewer mode switches waste less scan time on slewing and settling* — **supported**
  - mediator test at battery_capacity_wh=25: inconclusive. `wasted_scan_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=70.7: supports. `wasted_scan_s`: 388.625 with the intervention vs 895.562 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=141: supports. `wasted_scan_s`: 482.583 with the intervention vs 859.375 without, over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=35.4: supports. `wasted_scan_s`: 603.333 with the intervention vs 1201.67 without, over 6 of 32 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `wasted_scan_s`: 371.625 with the intervention vs 837.188 without, over 16 of 16 seed pairs

### Going further in the direction that helped keeps helping: charge_below=0.05 beats charge_below=0.1.

Proposed by: program. Compares `charge_below` = 0.05 instead of 0.1.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | -0.014 | [-0.044, +0.005] | 16 | 16 / 16 |
| battery_capacity_wh=35.4 | no meaningful benefit | -0.000 | [-0.024, +0.010] | 16 | 16 / 16 |
| battery_capacity_wh=50 | no meaningful benefit | -0.010 | [-0.043, +0.014] | 16 | 16 / 16 |
| battery_capacity_wh=70.7 | no meaningful benefit | -0.010 | [-0.041, +0.014] | 16 | 16 / 16 |
| battery_capacity_wh=100 | baseline better | -0.562 | [-0.877, -0.256] | 16 | 14 / 6 |
| battery_capacity_wh=141 | baseline better | -0.636 | [-0.914, -0.347] | 16 | 11 / 1 |
| battery_capacity_wh=200 | baseline better | -0.144 | [-0.309, -0.012] | 32 | 5 / 0 |
| battery_capacity_wh=283 | unresolved (inconclusive at the maximum number of seeds) | +0.003 | [-0.059, +0.032] | 48 | 1 / 0 |
| battery_capacity_wh=400 | no meaningful benefit | +0.006 | [+0.000, +0.018] | 16 | 0 / 0 |

**Original claim: refuted.** Did not hold anywhere it was tested.

- **supported** (reversed): where 84.0833 <= battery_capacity_wh < 237.908, use `charge_below` = 0.1 instead of 0.05.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 84.0833; battery_capacity_wh >= 336.452.
- Not established either way, so nothing is recommended, where: 237.908 <= battery_capacity_wh < 336.452.

### Neither tested setting is acceptable here; a setting further out does better: charge_below=0.4 beats charge_below=0.25.

Proposed by: program. Compares `charge_below` = 0.4 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.489 | [+0.160, +0.842] | 16 | 10 / 16 |
| battery_capacity_wh=35.4 | intervention better | +0.919 | [+0.585, +1.198] | 16 | 0 / 12 |
| battery_capacity_wh=50 | intervention better | +0.167 | [+0.014, +0.349] | 32 | 0 / 6 |
| battery_capacity_wh=70.7 | baseline better | -0.058 | [-0.101, -0.034] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.066 | [-0.081, -0.049] | 16 | 0 / 0 |
| battery_capacity_wh=141 | baseline better | -0.103 | [-0.122, -0.082] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.123 | [-0.145, -0.100] | 16 | 0 / 0 |
| battery_capacity_wh=283 | baseline better | -0.106 | [-0.154, -0.059] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.103 | [-0.171, -0.039] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 59.4559, use `charge_below` = 0.4 instead of 0.25.
- **supported** (reversed): where battery_capacity_wh >= 59.4559, use `charge_below` = 0.25 instead of 0.4.

### Going further in the direction that helped keeps helping: charge_below=0.6 beats charge_below=0.4.

Proposed by: program. Compares `charge_below` = 0.6 instead of 0.4.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.468 | [+0.145, +0.830] | 16 | 4 / 10 |
| battery_capacity_wh=35.4 | no meaningful benefit | -0.020 | [-0.036, -0.006] | 16 | 0 / 0 |
| battery_capacity_wh=50 | baseline better | -0.030 | [-0.041, -0.018] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.050 | [-0.069, -0.032] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.087 | [-0.116, -0.063] | 16 | 0 / 0 |
| battery_capacity_wh=141 | baseline better | -0.114 | [-0.141, -0.087] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.163 | [-0.192, -0.129] | 16 | 0 / 0 |
| battery_capacity_wh=283 | baseline better | -0.214 | [-0.250, -0.171] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.223 | [-0.287, -0.157] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 29.7489, use `charge_below` = 0.6 instead of 0.4.
- **supported** (reversed): where battery_capacity_wh >= 42.0714, use `charge_below` = 0.4 instead of 0.6.
- No meaningful benefit, so nothing is recommended, where: 29.7489 <= battery_capacity_wh < 42.0714.

### Going further in the direction that helped keeps helping: charge_below=0.8 beats charge_below=0.6.

Proposed by: program. Compares `charge_below` = 0.8 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | unresolved (inconclusive at the maximum number of seeds) | +0.143 | [-0.028, +0.324] | 48 | 3 / 9 |
| battery_capacity_wh=35.4 | no meaningful benefit | -0.015 | [-0.027, -0.001] | 16 | 0 / 0 |
| battery_capacity_wh=50 | baseline better | -0.027 | [-0.042, -0.012] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.035 | [-0.053, -0.018] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.074 | [-0.126, -0.034] | 16 | 0 / 0 |
| battery_capacity_wh=141 | baseline better | -0.104 | [-0.151, -0.059] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.139 | [-0.185, -0.094] | 16 | 0 / 0 |
| battery_capacity_wh=283 | baseline better | -0.196 | [-0.244, -0.143] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.255 | [-0.317, -0.190] | 16 | 0 / 0 |

**Original claim: refuted.** Did not hold anywhere it was tested.

- **supported** (reversed): where battery_capacity_wh >= 42.0714, use `charge_below` = 0.6 instead of 0.8.
- No meaningful benefit, so nothing is recommended, where: 29.7489 <= battery_capacity_wh < 42.0714.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 29.7489.

## Revision history

- `propose` claim_50710ae0c12c: proposed
- `propose` claim_1d9df8db4349: proposed
- `propose` claim_f26648f324c0: proposed
- `propose` claim_12ebc8f6ff7c: proposed
- `support` claim_50710ae0c12c: hypothesis -> supported: 1 decisive test(s), all in favour
- `refute` claim_1d9df8db4349: hypothesis -> refuted: 1 decisive test(s), none in favour
- `support` claim_f26648f324c0: hypothesis -> supported: 1 decisive test(s), all in favour
- `propose` claim_9e0c65de2bc0: keep-going rule, from claim_50710ae0c12c, along the charge_below ladder
- `refute` claim_9e0c65de2bc0: hypothesis -> refuted: 1 decisive test(s), none in favour
- `specialize` claim_85fd677d0fa0: reversed from claim_9e0c65de2bc0: all tested conditions
- `support` claim_85fd677d0fa0: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_50710ae0c12c: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_53deca70201d: narrowed from claim_50710ae0c12c: battery_capacity_wh >= 70.7107
- `support` claim_53deca70201d: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_1d9df8db4349: refuted -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_b02573d042ea: narrowed from claim_1d9df8db4349: battery_capacity_wh < 70.7107
- `support` claim_b02573d042ea: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_6011a3044a99: nothing-works-here rule, from claim_50710ae0c12c, along the charge_below ladder
- `support` claim_6011a3044a99: hypothesis -> supported: 1 decisive test(s), all in favour
- `supersede` claim_f26648f324c0: supported -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_81b5a6240130: narrowed from claim_f26648f324c0: battery_capacity_wh >= 70.7107
- `support` claim_81b5a6240130: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_12ebc8f6ff7c: hypothesis -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_204cb41b4e2d: narrowed from claim_12ebc8f6ff7c: battery_capacity_wh < 70.7107
- `support` claim_204cb41b4e2d: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_85fd677d0fa0: scope changed from [all tested conditions] to [battery_capacity_wh >= 70.7107]
- `propose` claim_212aaf17271b: keep-going rule, from claim_6011a3044a99, along the charge_below ladder
- `support` claim_212aaf17271b: hypothesis -> supported: 1 decisive test(s), all in favour
- `supersede` claim_6011a3044a99: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_fee1ef09ccca: narrowed from claim_6011a3044a99: battery_capacity_wh < 70.7107
- `support` claim_fee1ef09ccca: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_52738fc23ec6: reversed from claim_6011a3044a99: battery_capacity_wh >= 70.7107
- `support` claim_52738fc23ec6: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_b8a51d744aa6: reversed from claim_50710ae0c12c: 42.0416 <= battery_capacity_wh < 118.912
- `support` claim_b8a51d744aa6: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_53deca70201d: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 118.912]
- `propose` claim_6c08497129b5: keep-going rule, from claim_212aaf17271b, along the charge_below ladder
- `supersede` claim_212aaf17271b: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_af6a83c4ea34: narrowed from claim_212aaf17271b: battery_capacity_wh < 70.7107
- `support` claim_af6a83c4ea34: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_e6aa4fed3a9b: reversed from claim_212aaf17271b: battery_capacity_wh >= 70.7107
- `support` claim_e6aa4fed3a9b: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_b02573d042ea: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 118.912]
- `refute` claim_6c08497129b5: hypothesis -> refuted: 1 decisive test(s), none in favour
- `specialize` claim_85cf0de61158: reversed from claim_6c08497129b5: battery_capacity_wh >= 70.7107
- `support` claim_85cf0de61158: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_81b5a6240130: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_204cb41b4e2d: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 118.912]
- `rescope` claim_85fd677d0fa0: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 118.912]
- `rescope` claim_fee1ef09ccca: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_52738fc23ec6: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_af6a83c4ea34: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_e6aa4fed3a9b: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_85cf0de61158: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_85fd677d0fa0: scope changed from [battery_capacity_wh >= 118.912] to [118.912 <= battery_capacity_wh < 282.843]
- `rescope` claim_b8a51d744aa6: scope changed from [42.0416 <= battery_capacity_wh < 118.912] to [42.0416 <= battery_capacity_wh < 99.8434]
- `rescope` claim_53deca70201d: scope changed from [battery_capacity_wh >= 118.912] to [battery_capacity_wh >= 167.929]
- `rescope` claim_b02573d042ea: scope changed from [battery_capacity_wh < 118.912] to [battery_capacity_wh < 99.8434]
- `rescope` claim_204cb41b4e2d: scope changed from [battery_capacity_wh < 118.912] to [battery_capacity_wh < 167.929]
- `rescope` claim_85fd677d0fa0: scope changed from [118.912 <= battery_capacity_wh < 282.843] to [99.8434 <= battery_capacity_wh < 282.843]
- `rescope` claim_b8a51d744aa6: scope changed from [42.0416 <= battery_capacity_wh < 99.8434] to [29.7489 <= battery_capacity_wh < 99.8434]
- `rescope` claim_81b5a6240130: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 29.7489]
- `rescope` claim_fee1ef09ccca: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 50.0278]
- `rescope` claim_52738fc23ec6: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 50.0278]
- `rescope` claim_af6a83c4ea34: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 29.7489]
- `rescope` claim_e6aa4fed3a9b: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 50.0278]
- `rescope` claim_85cf0de61158: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 50.0278]
- `rescope` claim_85cf0de61158: scope changed from [battery_capacity_wh >= 50.0278] to [battery_capacity_wh >= 42.0714]
- `specialize` claim_b630adcb88e2: narrowed from claim_1d9df8db4349: battery_capacity_wh >= 237.908
- `contest` claim_b630adcb88e2: hypothesis -> contested: the 2 test(s) in its region disagree and could not be separated
- `rescope` claim_85fd677d0fa0: scope changed from [99.8434 <= battery_capacity_wh < 282.843] to [99.8434 <= battery_capacity_wh < 237.908]
- `rescope` claim_b02573d042ea: scope changed from [battery_capacity_wh < 99.8434] to [battery_capacity_wh < 42.0714]
- `specialize` claim_8dbe74108531: narrowed from claim_1d9df8db4349: 59.4559 <= battery_capacity_wh < 167.929
- `contest` claim_8dbe74108531: hypothesis -> contested: the 2 test(s) in its region disagree and could not be separated
- `specialize` claim_3b6229b35642: reversed from claim_1d9df8db4349: 237.908 <= battery_capacity_wh < 336.452
- `support` claim_3b6229b35642: hypothesis -> supported: 1 decisive test(s) in its region
- `retire` claim_b630adcb88e2: contested -> retired: its region is no longer supported by the pooled evidence
- `rescope` claim_204cb41b4e2d: scope changed from [battery_capacity_wh < 167.929] to [battery_capacity_wh < 42.0714]
- `specialize` claim_512a052bbf52: narrowed from claim_12ebc8f6ff7c: 59.4559 <= battery_capacity_wh < 167.929
- `support` claim_512a052bbf52: hypothesis -> supported: 2 decisive test(s) in its region
- `rescope` claim_fee1ef09ccca: scope changed from [battery_capacity_wh < 50.0278] to [battery_capacity_wh < 59.4559]
- `rescope` claim_52738fc23ec6: scope changed from [battery_capacity_wh >= 50.0278] to [battery_capacity_wh >= 59.4559]
- `rescope` claim_e6aa4fed3a9b: scope changed from [battery_capacity_wh >= 50.0278] to [battery_capacity_wh >= 42.0714]
- `rescope` claim_b8a51d744aa6: scope changed from [29.7489 <= battery_capacity_wh < 99.8434] to [29.7489 <= battery_capacity_wh < 118.743]
- `rescope` claim_8dbe74108531: scope changed from [59.4559 <= battery_capacity_wh < 167.929] to [42.0714 <= battery_capacity_wh < 118.743]
- `rescope` claim_85fd677d0fa0: scope changed from [99.8434 <= battery_capacity_wh < 237.908] to [84.0833 <= battery_capacity_wh < 237.908]

## Transfer: interpolation (inside the studied range)

4 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | spacecraft lost | success rate |
|---|---|---|---|
| reference | +0.3050 | 19.5% | 78.1% |
| flat | +0.1031 | 43.0% | 57.0% |
| pooled | +0.5313 | 1.6% | 96.9% |
| conditional | +0.5947 | 1.6% | 98.4% |
| oracle | +0.6070 | 0.0% | 95.3% |

Success: the spacecraft survived and recorded data for at least 20% of the episode (`docs/metrics.md`, 2.3).

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.0634 [+0.0459, +0.0828], p = 0.0002; resampling whole seeds: [+0.0457, +0.0824], p = 0.0002
- conditional minus flat: +0.4916 [+0.3851, +0.6003], p = 0.0002; resampling whole seeds: [+0.4257, +0.5467], p = 0.0002
- conditional minus reference: +0.2897 [+0.2037, +0.3797], p = 0.0002; resampling whole seeds: [+0.2210, +0.3545], p = 0.0002
- pooled minus reference: +0.2264 [+0.1331, +0.3190], p = 0.0002; resampling whole seeds: [+0.1601, +0.2869], p = 0.0002
- flat minus reference: -0.2019 [-0.2969, -0.1128], p = 0.0002; resampling whole seeds: [-0.2697, -0.1306], p = 0.0002
- oracle minus conditional: +0.0123 [-0.0167, +0.0474], p = 0.4797; resampling whole seeds: [-0.0159, +0.0477], p = 0.4777

The first interval treats every (condition, seed) episode pair as independent. The second averages over the conditions first and resamples the 32 seeds, because every condition reuses the same seeds.

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=35 | -0.535 (75%) reference | -0.762 (94%) charge_below=0.1, desat_above=0.3 | +0.388 (6%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.388 (6%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.348 (0%) charge_below=0.6, desat_above=0.6 |
| battery_capacity_wh=70 | +0.424 (3%) reference | -0.368 (78%) charge_below=0.1, desat_above=0.3 | +0.531 (0%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.552 (0%) charge_margin=0.25, desat_above=0.3 | +0.517 (0%) charge_below=0.25, desat_above=0.3 |
| battery_capacity_wh=140 | +0.584 (0%) reference | +0.718 (0%) charge_below=0.1, desat_above=0.3 | +0.546 (0%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.615 (0%) charge_margin=0.25, desat_above=0.3 | +0.718 (0%) charge_below=0.1, desat_above=0.3 |
| battery_capacity_wh=280 | +0.747 (0%) reference | +0.825 (0%) charge_below=0.1, desat_above=0.3 | +0.660 (0%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.825 (0%) charge_below=0.1, desat_above=0.3 | +0.846 (0%) charge_below=0.05, desat_above=0.3 |

## Transfer: extrapolation (outside the studied range)

2 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | spacecraft lost | success rate |
|---|---|---|---|
| reference | -0.0167 | 48.4% | 51.6% |
| flat | -0.0322 | 50.0% | 50.0% |
| pooled | +0.0308 | 40.6% | 57.8% |
| conditional | +0.3768 | 20.3% | 79.7% |
| oracle | +0.4790 | 9.4% | 82.8% |

Success: the spacecraft survived and recorded data for at least 20% of the episode (`docs/metrics.md`, 2.3).

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.3459 [+0.2242, +0.4728], p = 0.0002; resampling whole seeds: [+0.2355, +0.4590], p = 0.0002
- conditional minus flat: +0.4090 [+0.2630, +0.5607], p = 0.0002; resampling whole seeds: [+0.2962, +0.5186], p = 0.0002
- conditional minus reference: +0.3935 [+0.2505, +0.5385], p = 0.0002; resampling whole seeds: [+0.2811, +0.5006], p = 0.0002
- pooled minus reference: +0.0476 [-0.0436, +0.1585], p = 0.3837; resampling whole seeds: [-0.0420, +0.1475], p = 0.3261
- flat minus reference: -0.0155 [-0.0663, +0.0279], p = 0.6285; resampling whole seeds: [-0.0700, +0.0268], p = 0.6335
- oracle minus conditional: +0.1022 [+0.0189, +0.1964], p = 0.0198; resampling whole seeds: [+0.0223, +0.1920], p = 0.0182

The first interval treats every (condition, seed) episode pair as independent. The second averages over the conditions first and resamples the 32 seeds, because every condition reuses the same seeds.

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=18 | -0.877 (97%) reference | -0.941 (100%) charge_below=0.1, desat_above=0.3 | -0.640 (81%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | -0.123 (41%) charge_below=0.6, charge_margin=0.25, precharge_below=0.6, precharge_window_s=900 | +0.080 (19%) charge_below=0.8, desat_above=0.6 |
| battery_capacity_wh=600 | +0.843 (0%) reference | +0.877 (0%) charge_below=0.1, desat_above=0.3 | +0.702 (0%) charge_below=0.4, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.877 (0%) charge_below=0.1, desat_above=0.3 | +0.878 (0%) charge_below=0.05, desat_above=0.3 |

## Do the recommended settings still work together?

Every family was tested with only its own change. Here the reference policy, each recommended change on its own, and all of them together run on the same held-out seeds.

| conditions | reference | each change alone | all together | together minus reference | finding |
|---|---|---|---|---|---|
| battery_capacity_wh=35 | -0.535 | `charge_below` +0.182; `precharge_below,precharge_window_s` -0.318; `desat_above` -0.393; `charge_margin` -0.358 | +0.388 | +0.923 [+0.708, +1.128] | consistent |
| battery_capacity_wh=70 | +0.424 | `desat_above` +0.517; `charge_margin` +0.511 | +0.552 | +0.128 [+0.063, +0.222] | consistent |
| battery_capacity_wh=140 | +0.584 | `desat_above` +0.636; `charge_margin` +0.598 | +0.615 | +0.030 [-0.009, +0.067] | negative interaction |
| battery_capacity_wh=280 | +0.747 | `charge_below` +0.824; `desat_above` +0.760 | +0.825 | +0.077 [+0.027, +0.126] | consistent |
| battery_capacity_wh=18 | -0.877 | `precharge_below,precharge_window_s` -0.881; `charge_margin` -0.869; `charge_below` -0.158 | -0.123 | +0.753 [+0.527, +0.971] | consistent |
| battery_capacity_wh=600 | +0.843 | `charge_below` +0.899; `desat_above` +0.830 | +0.877 | +0.034 [-0.016, +0.089] | unhelpful change |

- battery_capacity_wh=140: every change is at least as good as the reference on its own, but together they score below the best of them. All together is -0.021 [-0.044, +0.003] against `desat_above` alone.
- battery_capacity_wh=600: on its own, `desat_above` (+0.830 against +0.843) scores below the reference here, so the claim behind it is being applied where it does not hold. All together is -0.022 [-0.048, -0.003] against `charge_below` alone.
