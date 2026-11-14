# Recorded results

Compact outputs of every experiment run on the Basilisk simulator. No language model
was involved in any of them. What they show is in
[`../docs/comparison.md`](../docs/comparison.md), Part B.

| Directory | What it is | Configuration |
|---|---|---|
| `bsk-battery/` | study 1: strategies across battery sizes | `studies/bsk_battery.json` |
| `bsk-battery/first-pass/` | study 1 as first run, before three decision rules were revised | |
| `bsk-battery-panel/` | study 2: battery size and solar-array area | `studies/bsk_battery_panel.json` |
| `bsk-battery-panel/first-evaluation/` | the held-out evaluation of study 2 as it first ran, before the rule for when a claim applies was corrected | |
| `bsk-battery-replication/` | study 1 repeated with four more sets of training seeds; `replication.md` is the summary. The replicate with seeds from 1000 is `bsk-battery/` | `studies/bsk_battery.json` with `tester.seed_base` 2000, 3000, 4000, 7000 |
| `bsk-battery-passive/` | study 1 with a fixed grid of test points instead of probes between disagreeing tests; `active-vs-passive.json` is the paired comparison with study 1 | `studies/bsk_battery_passive.json` |

## Files in a study directory

| File | Contents |
|---|---|
| `config.json` | the configuration the run used, resolved |
| `study.json` | size and cost: rounds, experiments, episodes, claims by status |
| `experiments.jsonl` | every experiment in the order it was run, with the reason it was chosen |
| `graph.json` | the claim graph: claims with scope, all evidence, explanations and their verdicts, relations, and the log of every revision |
| `transfer.json` | the held-out evaluation: every method at every condition, paired differences with both intervals |
| `composition.json` | whether settings supported one at a time still help together |
| `report.md` | all of the above as a readable report |
| `*.png` | figures (`sea claims plot`) |

The episode caches are not kept here (6 to 27 MB each); a reproduction re-simulates.

## Checking a reproduction

```bash
sea claims study --config studies/bsk_battery.json --out runs/bsk-battery --workers 4
```

```bash
sea claims verify runs/bsk-battery results/bsk-battery
```

`verify` ignores what differs between runs by design (random identifiers, timings)
and compares everything else. Details, versions and seeds:
[`../docs/reproducibility.md`](../docs/reproducibility.md).
