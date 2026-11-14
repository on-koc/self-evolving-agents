# Charging, desaturation and eclipse strategies across battery sizes (Basilisk / BSK-RL)

76 experiments in 20 rounds, 3056 simulator episodes (budget 4500).

**8 comparisons, 20 claims** (2 contested, 2 refuted, 6 superseded, 10 supported); 27 relations between claims.

## What the graph recommends, by condition

Settings that differ from the reference policy, in every region of conditions the supported claims tell apart. A dot keeps the reference value: either nothing was found to beat it there, or nothing could be established.

| battery_capacity_wh | `charge_below` | `charge_margin` | `desat_above` | `precharge_below` | `precharge_window_s` |
|---|---|---|---|---|---|
| below 28.46 | 0.6 | · | · | 0.6 | 900 |
| 28.46 to 36.89 | 0.6 | · | 0.3 | 0.6 | 900 |
| 36.89 to 62.07 | 0.4 | · | 0.3 | 0.6 | 900 |
| 62.07 to 77.11 | · | · | 0.3 | 0.6 | 900 |
| 77.11 to 129.5 | · | 0.25 | 0.3 | · | · |
| 129.5 to 175.5 | · | · | 0.3 | · | · |
| 175.5 to 366.6 | 0.1 | · | 0.3 | · | · |
| 366.6 and above | 0.1 | · | · | · | · |

## Claims by comparison

### A lower charge threshold collects more data.

Proposed by: seed (hand-written). Compares `charge_below` = 0.1 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | -0.014 | [-0.049, +0.013] | 16 | 16 / 16 |
| battery_capacity_wh=32.4 | no meaningful benefit | -0.070 | [-0.268, +0.014] | 16 | 16 / 15 |
| battery_capacity_wh=42 | baseline better | -0.389 | [-0.727, -0.096] | 16 | 16 / 11 |
| battery_capacity_wh=50 | baseline better | -0.837 | [-1.128, -0.531] | 16 | 16 / 5 |
| battery_capacity_wh=70.7 | baseline better | -1.105 | [-1.164, -1.050] | 16 | 16 / 0 |
| battery_capacity_wh=100 | baseline better | -0.701 | [-0.975, -0.388] | 16 | 11 / 0 |
| battery_capacity_wh=119 | baseline better | -0.379 | [-0.647, -0.113] | 16 | 7 / 0 |
| battery_capacity_wh=154 | unresolved (inconclusive at the maximum number of seeds) | +0.058 | [-0.027, +0.109] | 48 | 2 / 0 |
| battery_capacity_wh=200 | intervention better | +0.106 | [+0.072, +0.138] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.123 | [+0.049, +0.204] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh >= 175.499, use `charge_below` = 0.1 instead of 0.25.
- **supported** (reversed): where 36.889 <= battery_capacity_wh < 135.374, use `charge_below` = 0.25 instead of 0.1.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 36.889.
- Not established either way, so nothing is recommended, where: 135.374 <= battery_capacity_wh < 175.499.

Explanations (judged separately from the outcome):

- *less time is spent in charge mode* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 3693.75 with the intervention vs 5426.25 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400: supports. `time_charge_s`: 960 with the intervention vs 2895 without, over 16 of 16 seed pairs

### Topping up the battery before each eclipse improves the score.

