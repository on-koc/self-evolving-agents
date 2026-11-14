# Charging, desaturation and eclipse strategies across battery sizes (Basilisk / BSK-RL)

51 experiments in 15 rounds, 2208 simulator episodes (budget 4500).

**8 comparisons, 16 claims** (2 refuted, 3 superseded, 11 supported); 19 relations between claims.

## Claims by comparison

### A lower charge threshold collects more data.

Proposed by: seed (hand-written). Compares `charge_below` = 0.1 instead of 0.25.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | inconclusive | -0.024 | [-0.095, +0.009] | 48 | 47 / 46 |
| battery_capacity_wh=50 | baseline better | -1.010 | [-1.215, -0.745] | 16 | 16 / 3 |
| battery_capacity_wh=100 | baseline better | -0.344 | [-0.648, -0.059] | 16 | 6 / 0 |
| battery_capacity_wh=141 | inconclusive | -0.066 | [-0.193, +0.045] | 48 | 7 / 0 |
| battery_capacity_wh=200 | intervention better | +0.092 | [+0.062, +0.120] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.055 | [+0.009, +0.113] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (reversed): where battery_capacity_wh < 141.421, use `charge_below` = 0.25 instead of 0.1.
- **supported** (narrowed): where battery_capacity_wh >= 141.421, use `charge_below` = 0.1 instead of 0.25.

Explanations (judged separately from the outcome):

- *less time is spent in charge mode* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 2636.25 with the intervention vs 4125 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400: supports. `time_charge_s`: 1267.5 with the intervention vs 2141.25 without, over 16 of 16 seed pairs

### Topping up the battery before each eclipse improves the score.

Proposed by: seed (hand-written). Compares `precharge_below` = 0.6 instead of 0, `precharge_window_s` = 900 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.129 | [+0.002, +0.306] | 32 | 28 / 31 |
| battery_capacity_wh=50 | inconclusive | +0.072 | [-0.068, +0.215] | 48 | 12 / 14 |
| battery_capacity_wh=100 | intervention better | +0.034 | [+0.006, +0.061] | 16 | 0 / 0 |
| battery_capacity_wh=200 | inconclusive | -0.003 | [-0.023, +0.017] | 48 | 0 / 0 |
| battery_capacity_wh=400 | inconclusive | -0.021 | [-0.045, +0.000] | 48 | 0 / 0 |

**Original claim: supported.** Holds everywhere it was tested.

Explanations (judged separately from the outcome):

- *the battery does not get as low* — **supported**
  - mediator test at battery_capacity_wh=25: inconclusive. `min_battery`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=100: supports. `min_battery`: 0.18141 with the intervention vs 0.1485 without, over 16 of 16 seed pairs
- *it prevents battery depletion* — **refuted**
  - mediator test at battery_capacity_wh=25: inconclusive. `failure:battery`: 0.875 with the intervention vs 0.96875 without, over 32 of 32 seed pairs
  - mediator test at battery_capacity_wh=100: contradicts. `failure:battery`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs

### Unloading the reaction wheels early improves the score.

Proposed by: seed (hand-written). Compares `desat_above` = 0.3 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | inconclusive | +0.040 | [-0.022, +0.145] | 48 | 44 / 46 |
| battery_capacity_wh=50 | intervention better | +0.254 | [+0.037, +0.541] | 16 | 0 / 3 |
| battery_capacity_wh=100 | intervention better | +0.056 | [+0.020, +0.093] | 16 | 0 / 0 |
| battery_capacity_wh=200 | intervention better | +0.048 | [+0.022, +0.080] | 16 | 0 / 0 |
| battery_capacity_wh=400 | intervention better | +0.026 | [+0.005, +0.049] | 48 | 0 / 0 |

**Original claim: supported.** Holds everywhere it was tested.

Explanations (judged separately from the outcome):

- *it prevents the wheels from reaching their speed limit* — **refuted**
  - mediator test at battery_capacity_wh=200: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=50: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400: contradicts. `failure:wheels`: 0 with the intervention vs 0 without (identical in every seed), over 48 of 48 seed pairs
