# Agents

A method decides what memory an agent is shown and what is learned from its episodes;
the agent plays the episode. Any method that shows memory can be combined with any
agent that reads it, so DiscoveryWorld's own baselines can run with ReasoningBank, its
adaptations or the investigation memory exactly as they run with this repository's
`stepwise` agent.

| Agent | Origin | Model calls | Environments | Reads memory |
|---|---|---|---|---|
| `stepwise` | ReasoningBank paper | one per action | every environment | yes, at the end of its system prompt |
| `policy_program` | adaptation (this repository) | one per episode | scanning (`bsk-scan`, `toy-scan`) | yes |
| `hypothesizer` | DiscoveryWorld | two per action, plus one every 10 steps | DiscoveryWorld | yes, after its scientific knowledge |
| `react` | DiscoveryWorld | one per action | DiscoveryWorld | yes, before the task line |
| `plan_execute` | DiscoveryWorld | one per action, plus one per plan step | DiscoveryWorld | yes, in planner and executor prompts |
| `random` | DiscoveryWorld | none | DiscoveryWorld | no |

```bash
sea run --method no_memory --agent react --env discoveryworld --scenario "Reactor Lab" --difficulty Easy --seeds 0:5 --llm ollama:qwen2.5:14b --llm-option num_ctx=16384 --out runs/reactor-react
```

`sea agents` prints this table. `--agent` defaults to the method's own agent (`stepwise` for most methods,
`hypothesizer` for `hypothesizer` and `investigation_memory`, `policy_program` for
`policy_program`). `--agent-option NAME=VALUE` sets an agent's options (listed below).

## Which agent with which method

A combination that cannot work is refused before any model is called
(`methods/registry.py`, `check_combination`), with the reason.

| Method | stepwise | policy_program | hypothesizer | react | plan_execute | random |
|---|---|---|---|---|---|---|
| `no_memory` | yes | scanning only | yes | yes | yes | yes |
| `reasoningbank` | yes | scanning only | yes | yes | yes | no (reads no memory) |
| `matts` | yes | scanning only | yes | yes | yes | no |
| `conditioned_retrieval` | yes | scanning only | yes | yes | yes | no |
| `investigation_memory` | yes | scanning only | yes (default) | yes | yes | no |
| `claim_memory` | scanning only | scanning only | no | no | no | no |
| `policy_program` | no (own agent) | yes (own agent) | no | no | no | no |
| `hypothesizer` | no (own agent) | no | yes (own agent) | no | no | no |
| `claim_graph` | a study, not an agent's memory: `sea claims study` | | | | | |

- **Scanning only.** The policy-writing agent writes rule policies over named numeric
  features (battery, storage, ...). DiscoveryWorld exposes none.
- **`claim_memory`** shows claims tested by a claim study. Claim studies test parameters
  of rule policies, so they exist for the scanning environments only; claims from
  Basilisk say nothing about DiscoveryWorld, and running it there is refused.
- **Own agent.** `hypothesizer` and `policy_program` are methods that are agents; to run
  their agent with a memory, use the memory's method with `--agent hypothesizer`.
- **Checked on DiscoveryWorld with the stand-in model.** During the audit, every method
  that can run there, with the `stepwise` and `hypothesizer` agents. In the test suite,
  `no_memory`, `reasoningbank`, `conditioned_retrieval`, `investigation_memory` and
  `matts` with `react`; `no_memory` and `reasoningbank` with `plan_execute`; `no_memory`
  with `random`; `investigation_memory` with `stepwise`; and the Hypothesizer arms of the
  experiment (`tests/test_discoveryworld_agents.py`, `tests/test_discovery.py`). The
  protocol `protocols/discovery_agents_dry_run.json` takes DiscoveryWorld's baselines,
  alone and with memory, through the whole experiment (run, grade, report).
- **MaTTS with greedy agents.** DiscoveryWorld's ReAct and Plan-and-Execute decode at
  temperature 0, so several attempts at a task are nearly the same unless the backend
  varies its seed between samples or the temperature is raised
  (`--agent-option temperature=0.7`).

In the memory experiment an arm names its agent (`"agent": "react"`). A dry run with the
stand-in model, with DiscoveryWorld's baselines alone and carrying ReasoningBank and the
investigation memory, checks that every piece works together (its numbers mean
nothing):

```bash
sea discovery run --protocol protocols/discovery_agents_dry_run.json --out runs/discovery-agents-dry
```

