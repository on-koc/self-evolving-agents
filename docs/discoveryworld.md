# DiscoveryWorld: does memory make an agent investigate better?

**Status: built and verified for its mechanics; not run with a language model.** No
number below is a result. The experiment is specified in advance in
[`protocols/discoveryworld.md`](protocols/discoveryworld.md) and runs with one
command once a model is available.

## The question

> Can an agent with frozen model weights improve its scientific investigation
> strategies across tasks, enabling more efficient discovery and better predictions
> under unseen mechanisms?

The claim this design is built to test is narrower and sharper: **what carries over
from one scientific task to the next is how to investigate, not what was found.**
Remembering which substance removed the rust in one world is a different thing from
having learned how to identify the substance that removes it in a new world. The
main claim concerns the latter.

## Why DiscoveryWorld

[DiscoveryWorld](https://github.com/allenai/discoveryworld) (Jansen et al., NeurIPS
2024) adds what a compact experimental-design benchmark lacks: an agent has to
choose instruments, collect observations, pursue hypotheses and complete an
investigation in a simulated world. It scores three things separately:

| Measure | What it is | Source |
|---|---|---|
| task completion | the task was completed successfully | the simulator |
| procedural progress | share of the task's sub-goals reached (instruments used, samples collected, ...) | the simulator |
| explanatory knowledge | share of the world's critical questions that the agent's knowledge answers ("Does it clearly state the rust remover is `Substance B`?") | a model grades, with DiscoveryWorld's own prompt |

One property makes it suited to the question: **the answer changes with the seed.**
In 23 of the 24 theme-difficulty combinations, seeds 0 and 1 hide different
discoveries (checked from the scorecards):

| Task | Seed 0 | Seed 1 |
|---|---|---|
| Combinatorial Chemistry, Easy | the rust remover is Substance B | Substance D |
| Plant Nutrients, Normal | thorium at a medium level | titanium at a high level |
| Reactor Lab, Easy | frequency = 59 × microscope reading | 78 × densitometer reading |
| Proteomics, Easy | the vortisquid is the outlier | the animaplant |
| Space Sick, Challenge | the glowing rock detects harmful mushrooms | the same (the one exception) |

So a memory of answers can be told apart from a memory of methods, by testing in a
world of the same kind with another seed.

## Three kinds of memory

| Kind | Example | Scope |
|---|---|---|
| episode-specific evidence | an instrument returned a particular measurement | the world it came from |
| conditional scientific hypothesis | a relationship holds under specified conditions | where it was observed, stated |
| transferable investigation strategy | "choose an experiment where competing models predict different outcomes" | meant to transfer |

The investigation memory (`methods/investigation_memory`,
[page](methods/investigation_memory.md)) holds all three in one graph: hypotheses
linked to the evidence for and against them and to the conditions they were observed
under; strategies linked to the episodes they came from and to their record of use.
The interesting result would be that experience improves the third kind, and that
the third kind improves discovery elsewhere.

## Design

### Actor

Every arm uses the same agent: DiscoveryWorld's Hypothesizer
([page](methods/hypothesizer.md)), ported so that its prompts are byte-identical to
the released agent's. It keeps measurements and hypotheses within an episode and
starts each episode empty. The arms differ only in what memory across episodes is
placed in its prompt.

### Arms

| Arm | Memory across episodes | Isolates |
|---|---|---|
| `hypothesizer` | none | the baseline: DiscoveryWorld's own agent |
| `reasoningbank` | ReasoningBank, as published, on the same agent | the strongest published memory |
| `investigation_memory` | evidence, conditional hypotheses, strategies | the treatment |
| `answer_memory` | what was found in earlier worlds of this kind, as plain facts | the foil: remembering the substance |
| `placebo` | neutral text of similar length | having text in the memory slot |
| `instructed` | none; the five behaviours prescribed in the prompt | what instruction alone produces |

Lessons, on the frozen memory of `investigation_memory`: strategies removed;
findings (evidence and hypotheses) removed.

### Phases

1. **Experience:** the same stream of worlds for every arm (four themes, Easy, seeds
   0 to 2, interleaved). Memories learn.
2. **Transfer, memory frozen**, in three conditions:

| Condition | Worlds | Answer memory should | Strategy memory should |
|---|---|---|---|
| `same_world` | a world seen in experience again | help (the answer is the same) | help |
| `new_world` | a seen theme with an unseen seed | not help, or hurt (the answer differs) | help |
| `new_theme` | an unseen theme (Plant Nutrients, Reactor Lab) | not apply | help, if strategies transfer |

3. **Lesions**, on the transfer worlds.

The main claim is supported if strategy memory beats answer memory and the baseline
on `new_world` and `new_theme`, while answer memory's advantage is confined to
`same_world`.

## Measures

Defined in [`metrics.md`](metrics.md), section 10.