- *slower wheels draw less power, so less time is spent charging* — **supported**
  - mediator test at battery_capacity_wh=200: supports. `time_charge_s`: 3318.75 with the intervention vs 4125 without, over 16 of 16 seed pairs
  - moderator test at battery_capacity_wh=200: supports. effect by `max_wheel_speed_rpm`: 1500 -> -0.070, 3000 -> +0.006, 6000 -> +0.041
  - mediator test at battery_capacity_wh=50: supports. `time_charge_s`: 7818.46 with the intervention vs 8649.23 without, over 13 of 16 seed pairs
  - mediator test at battery_capacity_wh=100: supports. `time_charge_s`: 6228.75 with the intervention vs 7188.75 without, over 16 of 16 seed pairs
  - mediator test at battery_capacity_wh=400: supports. `time_charge_s`: 1981.25 with the intervention vs 2523.75 without, over 48 of 48 seed pairs

### Charging in longer blocks improves the score.

Proposed by: seed (hand-written). Compares `charge_margin` = 0.25 instead of 0.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | intervention better | +0.024 | [+0.001, +0.075] | 16 | 16 / 16 |
| battery_capacity_wh=50 | inconclusive | +0.095 | [-0.022, +0.223] | 48 | 13 / 14 |
| battery_capacity_wh=100 | intervention better | +0.048 | [+0.003, +0.104] | 16 | 0 / 0 |
| battery_capacity_wh=200 | inconclusive | +0.028 | [-0.011, +0.062] | 48 | 0 / 0 |
| battery_capacity_wh=400 | inconclusive | -0.001 | [-0.039, +0.031] | 48 | 0 / 0 |

**Original claim: supported.** Holds everywhere it was tested.

Explanations (judged separately from the outcome):

- *fewer mode switches waste less scan time on slewing and settling* — **supported**
  - mediator test at battery_capacity_wh=25: inconclusive. `wasted_scan_s`: too few seeds on which both arms completed the episode
  - mediator test at battery_capacity_wh=100: supports. `wasted_scan_s`: 371.625 with the intervention vs 837.188 without, over 16 of 16 seed pairs

### Going further in the direction that helped keeps helping: charge_below=0.05 beats charge_below=0.1.

Proposed by: program. Compares `charge_below` = 0.05 instead of 0.1.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | inconclusive | -0.034 | [-0.125, +0.005] | 48 | 48 / 47 |
| battery_capacity_wh=50 | no meaningful difference | -0.001 | [-0.015, +0.010] | 48 | 46 / 46 |
| battery_capacity_wh=70.7 | inconclusive | -0.009 | [-0.027, +0.008] | 48 | 46 / 46 |
| battery_capacity_wh=100 | baseline better | -0.562 | [-0.877, -0.256] | 16 | 14 / 6 |
| battery_capacity_wh=200 | baseline better | -0.144 | [-0.309, -0.012] | 32 | 5 / 0 |
| battery_capacity_wh=283 | inconclusive | +0.003 | [-0.059, +0.032] | 48 | 1 / 0 |
| battery_capacity_wh=400 | no meaningful difference | +0.006 | [+0.000, +0.018] | 16 | 0 / 0 |

**Original claim: refuted.** Did not hold anywhere it was tested.

- **supported** (reversed): where 70.7107 <= battery_capacity_wh < 282.843, use `charge_below` = 0.1 instead of 0.05.
- No meaningful difference where: battery_capacity_wh < 70.7107; battery_capacity_wh >= 282.843.

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
| battery_capacity_wh=35.4 | intervention better | +0.189 | [+0.056, +0.343] | 48 | 1 / 10 |
| battery_capacity_wh=42 | inconclusive | +0.048 | [-0.029, +0.153] | 48 | 0 / 3 |
| battery_capacity_wh=42.1 | inconclusive | +0.047 | [-0.030, +0.152] | 48 | 0 / 3 |
| battery_capacity_wh=50 | baseline better | -0.030 | [-0.041, -0.018] | 16 | 0 / 0 |
| battery_capacity_wh=70.7 | baseline better | -0.050 | [-0.069, -0.032] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.087 | [-0.116, -0.063] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.163 | [-0.192, -0.129] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.223 | [-0.287, -0.157] | 16 | 0 / 0 |

