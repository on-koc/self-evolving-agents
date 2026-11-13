# Reproducibility

What can be reproduced from this repository, how to check that a reproduction
succeeded, and what stands in the way.

## 1. What is reproducible

| Result | Reproducible | How it is checked |
|---|---|---|
| The two recorded claim studies (`results/bsk-battery`, `results/bsk-battery-panel`) | yes, exactly | `sea claims verify` against the recorded files (section 5) |
| The replication and the ablation (`results/bsk-battery-replication`, `results/bsk-battery-passive`) | yes, exactly | the same |
| Single simulator episodes | yes, exactly | a test re-simulates nine recorded episodes and compares every stored number |
| Every method's mechanics | yes | 262 tests, with scripted stand-ins for the model |
| Runs with a language model | **no result exists to reproduce.** When there is one: replayable from its call cache; not re-samplable (section 6) | |

"Exactly" was verified on one machine and one set of library versions, across
separate sessions. It has not been verified on another machine (section 7).

## 2. Environment

| | Version used for every recorded result |
|---|---|
| Python | 3.13.18 (the package declares 3.10 or newer) |
| Basilisk (`bsk`) | 2.12.2 |
| BSK-RL (`bsk-rl`) | 1.3.11 |
| NumPy | 2.4.6 |
| Gymnasium | 1.4.0 |
| DiscoveryWorld | 0.0.2 (tests only) |
| `anthropic` | 2.8.0 (tests against a local stand-in only) |
| `google-genai` | 3.3.0 (tests against a local stand-in only) |
| matplotlib | 3.10.9 (figures) |
| Platform | Linux x86-64, 4 cores |

```bash
pip install -e ".[all,dev]"
```

On first use Basilisk downloads about 116 MB of SPICE kernels from
`naif.jpl.nasa.gov`. The versions above are not pinned in `pyproject.toml`, which
gives lower bounds only; to reproduce the recorded numbers, install these versions.

Check the installation before spending time on a study:

```bash
pytest tests/test_real_simulators.py -k recorded
```

It re-simulates nine episodes of the first study (four of them lost spacecraft) and
compares them with `tests/data/bsk_recorded_episodes.json` to the last stored digit.
If it fails while the other Basilisk tests pass, the simulator works but is not the
one the results came from, and the numbers in `results/` will not be reproduced.

## 3. Sources of randomness, and how each is fixed

| Source | Fixed by | Verified by |
|---|---|---|
| The simulator: orbit, epoch, initial battery, buffer and wheel states, disturbance torques | the episode's seed. BSK-RL seeds NumPy's global generator on reset and draws everything from it | `test_bsk_episode_is_exactly_reproducible`; `test_bsk_reproduces_episodes_of_the_recorded_study` |
| Same seed under different policies or conditions | the same draws in the same order, so both arms of a comparison start identically | `test_bsk_same_seed_gives_matched_initial_conditions_across_policies` |
| Reusing one simulator for many episodes | a re-tasked simulator gives the same episode as a fresh one | `test_bsk_retask_reuses_the_simulator_and_matches_a_fresh_one` |
| Parallel workers | an episode's outcome depends only on its task and policy, not on which worker ran it or in what order | a test compares serial and parallel runs |
| Bootstrap and permutation resampling | a fixed generator seed (0) in every call | deterministic by construction |
| Which experiment the planner runs next | a deterministic function of the graph | follows from the rows above; checked end to end by `sea claims verify` |
| Identifiers of claims, evidence, experiments | **not fixed**: random by design | ignored by `sea claims verify` |
| Timings | **not fixed** | ignored by `sea claims verify` |
| A language model's sampling | **cannot be fixed** for models that accept no seed or temperature | every call is cached; a rerun replays (section 6) |

## 4. Seeds

No seed is used for more than one purpose.

| Purpose | Seeds |
|---|---|
| Exploratory look at the simulator, before the hypotheses were written | 100 to 123; used nowhere else |
| Experiments of the recorded studies ("training") | 1000 to 1047 |
| Experiments of the replicates | 2000 to 2047, 3000 to 3047, 4000 to 4047, 7000 to 7047 |
| Held-out evaluation | 5000 to 5031 |
| Tuning seeds of the grid search | 6000 to 6015 |
| Task streams of the model-comparison protocols | 0 to 9 or 0 to 14 per regime |

`sea claims replicate` refuses a configuration whose training seeds overlap its
held-out or tuning seeds.

## 5. Reproducing the recorded results

Every study is described by one file in `studies/`, and every run directory holds
the resolved configuration it ran with (`config.json`).

| Result | Command | Time on 4 cores |
|---|---|---|
| Study 1 | `sea claims study --config studies/bsk_battery.json --out runs/bsk-battery --workers 4` | about 30 min |
| Study 2 | `sea claims study --config studies/bsk_battery_panel.json --out runs/bsk-battery-panel --workers 4` | about 75 min |
| Replication | `sea claims replicate --config studies/bsk_battery.json --out runs/bsk-battery-replication --seed-bases 1000,2000,3000,4000,7000 --workers 4` | about 2.5 h |
| Ablation | `sea claims study --config studies/bsk_battery_passive.json --out runs/bsk-battery-passive --cache runs/bsk-battery-replication/episodes.sqlite --workers 4` | about 15 min after the replication, whose cache it shares |
| Ablation, comparison | `sea claims compare runs/bsk-battery-replication/seed-1000 runs/bsk-battery-passive --cache runs/bsk-battery-replication/episodes.sqlite` | minutes |
| Figures | `sea claims plot runs/bsk-battery` | seconds |

