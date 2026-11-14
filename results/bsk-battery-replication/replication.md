# Replication across training seeds: Charging, desaturation and eclipse strategies across battery sizes (Basilisk / BSK-RL)

5 replicates of the same study, with training seeds starting at 1000, 2000, 3000, 4000, 7000. Every replicate is evaluated on the same held-out conditions and the same held-out seeds, so the spread between replicates is the run-to-run variability of the whole procedure. Methods that do not depend on the experiments (the reference policy, the grid search) score the same in every replicate.

## Size and cost of each replicate

| training seeds from | experiments | episodes | claims | supported | comparisons |
|---|---|---|---|---|---|
| 1000 | 77 | 2688 | 21 | 13 | 8 |
| 2000 | 75 | 2720 | 22 | 14 | 8 |
| 3000 | 79 | 2608 | 21 | 12 | 8 |
| 4000 | 71 | 2304 | 21 | 13 | 8 |
| 7000 | 76 | 3056 | 20 | 10 | 8 |

## Held-out score: interpolation (inside the studied range)

| method | mean over replicates | sd | min | max | each replicate |
|---|---|---|---|---|---|
| reference | +0.305 | 0.000 | +0.305 | +0.305 | +0.305, +0.305, +0.305, +0.305, +0.305 |
| flat | +0.197 | 0.085 | +0.103 | +0.259 | +0.103, +0.259, +0.259, +0.259, +0.103 |
| pooled | +0.460 | 0.040 | +0.443 | +0.531 | +0.443, +0.531, +0.443, +0.443, +0.443 |
| conditional | +0.611 | 0.015 | +0.592 | +0.622 | +0.598, +0.621, +0.622, +0.621, +0.592 |
| oracle | +0.607 | 0.000 | +0.607 | +0.607 | +0.607, +0.607, +0.607, +0.607, +0.607 |

| spacecraft lost | mean over replicates | min | max |
|---|---|---|---|
| reference | 19.5% | 19.5% | 19.5% |
| flat | 35.0% | 29.7% | 43.0% |
| pooled | 1.6% | 1.6% | 1.6% |
| conditional | 1.6% | 1.6% | 1.6% |
| oracle | 0.0% | 0.0% | 0.0% |

| success rate | mean over replicates | min | max |
|---|---|---|---|
| reference | 78.1% | 78.1% | 78.1% |
| flat | 64.5% | 57.0% | 69.5% |
| pooled | 93.8% | 93.0% | 96.9% |
| conditional | 97.7% | 97.7% | 97.7% |
| oracle | 95.3% | 95.3% | 95.3% |

| paired difference | mean over replicates | sd | min | max | replicates whose 95% interval excludes zero | the same, resampling whole seeds |
|---|---|---|---|---|---|---|
| conditional minus pooled | +0.150 | 0.037 | +0.090 | +0.179 | 5 of 5 (above) | 5 of 5 (above) |
| conditional minus flat | +0.414 | 0.071 | +0.362 | +0.495 | 5 of 5 (above) | 5 of 5 (above) |
| conditional minus reference | +0.306 | 0.015 | +0.287 | +0.317 | 5 of 5 (above) | 5 of 5 (above) |
| pooled minus reference | +0.155 | 0.040 | +0.138 | +0.226 | 5 of 5 (above) | 5 of 5 (above) |
| flat minus reference | -0.108 | 0.085 | -0.202 | -0.046 | 2 of 5 (below) | 2 of 5 (below) |
| oracle minus conditional | -0.004 | 0.015 | -0.015 | +0.015 | 0 of 5 | 0 of 5 |

Settings the claim graph recommended at each held-out condition:

| conditions | settings (number of replicates) | score: mean, min to max |
|---|---|---|
| battery_capacity_wh=35 | charge_below=0.6, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 (3); charge_below=0.6, charge_margin=0.25, desat_above=0.3 (1); charge_below=0.6, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 (1) | +0.349, +0.319 to +0.357 |
| battery_capacity_wh=70 | charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 (4); desat_above=0.3, precharge_below=0.6, precharge_window_s=900 (1) | +0.578, +0.575 to +0.589 |
| battery_capacity_wh=140 | charge_below=0.1, charge_margin=0.25, desat_above=0.3, precharge_below=0.6, precharge_window_s=900 (3); desat_above=0.3 (2) | +0.681, +0.636 to +0.711 |
| battery_capacity_wh=280 | charge_below=0.1, desat_above=0.3 (2); charge_below=0.05, charge_margin=0.25, desat_above=0.3 (2); charge_below=0.05, desat_above=0.3 (1) | +0.836, +0.825 to +0.846 |

## Held-out score: extrapolation (outside the studied range)

| method | mean over replicates | sd | min | max | each replicate |
|---|---|---|---|---|---|
| reference | -0.017 | 0.000 | -0.017 | -0.017 | -0.017, -0.017, -0.017, -0.017, -0.017 |
| flat | -0.031 | 0.001 | -0.032 | -0.030 | -0.032, -0.030, -0.030, -0.030, -0.032 |
| pooled | +0.180 | 0.083 | +0.031 | +0.217 | +0.217, +0.031, +0.217, +0.217, +0.217 |
| conditional | +0.372 | 0.007 | +0.360 | +0.377 | +0.377, +0.377, +0.360, +0.377, +0.370 |
| oracle | +0.479 | 0.000 | +0.479 | +0.479 | +0.479, +0.479, +0.479, +0.479, +0.479 |

