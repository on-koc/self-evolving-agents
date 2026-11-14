# Policy-writing agent (adaptation)

**Origin:** this project. **Code:** `methods/policy_program/`.
**Evidence in this repository:** verified for correctness with scripted stand-ins;
never run with a language model.

## Motivation

The paper's agent makes one model call per action. A three-orbit scanning episode is
about 105 actions, so a stream of 30 episodes is over 3,000 calls per method, before
judging and extraction. Two things follow from that: comparisons become expensive,
and the agent's strategy exists only implicitly, spread over a hundred decisions.

This agent has the model write its strategy down once, as an executable policy.

## The method

Before the episode the model is given the task, the environment's documentation, the
features a policy may read and the actions it may take, and whatever a memory method
retrieved. It replies with a short rationale and a rule policy in JSON: an ordered
list of `if condition then action` rules over named features, a default action, and
named parameters. The policy is validated; if it is invalid the model is told why and
asked again (three attempts). Then the policy is executed unchanged at every step.

```json
{"name": "reserve", "params": {"low": 0.3},
 "rules": [{"if": {"battery": {"<": "$low"}}, "do": "charge"}],
 "default": "scan"}
```

## Implementation

| Module | Contents |
|---|---|
| `agent.py` | `PolicyProgramAgent` |
| `prompts.py` | the policy format, and the memory instruction with its last sentence changed ("Before writing the policy, please first explicitly discuss if you want to use each memory item or not") |
| `config.py` | `PolicyProgramConfig` (the baseline's parameters) |

It is an agent, so it can be paired with any memory method: `--agent policy_program`
on `sea run`, or `"agent": "policy_program"` in a protocol. The method named
`policy_program` is that agent with the ReasoningBank memory.

## Differences from the ReasoningBank baseline

- **Acting:** one model call per episode instead of one per step. The agent cannot
  react to anything its rules do not anticipate, and it does not reason at each step.
- **Memory instruction:** the published instruction with its last sentence adapted
  to a single decision.
- **Extraction input:** the published extractor sees reasoning and action at each
  step. This agent produces no step-by-step reasoning, so the extractor is shown the
  policy and its rationale, and each step's observation summary and feedback
  (`observations=true` is forced). Long runs of one identical action are summarised.

The judge, the bank, retrieval and consolidation are the baseline's.

## Assumptions and dependencies

- The environment exposes named numeric features and a small set of named actions.
  The scanning environments do. DiscoveryWorld does not, so this agent cannot be
  used there.
- A fixed rule list is expressive enough for the task. For the scanning task the
  reference policy is itself such a list, so the answer is yes by construction.

## Running it

```bash
sea run --method policy_program --env toy-scan --regime nominal,small_battery --order interleaved --seeds 0:3 --llm offline-demo --out runs/policy-dry
```

With no memory, for the reference point of a comparison under this agent:

```bash
sea run --method no_memory --agent policy_program --env toy-scan --seeds 0:3 --llm offline-demo --out runs/policy-none-dry
```

`protocols/scan_policy_agent.json` compares every memory method under this agent.

## Expected behaviour and limitations

A run costs roughly one fiftieth of a step-by-step run (estimated from prompt sizes,
not measured with a model). The price is that results obtained with it are results
about *this* agent. A memory that helps a policy-writing agent need not help a
step-by-step one, and the reverse: the comparison under this agent is not a
substitute for the comparison under the paper's agent, only a cheaper first look.

Because the strategy is explicit, a policy an agent wrote can be rerun on other seeds
and conditions without the model. That is the property the claim graph relies on,
and the route by which model-written strategies could be tested there.