Proposed by: seed (hand-written). Compares `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.113 | [+0.003, +0.254] | 48 | 43 / 47 |
| battery_capacity_wh=50 | intervention better | +0.169 | [+0.012, +0.334] | 48 | 8 / 14 |
| battery_capacity_wh=70.7 | intervention better | +0.060 | [+0.008, +0.160] | 32 | 0 / 1 |
| battery_capacity_wh=84.1 | unresolved (inconclusive at the maximum number of seeds) | +0.010 | [-0.055, +0.046] | 48 | 1 / 0 |
| battery_capacity_wh=100 | unresolved (inconclusive at the maximum number of seeds) | +0.004 | [-0.063, +0.039] | 48 | 1 / 0 |
| battery_capacity_wh=119 | intervention better | +0.030 | [+0.009, +0.051] | 32 | 0 / 0 |
| battery_capacity_wh=154 | intervention better | +0.022 | [+0.005, +0.040] | 48 | 0 / 0 |
| battery_capacity_wh=200 | unresolved (inconclusive at the maximum number of seeds) | +0.011 | [-0.010, +0.032] | 48 | 0 / 0 |
| battery_capacity_wh=238 | unresolved (inconclusive at the maximum number of seeds) | -0.002 | [-0.025, +0.021] | 48 | 0 / 0 |
| battery_capacity_wh=283 | no meaningful benefit | -0.034 | [-0.085, +0.012] | 16 | 0 / 0 |
| battery_capacity_wh=400 | no meaningful benefit | -0.041 | [-0.115, +0.010] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 77.1095, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- **contested** (narrowed): where 109.087 <= battery_capacity_wh < 259.526, use `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh >= 259.526.
- Not established either way, so nothing is recommended, where: 77.1095 <= battery_capacity_wh < 109.087.

Explanations (judged separately from the outcome):

- *the battery does not get as low* — **supported**
  - mediator test at battery_capacity_wh=25: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=70.7: supports. `min_battery`: 0.12998 with the intervention vs 0.09913 without, over 31 of 32 seed pairs
  - mediator test at battery_capacity_wh=119: supports. `min_battery`: 0.1922 with the intervention vs 0.16291 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=154: supports. `min_battery`: 0.21073 with the intervention vs 0.18739 without, over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=50: supports. `min_battery`: 0.10197 with the intervention vs 0.05546 without, over 32 of 48 seed pairs
- *it prevents battery depletion* — **refuted**
  - mediator test at battery_capacity_wh=25: inconclusive. `failure:battery`: 0.89583 with the intervention vs 0.97917 without, over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=70.7: inconclusive. `failure:battery`: 0 with the intervention vs 0.03125 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=119: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=154: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 48 of 48 seed pairs
  - mediator test at battery_capacity_wh=50: inconclusive. `failure:battery`: 0.16667 with the intervention vs 0.29167 without, over 48 of 48 seed pairs

### Unloading the reaction wheels early improves the score.

Proposed by: seed (hand-written). Compares `desat_above` = 0.3 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | -0.016 | [-0.040, +0.009] | 16 | 16 / 16 |
| battery_capacity_wh=32.4 | intervention better | +0.108 | [+0.007, +0.258] | 32 | 24 / 26 |
| battery_capacity_wh=42 | intervention better | +0.852 | [+0.494, +1.159] | 16 | 1 / 11 |
| battery_capacity_wh=50 | intervention better | +0.458 | [+0.160, +0.769] | 16 | 0 / 5 |
| battery_capacity_wh=70.7 | intervention better | +0.100 | [+0.057, +0.146] | 16 | 0 / 0 |
| battery_capacity_wh=100 | intervention better | +0.099 | [+0.048, +0.153] | 16 | 0 / 0 |
| battery_capacity_wh=200 | intervention better | +0.082 | [+0.041, +0.125] | 16 | 0 / 0 |
| battery_capacity_wh=283 | intervention better | +0.043 | [+0.008, +0.085] | 16 | 0 / 0 |
| battery_capacity_wh=336 | intervention better | +0.042 | [+0.003, +0.092] | 16 | 0 / 0 |
| battery_capacity_wh=400 | unresolved (inconclusive at the maximum number of seeds) | +0.019 | [+0.001, +0.041] | 48 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where 28.4605 <= battery_capacity_wh < 366.606, use `desat_above` = 0.3 instead of 0.6.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 28.4605.
- Not established either way, so nothing is recommended, where: battery_capacity_wh >= 366.606.

Explanations (judged separately from the outcome):

- *it prevents the wheels from reaching their speed limit* — **refuted**
  - mediator test at battery_capacity_wh=200: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=70.7: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=32.4: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=283: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=336: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
