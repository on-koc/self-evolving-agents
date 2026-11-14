# DiscoveryWorld memory experiment: protocol

**Written before any run, with no result in hand.** Design and rationale:
[`../discoveryworld.md`](../discoveryworld.md). Protocol files:
`protocols/discovery_pilot.json` (one repeat, fewer worlds) and
`protocols/discovery_main.json` (the full design).

## Procedure

1. **Pilot.** Run `discovery_pilot.json` with the chosen model. Its purpose is to
   find failures of the setup (parse errors, context overflow, cost), not to test
   hypotheses. Changes made after the pilot are listed with the results.
2. **Coder validation.** From the pilot's episodes, export 50 records
   (`sea discovery code-sample`), have them coded by two people who do not know the
   arms, and compute agreement with the model coder (`sea discovery agreement`).
   Coded behaviours are reported as results only for behaviours with Cohen's kappa
   of at least 0.6 between the model and the people's consensus.
3. **Main run.** `discovery_main.json`, three repeats, unchanged model, grader and
   settings. Grade with one fixed grader model, different from the actor.
4. **Report** everything listed below, whatever it shows.

## Hypotheses

Comparisons are paired by world (same world, same position in a phase), repeats
averaged first. "Better" means the 95% bootstrap interval of the paired difference
lies above zero.

| | Prediction | Measure | Refuted if |
|---|---|---|---|
| D1 | investigation memory beats the Hypothesizer on `new_world` | completion, knowledge | the interval includes zero or lies below |
| D2 | investigation memory beats the Hypothesizer on `new_theme` | completion, progress, knowledge | as D1 |
| D3 | investigation memory beats answer memory on `new_world` and `new_theme`, but not on `same_world` | completion, knowledge | it does not beat it on `new_world`, or it beats it on `same_world` as much |
| D4 | answer memory has more stale knowledge than investigation memory on `new_world` | stale knowledge; first chemistry test is an earlier answer | no difference |
| D5 | investigation memory beats ReasoningBank on `new_world` and `new_theme` | completion, knowledge, stale knowledge | as D1 |
| D6 | removing the strategies from the frozen memory lowers completion and knowledge on `new_theme` | lesion difference | no difference |
| D7 | removing the findings lowers completion on `same_world` more than on `new_theme` | lesion difference by condition | the reverse |
| D8 | the placebo does not differ from the Hypothesizer | all | it is better, in which case any memory arm's advantage must be measured against the placebo |

## Emergence of behaviours

For each behaviour (alternatives, confounds, revision, controls; premature
commitment in the other direction), it is said to **emerge from memory** only if all
four hold:

| | Condition |
|---|---|
| E1 | more frequent with investigation memory than with the Hypothesizer on `new_world` and on `new_theme` |
| E2 | lower when the strategies are removed from the frozen memory (lesion) |
| E3 | not raised by the placebo |
| E4 | more frequent in the second half of the experience phase than in the first, with investigation memory, and not with the Hypothesizer |

The level in the `instructed` arm is reported next to it. A behaviour that meets E1
to E4 and that the `instructed` arm produces at a similar rate is reported as
"learned, and also obtainable by instruction". One that meets E1 to E4 but appears
mainly through the coder is reported as provisional unless the coder passed
validation for it.

## Analysis

- Paired differences with 95% bootstrap intervals (5,000 resamples) and sign-flip
  permutation p-values, as in the rest of this repository.
- Eight hypotheses and four behaviours: no correction for multiplicity; every
  comparison is reported, and p-values near 0.05 are described as weak.
- The number of worlds is fixed by the benchmark (five seeds per combination); the
  main protocol has 16 transfer worlds per repeat. This is small, and the
  experiment is better at finding large effects than at excluding small ones. No
  power calculation was possible without a pilot.
- Knowledge and stale knowledge are graded once, by one grader; the grader is
  recorded with every grade, and grades from different graders are never pooled.

## Reporting

- Every arm, condition, hypothesis and behaviour, including those that fail.
- Changes to prompts, defaults or protocols after the pilot, with the reason.
- Runs that stopped early (budget, errors), with the number of episodes completed.
- The coder agreement table, whatever it shows.
