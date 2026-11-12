# Charging, desaturation and eclipse strategies across battery sizes (Basilisk / BSK-RL)

77 experiments in 21 rounds, 2688 simulator episodes (budget 4500).

**8 comparisons, 21 claims** (2 refuted, 6 superseded, 13 supported); 29 relations between claims.

## Claims by comparison

### A lower charge threshold collects more data.

Proposed by: seed (hand-written). Compares `charge_below` = 0.1 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | +0.003 | [-0.022, +0.017] | 16 | 16 / 16 |
| battery_capacity_wh=32.4 | no meaningful benefit | -0.091 | [-0.345, +0.015] | 16 | 16 / 15 |
| battery_capacity_wh=42 | baseline better | -0.534 | [-0.869, -0.216] | 16 | 16 / 10 |
| battery_capacity_wh=50 | baseline better | -1.010 | [-1.215, -0.745] | 16 | 16 / 3 |
| battery_capacity_wh=70.7 | baseline better | -1.130 | [-1.182, -1.075] | 16 | 16 / 0 |
| battery_capacity_wh=100 | baseline better | -0.344 | [-0.648, -0.059] | 16 | 6 / 0 |
| battery_capacity_wh=119 | baseline better | -0.168 | [-0.328, -0.031] | 48 | 11 / 0 |
| battery_capacity_wh=154 | unresolved (inconclusive at the maximum number of seeds) | +0.005 | [-0.105, +0.088] | 48 | 4 / 0 |
| battery_capacity_wh=200 | intervention better | +0.092 | [+0.062, +0.120] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.055 | [+0.009, +0.113] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh >= 175.499, use `charge_below` = 0.1 instead of 0.25.
- **supported** (reversed): where 36.889 <= battery_capacity_wh < 135.374, use `charge_below` = 0.25 instead of 0.1.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 36.889.
- Not established either way, so nothing is recommended, where: 135.374 <= battery_capacity_wh < 175.499.

Explanations (judged separately from the outcome):

- *less time is spent in charge mode* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 2636.25 with the intervention vs 4125 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400: supports. `time_charge_s`: 1267.5 with the intervention vs 2141.25 without, over 16 of 16 seed pairs

### Topping up the battery before each eclipse improves the score.

