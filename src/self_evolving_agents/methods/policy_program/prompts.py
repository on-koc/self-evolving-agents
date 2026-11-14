"""Prompts of the policy-writing agent. Not from the ReasoningBank paper."""

from __future__ import annotations

# The published instruction with its last sentence changed: the agent makes one
# decision (the policy) instead of acting step by step.
MEMORY_INSTRUCTION_POLICY = (
    "Below are some memory items that I accumulated from past interaction from the environment "
    "that may be helpful to solve the task. You can use it when you feel it's relevant. Before "
    "writing the policy, please first explicitly discuss if you want to use each memory item or "
    "not."
)

POLICY_FORMAT = """\
You will not choose actions step by step. Instead, write one decision policy now. It will be executed unchanged at every step of the episode, so it must cover every situation that can arise.

The policy is a JSON object:

```json
{
  "name": "short-name",
  "params": {"threshold_a": 0.5, "window_s": 600},
  "rules": [
    {"if": {"feature_x": {"<": "$threshold_a"}, "feature_y": {"==": 1}}, "do": "action_1"},
    {"if": {"any": [{"feature_z": {">": "$window_s"}}, {"not": {"feature_w": {">=": 0.2}}}]}, "do": "action_2"}
  ],
  "default": "action_3"
}
```

- Rules are checked in order and the first one whose condition holds decides the action; `default` applies when none hold.
- A condition maps feature names to comparisons (`<`, `<=`, `>`, `>=`, `==`, `!=`). Several features in one condition must all hold. `all`, `any` and `not` combine conditions.
- A threshold is a number, or `"$name"` to refer to an entry of `params`. Use parameters for the numbers you might want to tune.
- Only the features and actions listed for this environment may be used. The names in the example above are placeholders.

Reply with a brief rationale, then the policy in a ```json code block."""