- *slower wheels draw less power, so less time is spent charging* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 3971.25 with the intervention vs 5426.25 without, over 16 of 16 seed pairs
  - moderator test at battery_capacity_wh=200: supports. effect by `max_wheel_speed_rpm`: 1500 -> -0.068, 3000 -> +0.013, 6000 -> +0.063
  - mediator test at battery_capacity_wh=70.7: supports. `time_charge_s`: 7485 with the intervention vs 9251.25 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=42: inconclusive. `time_charge_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=32.4: inconclusive. `time_charge_s`: 8300 with the intervention vs 9650 without, over 6 of 32 seed pairs
  - mediator test at battery_capacity_wh=283: supports. `time_charge_s`: 3045 with the intervention vs 3915 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=336: supports. `time_charge_s`: 2640 with the intervention vs 3472.5 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `time_charge_s`: 6577.5 with the intervention vs 8298.75 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: supports. `time_charge_s`: 8252.73 with the intervention vs 9796.36 without, over 11 of 16 seed pairs

### Charging in longer blocks improves the score.

Proposed by: seed (hand-written). Compares `charge_margin` = 0.25 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | +0.006 | [+0.001, +0.013] | 16 | 16 / 16 |
| battery_capacity_wh=32.4 | intervention better | +0.038 | [+0.007, +0.080] | 16 | 15 / 15 |
| battery_capacity_wh=42 | intervention better | +0.158 | [+0.011, +0.321] | 48 | 24 / 28 |
| battery_capacity_wh=50 | unresolved (inconclusive at the maximum number of seeds) | +0.168 | [-0.007, +0.339] | 48 | 10 / 14 |
| battery_capacity_wh=54.5 | intervention better | +0.139 | [+0.004, +0.286] | 48 | 8 / 11 |
| battery_capacity_wh=70.7 | unresolved (inconclusive at the maximum number of seeds) | +0.056 | [-0.031, +0.140] | 48 | 2 / 1 |
| battery_capacity_wh=84.1 | intervention better | +0.065 | [+0.010, +0.123] | 16 | 0 / 0 |
| battery_capacity_wh=100 | intervention better | +0.051 | [+0.012, +0.096] | 32 | 0 / 0 |
| battery_capacity_wh=119 | intervention better | +0.054 | [+0.017, +0.098] | 32 | 0 / 0 |
| battery_capacity_wh=141 | unresolved (inconclusive at the maximum number of seeds) | +0.027 | [-0.001, +0.057] | 48 | 0 / 0 |
| battery_capacity_wh=200 | unresolved (inconclusive at the maximum number of seeds) | +0.018 | [-0.010, +0.047] | 48 | 0 / 0 |
| battery_capacity_wh=400 | unresolved (inconclusive at the maximum number of seeds) | +0.007 | [-0.010, +0.027] | 48 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **contested** (narrowed): where 28.4605 <= battery_capacity_wh < 77.1095, use `charge_margin` = 0.25 instead of 0.
- **supported** (narrowed): where 77.1095 <= battery_capacity_wh < 129.534, use `charge_margin` = 0.25 instead of 0.
- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 28.4605.
- Not established either way, so nothing is recommended, where: battery_capacity_wh >= 129.534.

Explanations (judged separately from the outcome):

- *fewer mode switches waste less scan time on slewing and settling* — **supported**
  - mediator test at battery_capacity_wh=42: supports. `wasted_scan_s`: 434.222 with the intervention vs 905.444 without, over 18 of 48 seed pairs
  - mediator test at battery_capacity_wh=54.5: supports. `wasted_scan_s`: 376.571 with the intervention vs 859.429 without, over 35 of 48 seed pairs
  - mediator test at battery_capacity_wh=32.4: inconclusive. `wasted_scan_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=100: supports. `wasted_scan_s`: 439.031 with the intervention vs 870.094 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=84.1: supports. `wasted_scan_s`: 482.062 with the intervention vs 1046.19 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=119: supports. `wasted_scan_s`: 457.219 with the intervention vs 848.812 without, over 32 of 32 seed pairs

### Going further in the direction that helped keeps helping: charge_below=0.05 beats charge_below=0.1.

