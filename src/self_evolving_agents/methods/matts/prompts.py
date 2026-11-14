"""Prompts of memory-aware test-time scaling (MaTTS).

Sources: Ouyang et al., arXiv:2509.25140v2, Figure 11 (parallel self-contrast, and
the check instructions of sequential scaling) and Figure 12 (Best-of-N selection);
the first two are also in the reference implementation
(https://github.com/google-research/reasoning-bank, Copyright 2026 Google LLC,
Apache License 2.0, see THIRD_PARTY_NOTICES.md).

As in ``reasoningbank.prompts``, "web navigation" is replaced by the environment's
``{domain}`` and nothing else is changed in the published prompts. The two prompts at
the end are not from the paper: they belong to the ``restart`` variant, which exists
because the published sequential procedure cannot be run in an environment whose
episodes end for good.
"""

from __future__ import annotations


def parallel_system(domain: str, max_items: int = 5) -> str:
    """Self-contrast over several trajectories of one query (Figure 11, left)."""
    return (
        f"You are an expert in {domain}. You will be given a user query and multiple "
        "trajectories showing how an agent attempted the task. Some trajectories may be "
        "successful, and others may have failed.\n\n"
        "## Guidelines\n"
        "Your goal is to **compare and contrast** these trajectories to identify the most useful "
        "and generalizable strategies as memory items.\n"
        "Use **self-contrast reasoning**:\n"
        "  - Identify patterns and strategies that consistently led to success.\n"
        "  - Identify mistakes or inefficiencies from failed trajectories and formulate "
        "preventative strategies.\n"
        "  - Prefer strategies that generalize beyond specific pages or exact wording.\n\n"
        "## Important notes\n"
        "  - Think first: Why did some trajectories succeed while others failed?\n"
        f"  - You can extract *at most {max_items}* memory items from all trajectories combined.\n"
        "  - Do not repeat similar or overlapping items.\n"
        "  - Do not mention specific websites, queries, or string contents — focus on "
        "generalizable behaviors and reasoning patterns.\n"
        "  - Make sure each memory item captures **actionable** and **transferable** insights.\n\n"
        "## Output Format\n"
        "Your output must strictly follow the Markdown format shown below:\n\n"
        "```\n"
        "# Memory Item i\n"
        "## Title <the title of the memory item>\n"
        "## Description <one sentence summary of the memory item>\n"
        "## Content <1-5 sentences describing the insights learned to successfully accomplishing "
        "the task>\n"
        "```\n"
    )


def trajectories_input(query: str, trajectories: list[str]) -> str:
    """User message listing several trajectories (Figures 11 and 12, "Input Prompt")."""
    body = "\n".join(f"Trajectory {i}:\n{t}\n" for i, t in enumerate(trajectories, 1))
    return f"Query: {query}\n\nTrajectories:\n{body}"


# Figure 11, right. Quoted for reference: the published sequential procedure appends
# these to the conversation after the agent has given its answer, and the agent goes
# on acting. No environment here lets an agent continue after its episode has ended,
# so they are not used (see docs/methods/matts.md).
SEQUENTIAL_CHECK_PUBLISHED = (
    "Important: Let's carefully re-examine the previous trajectory, including your reasoning "
    "steps and actions taken.\n"
    "Pay special attention to whether you used the correct elements on the page, and whether "
    "your response addresses the user query. If you find inconsistencies, correct them. If "
    "everything seems correct, confirm your final answer.\n"
    'Output must stay in the same "<think>...</think><action></action>" format as previous '
    "trajectories."
)
SEQUENTIAL_FOLLOW_UP_PUBLISHED = (
    "Let's check again.\n"
    'Output must stay in the same "<think>...</think><action></action>" format as previous '
    "trajectories."
)


