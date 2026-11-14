# Robustness experiments on the claim graph: protocol

Written before the runs it describes, and committed before they were started. Results
are reported in `docs/comparison.md` whatever they turn out to be.

Both experiments use the Basilisk simulator only. No language model is involved.

## Why

The two recorded studies each produced one claim graph. The intervals reported for
their held-out scores describe how well that one graph's recommendations score. Two
questions are left open:

1. **Run-to-run variability.** How different would the graph, and its held-out score,
   have been had the experiments drawn other seeds?
2. **Does choosing experiments actively matter?** The planner probes between results
   that disagree. Whether that is better than testing a fixed grid has not been
   compared.

## R1. Replication across training seeds

**Design.** The one-variable battery study (`studies/bsk_battery.json`) is run five
times. The runs differ only in the training seeds: 48 consecutive seeds starting at
1000 (the recorded run), 2000, 3000, 4000 and 7000. Hypotheses, ladder rule, planner,
decision rules, budget, held-out conditions (35, 70, 140, 280 Wh inside the range;
18 and 600 Wh outside), held-out seeds (5000 to 5031) and tuning seeds (6000 to 6015)
are identical. No training seed is a held-out or tuning seed.

**Measures, per replicate.** Experiments and episodes used; claims by status; which
comparisons the ladder rule proposed; held-out mean score and share of spacecraft
lost for each method; the paired differences already reported for the recorded run;
the settings recommended at each held-out condition; the verdict of every test.

**Analysis.** For each method and each paired difference: mean, sample standard
deviation, minimum and maximum over the five replicates, and the number of replicates
whose own 95% interval excludes zero. For each held-out condition: how many
replicates recommend which settings. For each test made by every replicate at the
same condition: whether the verdicts are unanimous.

The reference policy and the grid search do not depend on the training seeds, so
their scores are the same in every replicate by construction.

**Expectation, stated in advance.** Inside the studied range the ordering reference <
best single setting < conditional claims should hold in every replicate, because the
recorded differences are several times their interval widths. There is no prior
estimate of the spread; measuring it is the purpose.

**What would count against the method.** A replicate in which conditional claims do
not beat the best single setting, or lose the spacecraft clearly more often than it;
or recommended settings that differ between replicates at most held-out conditions.

```bash
sea claims replicate --config studies/bsk_battery.json --out runs/bsk-battery-replication --seed-bases 1000,2000,3000,4000,7000 --workers 4
```

## R2. Active against passive experiment selection

**Design.** The battery study is run once more with the boundary probes switched off
(`studies/bsk_battery_passive.json`). Instead of five grid points plus bisection
between disagreeing neighbours, every comparison is tested at a fixed log-spaced grid
of nine battery sizes (25, 35.4, 50, 70.7, 100, 141, 200, 283, 400 Wh). Everything
else is the same as in the recorded (active) run: hypotheses, ladder rule, moderator
sweep, sequential test, decision rules, training seeds from 1000, held-out conditions
and seeds.

The designs are matched in size by construction, not by budget: the active run made
76 outcome tests over 8 comparisons; nine grid points for 8 comparisons is 72. The
number of episodes each design needs follows from the sequential rule and is
reported. The passive run's episode budget is set to 7,200, more than the fixed grid
can use, so that it is never cut short.

**Measures.** Experiments and episodes used; held-out mean score and share of
spacecraft lost for each method; the paired difference between the two designs'
conditional recommendations on the same held-out conditions and seeds, with its 95%
bootstrap interval.

**Expectation, stated in advance.** A nine-point grid over a 16-fold range has
neighbouring points a factor 1.41 apart; the bisection rule stops at 1.3. At this
scale the two designs resolve boundaries about equally well, so no difference in
held-out score beyond noise is expected, and a similar number of episodes. Active
selection should pay only where a fixed grid of the same resolution would be much
larger: a wider range, or more than one condition variable. That is not tested here.

**How the outcome will be read.** A paired difference smaller than 0.02 in absolute
value whose interval includes zero is recorded as "no measurable benefit of active
selection at this scale". Anything else is reported with its sign.

```bash
sea claims study --config studies/bsk_battery_passive.json --out runs/bsk-battery-passive --cache runs/bsk-battery-replication/episodes.sqlite --workers 4
```

```bash
sea claims compare runs/bsk-battery-replication/seed-1000 runs/bsk-battery-passive --cache runs/bsk-battery-replication/episodes.sqlite
```

## Limits of both

One task family, one condition variable, one simulator. Five replicates give a rough
idea of the spread, not a distribution. The held-out seeds are the same for every
replicate, so variability due to the choice of held-out seeds is not included.

## Outcome

Added after the runs. Nothing above this line was changed.

Both experiments were run as specified. Results and files are in
[`../comparison.md`](../comparison.md), sections B.5 and B.6.

**R1.** The stated expectation held: reference below best single setting below
conditional claims, inside the studied range, in all five replicates. The three
things named as counting against the method:

| Named in advance | What happened |
|---|---|
| a replicate in which conditional claims do not beat the best single setting | By mean score: none, inside or outside the range. By interval: the difference excludes zero in five of five replicates inside the range and in three of five outside it |
| a replicate in which they lose the spacecraft clearly more often | Inside the range the share is the same (1.6%) in all five. Outside it the claims lose 20.3% against 17.2% in four replicates (13 episodes against 11 of 64; interval of the difference −0.05 to +0.13 or wider) and 20.3% against 40.6% in the fifth. "Clearly" was not defined in advance; by the interval, no replicate shows it |
| recommended settings that differ between replicates at most held-out conditions | **This occurred**, at all six held-out conditions |

**R2.** Active minus fixed grid, inside the range: +0.003, interval [−0.005,
+0.011] as specified (resampling single episodes), [−0.003, +0.009] resampling
seeds. By the rule stated above this is recorded as *no measurable benefit of active
selection at this scale*. The fixed grid used 2,224 episodes, the active run 2,688.

**Departures from the protocol.**

- A second interval was added to every paired difference: one that resamples the
  held-out seeds, because every held-out condition reuses the same seeds. It was
  implemented while the last replicate was still running, for reasons unrelated to
  the replication, and no count in the summary differs between the two intervals.
  Both are in the result files.
- The success rate was added to the reported measures.
- The runs were made with the claim-graph code as it stood when the protocol was
  committed. The summary and the comparison were then computed with the current
  code, which gives identical numbers for everything the earlier code reported.