Proposed by: program. Compares `charge_below` = 0.05 instead of 0.1.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | no meaningful benefit | +0.003 | [+0.001, +0.006] | 16 | 16 / 16 |
| battery_capacity_wh=50 | no meaningful benefit | -0.005 | [-0.032, +0.014] | 16 | 16 / 16 |
| battery_capacity_wh=100 | no meaningful benefit | -0.271 | [-0.568, +0.007] | 16 | 15 / 11 |
| battery_capacity_wh=200 | no meaningful benefit | -0.099 | [-0.217, +0.005] | 48 | 6 / 0 |
| battery_capacity_wh=238 | unresolved (inconclusive at the maximum number of seeds) | -0.059 | [-0.166, +0.024] | 48 | 4 / 0 |
| battery_capacity_wh=283 | unresolved (inconclusive at the maximum number of seeds) | +0.005 | [-0.054, +0.034] | 48 | 1 / 0 |
| battery_capacity_wh=400 | unresolved (inconclusive at the maximum number of seeds) | +0.011 | [+0.003, +0.021] | 48 | 0 / 0 |

**Original claim: refuted.** Did not hold anywhere it was tested.

- No meaningful benefit, so nothing is recommended, where: battery_capacity_wh < 218.174.
- Not established either way, so nothing is recommended, where: battery_capacity_wh >= 218.174.

### Neither tested setting is acceptable here; a setting further out does better: charge_below=0.4 beats charge_below=0.25.

Proposed by: program. Compares `charge_below` = 0.4 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.319 | [+0.124, +0.537] | 32 | 23 / 31 |
| battery_capacity_wh=42 | intervention better | +0.706 | [+0.351, +1.007] | 16 | 1 / 11 |
| battery_capacity_wh=50 | intervention better | +0.313 | [+0.037, +0.604] | 16 | 0 / 5 |
| battery_capacity_wh=54.5 | intervention better | +0.297 | [+0.019, +0.615] | 16 | 0 / 5 |
| battery_capacity_wh=70.7 | baseline better | -0.038 | [-0.052, -0.020] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.069 | [-0.089, -0.050] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.115 | [-0.142, -0.083] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.144 | [-0.225, -0.062] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 62.0737, use `charge_below` = 0.4 instead of 0.25.
- **supported** (reversed): where battery_capacity_wh >= 62.0737, use `charge_below` = 0.25 instead of 0.4.

### Going further in the direction that helped keeps helping: charge_below=0.6 beats charge_below=0.4.

Proposed by: program. Compares `charge_below` = 0.6 instead of 0.4.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.976 | [+0.683, +1.208] | 16 | 2 / 15 |
| battery_capacity_wh=32.4 | intervention better | +0.783 | [+0.451, +1.070] | 16 | 0 / 11 |
| battery_capacity_wh=42 | unresolved (inconclusive at the maximum number of seeds) | +0.032 | [-0.025, +0.124] | 48 | 0 / 2 |
| battery_capacity_wh=50 | no meaningful benefit | -0.032 | [-0.065, +0.000] | 16 | 0 / 0 |
| battery_capacity_wh=54.5 | no meaningful benefit | -0.022 | [-0.049, +0.006] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.056 | [-0.075, -0.039] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.078 | [-0.107, -0.046] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.143 | [-0.185, -0.106] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.188 | [-0.258, -0.117] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 36.889, use `charge_below` = 0.6 instead of 0.4.
- **supported** (reversed): where battery_capacity_wh >= 62.0737, use `charge_below` = 0.4 instead of 0.6.
- No meaningful benefit, so nothing is recommended, where: 45.8258 <= battery_capacity_wh < 62.0737.
- Not established either way, so nothing is recommended, where: 36.889 <= battery_capacity_wh < 45.8258.

### Going further in the direction that helped keeps helping: charge_below=0.8 beats charge_below=0.6.

Proposed by: program. Compares `charge_below` = 0.8 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | unresolved (inconclusive at the maximum number of seeds) | +0.050 | [-0.024, +0.150] | 48 | 2 / 5 |
| battery_capacity_wh=32.4 | no meaningful benefit | -0.019 | [-0.042, +0.003] | 16 | 0 / 0 |
| battery_capacity_wh=42 | baseline better | -0.032 | [-0.049, -0.015] | 16 | 0 / 0 |
| battery_capacity_wh=50 | baseline better | -0.029 | [-0.048, -0.009] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.059 | [-0.094, -0.027] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.059 | [-0.097, -0.025] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.135 | [-0.173, -0.095] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.236 | [-0.307, -0.169] | 16 | 0 / 0 |