**Original claim: superseded.** Too general as stated; replaced by the narrower claims below.

- **supported** (narrowed): where battery_capacity_wh < 42.0714, use `charge_below` = 0.6 instead of 0.4.
- **supported** (reversed): where battery_capacity_wh >= 42.0714, use `charge_below` = 0.4 instead of 0.6.

### Going further in the direction that helped keeps helping: charge_below=0.8 beats charge_below=0.6.

Proposed by: program. Compares `charge_below` = 0.8 instead of 0.6.

| conditions | result | effect on score | 95%+ interval | seeds | failures (intervention / baseline) |
|---|---|---|---|---|---|
| battery_capacity_wh=25 | inconclusive | +0.143 | [-0.028, +0.324] | 48 | 3 / 9 |
| battery_capacity_wh=50 | baseline better | -0.027 | [-0.042, -0.012] | 16 | 0 / 0 |
| battery_capacity_wh=100 | baseline better | -0.074 | [-0.126, -0.034] | 16 | 0 / 0 |
| battery_capacity_wh=200 | baseline better | -0.139 | [-0.185, -0.094] | 16 | 0 / 0 |
| battery_capacity_wh=400 | baseline better | -0.255 | [-0.317, -0.190] | 16 | 0 / 0 |

**Original claim: refuted.** Did not hold anywhere it was tested.

- **supported** (reversed): where all tested conditions, use `charge_below` = 0.6 instead of 0.8.

## Revision history

