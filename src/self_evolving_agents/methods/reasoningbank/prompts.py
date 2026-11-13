"""Prompts of ReasoningBank, as published.

Sources: Ouyang et al., *ReasoningBank: Scaling Agent Self-Evolving with Reasoning
Memory* (arXiv:2509.25140v2), Figure 9 (memory extraction), Figure 10
(LLM-as-a-judge) and Appendix A.2 (the instruction placed before retrieved items);
and the reference implementation (https://github.com/google-research/reasoning-bank,
Copyright 2026 Google LLC, Apache License 2.0, see THIRD_PARTY_NOTICES.md), whose
software-engineering port carries the same extraction prompts.

What differs from the published text, and nothing else:

* "web navigation" is replaced by a ``{domain}`` supplied by the environment. The
  authors made the same substitution for their software-engineering experiments.
* The judge's system instruction describes three kinds of web task. That passage is
  replaced by the environment's own statement of what counts as success. The frame
  around it, the inputs and the two-line answer format are the published ones.
* Emphasis markers (``**...**``, ``*at most 3*``) follow the reference code; the
  figures do not show markup.

The reference code's WebArena prompts were revised after publication (a different
fourth note, "when or when NOT to use" in the description field, strictness rules for
the judge). Those revisions are available through ``revised=True`` / ``strict=True``
and are off by default.
"""

from __future__ import annotations

# Appendix A.2; identical in the reference code (agents/legacy/agent.py).
MEMORY_INSTRUCTION = (
    "Below are some memory items that I accumulated from past interaction from the environment "
    "that may be helpful to solve the task. You can use it when you feel it's relevant. In each "
    "step, please first explicitly discuss if you want to use each memory item or not, and then "
    "take action."
)

_FORMAT = """\
## Output Format
Your output must strictly follow the Markdown format shown below:

```
# Memory Item i
## Title <the title of the memory item>
## Description <{description}>
## Content <{content}>
```
"""

_NOTE_PUBLISHED = (
    "  - Do not mention specific websites, queries, or string contents, but rather focus on the "
    "generalizable insights."
)
# Fourth note of the reference code's later WebArena prompts.
_NOTE_REVISED_SUCCESS = (
    "  - Prefer concrete, actionable procedures over abstract principles. Do not embed specific "
    "product names, queries, or literal string contents from the task."
)
_NOTE_REVISED_FAILURE = (
    "  - Prefer concrete, actionable recovery procedures over abstract principles. Do not embed "
    "specific product names, queries, or literal string contents from the task."
)
_DESCRIPTION_PUBLISHED = "one sentence summary of the memory item"
_DESCRIPTION_REVISED = "one sentence summary describing when or when NOT to use the memory item"
_CONTENT_PUBLISHED = (
    "1-3 sentences describing the insights learned to successfully accomplishing the task"
)


def success_extraction_system(domain: str, max_items: int = 3, revised: bool = False) -> str:
    """System instruction for extracting items from a successful trajectory (Figure 9, left)."""
    return (
        f"You are an expert in {domain}. You will be given a user query, the corresponding "
        "trajectory that represents **how an agent successfully accomplished the task**.\n\n"
        "## Guidelines\n"
        "You need to extract and summarize useful insights in the format of memory items based on "
        "the agent's successful trajectory.\n"
        "The goal of summarized memory items is to be helpful and generalizable for future similar "
        "tasks.\n\n"
        "## Important notes\n"
        "  - You must first think why the trajectory is successful, and then summarize the "
        "insights.\n"
        f"  - You can extract *at most {max_items}* memory items from the trajectory.\n"
        "  - You must not repeat similar or overlapping items.\n"
        f"{_NOTE_REVISED_SUCCESS if revised else _NOTE_PUBLISHED}\n\n"
        + _FORMAT.format(
            description=_DESCRIPTION_REVISED if revised else _DESCRIPTION_PUBLISHED,
            content=_CONTENT_PUBLISHED,
        )
    )


def failure_extraction_system(domain: str, max_items: int = 3, revised: bool = False) -> str:
    """System instruction for extracting items from a failed trajectory (Figure 9, right)."""
    return (
        f"You are an expert in {domain}. You will be given a user query, the corresponding "
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
        "  - You must not repeat similar or overlapping items.\n"
        f"{_NOTE_REVISED_FAILURE if revised else _NOTE_PUBLISHED}\n\n"
        + _FORMAT.format(
            description=_DESCRIPTION_REVISED if revised else _DESCRIPTION_PUBLISHED,
            content=_CONTENT_PUBLISHED,
        )
    )


def extraction_input(query: str, trajectory: str) -> str:
    """User message for extraction (Figure 9, "Input Prompt")."""
    return f"Query: {query}\n\nTrajectory:\n{trajectory}"


# Added to the judge by the reference code after publication; not in Figure 10.
_STRICTNESS = (
    "*Strictness rules*\n"
    "Before calling a task successful, verify all three:\n"
    "- Completeness: every constraint in the task is satisfied by the end of the episode, not "
    "merely attempted.\n"
    "- Grounding: everything the verdict relies on is traceable to the action history or the "
    "final state; what was inferred or guessed without a visible source counts as failure.\n"
    "- Right target: the agent acted on what the task names, not on something adjacent.\n"
    "When uncertain on any of these, mark failure. A false success is more harmful than a "
    "false failure, because memory induction amplifies it into future behavior.\n\n"
)


def judge_system(domain: str, success_doc: str, strict: bool = False) -> str:
    """System instruction of the LLM-as-a-judge (Figure 10).

    ``success_doc`` is the environment's statement of what counts as success; it
    stands where the published prompt describes its three types of web task.
    """
    criterion = f"{success_doc.strip()}\n\n" if success_doc.strip() else ""
    return (
        f"You are an expert in evaluating the performance of an agent working on {domain}. Given "
        "the task, the agent's action history and the final state of the environment, your goal "
        "is to decide whether the agent's execution is successful or not.\n\n"
        f"{criterion}"
        f"{_STRICTNESS if strict else ''}"
        "*IMPORTANT*\n"
        "Format your response into two lines as shown below:\n\n"
        "Thoughts: <your thoughts and reasoning process>\n"
        'Status: "success" or "failure"\n'
    )


def judge_input(query: str, history: str, final_state: str) -> str:
    """User message for the judge (Figure 10, "Input Prompt")."""
    return (
        f"User Intent: {query}\n\n"
        f"Trajectory:\n{history}\n\n"
        "The detailed final state of the environment:\n\n"
        f"```md\n{final_state or '(not available)'}\n```"
    )