**Original claim: refuted.** Did not hold anywhere it was tested.

- **supported** (reversed): where battery_capacity_wh >= 36.889, use `charge_below` = 0.6 instead of 0.8.
- No meaningful benefit, so nothing is recommended, where: 28.4605 <= battery_capacity_wh < 36.889.
- Not established either way, so nothing is recommended, where: battery_capacity_wh < 28.4605.

## Revision history

- `propose` claim_a1fe21f8ec3c: proposed
- `propose` claim_6d556c97cc97: proposed
- `propose` claim_1dce0f28d7d7: proposed
- `propose` claim_c54a7322b419: proposed
- `support` claim_a1fe21f8ec3c: hypothesis -> supported: 1 decisive test(s), all in favour
- `support` claim_1dce0f28d7d7: hypothesis -> supported: 1 decisive test(s), all in favour
- `propose` claim_da033d146bc7: keep-going rule, from claim_a1fe21f8ec3c, along the charge_below ladder
- `refute` claim_da033d146bc7: hypothesis -> refuted: 1 decisive test(s), none in favour
- `supersede` claim_a1fe21f8ec3c: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_31eeb6decc3c: narrowed from claim_a1fe21f8ec3c: battery_capacity_wh >= 70.7107
- `support` claim_31eeb6decc3c: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_6d556c97cc97: hypothesis -> superseded: established in only part of its scope; replaced by narrower claims
- `specialize` claim_a156716ad3a7: narrowed from claim_6d556c97cc97: battery_capacity_wh < 70.7107
- `support` claim_a156716ad3a7: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_5ebcea957ecd: nothing-works-here rule, from claim_a1fe21f8ec3c, along the charge_below ladder
- `support` claim_5ebcea957ecd: hypothesis -> supported: 1 decisive test(s), all in favour
- `specialize` claim_06165d06b254: reversed from claim_a1fe21f8ec3c: 42.0416 <= battery_capacity_wh < 118.912
- `support` claim_06165d06b254: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_31eeb6decc3c: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 118.912]
- `rescope` claim_a156716ad3a7: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 118.912]
- `supersede` claim_1dce0f28d7d7: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_6f78df4f4155: narrowed from claim_1dce0f28d7d7: battery_capacity_wh >= 70.7107
- `support` claim_6f78df4f4155: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_83dd9558ff24: keep-going rule, from claim_5ebcea957ecd, along the charge_below ladder
- `support` claim_83dd9558ff24: hypothesis -> supported: 1 decisive test(s), all in favour
- `rescope` claim_6f78df4f4155: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_06165d06b254: scope changed from [42.0416 <= battery_capacity_wh < 118.912] to [42.0416 <= battery_capacity_wh < 154.272]
- `rescope` claim_31eeb6decc3c: scope changed from [battery_capacity_wh >= 118.912] to [battery_capacity_wh >= 154.272]
- `rescope` claim_a156716ad3a7: scope changed from [battery_capacity_wh < 118.912] to [battery_capacity_wh < 154.272]
- `propose` claim_bf7a4a459b16: keep-going rule, from claim_83dd9558ff24, along the charge_below ladder
- `rescope` claim_06165d06b254: scope changed from [42.0416 <= battery_capacity_wh < 154.272] to [32.4037 <= battery_capacity_wh < 154.272]
- `rescope` claim_6f78df4f4155: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `rescope` claim_06165d06b254: scope changed from [32.4037 <= battery_capacity_wh < 154.272] to [32.4037 <= battery_capacity_wh < 135.374]
- `rescope` claim_31eeb6decc3c: scope changed from [battery_capacity_wh >= 154.272] to [battery_capacity_wh >= 175.499]
- `rescope` claim_a156716ad3a7: scope changed from [battery_capacity_wh < 154.272] to [battery_capacity_wh < 175.499]
- `rescope` claim_06165d06b254: scope changed from [32.4037 <= battery_capacity_wh < 135.374] to [36.889 <= battery_capacity_wh < 135.374]
- `rescope` claim_6f78df4f4155: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 28.4605]
- `refute` claim_c54a7322b419: hypothesis -> refuted: 1 decisive test(s), none in favour
- `supersede` claim_5ebcea957ecd: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_ca2db2affd8a: narrowed from claim_5ebcea957ecd: battery_capacity_wh < 70.7107
- `support` claim_ca2db2affd8a: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_ddbed9233ccf: reversed from claim_5ebcea957ecd: battery_capacity_wh >= 70.7107
- `support` claim_ddbed9233ccf: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_ca2db2affd8a: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_ddbed9233ccf: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `supersede` claim_c54a7322b419: refuted -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_b4a3559feb5b: narrowed from claim_c54a7322b419: 32.4037 <= battery_capacity_wh < 54.4922
- `support` claim_b4a3559feb5b: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_83dd9558ff24: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_3560797326f6: narrowed from claim_83dd9558ff24: battery_capacity_wh < 70.7107
- `support` claim_3560797326f6: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_7c9b71687cd6: reversed from claim_83dd9558ff24: battery_capacity_wh >= 70.7107
- `support` claim_7c9b71687cd6: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_3560797326f6: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_7c9b71687cd6: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_ca2db2affd8a: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 54.4922]
- `rescope` claim_ddbed9233ccf: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 54.4922]
- `rescope` claim_b4a3559feb5b: scope changed from [32.4037 <= battery_capacity_wh < 54.4922] to [32.4037 <= battery_capacity_wh < 62.0737]
- `rescope` claim_b4a3559feb5b: scope changed from [32.4037 <= battery_capacity_wh < 62.0737] to [28.4605 <= battery_capacity_wh < 62.0737]
- `rescope` claim_3560797326f6: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 32.4037]
- `rescope` claim_7c9b71687cd6: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 54.4922]
- `rescope` claim_ca2db2affd8a: scope changed from [battery_capacity_wh < 54.4922] to [battery_capacity_wh < 62.0737]
- `rescope` claim_ddbed9233ccf: scope changed from [battery_capacity_wh >= 54.4922] to [battery_capacity_wh >= 62.0737]
- `refute` claim_bf7a4a459b16: hypothesis -> refuted: 1 decisive test(s), none in favour
- `specialize` claim_b3b579a1092d: reversed from claim_bf7a4a459b16: battery_capacity_wh >= 70.7107
- `support` claim_b3b579a1092d: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_b3b579a1092d: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_7c9b71687cd6: scope changed from [battery_capacity_wh >= 54.4922] to [battery_capacity_wh >= 62.0737]
- `rescope` claim_3560797326f6: scope changed from [battery_capacity_wh < 32.4037] to [battery_capacity_wh < 36.889]
- `rescope` claim_b3b579a1092d: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 32.4037]
- `rescope` claim_6f78df4f4155: scope changed from [battery_capacity_wh >= 28.4605] to [28.4605 <= battery_capacity_wh < 282.843]
- `rescope` claim_6f78df4f4155: scope changed from [28.4605 <= battery_capacity_wh < 282.843] to [28.4605 <= battery_capacity_wh < 336.452]
- `rescope` claim_b3b579a1092d: scope changed from [battery_capacity_wh >= 32.4037] to [battery_capacity_wh >= 36.889]
- `rescope` claim_6f78df4f4155: scope changed from [28.4605 <= battery_capacity_wh < 336.452] to [28.4605 <= battery_capacity_wh < 366.606]
- `specialize` claim_9fbf97cd817f: narrowed from claim_c54a7322b419: 84.0833 <= battery_capacity_wh < 141.421
- `support` claim_9fbf97cd817f: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_9fbf97cd817f: scope changed from [84.0833 <= battery_capacity_wh < 141.421] to [62.0737 <= battery_capacity_wh < 118.743]
- `contest` claim_9fbf97cd817f: supported -> contested: the 2 test(s) in its region disagree and could not be separated
- `rescope` claim_9fbf97cd817f: scope changed from [62.0737 <= battery_capacity_wh < 118.743] to [62.0737 <= battery_capacity_wh < 129.534]
- `rescope` claim_a156716ad3a7: scope changed from [battery_capacity_wh < 175.499] to [battery_capacity_wh < 84.0833]
- `specialize` claim_9a4db5f55f4e: narrowed from claim_6d556c97cc97: 109.087 <= battery_capacity_wh < 175.499
- `support` claim_9a4db5f55f4e: hypothesis -> supported: 2 decisive test(s) in its region
- `rescope` claim_a156716ad3a7: scope changed from [battery_capacity_wh < 84.0833] to [battery_capacity_wh < 77.1095]
- `rescope` claim_9a4db5f55f4e: scope changed from [109.087 <= battery_capacity_wh < 175.499] to [109.087 <= battery_capacity_wh < 259.526]
- `contest` claim_9a4db5f55f4e: supported -> contested: the 4 test(s) in its region disagree and could not be separated
- `rescope` claim_b4a3559feb5b: scope changed from [28.4605 <= battery_capacity_wh < 62.0737] to [28.4605 <= battery_capacity_wh < 77.1095]
- `contest` claim_b4a3559feb5b: supported -> contested: the 5 test(s) in its region disagree and could not be separated
- `rescope` claim_9fbf97cd817f: scope changed from [62.0737 <= battery_capacity_wh < 129.534] to [77.1095 <= battery_capacity_wh < 129.534]
- `support` claim_9fbf97cd817f: contested -> supported: 3 decisive test(s) in its region