- `propose` claim_86195822c600: proposed
- `propose` claim_e30852c4c952: proposed
- `propose` claim_02c6b490235d: proposed
- `propose` claim_e60f5d1e9baf: proposed
- `support` claim_86195822c600: hypothesis -> supported: 1 decisive test(s), all in favour
- `support` claim_02c6b490235d: hypothesis -> supported: 1 decisive test(s), all in favour
- `propose` claim_4094c769cdea: keep-going rule, from claim_86195822c600, along the charge_below ladder
- `refute` claim_4094c769cdea: hypothesis -> refuted: 1 decisive test(s), none in favour
- `specialize` claim_a5484dc6ec82: reversed from claim_4094c769cdea: all tested conditions
- `support` claim_a5484dc6ec82: hypothesis -> supported: 1 decisive test(s) in its region
- `support` claim_e30852c4c952: hypothesis -> supported: 1 decisive test(s), all in favour
- `propose` claim_606ee63842e4: nothing-works-here rule, from claim_86195822c600, along the charge_below ladder
- `support` claim_606ee63842e4: hypothesis -> supported: 1 decisive test(s), all in favour
- `support` claim_e60f5d1e9baf: hypothesis -> supported: 1 decisive test(s), all in favour
- `propose` claim_ffc92424e8fe: keep-going rule, from claim_606ee63842e4, along the charge_below ladder
- `support` claim_ffc92424e8fe: hypothesis -> supported: 1 decisive test(s), all in favour
- `supersede` claim_606ee63842e4: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_770674116107: narrowed from claim_606ee63842e4: battery_capacity_wh < 70.7107
- `support` claim_770674116107: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_29aaa57cbe4c: reversed from claim_606ee63842e4: battery_capacity_wh >= 70.7107
- `support` claim_29aaa57cbe4c: hypothesis -> supported: 1 decisive test(s) in its region
- `supersede` claim_86195822c600: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_83412a8f9fb9: reversed from claim_86195822c600: battery_capacity_wh < 100
- `support` claim_83412a8f9fb9: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_85a2d1cd0a3a: narrowed from claim_86195822c600: battery_capacity_wh >= 100
- `support` claim_85a2d1cd0a3a: hypothesis -> supported: 1 decisive test(s) in its region
- `propose` claim_e0684f8a5c97: keep-going rule, from claim_ffc92424e8fe, along the charge_below ladder
- `rescope` claim_770674116107: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_29aaa57cbe4c: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_83412a8f9fb9: scope changed from [battery_capacity_wh < 100] to [battery_capacity_wh < 141.421]
- `rescope` claim_85a2d1cd0a3a: scope changed from [battery_capacity_wh >= 100] to [battery_capacity_wh >= 141.421]
- `supersede` claim_ffc92424e8fe: supported -> superseded: evidence disagrees across conditions; replaced by narrower claims
- `specialize` claim_0e274264ebb3: narrowed from claim_ffc92424e8fe: battery_capacity_wh < 70.7107
- `support` claim_0e274264ebb3: hypothesis -> supported: 1 decisive test(s) in its region
- `specialize` claim_2aa057d25036: reversed from claim_ffc92424e8fe: battery_capacity_wh >= 70.7107
- `support` claim_2aa057d25036: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_0e274264ebb3: scope changed from [battery_capacity_wh < 70.7107] to [battery_capacity_wh < 42.0416]
- `rescope` claim_2aa057d25036: scope changed from [battery_capacity_wh >= 70.7107] to [battery_capacity_wh >= 42.0416]
- `rescope` claim_770674116107: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 54.4922]
- `rescope` claim_29aaa57cbe4c: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 54.4922]
- `refute` claim_e0684f8a5c97: hypothesis -> refuted: 1 decisive test(s), none in favour
- `specialize` claim_0268cac8db4e: reversed from claim_e0684f8a5c97: all tested conditions
- `support` claim_0268cac8db4e: hypothesis -> supported: 1 decisive test(s) in its region
- `rescope` claim_770674116107: scope changed from [battery_capacity_wh < 54.4922] to [battery_capacity_wh < 62.0737]
- `rescope` claim_29aaa57cbe4c: scope changed from [battery_capacity_wh >= 54.4922] to [battery_capacity_wh >= 62.0737]
- `rescope` claim_a5484dc6ec82: scope changed from [all tested conditions] to [battery_capacity_wh >= 100]
- `rescope` claim_a5484dc6ec82: scope changed from [battery_capacity_wh >= 100] to [battery_capacity_wh >= 70.7107]
- `rescope` claim_a5484dc6ec82: scope changed from [battery_capacity_wh >= 70.7107] to [70.7107 <= battery_capacity_wh < 282.843]
- `rescope` claim_0e274264ebb3: scope changed from [battery_capacity_wh < 42.0416] to [battery_capacity_wh < 35.3553]
- `rescope` claim_2aa057d25036: scope changed from [battery_capacity_wh >= 42.0416] to [battery_capacity_wh >= 35.3553]
- `rescope` claim_0e274264ebb3: scope changed from [battery_capacity_wh < 35.3553] to [battery_capacity_wh < 42.0714]
- `rescope` claim_2aa057d25036: scope changed from [battery_capacity_wh >= 35.3553] to [battery_capacity_wh >= 42.0714]

## Transfer: interpolation (inside the studied range)

4 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | failure rate |
|---|---|---|
| conditional | +0.5939 | 1.6% |
| flat | +0.1031 | 43.0% |
| reference | +0.3050 | 19.5% |
| oracle | +0.6070 | 0.0% |

Paired differences over the same (condition, seed) episodes:

- conditional minus flat: +0.4908 [+0.3846, +0.5997], p = 0.0002
- conditional minus reference: +0.2889 [+0.2049, +0.3754], p = 0.0002
- flat minus reference: -0.2019 [-0.2969, -0.1128], p = 0.0002
- oracle minus conditional: +0.0131 [-0.0152, +0.0482], p = 0.4455

Per condition (mean score, failure rate, settings used):