## How memory reaches each agent

With no memory, every DiscoveryWorld port sends exactly the original's prompts. With
memory, the method's text is inserted in one place:

| Agent | Where |
|---|---|
| `stepwise` | the end of the system prompt, as in the ReasoningBank paper |
| `hypothesizer` | after the current scientific knowledge, before "Please create your output" |
| `react` | after the hints, before "Task: ..." |
| `plan_execute` | planner: after its key instructions, before "Now solve this task:"; executor: as `react`. `memory_in` chooses `both` (default), `planner`, `executor` or `none` |
| `random` | nowhere |

## What the knowledge score grades

DiscoveryWorld's knowledge score asks a grader whether the agent's knowledge contains
the discovery. What counts as the agent's knowledge follows the paper's own scripts:

| Agent | Knowledge graded |
|---|---|
| `hypothesizer` | its store of measurements and hypotheses at the end of the episode |
| `react`, `plan_execute` | every `thought` of the actions sent to the game, numbered ("Thought 1: ..."), as `scripts/analysisReactKnowledge.py` builds it from the run log |
| `stepwise` | its reasoning at every step, numbered the same way |
| `random` | nothing (no knowledge) |

## DiscoveryWorld's baselines

DiscoveryWorld was released with four baseline agents. All four are here as faithful
ports; where a port departs from the original it is listed below.

### Hypothesizer

Acts, then records measurements and hypotheses with a status after every step, and
consolidates them every 10 steps. Documented on its own page,
[`methods/hypothesizer.md`](methods/hypothesizer.md); its prompts are byte-identical to
the released agent's (31 of 31 compared).

### ReAct (`react`)

Source: `agents/recoma/` of DiscoveryWorld (`react_controller.py`,
`discoveryworld_promptlm.py`, `prompts/react_prompt.txt`, `configs/react.jsonnet`), run
on ReComA (`allenai/recoma`, commit `b262ab5`). Port: `agents/discoveryworld/react.py`.

At every step the model receives one prompt: the game's rules and hints, the task
followed by the history of its earlier actions and what the game answered to each
(newest first, as much as fits in 10,000 characters), the current observation as the
API's JSON (without the task progress), the actions, the teleport locations and the
objects within reach; inside a dialog, the dialog instead of the action lists. It
replies with one JSON action carrying a `thought`. `{"action": "SUBMIT", "arg1": ...}`
ends the episode. Decoding: temperature 0, at most 400 reply tokens, stopped at a
closing code fence.

| Option | Default | Meaning |
|---|---|---|
| `temperature` | 0.0 | decoding temperature (greedy, as released) |
| `max_tokens` | 400 | reply limit |
| `max_output_length` | 10000 | characters of task and history in the prompt |
| `max_history` | -1 | history entries kept before trimming by length (-1: all that fit) |
| `max_llm_calls` | 1000 | the episode ends after this many calls |
| `released_reads` | true | read the observation as often as the released runs did (below) |
| `released_step_limit` | true | stop at DiscoveryWorld's own step count, as released (below) |

### Plan-and-Execute (`plan_execute`)

Source: `agents/recoma/plan_and_execute.py`, `prompts/planner_prompt.txt`,
`prompts/executer_prompt.txt`, `configs/plan_and_execute.jsonnet`. Port:
`agents/discoveryworld/plan_execute.py`.

A planner writes one step at a time ("Step 3: Find the key to the door"). Its prompt is a
conversation: a worked example, the instructions, the task, and every earlier step as an
assistant turn followed by its result as a user turn (` --Task completed!...`). An
executor, a ReAct controller with its own prompt, carries the step out in the game until
it submits ("Task completed!" or "Task failed!" with a thought); the submission is the
step's result. Once a subtask has taken more than step limit / 5 actions, the executor's
prompt asks "ARE YOU SURE YOU WANT TO CONTINUE?". The episode ends when a plan step ends
in "Done!", when the task is complete, or at the step limit. Planner: at most 100 tokens,
stopped at a line break; executor: 400 tokens, stopped at a closing code fence; both
greedy.

| Option | Default | Meaning |
|---|---|---|
| `temperature` | 0.0 | for both |
| `plan_max_tokens`, `act_max_tokens` | 100, 400 | reply limits |
| `max_output_length` | 10000 | characters of subtask and history in an executor prompt |
| `termination_divisor` | 5 | the "are you sure" warning appears after step limit / this many actions in a subtask |
| `max_llm_calls` | 1000 | the episode ends after this many calls |
| `memory_in` | `both` | which prompts carry a method's memory |
| `released_reads`, `released_step_limit` | true | as for `react` |