## Transfer: interpolation (inside the studied range)

4 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | spacecraft lost | success rate |
|---|---|---|---|
| reference | +0.3050 | 19.5% | 78.1% |
| flat | +0.1031 | 43.0% | 57.0% |
| pooled | +0.4426 | 1.6% | 93.0% |
| conditional | +0.5921 | 1.6% | 97.7% |
| oracle | +0.6070 | 0.0% | 95.3% |

Success: the spacecraft survived and recorded data for at least 20% of the episode (`docs/metrics.md`, 2.3).

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.1495 [+0.1196, +0.1813], p = 0.0002; resampling whole seeds: [+0.1275, +0.1711], p = 0.0002
- conditional minus flat: +0.4890 [+0.3850, +0.5956], p = 0.0002; resampling whole seeds: [+0.4180, +0.5481], p = 0.0002
- conditional minus reference: +0.2871 [+0.2061, +0.3704], p = 0.0002; resampling whole seeds: [+0.2209, +0.3490], p = 0.0002
- pooled minus reference: +0.1376 [+0.0400, +0.2350], p = 0.0050; resampling whole seeds: [+0.0714, +0.2010], p = 0.0010
- flat minus reference: -0.2019 [-0.2969, -0.1128], p = 0.0002; resampling whole seeds: [-0.2697, -0.1306], p = 0.0002
- oracle minus conditional: +0.0149 [-0.0109, +0.0472], p = 0.3743; resampling whole seeds: [-0.0088, +0.0483], p = 0.4585