Proposed by: seed (hand-written). Compares `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.129 | [+0.002, +0.306] | 32 | 28 / 31 |
| battery_capacity_wh=35.4 | intervention better | +0.291 | [+0.029, +0.625] | 16 | 9 / 12 |
| battery_capacity_wh=42.1 | intervention better | +0.370 | [+0.099, +0.673] | 16 | 5 / 10 |
| battery_capacity_wh=50 | unresolved (inconclusive at the maximum number of seeds) | +0.072 | [-0.068, +0.215] | 48 | 12 / 14 |
| battery_capacity_wh=59.5 | intervention better | +0.042 | [+0.014, +0.068] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | intervention better | +0.039 | [+0.010, +0.068] | 16 | 0 / 0 |
| battery_capacity_wh=100 | intervention better | +0.034 | [+0.006, +0.061] | 16 | 0 / 0 |
| battery_capacity_wh=119 | intervention better | +0.036 | [+0.011, +0.060] | 32 | 0 / 0 |
| battery_capacity_wh=154 | unresolved (inconclusive at the maximum number of seeds) | +0.009 | [-0.011, +0.029] | 48 | 0 / 0 |
| battery_capacity_wh=200 | no meaningful benefit | -0.003 | [-0.023, +0.017] | 48 | 0 / 0 |
| battery_capacity_wh=400 | no meaningful benefit | -0.039 | [-0.088, +0.001] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 45.8803, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- **supported** (narrowed): where 54.5436 <= battery_capacity_wh < 135.374, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh >= 175.499.
- Not established either way, so nothing is recommended, where: 45.8803 <= battery_capacity_wh < 54.5436; 135.374 <= battery_capacity_wh < 175.499.

Explanations (judged separately from the outcome):

- *the battery does not get as low* — **supported**
  - mediator test at battery_capacity_wh=25: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=70.7: supports. `min_battery`: 0.14246 with the intervention vs 0.09956 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=119: supports. `min_battery`: 0.19276 with the intervention vs 0.17195 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=35.4: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=59.5: supports. `min_battery`: 0.11991 with the intervention vs 0.07604 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42.1: supports. `min_battery`: 0.11848 with the intervention vs 0.04063 without, over 6 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `min_battery`: 0.18141 with the intervention vs 0.1485 without, over 16 of 16 seed pairs
- *it prevents battery depletion* — **contested**
  - mediator test at battery_capacity_wh=25: inconclusive. `failure:battery`: 0.875 with the intervention vs 0.96875 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=70.7: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=119: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=35.4: inconclusive. `failure:battery`: 0.5625 with the intervention vs 0.75 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=59.5: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42.1: supports. `failure:battery`: 0.3125 with the intervention vs 0.625 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs

### Unloading the reaction wheels early improves the score.

Proposed by: seed (hand-written). Compares `desat_above` = 0.3 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | unresolved (inconclusive at the maximum number of seeds) | +0.040 | [-0.022, +0.145] | 48 | 44 / 46 |
| battery_capacity_wh=32.4 | intervention better | +0.186 | [+0.016, +0.436] | 16 | 13 / 15 |
| battery_capacity_wh=42 | intervention better | +0.598 | [+0.233, +0.946] | 16 | 2 / 10 |
| battery_capacity_wh=50 | intervention better | +0.254 | [+0.037, +0.541] | 16 | 0 / 3 |
| battery_capacity_wh=70.7 | intervention better | +0.057 | [+0.017, +0.099] | 16 | 0 / 0 |
| battery_capacity_wh=100 | intervention better | +0.056 | [+0.020, +0.093] | 16 | 0 / 0 |
| battery_capacity_wh=200 | intervention better | +0.048 | [+0.022, +0.080] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.026 | [+0.005, +0.049] | 48 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh >= 28.4605, use `desat_above` = 0.3 instead of 0.6.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 28.4605.

Explanations (judged separately from the outcome):

- *it prevents the wheels from reaching their speed limit* — **refuted**
  - mediator test at battery_capacity_wh=200: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=70.7: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=32.4: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=100: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
- *slower wheels draw less power, so less time is spent charging* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 3318.75 with the intervention vs 4125 without, over 16 of 16 seed pairs
  - moderator test at battery_capacity_wh=200: supports. effect by `max_wheel_speed_rpm`: 1500 -> -0.070, 3000 -> +0.006, 6000 -> +0.041
  - mediator test at battery_capacity_wh=70.7: supports. `time_charge_s`: 7080 with the intervention vs 8058.75 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42: inconclusive. `time_charge_s`: 7680 with the intervention vs 8020 without, over 6 of 16 seed pairs
  - mediator test at battery_capacity_wh=32.4: inconclusive. `time_charge_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=400: supports. `time_charge_s`: 1981.25 with the intervention vs 2523.75 without, over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `time_charge_s`: 6228.75 with the intervention vs 7188.75 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: supports. `time_charge_s`: 7818.46 with the intervention vs 8649.23 without, over 13 of 16 seed pairs

### Charging in longer blocks improves the score.