### Random (`random`)

Source: `agents/RandomAgent.py`. Port: `agents/discoveryworld/random_agent.py`. Inside a
dialog a random option; otherwise a random action from the full list, with random objects
within reach as arguments and a random direction, teleport location or post number where
the action takes one. Options: `seed` (mixed with the task and the attempt) and
`rng_seed` (seed the generator with exactly this number, as the original's
`randomAgent(api, numSteps, seed)` does).

## How the ports were checked

The original code was run side by side with the ports on the same worlds, with a scripted
model whose replies depend only on the prompt (`tests/dw_scripted.py`): the replies use
instruments, talk to characters and answer dialogs, try invalid actions, teleport, read,
write long thoughts (so that the history is trimmed), come with and without code fences,
and in Plan-and-Execute end subtasks in success and failure, run one long enough to draw
the warning, and end the plan with "Done!". If the prompts agree, so do the replies, and
the runs stay in step.

| Agent | Compared | Result |
|---|---|---|
| ReAct | 13 runs on 6 scenario-difficulty combinations (the instrument and dialog unit tests, Combinatorial Chemistry Easy, Space Sick Easy and Normal, Rocket Science Easy), 19 to 26 calls each | every prompt byte-identical, with the same decoding parameters |
| Plan-and-Execute | 6 runs on 3 combinations (the instrument and dialog unit tests, Space Sick Normal), 27 calls each, planner conversations of up to 25 messages | every prompt byte-identical |
| Random | 3 worlds, 90 actions | every action identical for the same generator seed |

In all, 472 prompts were compared. Three of the runs are kept as fingerprints (`tests/data/discoveryworld_baseline_prompts.json`)
and the random agent's actions as a fixture; the tests rerun the ports against them. The
template files are compared with the released ones by SHA-256.

## Where the ports depart from the released agents

| Situation | Released agent | Port | Consequence |
|---|---|---|---|
| A reply contains no readable JSON action | the run stops with an exception (and with it every later episode of the run) | one step passes without an action; the history shows the reply and an error | only where the original produces no result at all |
| The task text alone is longer than the history limit | the trimming loop never ends | trimming stops when no history is left | as above |
| The step limit is reached, or the task completes | DiscoveryWorld updates its step counter and completion flag only when the observation is read, so the runner asks the model once more and discards the answer | no extra call | one model call fewer per episode; no effect on actions or scores |
| Spending | an episode stops at $50 of model spend (`max_llm_cost`) | the run-level budget applies (`--max-cost`, `--max-calls`) | none unless a budget is reached |
| Model access | LiteLLM, with `seed = 123` in the README's commands | any backend of [`models.md`](models.md); pass `--llm-option seed=123` to an OpenAI-compatible or Ollama backend to match | same requests |
| Random agent seed | from the clock (not reproducible) | from `seed`, the task and the attempt, or exactly `rng_seed` | repeatable episodes |
| Random agent with nothing within reach for an action that needs an object | crashes; the batch runner restarts the episode with a new clock seed | the argument stays empty and the game rejects the action | rare |

Two behaviours of the released runs are reproduced on purpose, because they change what
the agent sees:

- **Reading the observation consumes a message.** DiscoveryWorld queues important
  messages (instrument readings, documents read) and shows the first one as
  `extended_action_message` when the observation is read, removing it from the queue.
  The released ReAct and Plan-and-Execute runs read the observation once for every model
  call and once more after every action, to write their log, before the world advances.
  The log's read takes the message, so the agent never sees it there (it still sees
  `lastActionMessage`). The ports read exactly as often (`released_reads=true`); a test
  checks that an instrument reading is visible without the extra read and hidden with it.
- **One action fewer than the step limit.** DiscoveryWorld's step counter is already 1
  when a world is loaded, and the runner stops when the counter reaches the limit, so a
  100-step ReAct or Plan-and-Execute episode has at most 99 actions (999 of 1000). The
  ports stop at the same point (`released_step_limit=true`). The Hypothesizer and random
  agent use the whole limit, as theirs did.

Both ports also drop nothing from the prompt and add nothing to it: the observation is
the API's JSON with the images and the task progress removed, exactly as the original's
`populate_template_dictionary` builds it.
