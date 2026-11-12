"""Prompts for memory use, judging, extraction and test-time scaling.

The extraction, judging and scaling prompts are adapted from the reference
implementation of ReasoningBank (https://github.com/google-research/reasoning-bank,
Copyright 2026 Google LLC, Apache License 2.0): ``WebArena/prompts/memory_instruction.py``
and ``WebArena/prompts/autoeval_prompts.py``. ``MEMORY_INSTRUCTION`` is quoted
unchanged. See THIRD_PARTY_NOTICES.md.

What changed, and why:

* "web navigation" became a ``{domain}`` supplied by the environment.
* The extraction prompts ask for the *conditions* under which an insight was
  observed. On the web a task is identified by its query; in a simulator the same
  task runs under different operating regimes, and a rule that holds in one regime
  can fail in another.
* The extraction prompts ask that explanations be marked as hypotheses. A trajectory
  shows what happened; it rarely shows why.
* The judge's strictness rules were restated for episodes that end by failure
  condition or time limit instead of by an answer to a user.
* Sequential scaling re-examines a finished attempt and writes notes for the next
  one, because a simulated episode cannot be amended after the fact the way an
  answer to a user can.
* The best-of-N selection prompt is new; the paper describes it (Figure 12) but the
  released code does not include it.
"""

from __future__ import annotations

# Quoted verbatim from the reference implementation (agent system-prompt suffix).
MEMORY_INSTRUCTION = (
    "Below are some memory items that I accumulated from past interaction from the environment "
    "that may be helpful to solve the task. You can use it when you feel it's relevant. In each "
    "step, please first explicitly discuss if you want to use each memory item or not, and then "
    "take action."
)

# Used instead of MEMORY_INSTRUCTION when the model writes one policy for the whole
# episode rather than acting step by step.
MEMORY_INSTRUCTION_POLICY = (
    "Below are some memory items that I accumulated from past interaction from the environment "
    "that may be helpful to solve the task. You can use it when you feel it's relevant. Before "
    "writing the policy, please first explicitly discuss if you want to use each memory item or "
    "not."
)

_ITEM_FORMAT = """\
## Output Format
Your output must strictly follow the Markdown format shown below:

```
# Memory Item i
## Title <the title of the memory item>
## Description <one sentence summary describing when or when NOT to use the memory item>
## Content <{length} describing the insights learned to {purpose}>
```
"""

_SHARED_NOTES = """\
  - You must not repeat similar or overlapping items.
  - Prefer concrete, actionable procedures over abstract principles. Do not embed identifiers that only exist in this episode (object IDs, coordinates, timestamps).
  - A rule that works under one configuration can fail under another. In the description, state the conditions under which the insight was observed, using the conditions given in the task, and when it should NOT be applied.
  - Report quantities you saw in the trajectory as observations. When you explain *why* something worked or failed, mark the explanation as a hypothesis unless the trajectory itself demonstrates it."""


def success_extraction_system(domain: str, max_items: int = 3) -> str:
    return (
        f"You are an expert in {domain}. You will be given a task, and the corresponding "
        "trajectory that represents **how an agent successfully accomplished the task**.\n\n"
        "## Guidelines\n"
        "You need to extract and summarize useful insights in the format of memory items based on "
        "the agent's successful trajectory.\n"
        "The goal of summarized memory items is to be helpful and generalizable for future similar "
        "tasks.\n\n"
        "## Important notes\n"
        "  - You must first think why the trajectory is successful, and then summarize the insights.\n"
        f"  - You can extract *at most {max_items}* memory items from the trajectory.\n"
        f"{_SHARED_NOTES}\n\n"
        + _ITEM_FORMAT.format(
            length="1-3 sentences",
            purpose="successfully accomplishing similar tasks in the future",
        )
    )


def failure_extraction_system(domain: str, max_items: int = 3) -> str:
    return (
        f"You are an expert in {domain}. You will be given a task, and the corresponding "
        "trajectory that represents **how an agent attempted to resolve the task but failed**.\n\n"
        "## Guidelines\n"
        "You need to extract and summarize useful insights in the format of memory items based on "
        "the agent's failed trajectory.\n"
        "The goal of summarized memory items is to be helpful and generalizable for future similar "
        "tasks.\n\n"
        "## Important notes\n"
        "  - You must first reflect and think why the trajectory failed, and then summarize what "
        "lessons you have learned or strategies to prevent the failure in the future.\n"
        f"  - You can extract *at most {max_items}* memory items from the trajectory.\n"
        f"{_SHARED_NOTES}\n\n"
        + _ITEM_FORMAT.format(
            length="1-3 sentences",
            purpose="avoid such failures and successfully accomplishing similar tasks in the future",
        )
    )