Proposed by: seed (hand-written). Compares `charge_margin` = 0.25 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.024 | [+0.001, +0.075] | 16 | 16 / 16 |
| battery_capacity_wh=35.4 | intervention better | +0.233 | [+0.020, +0.472] | 32 | 20 / 25 |
| battery_capacity_wh=42.1 | intervention better | +0.344 | [+0.116, +0.635] | 16 | 6 / 10 |
| battery_capacity_wh=50 | unresolved (inconclusive at the maximum number of seeds) | +0.095 | [-0.022, +0.223] | 48 | 13 / 14 |
| battery_capacity_wh=59.5 | unresolved (inconclusive at the maximum number of seeds) | +0.056 | [-0.048, +0.152] | 48 | 7 / 6 |
| battery_capacity_wh=70.7 | intervention better | +0.059 | [+0.012, +0.110] | 16 | 0 / 0 |
| battery_capacity_wh=100 | intervention better | +0.048 | [+0.003, +0.104] | 16 | 0 / 0 |
| battery_capacity_wh=119 | intervention better | +0.061 | [+0.023, +0.101] | 32 | 0 / 0 |
| battery_capacity_wh=154 | unresolved (inconclusive at the maximum number of seeds) | +0.039 | [-0.001, +0.077] | 48 | 0 / 0 |
| battery_capacity_wh=200 | unresolved (inconclusive at the maximum number of seeds) | +0.028 | [-0.011, +0.062] | 48 | 0 / 0 |
| battery_capacity_wh=400 | unresolved (inconclusive at the maximum number of seeds) | -0.001 | [-0.039, +0.031] | 48 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 45.8803, use `charge_margin` = 0.25 instead of 0.
- **supported** (narrowed): where 64.8587 <= battery_capacity_wh < 135.374, use `charge_margin` = 0.25 instead of 0.
- Not established either way, so nothing is recommended, where: 45.8803 <= battery_capacity_wh < 64.8587; battery_capacity_wh >= 135.374.

Explanations (judged separately from the outcome):