An interrupted run continues from its episode cache when the same command is given
again.

**Checking a reproduction.** A plain `diff` against `results/` always reports
differences, because identifiers are random. This compares everything else:

```bash
sea claims verify runs/bsk-battery results/bsk-battery
```

It compares the configuration, the study summary, every experiment in order, the
whole claim graph (claims, scopes, evidence, relations, revision log), the held-out
evaluation and the composition check, after renaming identifiers by order of
appearance and dropping timings. It exits with 0 if all six files agree and prints
where the first differences are otherwise. `--tolerance 1e-6` accepts differences in
the last digits, for another machine.

**What was checked here.**

- Both recorded studies were replayed from their episode caches with the final code:
  0 episodes simulated, all six files identical to `results/`.
- 28 episodes spread over four battery sizes, three policies and five seeds were
  simulated again from scratch in a later session and compared with the outcomes
  recorded the day before: all identical.
- The code that ran the replication was the claim-graph code as of commit `426e9b9`.
  The later move into `methods/claim_graph/` changed its location, not its
  behaviour: the replays above were made after the move.

## 6. Runs with a language model

None has been made. For when one is:

- Every arm of a protocol writes its resolved configuration, the model identifier,
  the embedder, the options and the full task list to `config.json`.
- Every model call is stored with its full request and reply in the run's
  provenance store, and cached on disk under a hash of the model, the prompts and a
  sample index. Running the same command again **replays** the recorded calls and
  costs nothing. This reproduces the *analysis* of a run, not the run.
- A fresh run will differ. Models that accept no temperature or seed cannot be made
  deterministic, and a model served under one name can change. Protocols therefore
  repeat each arm and report the spread; a result should be quoted with the model
  identifier and the date.
- The published decoding temperatures are requested and are dropped by the backend
  for models that reject them. `config.json` does not prove which temperature was
  applied; the model's documentation does.

## 7. Limits and known confounds

**Limits of the reproducibility claims.**

- Exact agreement has been observed on one machine type with one set of versions.
  Basilisk integrates equations of motion in floating point; another processor,
  compiler or library version may change the last digits, and a change in the last
  digit can flip a threshold decision of a rule policy and with it an episode. The
  installation check in section 2 detects this.
- The SPICE kernels are downloaded, not pinned.
- `results/` holds the outputs of the studies, not their episode caches (6 to 27 MB
  each), so a reproduction re-simulates.

**Confounds in the recorded evidence.** Each is discussed where the results are
reported; they are collected here so that none is overlooked.

| Confound | Effect on the conclusions | Where addressed |
|---|---|---|
| The hypotheses and the condition to vary were chosen after an exploratory sweep (seeds 100 to 123) had already shown that the effect of the charge threshold reverses with battery size | the studies show that the method finds and bounds such reversals where they exist. They are not evidence about how often lessons reverse, and not a test with uninformed hypotheses | `results-bsk-battery.md`, Setup; `discussion.md` |
| Decision rules were revised after the first pass of study 1 | made from the training evidence, before held-out scores were looked at; both versions recorded | `comparison.md` B.7 |
| The rule for when a claim applies was corrected after held-out numbers of study 2 had been seen | the held-out data of study 2 are not a clean test of that rule; all three versions are reported, and the default is the one that scores *lower* | `comparison.md` B.7 |
| Held-out conditions were chosen by hand | results hold for those 16 conditions; nothing is inferred about others | `metrics.md` 4.2 |
| The same 32 held-out seeds serve every condition and every replicate | intervals resample seeds; variability from the choice of held-out seeds is not in the replication spread | `metrics.md` 4.2, [`protocols/robustness.md`](protocols/robustness.md) |
| `flat` and `pooled` are derived from the claim graph's own experiments | they are controls on how evidence is used, not independent learners | `comparison.md` B.2 |
| The grid search tunes two parameters; the claim graph sets five | the grid search is a reference, not an upper bound | `metrics.md` 5.5 |
| One simulator, one task, one rule-policy family | no generality beyond it is shown | `discussion.md` |
| Many tests, each controlled at 5%, none corrected across tests | some claims are false positives; replication measures how often verdicts disagree | `comparison.md` B.5, B.9 |

**Pre-registration.** The robustness experiments were specified in
[`protocols/robustness.md`](protocols/robustness.md) and committed (`3b40312`) before
they were started. The language-model comparison is specified in
[`protocols/model-comparison.md`](protocols/model-comparison.md) and has
not been run. The two original studies were *not* pre-registered: their held-out
conditions and seeds were fixed in their configuration files before the experiments
ran, but the analysis rules changed as described above.

## 8. Tests

```bash
pytest
```

| File | What it covers |
|---|---|
| `test_reasoningbank.py` | the baseline, one test or more per row of the fidelity audit |
| `test_methods.py` | dependencies between method folders; the registry; MaTTS; conditioned retrieval; the policy-writing agent; claims as memory; metrics |
| `test_claims.py` | the claim graph: testing, labels, partition, revision, planner, recommendation, evaluation, replication |
| `test_cli.py` | every command end to end, on the toy environment |
| `test_real_simulators.py` | Basilisk and DiscoveryWorld: determinism, matched seeds, physics sanity, recorded episodes |
| `test_core.py`, `test_llm.py`, `test_envs_and_agents.py` | policies, statistics, embeddings, provenance, the model layer against a local stand-in for the API, agents |

Tests that need Basilisk or DiscoveryWorld are skipped when those are not installed.
No test calls a language model or any external service.