def contrast_extraction_system(domain: str, max_items: int = 5) -> str:
    """Self-contrast across several attempts at the same task (MaTTS, parallel scaling)."""
    return (
        f"You are an expert in {domain}. You will be given a task and multiple trajectories "
        "showing how an agent attempted the task.\n"
        "Some trajectories may be successful, and others may have failed.\n\n"
        "## Guidelines\n"
        "Your goal is to **compare and contrast** these trajectories to identify the most useful "
        "and generalizable strategies as memory items.\n"
        "Use **self-contrast reasoning**:\n"
        "  - Identify patterns and strategies that consistently led to success.\n"
        "  - Identify mistakes or inefficiencies from failed trajectories and formulate "
        "preventative strategies.\n"
        "  - Prefer strategies that generalize beyond this particular episode.\n\n"
        "## Important notes\n"
        "  - Think first: Why did some trajectories succeed while others failed?\n"
        f"  - You can extract *at most {max_items}* memory items from all trajectories combined.\n"
        f"{_SHARED_NOTES}\n"
        "  - The trajectories start from the same situation, so a difference in outcome is "
        "evidence about the difference in what the agent did. Say which difference you think "
        "mattered.\n"
        "  - Make sure each memory item captures **actionable** and **transferable** insights.\n\n"
        + _ITEM_FORMAT.format(
            length="1-5 sentences",
            purpose="avoid such failures and successfully accomplishing similar tasks in the future",
        )
    )


def refine_extraction_system(domain: str, max_items: int = 3) -> str:
    """Extraction from a series of attempts with refinement notes (MaTTS, sequential scaling)."""
    return (
        f"You are an expert in {domain}. You will be given a task and a series of attempts at it "
        "by the same agent. After each attempt the agent re-examined what it had done and wrote "
        "notes before trying again.\n\n"
        "## Guidelines\n"
        "You need to extract and summarize useful insights in the format of memory items from the "
        "whole series: the attempts, the corrections the agent made between them, and whether "
        "those corrections helped.\n"
        "The goal of summarized memory items is to be helpful and generalizable for future similar "
        "tasks.\n\n"
        "## Important notes\n"
        "  - You must first think about what changed between attempts and what effect each change "
        "had, and then summarize the insights.\n"
        f"  - You can extract *at most {max_items}* memory items from the series.\n"
        f"{_SHARED_NOTES}\n\n"
        + _ITEM_FORMAT.format(
            length="1-3 sentences",
            purpose="successfully accomplishing similar tasks in the future",
        )
    )


def judge_system(domain: str, success_doc: str) -> str:
    criterion = f"\n{success_doc}\n" if success_doc else ""
    return (
        f"You are an expert in evaluating the performance of an agent working on {domain}. Given "
        "the task, the rules of the environment, the agent's trajectory (what it observed, its "
        "reasoning, the actions it took and the feedback it received) and the final state, your "
        "goal is to decide whether the agent's execution is successful or not.\n"
        f"{criterion}\n"
        "*Strictness rules*\n"
        "Before calling an episode successful, verify all three:\n"
        "- Completeness: every requirement in the task statement is satisfied by the end of the "
        "episode, not merely attempted.\n"
        "- Grounding: rely only on what the observations and feedback in the trajectory show. What "
        "the agent says or believes it achieved does not count as evidence.\n"
        "- No terminal failure: if the episode ended because a failure condition named in the "
        "rules was met, it is a failure regardless of earlier progress.\n"
        "When uncertain on any of these, mark failure. A false success is more harmful than a "
        "false failure, because memory induction amplifies it into future behavior.\n\n"
        "*IMPORTANT*\n"
        "Format your response into two lines as shown below:\n\n"
        "Thoughts: <your thoughts and reasoning process>\n"
        'Status: "success" or "failure"\n'
    )


SEQUENTIAL_CHECK = (
    "Important: Let's carefully re-examine the previous attempt, including your reasoning steps "
    "and the actions taken.\n"
    "Pay special attention to whether each action had the effect you expected, where reward or "
    "progress was lost, and whether the task's requirements were met by the end.\n"
    "If you find mistakes or inefficiencies, state concretely what you will do differently in the "
    "next attempt. If everything seems correct, say so and state what you will keep doing.\n"
    "Reply with a short list of notes for your next attempt."
)

SEQUENTIAL_CHECK_FOLLOWING = (
    "Let's check again. Compare the latest attempt with the earlier ones and with your notes.\n"
    "Reply with an updated short list of notes for your next attempt."
)

REFINEMENT_NOTES_HEADER = (
    "You have attempted this task before from the same starting situation. These are your own "
    "notes from re-examining the earlier attempts:"
)


def selection_system(domain: str, n: int) -> str:
    """Best-of-N: choose the best attempt without access to ground truth."""
    return (
        f"You are an expert in {domain}. You will be given a task and {n} trajectories showing "
        "different attempts at it by an agent. Your goal is to select the attempt that best "
        "accomplished the task.\n\n"
        "Judge only from what the trajectories show: the observations, the feedback the agent "
        "received and the final state. An attempt that ended in a failure condition is worse than "
        "one that did not, whatever else it achieved. Between otherwise comparable attempts, "
        "prefer the one that met more of the task's requirements.\n\n"
        "*IMPORTANT*\n"
        "Format your response into two lines as shown below:\n\n"
        "Thoughts: <your comparison of the attempts>\n"
        "Best: <the number of the best trajectory>\n"
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