| Group | Measures |
|---|---|
| DiscoveryWorld's own | task completion, procedural progress, explanatory knowledge |
| remembering instead of finding | stale knowledge: the knowledge written in a new world states an earlier world's answer (graded with the earlier world's critical questions); in chemistry, the first test is an earlier world's answer |
| efficiency | steps; candidates tested before the final answer |
| investigative behaviours | controls, alternatives, confounds, revision, premature commitment: from the actions where they can be read, and coded by a model blind to the arm |
| use of strategies | a shown strategy is cited in the agent's reasoning |

### Emergence

A behaviour's appearance counts as evidence of learning only if it was not
prescribed. No prompt outside the `instructed` arm names the five behaviours (a test
checks every prompt text for the words). A behaviour is said to emerge from memory
when, as fixed in the protocol: it is more frequent with the investigation memory
than with the Hypothesizer on new worlds and new themes; removing the strategies
from the frozen memory lowers it; the placebo does not raise it; and it grows over
the experience phase. Its level in the `instructed` arm is reported beside it: if
instruction produces the behaviour as well as memory does, memory has found
something a prompt could have said.

## How the behaviours are detected

| Behaviour | From the actions (no model) | Elsewhere |
|---|---|---|
| alternatives | candidates tested before the final answer; in chemistry, distinct jar contents tested | coded |
| confounds | chemistry: the jar cleaned before a test with different contents | coded |
| revision | chemistry: a failed test followed by a different one, not repeated | coded |
| controls | Archaeology (Challenge): known-age artifacts measured; Reactor Lab: known crystals measured | coded |
| premature commitment | the task completed with at most one candidate tested | coded |

The detectors were checked on real DiscoveryWorld runs with scripted actions: a
chemistry investigation that tests Substance A, cleans the jar and tests Substance B
yields two distinct tests, the first failing and the second removing the rust,
cleaning before the switch, and revision after the failure; the same without
cleaning yields one contaminated test.

The coder sees a record of the episode with every sentence that mentions memory or
earlier tasks removed. Its codes are not results until its agreement with people is
measured: `sea discovery code-sample` exports episodes without their arm, and `sea
discovery agreement` computes Cohen's kappa against people's labels.

## What has been verified

| Part | How |
|---|---|
| The Hypothesizer port | run side by side with the released code on the same worlds and replies: 31 of 31 prompts byte-identical, with their temperatures and reply limits |
| The knowledge grader | its prompt is byte-identical to DiscoveryWorld's `scripts/knowledgeScorer.py` |
| All scenarios load | "It's (not) Rocket Science!" failed on Python 3.12 and later; a compatibility shim gives the numbers Python 3.11 gives from the same seed. All 24 combinations load |
| Behaviour detectors | on scripted real investigations (above) and constructed episodes |
| The memory | extraction, scoping of findings to their world, transfer of strategies, review and replacement, lesions, variants, freezing: unit tests |
| The whole experiment | dry run on real DiscoveryWorld with the rule-based stand-in: experience, three transfer conditions, a lesion, grading, report |

What has not: anything about how an agent with a real model behaves.

## Running it

```bash
sea discovery run --protocol protocols/discovery_pilot.json --out runs/discovery-pilot
```

```bash
sea discovery grade runs/discovery-pilot --grader openai:gpt-4o
```

```bash
sea discovery report runs/discovery-pilot
```

The model is set in the protocol or overridden with `--llm` (any backend of
[`models.md`](models.md)). The grader should be a different, fixed model, and the
same for every arm.

**Cost.** The Hypothesizer makes two calls per step with about 7,000 prompt tokens
each in its original JSON mode; a 100-step episode is about 200 calls and 1.5 million
prompt tokens. The main protocol has about 200 episodes per repeat. With a hosted
model that is expensive; with a local model it is a matter of time (several minutes
per episode). `agent_options.observation = "text"` cuts the prompt to about 2,000
tokens, at the price of departing from the released agent. The pilot protocol (84
episodes) is about a seventh of the main one (200 episodes per repeat, three repeats).

## Threats to validity

- **Grader bias.** The knowledge score depends on a model. It is DiscoveryWorld's
  own procedure; a fixed grader for all arms, blind to the arm, limits the damage.
- **Coder validity.** Until measured against people, coded behaviours are not
  results; the action detectors cover only some behaviours in some themes.
- **Redaction is imperfect.** An agent's reasoning can reveal that it has a memory in
  ways the redaction does not catch.
- **Answer leakage within a theme.** Hypotheses from other worlds of the same kind
  are shown with their conditions (`other_worlds=scoped`). If that hurts on new
  worlds, `other_worlds=hide` is the arm to compare with.
- **Few worlds.** Five seeds per combination limit how many distinct worlds exist;
  the protocol uses seeds 0 to 4 and all differences are paired by world.
- **One actor.** All arms share the Hypothesizer; conclusions are about memory on
  that agent.