The first interval treats every (condition, seed) episode pair as independent. The second averages over the conditions first and resamples the 32 seeds, because every condition reuses the same seeds.

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=35 | -0.535 (75%) reference | -0.762 (94%) charge_below=0.1, desat_above=0.3 | +0.357 (6%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.319 (6%) charge_below=0.6, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.348 (0%) charge_below=0.6, desat_above=0.6 |
| battery_capacity_wh=70 | +0.424 (3%) reference | -0.368 (78%) charge_below=0.1, desat_above=0.3 | +0.460 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.589 (0%) desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.517 (0%) charge_below=0.25, desat_above=0.3 |
| battery_capacity_wh=140 | +0.584 (0%) reference | +0.718 (0%) charge_below=0.1, desat_above=0.3 | +0.465 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.636 (0%) desat_above=0.3 | +0.718 (0%) charge_below=0.1, desat_above=0.3 |
| battery_capacity_wh=280 | +0.747 (0%) reference | +0.825 (0%) charge_below=0.1, desat_above=0.3 | +0.489 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.825 (0%) charge_below=0.1, desat_above=0.3 | +0.846 (0%) charge_below=0.05, desat_above=0.3 |

## Transfer: extrapolation (outside the studied range)

2 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | spacecraft lost | success rate |
|---|---|---|---|
| reference | -0.0167 | 48.4% | 51.6% |
| flat | -0.0322 | 50.0% | 50.0% |
| pooled | +0.2168 | 17.2% | 65.6% |
| conditional | +0.3704 | 20.3% | 73.4% |
| oracle | +0.4790 | 9.4% | 82.8% |

Success: the spacecraft survived and recorded data for at least 20% of the episode (`docs/metrics.md`, 2.3).

Paired differences over the same (condition, seed) episodes:

- conditional minus pooled: +0.1536 [-0.0044, +0.3102], p = 0.0742; resampling whole seeds: [-0.0157, +0.3148], p = 0.0808
- conditional minus flat: +0.4026 [+0.2642, +0.5476], p = 0.0002; resampling whole seeds: [+0.2916, +0.5122], p = 0.0002
- conditional minus reference: +0.3872 [+0.2546, +0.5293], p = 0.0002; resampling whole seeds: [+0.2788, +0.4897], p = 0.0002
- pooled minus reference: +0.2336 [+0.0523, +0.4253], p = 0.0168; resampling whole seeds: [+0.0892, +0.3713], p = 0.0038
- flat minus reference: -0.0155 [-0.0663, +0.0279], p = 0.6285; resampling whole seeds: [-0.0700, +0.0268], p = 0.6335
- oracle minus conditional: +0.1085 [+0.0093, +0.2177], p = 0.0430; resampling whole seeds: [+0.0133, +0.2056], p = 0.0376

The first interval treats every (condition, seed) episode pair as independent. The second averages over the conditions first and resamples the 32 seeds, because every condition reuses the same seeds.

Per condition (mean score, failure rate, settings used):

| conditions | reference | flat | pooled | conditional | oracle |
|---|---|---|---|---|---|
| battery_capacity_wh=18 | -0.877 (97%) reference | -0.941 (100%) charge_below=0.1, desat_above=0.3 | -0.065 (34%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | -0.158 (41%) charge_below=0.6, precharge_below=0.6, precharge_window_s=900 | +0.080 (19%) charge_below=0.8, desat_above=0.6 |
| battery_capacity_wh=600 | +0.843 (0%) reference | +0.877 (0%) charge_below=0.1, desat_above=0.3 | +0.499 (0%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.899 (0%) charge_below=0.1 | +0.878 (0%) charge_below=0.05, desat_above=0.3 |

## Do the recommended settings still work together?

Every family was tested with only its own change. Here the reference policy, each recommended change on its own, and all of them together run on the same held-out seeds.

| conditions | reference | each change alone | all together | together minus reference | finding |
|---|---|---|---|---|---|
| battery_capacity_wh=35 | -0.535 | `precharge_below,precharge_window_s` -0.318; `desat_above` -0.393; `charge_below` +0.348 | +0.319 | +0.855 [+0.644, +1.056] | negative interaction |
| battery_capacity_wh=70 | +0.424 | `precharge_below,precharge_window_s` +0.493; `desat_above` +0.517 | +0.589 | +0.165 [+0.108, +0.253] | consistent |
| battery_capacity_wh=140 | +0.584 | `desat_above` +0.636 | +0.636 | +0.051 [+0.016, +0.082] | consistent |
| battery_capacity_wh=280 | +0.747 | `charge_below` +0.824; `desat_above` +0.760 | +0.825 | +0.077 [+0.027, +0.126] | consistent |
| battery_capacity_wh=18 | -0.877 | `precharge_below,precharge_window_s` -0.881; `charge_below` -0.158 | -0.158 | +0.719 [+0.500, +0.927] | consistent |
| battery_capacity_wh=600 | +0.843 | `charge_below` +0.899 | +0.899 | +0.056 [+0.019, +0.100] | consistent |

- battery_capacity_wh=35: every change is at least as good as the reference on its own, but together they score below the best of them. All together is -0.029 [-0.154, +0.060] against `charge_below` alone.