- *fewer mode switches waste less scan time on slewing and settling* — **supported**
  - mediator test at battery_capacity_wh=25: inconclusive. `wasted_scan_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=70.7: supports. `wasted_scan_s`: 388.625 with the intervention vs 895.562 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=119: supports. `wasted_scan_s`: 474.812 with the intervention vs 927.844 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=35.4: supports. `wasted_scan_s`: 603.333 with the intervention vs 1201.67 without, over 6 of 32 seed pairs
  - mediator test at battery_capacity_wh=42.1: supports. `wasted_scan_s`: 350.833 with the intervention vs 881.667 without, over 6 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `wasted_scan_s`: 371.625 with the intervention vs 837.188 without, over 16 of 16 seed pairs

### Going further in the direction that helped keeps helping: charge_below=0.05 beats charge_below=0.1.

Proposed by: program. Compares `charge_below` = 0.05 instead of 0.1.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | -0.014 | [-0.044, +0.005] | 16 | 16 / 16 |
| battery_capacity_wh=50 | no meaningful benefit | -0.010 | [-0.043, +0.014] | 16 | 16 / 16 |
| battery_capacity_wh=70.7 | no meaningful benefit | -0.010 | [-0.041, +0.014] | 16 | 16 / 16 |
| battery_capacity_wh=91.7 | baseline better | -0.424 | [-0.768, -0.127] | 16 | 16 / 10 |
| battery_capacity_wh=100 | baseline better | -0.562 | [-0.877, -0.256] | 16 | 14 / 6 |
| battery_capacity_wh=119 | baseline better | -0.865 | [-1.084, -0.584] | 16 | 15 / 2 |
| battery_capacity_wh=200 | baseline better | -0.144 | [-0.309, -0.012] | 32 | 5 / 0 |
| battery_capacity_wh=238 | unresolved (inconclusive at the maximum number of seeds) | -0.034 | [-0.119, +0.027] | 48 | 3 / 0 |
| battery_capacity_wh=283 | unresolved (inconclusive at the maximum number of seeds) | +0.003 | [-0.059, +0.032] | 48 | 1 / 0 |
| battery_capacity_wh=336 | unresolved (inconclusive at the maximum number of seeds) | +0.019 | [+0.009, +0.030] | 48 | 0 / 0 |
| battery_capacity_wh=400 | no meaningful benefit | +0.006 | [+0.000, +0.018] | 16 | 0 / 0 |

**Original claim: refuted.** Did not hold anywhere it was tested.

- **supported** (reversed): where 80.5183 <= battery_capacity_wh < 218.174, use `charge_below` = 0.1 instead of 0.05.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 80.5183; battery_capacity_wh >= 366.606.
- Not established either way, so nothing is recommended, where: 218.174 <= battery_capacity_wh < 366.606.

### Neither tested setting is acceptable here; a setting further out does better: charge_below=0.4 beats charge_below=0.25.

Proposed by: program. Compares `charge_below` = 0.4 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.489 | [+0.160, +0.842] | 16 | 10 / 16 |
| battery_capacity_wh=42 | intervention better | +0.670 | [+0.360, +0.971] | 16 | 0 / 10 |
| battery_capacity_wh=50 | intervention better | +0.167 | [+0.014, +0.349] | 32 | 0 / 6 |
| battery_capacity_wh=54.5 | intervention better | +0.198 | [+0.024, +0.396] | 32 | 0 / 7 |
| battery_capacity_wh=70.7 | baseline better | -0.058 | [-0.101, -0.034] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.066 | [-0.081, -0.049] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.123 | [-0.145, -0.100] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.103 | [-0.171, -0.039] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 62.0737, use `charge_below` = 0.4 instead of 0.25.
- **supported** (reversed): where battery_capacity_wh >= 62.0737, use `charge_below` = 0.25 instead of 0.4.

### Going further in the direction that helped keeps helping: charge_below=0.6 beats charge_below=0.4.

Proposed by: program. Compares `charge_below` = 0.6 instead of 0.4.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.468 | [+0.145, +0.830] | 16 | 4 / 10 |
| battery_capacity_wh=32.4 | intervention better | +0.433 | [+0.119, +0.785] | 16 | 0 / 6 |
| battery_capacity_wh=42 | no meaningful benefit | -0.012 | [-0.026, +0.003] | 16 | 0 / 0 |
| battery_capacity_wh=50 | baseline better | -0.030 | [-0.041, -0.018] | 16 | 0 / 0 |
| battery_capacity_wh=54.5 | baseline better | -0.030 | [-0.047, -0.013] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.050 | [-0.069, -0.032] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.087 | [-0.116, -0.063] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.163 | [-0.192, -0.129] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.223 | [-0.287, -0.157] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 36.889, use `charge_below` = 0.6 instead of 0.4.
- **supported** (reversed): where battery_capacity_wh >= 45.8258, use `charge_below` = 0.4 instead of 0.6.
- No meaningful benefit, so nothing is recommended, where: 36.889 <= battery_capacity_wh < 45.8258.

### Going further in the direction that helped keeps helping: charge_below=0.8 beats charge_below=0.6.

Proposed by: program. Compares `charge_below` = 0.8 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | unresolved (inconclusive at the maximum number of seeds) | +0.143 | [-0.028, +0.324] | 48 | 3 / 9 |
| battery_capacity_wh=32.4 | no meaningful benefit | -0.006 | [-0.018, +0.005] | 16 | 0 / 0 |
| battery_capacity_wh=42 | baseline better | -0.026 | [-0.035, -0.016] | 16 | 0 / 0 |
| battery_capacity_wh=50 | baseline better | -0.027 | [-0.042, -0.012] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.035 | [-0.053, -0.018] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.074 | [-0.126, -0.034] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.139 | [-0.185, -0.094] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.255 | [-0.317, -0.190] | 16 | 0 / 0 |

**Original claim: refuted.** Did not hold anywhere it was tested.

- **supported** (reversed): where battery_capacity_wh >= 36.889, use `charge_below` = 0.6 instead of 0.8.
- No meaningful benefit, so nothing is recommended, where: 28.4605 <= battery_capacity_wh < 36.889.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 28.4605.

## Revision history

- `propose` claim_c4bfa196ead1: proposed
- `propose` claim_c14ac54b9caf: proposed
- `propose` claim_5ee5f00d287a: proposed
- `propose` claim_887b7adac740: proposed
- `support` claim_c4bfa196ead1: hypothesis -> supported: 1 decisive test(s), all in favour
- `refute` claim_c14ac54b9caf: hypothesis -> refuted: 1 decisive test(s), none in favour
- `support` claim_5ee5f00d287a: hypothesis -> supported: 1 decisive test(s), all in favour
- `propose` claim_44eabb787bd8: keep-going rule, from claim_c4bfa196ead1, along the charge_below ladder
- `refute` claim_44eabb787bd8: hypothesis -> refuted: 1 decisive test(s), none in favour
- `specialize` claim_9e0669d11d54: reversed from claim_44eabb787bd8: all tested conditions
- `support` claim_9e0669d11d54: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_c4bfa196ead1: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_f79313056616: narrowed from claim_c4bfa196ead1: battery_capacity_wh >= 70.7107
- `support` claim_f79313056616: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_c14ac54b9caf: refuted -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_59337f2327c1: narrowed from claim_c14ac54b9caf: battery_capacity_wh < 70.7107
- `support` claim_59337f2327c1: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_96b0b8099a85: nothing-works-here rule, from claim_c4bfa196ead1, along the charge_below ladder
- `support` claim_96b0b8099a85: hypothesis -> supported: 1 decisive test(s), all in favour
- `specialize` claim_590bcc6a613e: reversed from claim_c4bfa196ead1: 42.0416 <= battery_capacity_wh < 118.912
- `support` claim_590bcc6a613e: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_f79313056616: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 118.912]
- `rescope` claim_59337f2327c1: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 118.912]
- `supersede` claim_5ee5f00d287a: supported -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_9fe949987656: narrowed from claim_5ee5f00d287a: battery_capacity_wh >= 70.7107
- `support` claim_9fe949987656: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_a05b8beebeb8: keep-going rule, from claim_96b0b8099a85, along the charge_below ladder
- `support` claim_a05b8beebeb8: hypothesis -> supported: 1 decisive test(s), all in favour
- `rescope` claim_9fe949987656: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_590bcc6a613e: scope changed from [42.0416 <= battery_capacity_wh < 118.912] to [42.0416 <= battery_capacity_wh < 154.272]
- `rescope` claim_f79313056616: scope changed from [battery_capacity_wh >= 118.912] to [battery_capacity_wh >= 154.272]
- `rescope` claim_59337f2327c1: scope changed from [battery_capacity_wh < 118.912] to [battery_capacity_wh < 154.272]
- `propose` claim_79ccea55eecb: keep-going rule, from claim_a05b8beebeb8, along the charge_below ladder
- `rescope` claim_590bcc6a613e: scope changed from [42.0416 <= battery_capacity_wh < 154.272] to [32.4037 <= battery_capacity_wh < 154.272]
- `rescope` claim_9fe949987656: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `rescope` claim_590bcc6a613e: scope changed from [32.4037 <= battery_capacity_wh < 154.272] to [32.4037 <= battery_capacity_wh < 135.374]
- `rescope` claim_f79313056616: scope changed from [battery_capacity_wh >= 154.272] to [battery_capacity_wh >= 175.499]
- `rescope` claim_59337f2327c1: scope changed from [battery_capacity_wh < 154.272] to [battery_capacity_wh < 135.374]
- `rescope` claim_590bcc6a613e: scope changed from [32.4037 <= battery_capacity_wh < 135.374] to [36.889 <= battery_capacity_wh < 135.374]
- `rescope` claim_9fe949987656: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 28.4605]
- `supersede` claim_887b7adac740: hypothesis -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_00634540de79: narrowed from claim_887b7adac740: battery_capacity_wh < 70.7107
- `support` claim_00634540de79: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_00634540de79: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 118.912]
- `rescope` claim_9e0669d11d54: scope changed from [all tested conditions] to [battery_capacity_wh >= 70.7107]
- `supersede` claim_96b0b8099a85: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_a3f1fc98e225: narrowed from claim_96b0b8099a85: battery_capacity_wh < 70.7107
- `support` claim_a3f1fc98e225: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_8c28017d6b40: reversed from claim_96b0b8099a85: battery_capacity_wh >= 70.7107
- `support` claim_8c28017d6b40: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_9e0669d11d54: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 118.912]
- `rescope` claim_a3f1fc98e225: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_8c28017d6b40: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_00634540de79: scope changed from [battery_capacity_wh < 118.912] to [battery_capacity_wh < 154.272]
- `supersede` claim_a05b8beebeb8: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_e6ba1d0015f8: narrowed from claim_a05b8beebeb8: battery_capacity_wh < 70.7107
- `support` claim_e6ba1d0015f8: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_a99da078f4f1: reversed from claim_a05b8beebeb8: battery_capacity_wh >= 70.7107
- `support` claim_a99da078f4f1: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_e6ba1d0015f8: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_a99da078f4f1: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_9e0669d11d54: scope changed from [battery_capacity_wh >= 118.912] to [battery_capacity_wh >= 91.724]
- `rescope` claim_a3f1fc98e225: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 54.4922]
- `rescope` claim_8c28017d6b40: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 54.4922]
- `rescope` claim_00634540de79: scope changed from [battery_capacity_wh < 154.272] to [battery_capacity_wh < 135.374]
- `rescope` claim_e6ba1d0015f8: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 32.4037]
- `rescope` claim_a99da078f4f1: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 54.4922]
- `rescope` claim_a3f1fc98e225: scope changed from [battery_capacity_wh < 54.4922] to [battery_capacity_wh < 62.0737]
- `rescope` claim_8c28017d6b40: scope changed from [battery_capacity_wh >= 54.4922] to [battery_capacity_wh >= 62.0737]
- `rescope` claim_9e0669d11d54: scope changed from [battery_capacity_wh >= 91.724] to [battery_capacity_wh >= 80.5183]
- `refute` claim_79ccea55eecb: hypothesis -> refuted: 1 decisive test(s), none in favour
- `specialize` claim_548c5cd93f51: reversed from claim_79ccea55eecb: battery_capacity_wh >= 70.7107
- `support` claim_548c5cd93f51: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_548c5cd93f51: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_a99da078f4f1: scope changed from [battery_capacity_wh >= 54.4922] to [battery_capacity_wh >= 47.8435]
- `rescope` claim_e6ba1d0015f8: scope changed from [battery_capacity_wh < 32.4037] to [battery_capacity_wh < 36.889]
- `rescope` claim_548c5cd93f51: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `rescope` claim_548c5cd93f51: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 36.889]
- `rescope` claim_9e0669d11d54: scope changed from [battery_capacity_wh >= 80.5183] to [80.5183 <= battery_capacity_wh < 282.843]
- `rescope` claim_9e0669d11d54: scope changed from [80.5183 <= battery_capacity_wh < 282.843] to [80.5183 <= battery_capacity_wh < 237.908]
- `rescope` claim_9e0669d11d54: scope changed from [80.5183 <= battery_capacity_wh < 237.908] to [80.5183 <= battery_capacity_wh < 218.174]
- `rescope` claim_59337f2327c1: scope changed from [battery_capacity_wh < 135.374] to [battery_capacity_wh < 59.4559]
- `contest` claim_59337f2327c1: supported -> contested: the 2 test(s) in its region disagree and could not be separated
- `specialize` claim_0668ce9a5bc4: narrowed from claim_c14ac54b9caf: 59.4559 <= battery_capacity_wh < 135.374
- `support` claim_0668ce9a5bc4: hypothesis -> supported: 2 decisive test(s) in its region
- `rescope` claim_59337f2327c1: scope changed from [battery_capacity_wh < 59.4559] to [battery_capacity_wh < 42.0714]
- `support` claim_59337f2327c1: contested -> supported: 2 decisive test(s) in its region
- `rescope` claim_0668ce9a5bc4: scope changed from [59.4559 <= battery_capacity_wh < 135.374] to [42.0714 <= battery_capacity_wh < 135.374]
- `contest` claim_0668ce9a5bc4: supported -> contested: the 3 test(s) in its region disagree and could not be separated
- `rescope` claim_59337f2327c1: scope changed from [battery_capacity_wh < 42.0714] to [battery_capacity_wh < 54.5436]
- `contest` claim_59337f2327c1: supported -> contested: the 3 test(s) in its region disagree and could not be separated
- `rescope` claim_0668ce9a5bc4: scope changed from [42.0714 <= battery_capacity_wh < 135.374] to [54.5436 <= battery_capacity_wh < 135.374]
- `support` claim_0668ce9a5bc4: contested -> supported: 3 decisive test(s) in its region
- `rescope` claim_00634540de79: scope changed from [battery_capacity_wh < 135.374] to [battery_capacity_wh < 35.3553]
- `specialize` claim_b6e8a1514a7f: narrowed from claim_887b7adac740: 59.4559 <= battery_capacity_wh < 135.374
- `support` claim_b6e8a1514a7f: hypothesis -> supported: 2 decisive test(s) in its region
- `rescope` claim_00634540de79: scope changed from [battery_capacity_wh < 35.3553] to [battery_capacity_wh < 42.0714]
- `rescope` claim_b6e8a1514a7f: scope changed from [59.4559 <= battery_capacity_wh < 135.374] to [64.8587 <= battery_capacity_wh < 135.374]
- `rescope` claim_59337f2327c1: scope changed from [battery_capacity_wh < 54.5436] to [battery_capacity_wh < 45.8803]
- `support` claim_59337f2327c1: contested -> supported: 3 decisive test(s) in its region
- `rescope` claim_0668ce9a5bc4: scope changed from [54.5436 <= battery_capacity_wh < 135.374] to [45.8803 <= battery_capacity_wh < 135.374]
- `contest` claim_0668ce9a5bc4: supported -> contested: the 4 test(s) in its region disagree and could not be separated
- `rescope` claim_00634540de79: scope changed from [battery_capacity_wh < 42.0714] to [battery_capacity_wh < 45.8803]
- `rescope` claim_0668ce9a5bc4: scope changed from [45.8803 <= battery_capacity_wh < 135.374] to [54.5436 <= battery_capacity_wh < 135.374]
- `support` claim_0668ce9a5bc4: contested -> supported: 4 decisive test(s) in its region
- `rescope` claim_a99da078f4f1: scope changed from [battery_capacity_wh >= 47.8435] to [battery_capacity_wh >= 45.8258]

## Transfer: interpolation (inside the studied range)

4 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | failure rate |
|---|---|---|
| reference | +0.3050 | 19.5% |
| flat | +0.1031 | 43.0% |
| pooled | +0.4426 | 1.6% |
| conditional | +0.5979 | 1.6% |
| oracle | +0.6070 | 0.0% |

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.1553 [+0.1275, +0.1851], p = 0.0002
- conditional minus flat: +0.4948 [+0.3894, +0.6014], p = 0.0002
- conditional minus reference: +0.2929 [+0.2096, +0.3802], p = 0.0002
- pooled minus reference: +0.1376 [+0.0400, +0.2350], p = 0.0050
- flat minus reference: -0.2019 [-0.2969, -0.1128], p = 0.0002
- oracle minus conditional: +0.0091 [-0.0185, +0.0430], p = 0.5839

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=35 | -0.535 (75%) reference | -0.762 (94%) charge_below=0.1, desat_above=0.3 | +0.357 (6%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.357 (6%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.348 (0%) charge_below=0.6, desat_above=0.6 |
| battery_capacity_wh=70 | +0.424 (3%) reference | -0.368 (78%) charge_below=0.1, desat_above=0.3 | +0.460 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.575 (0%) charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.517 (0%) charge_below=0.25, desat_above=0.3 |
| battery_capacity_wh=140 | +0.584 (0%) reference | +0.718 (0%) charge_below=0.1, desat_above=0.3 | +0.465 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.636 (0%) desat_above=0.3 | +0.718 (0%) charge_below=0.1, desat_above=0.3 |
| battery_capacity_wh=280 | +0.747 (0%) reference | +0.825 (0%) charge_below=0.1, desat_above=0.3 | +0.489 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.825 (0%) charge_below=0.1, desat_above=0.3 | +0.846 (0%) charge_below=0.05, desat_above=0.3 |

## Transfer: extrapolation (outside the studied range)

2 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | failure rate |
|---|---|---|
| reference | -0.0167 | 48.4% |
| flat | -0.0322 | 50.0% |
| pooled | +0.2168 | 17.2% |
| conditional | +0.3768 | 20.3% |
| oracle | +0.4790 | 9.4% |

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.1599 [+0.0171, +0.2979], p = 0.0274
- conditional minus flat: +0.4090 [+0.2630, +0.5607], p = 0.0002
- conditional minus reference: +0.3935 [+0.2505, +0.5385], p = 0.0002
- pooled minus reference: +0.2336 [+0.0523, +0.4253], p = 0.0168
- flat minus reference: -0.0155 [-0.0663, +0.0279], p = 0.6285
- oracle minus conditional: +0.1022 [+0.0189, +0.1964], p = 0.0198

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=18 | -0.877 (97%) reference | -0.941 (100%) charge_below=0.1, desat_above=0.3 | -0.065 (34%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | -0.123 (41%) charge_below=0.6, charge_margin=0.25, precharge_below=0.6, precharge_window_s=900 | +0.080 (19%) charge_below=0.8, desat_above=0.6 |
| battery_capacity_wh=600 | +0.843 (0%) reference | +0.877 (0%) charge_below=0.1, desat_above=0.3 | +0.499 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.877 (0%) charge_below=0.1, desat_above=0.3 | +0.878 (0%) charge_below=0.05, desat_above=0.3 |

## Do the recommended settings still work together?

Every family was tested with only its own change. Here the reference policy, each recommended change on its own, and all of them together run on the same held-out seeds.

| conditions | reference | each change alone | all together | together minus reference | finding |
|---|---|---|---|---|---|
| battery_capacity_wh=35 | -0.535 | `precharge_below,precharge_window_s` -0.318; `desat_above` -0.393; `charge_margin` -0.358; `charge_below` +0.348 | +0.357 | +0.892 [+0.677, +1.097] | consistent |
| battery_capacity_wh=70 | +0.424 | `precharge_below,precharge_window_s` +0.493; `desat_above` +0.517; `charge_margin` +0.511 | +0.575 | +0.151 [+0.082, +0.245] | consistent |
| battery_capacity_wh=140 | +0.584 | `desat_above` +0.636 | +0.636 | +0.051 [+0.016, +0.082] | consistent |
| battery_capacity_wh=280 | +0.747 | `charge_below` +0.824; `desat_above` +0.760 | +0.825 | +0.077 [+0.027, +0.126] | consistent |
| battery_capacity_wh=18 | -0.877 | `precharge_below,precharge_window_s` -0.881; `charge_margin` -0.869; `charge_below` -0.158 | -0.123 | +0.753 [+0.527, +0.971] | consistent |
| battery_capacity_wh=600 | +0.843 | `charge_below` +0.899; `desat_above` +0.830 | +0.877 | +0.034 [-0.016, +0.089] | unhelpful change |

- battery_capacity_wh=600: on its own, `desat_above` (+0.830 against +0.843) scores below the reference here, so the claim behind it is being applied where it does not hold. All together is -0.022 [-0.048, -0.003] against `charge_below` alone.