| conditions | conditional | flat | reference | oracle |
|---|---|---|---|---|
| battery_capacity_wh=35 | +0.357 (6%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | -0.762 (94%) charge_below=0.1, desat_above=0.3 | -0.535 (75%) reference | +0.348 (0%) charge_below=0.6, desat_above=0.6 |
| battery_capacity_wh=70 | +0.575 (0%) charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | -0.368 (78%) charge_below=0.1, desat_above=0.3 | +0.424 (3%) reference | +0.517 (0%) charge_below=0.25, desat_above=0.3 |
| battery_capacity_wh=140 | +0.655 (0%) charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.718 (0%) charge_below=0.1, desat_above=0.3 | +0.584 (0%) reference | +0.718 (0%) charge_below=0.1, desat_above=0.3 |
| battery_capacity_wh=280 | +0.789 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.825 (0%) charge_below=0.1, desat_above=0.3 | +0.747 (0%) reference | +0.846 (0%) charge_below=0.05, desat_above=0.3 |

## Transfer: extrapolation (outside the studied range)

2 conditions never used in an experiment, 32 held-out seeds each.

| method | mean score | failure rate |
|---|---|---|
| conditional | +0.3766 | 17.2% |
| flat | -0.0322 | 50.0% |
| reference | -0.0167 | 48.4% |
| oracle | +0.4790 | 9.4% |

Paired differences over the same (condition, seed) episodes:

- conditional minus flat: +0.4088 [+0.2580, +0.5724], p = 0.0002
- conditional minus reference: +0.3933 [+0.2435, +0.5493], p = 0.0002
- flat minus reference: -0.0155 [-0.0663, +0.0279], p = 0.6285
- oracle minus conditional: +0.1024 [-0.0136, +0.2191], p = 0.0926

Per condition (mean score, failure rate, settings used):

| conditions | conditional | flat | reference | oracle |
|---|---|---|---|---|
| battery_capacity_wh=18 | -0.065 (34%) charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | -0.941 (100%) charge_below=0.1, desat_above=0.3 | -0.877 (97%) reference | +0.080 (19%) charge_below=0.8, desat_above=0.6 |
| battery_capacity_wh=600 | +0.818 (0%) charge_below=0.1, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 | +0.877 (0%) charge_below=0.1, desat_above=0.3 | +0.843 (0%) reference | +0.878 (0%) charge_below=0.05, desat_above=0.3 |

## Do the recommended settings still work together?

- battery_capacity_wh=35: combined +0.357 vs reference -0.535 (difference +0.892 [+0.677, +1.097]); single changes {'charge_below': 0.3479, 'precharge_below,precharge_window_s': -0.3176, 'desat_above': -0.3927, 'charge_margin': -0.3576}; interaction: none detected.
- battery_capacity_wh=70: combined +0.575 vs reference +0.424 (difference +0.151 [+0.082, +0.245]); single changes {'precharge_below,precharge_window_s': 0.4932, 'desat_above': 0.5166, 'charge_margin': 0.5106}; interaction: none detected.
- battery_capacity_wh=140: combined +0.655 vs reference +0.584 (difference +0.071 [+0.031, +0.109]); single changes {'precharge_below,precharge_window_s': 0.6068, 'desat_above': 0.6357, 'charge_margin': 0.5981}; interaction: none detected.
- battery_capacity_wh=280: combined +0.789 vs reference +0.747 (difference +0.042 [-0.012, +0.097]); single changes {'charge_below': 0.8244, 'precharge_below,precharge_window_s': 0.7277, 'desat_above': 0.7596, 'charge_margin': 0.7607}; interaction: negative.
- battery_capacity_wh=18: combined -0.065 vs reference -0.877 (difference +0.812 [+0.583, +1.027]); single changes {'charge_below': -0.1583, 'precharge_below,precharge_window_s': -0.8813, 'desat_above': -0.8568, 'charge_margin': -0.869}; interaction: none detected.
- battery_capacity_wh=600: combined +0.818 vs reference +0.843 (difference -0.025 [-0.066, +0.022]); single changes {'charge_below': 0.8991, 'precharge_below,precharge_window_s': 0.8058, 'desat_above': 0.8299, 'charge_margin': 0.8407}; interaction: negative.