| spacecraft lost | mean over replicates | min | max |
|---|---|---|---|
| reference | 48.4% | 48.4% | 48.4% |
| flat | 50.0% | 50.0% | 50.0% |
| pooled | 21.9% | 17.2% | 40.6% |
| conditional | 20.3% | 20.3% | 20.3% |
| oracle | 9.4% | 9.4% | 9.4% |

| success rate | mean over replicates | min | max |
|---|---|---|---|
| reference | 51.6% | 51.6% | 51.6% |
| flat | 50.0% | 50.0% | 50.0% |
| pooled | 64.1% | 57.8% | 65.6% |
| conditional | 77.2% | 73.4% | 79.7% |
| oracle | 82.8% | 82.8% | 82.8% |

| paired difference | mean over replicates | sd | min | max | replicates whose 95% interval excludes zero | the same, resampling whole seeds |
|---|---|---|---|---|---|---|
| conditional minus pooled | +0.193 | 0.086 | +0.143 | +0.346 | 3 of 5 (above) | 3 of 5 (above) |
| conditional minus flat | +0.403 | 0.008 | +0.389 | +0.409 | 5 of 5 (above) | 5 of 5 (above) |
| conditional minus reference | +0.389 | 0.007 | +0.377 | +0.394 | 5 of 5 (above) | 5 of 5 (above) |
| pooled minus reference | +0.196 | 0.083 | +0.048 | +0.234 | 4 of 5 (above) | 4 of 5 (above) |
| flat minus reference | -0.014 | 0.001 | -0.015 | -0.013 | 0 of 5 | 0 of 5 |
| oracle minus conditional | +0.107 | 0.007 | +0.102 | +0.119 | 5 of 5 (above) | 5 of 5 (above) |

Settings the claim graph recommended at each held-out condition:

| conditions | settings (number of replicates) | score: mean, min to max |
|---|---|---|
| battery_capacity_wh=18 | charge_below=0.6, charge_margin=0.25, precharge_below=0.6, precharge_window_s=900 (2); charge_below=0.6, charge_margin=0.25 (1); charge_below=0.6 (1); charge_below=0.6, precharge_below=0.6, precharge_window_s=900 (1) | -0.137, -0.158 to -0.123 |
| battery_capacity_wh=600 | charge_below=0.1, desat_above=0.3 (2); charge_below=0.05, desat_above=0.3 (2); charge_below=0.1 (1) | +0.882, +0.877 to +0.899 |

## Do the replicates reach the same verdicts?

Tests made by every replicate at the same conditions: 59. Unanimous: 36 (61%).