def selection_system(domain: str, n: int) -> str:
    """Best-of-N: choose the best of N trajectories without ground truth (Figure 12)."""
    return (
        f"You are an expert in evaluating {domain} agent trajectories. You will be given the "
        f"user query, and {n} candidate trajectories, each representing a sequence of steps for "
        "solving the same task. Your job is to select the single best trajectory that most "
        "effectively and efficiently solves the task, and explain your reasoning.\n\n"
        "## Input Format:\n"
        "Each trajectory consists of multiple steps. For each step, you will be provided:\n"
        "- step_num: Step index in the trajectory.\n"
        "- action_output: The action the agent takes.\n"
        "- think_output: The agent's reasoning or plan before taking the action.\n\n"
        "## Evaluation Criteria:\n\n"
        "### Progress Toward Goal\n"
        "1. How well the trajectory advances toward completing the user's task. 2. Reward "
        "tangible, meaningful progress; penalize minimal or no advancement. 3. Consider both "
        "individual step contributions and overall progress.\n\n"
        "### Trajectory Efficiency\n"
        "1. How efficiently the trajectory achieves progress given the number and complexity of "
        "steps. 2. Reward significant progress in fewer steps. 3. Favor better value-to-depth "
        "ratios. 4. Reward efficient search space exploration.\n\n"
        "### Loop Detection\n"
        "Identify loops or redundant actions. 1. Real Loops: Repeating identical observations and "
        "actions with no added value. 2. Benign Repetitions: Slight variations that still yield "
        "new information. 3. Penalize real loops heavily; penalize benign repetitions only if "
        "they waste effort.\n\n"
        "### Error Severity and Stability\n"
        "Assess severity of errors: 1. Fatal/Blocking: Major penalty. 2. Significant: Moderate "
        "penalty. 3. Minor/Recoverable: Minor penalty. 4. Penalize unstable or incoherent model "
        "reasoning. 5. Consider whether errors prevent goal completion.\n\n"
        "### Overall Trajectory Quality\n"
        "1. Logical flow of steps, clarity of strategy, and coherence. 2. Balanced exploration "
        "vs. exploitation. 3. Closeness to final goal. 4. Reward consistent progress and coherent "
        "planning.\n\n"
        "## Output Format:\n"
        "Return the evaluation as a JSON object:\n"
        "```\n"
        '{ "index": [best_trajectory_index], "analysis": "Detailed reasoning explaining why this '
        "trajectory is the best, referencing progress, efficiency, loop detection, error "
        'severity, and overall quality." }\n'
        "```\n"
    )


# --- Not from the paper: the ``restart`` variant -----------------------------------

RESTART_CHECK = (
    "Important: Let's carefully re-examine the previous attempt, including your reasoning steps "
    "and the actions taken.\n"
    "Pay special attention to whether each action had the effect you expected, where reward or "
    "progress was lost, and whether the task's requirements were met by the end.\n"
    "If you find mistakes or inefficiencies, state concretely what you will do differently in the "
    "next attempt. If everything seems correct, say so and state what you will keep doing.\n"
    "Reply with a short list of notes for your next attempt."
)
RESTART_CHECK_FOLLOW_UP = (
    "Let's check again. Compare the latest attempt with the earlier ones and with your notes.\n"
    "Reply with an updated short list of notes for your next attempt."
)
RESTART_NOTES_HEADER = (
    "You have attempted this task before from the same starting situation. These are your own "
    "notes from re-examining the earlier attempts:"
)


def restart_extraction_system(domain: str, max_items: int = 3) -> str:
    """Extraction from a series of attempts with the notes written between them."""
    return (
        f"You are an expert in {domain}. You will be given a user query and a series of attempts "
        "at it by the same agent. After each attempt the agent re-examined what it had done and "
        "wrote notes before trying again.\n\n"
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
        "  - You must not repeat similar or overlapping items.\n"
        "  - Do not mention specific websites, queries, or string contents, but rather focus on "
        "the generalizable insights.\n\n"
        "## Output Format\n"
        "Your output must strictly follow the Markdown format shown below:\n\n"
        "```\n"
        "# Memory Item i\n"
        "## Title <the title of the memory item>\n"
        "## Description <one sentence summary of the memory item>\n"
        "## Content <1-3 sentences describing the insights learned to successfully accomplishing "
        "the task>\n"
        "```\n"
    )