| comparison | conditions | verdicts (number of replicates) |
|---|---|---|
| `charge_below 0.05 vs 0.1` | battery_capacity_wh=25 | no meaningful benefit (5) |
| `charge_below 0.05 vs 0.1` | battery_capacity_wh=50 | no meaningful benefit (5) |
| `charge_below 0.05 vs 0.1` | battery_capacity_wh=100 | baseline better (4), no meaningful benefit (1) **differ** |
| `charge_below 0.05 vs 0.1` | battery_capacity_wh=200 | baseline better (3), no meaningful benefit (2) **differ** |
| `charge_below 0.05 vs 0.1` | battery_capacity_wh=238 | unresolved (3), intervention better (2) **differ** |
| `charge_below 0.05 vs 0.1` | battery_capacity_wh=283 | intervention better (3), unresolved (2) **differ** |
| `charge_below 0.05 vs 0.1` | battery_capacity_wh=400 | unresolved (2), intervention better (2), no meaningful benefit (1) **differ** |
| `charge_below 0.1 vs 0.25` | battery_capacity_wh=25 | no meaningful benefit (5) |
| `charge_below 0.1 vs 0.25` | battery_capacity_wh=32.4 | no meaningful benefit (3), baseline better (2) **differ** |
| `charge_below 0.1 vs 0.25` | battery_capacity_wh=42 | baseline better (5) |
| `charge_below 0.1 vs 0.25` | battery_capacity_wh=50 | baseline better (5) |
| `charge_below 0.1 vs 0.25` | battery_capacity_wh=70.7 | baseline better (5) |
| `charge_below 0.1 vs 0.25` | battery_capacity_wh=100 | baseline better (5) |
| `charge_below 0.1 vs 0.25` | battery_capacity_wh=119 | baseline better (5) |
| `charge_below 0.1 vs 0.25` | battery_capacity_wh=154 | intervention better (3), unresolved (2) **differ** |
| `charge_below 0.1 vs 0.25` | battery_capacity_wh=200 | intervention better (5) |
| `charge_below 0.1 vs 0.25` | battery_capacity_wh=400 | intervention better (5) |
| `charge_below 0.4 vs 0.25` | battery_capacity_wh=25 | intervention better (5) |
| `charge_below 0.4 vs 0.25` | battery_capacity_wh=42 | intervention better (5) |
| `charge_below 0.4 vs 0.25` | battery_capacity_wh=50 | intervention better (5) |
| `charge_below 0.4 vs 0.25` | battery_capacity_wh=54.5 | intervention better (4), baseline better (1) **differ** |
| `charge_below 0.4 vs 0.25` | battery_capacity_wh=70.7 | baseline better (4), unresolved (1) **differ** |
| `charge_below 0.4 vs 0.25` | battery_capacity_wh=100 | baseline better (5) |
| `charge_below 0.4 vs 0.25` | battery_capacity_wh=200 | baseline better (5) |
| `charge_below 0.4 vs 0.25` | battery_capacity_wh=400 | baseline better (5) |
| `charge_below 0.6 vs 0.4` | battery_capacity_wh=25 | intervention better (5) |
| `charge_below 0.6 vs 0.4` | battery_capacity_wh=32.4 | intervention better (5) |
| `charge_below 0.6 vs 0.4` | battery_capacity_wh=42 | baseline better (2), unresolved (2), no meaningful benefit (1) **differ** |
| `charge_below 0.6 vs 0.4` | battery_capacity_wh=50 | baseline better (3), unresolved (1), no meaningful benefit (1) **differ** |
| `charge_below 0.6 vs 0.4` | battery_capacity_wh=70.7 | baseline better (5) |
| `charge_below 0.6 vs 0.4` | battery_capacity_wh=100 | baseline better (5) |
| `charge_below 0.6 vs 0.4` | battery_capacity_wh=200 | baseline better (5) |
| `charge_below 0.6 vs 0.4` | battery_capacity_wh=400 | baseline better (5) |
| `charge_below 0.8 vs 0.6` | battery_capacity_wh=25 | unresolved (5) |
| `charge_below 0.8 vs 0.6` | battery_capacity_wh=32.4 | no meaningful benefit (3), baseline better (2) **differ** |
| `charge_below 0.8 vs 0.6` | battery_capacity_wh=42 | baseline better (4), no meaningful benefit (1) **differ** |
| `charge_below 0.8 vs 0.6` | battery_capacity_wh=50 | baseline better (5) |
| `charge_below 0.8 vs 0.6` | battery_capacity_wh=70.7 | baseline better (5) |
| `charge_below 0.8 vs 0.6` | battery_capacity_wh=100 | baseline better (5) |
| `charge_below 0.8 vs 0.6` | battery_capacity_wh=200 | baseline better (5) |
| `charge_below 0.8 vs 0.6` | battery_capacity_wh=400 | baseline better (5) |
| `charge_margin 0.25 vs 0` | battery_capacity_wh=25 | intervention better (3), unresolved (1), no meaningful benefit (1) **differ** |
| `charge_margin 0.25 vs 0` | battery_capacity_wh=50 | intervention better (3), unresolved (2) **differ** |
| `charge_margin 0.25 vs 0` | battery_capacity_wh=100 | intervention better (5) |
| `charge_margin 0.25 vs 0` | battery_capacity_wh=200 | intervention better (3), unresolved (2) **differ** |
| `charge_margin 0.25 vs 0` | battery_capacity_wh=400 | unresolved (5) |
| `desat_above 0.3 vs 0.6` | battery_capacity_wh=25 | unresolved (3), no meaningful benefit (2) **differ** |
| `desat_above 0.3 vs 0.6` | battery_capacity_wh=32.4 | intervention better (5) |
| `desat_above 0.3 vs 0.6` | battery_capacity_wh=42 | intervention better (5) |
| `desat_above 0.3 vs 0.6` | battery_capacity_wh=50 | intervention better (5) |
| `desat_above 0.3 vs 0.6` | battery_capacity_wh=70.7 | intervention better (5) |
| `desat_above 0.3 vs 0.6` | battery_capacity_wh=100 | intervention better (5) |
| `desat_above 0.3 vs 0.6` | battery_capacity_wh=200 | intervention better (5) |
| `desat_above 0.3 vs 0.6` | battery_capacity_wh=400 | intervention better (4), unresolved (1) **differ** |
| `precharge_below 0.6 vs 0, precharge_window_s 900 vs 0` | battery_capacity_wh=25 | intervention better (4), unresolved (1) **differ** |
| `precharge_below 0.6 vs 0, precharge_window_s 900 vs 0` | battery_capacity_wh=50 | intervention better (3), unresolved (2) **differ** |
| `precharge_below 0.6 vs 0, precharge_window_s 900 vs 0` | battery_capacity_wh=100 | intervention better (4), unresolved (1) **differ** |
| `precharge_below 0.6 vs 0, precharge_window_s 900 vs 0` | battery_capacity_wh=200 | unresolved (4), no meaningful benefit (1) **differ** |
| `precharge_below 0.6 vs 0, precharge_window_s 900 vs 0` | battery_capacity_wh=400 | no meaningful benefit (4), baseline better (1) **differ** |
