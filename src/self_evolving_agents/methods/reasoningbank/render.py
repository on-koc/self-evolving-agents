"""Text shown to the extractor, the judge and the agent.

The paper's extractor sees, for each step, the agent's reasoning and its action, and
nothing else ("we use the thinking process ... as the approximation of [the
observations]", section 3.1). That is the default here. Methods built on top can ask
for the observation summary and the action's feedback as well (``observations=True``),
which matters for agents that produce no step-by-step reasoning.

Ground-truth outcome metrics are never rendered: at test time nobody hands the agent
the answer.
"""

from __future__ import annotations

from collections.abc import Sequence

from ...agents.base import MemoryBlock
from ...types import Step, Trajectory
from . import prompts
from .schema import MemoryItem


def render_memory(items: Sequence[MemoryItem], with_description: bool = False) -> str:
    return "\n\n".join(item.render(i, with_description) for i, item in enumerate(items, 1))


def memory_block(
    items: Sequence[MemoryItem],
    *,
    instruction: str = prompts.MEMORY_INSTRUCTION,
    with_description: bool = False,
) -> MemoryBlock:
    """The retrieved items as they go into the agent's system prompt (Appendix A.2)."""
    if not items:
        return MemoryBlock()
    return MemoryBlock(
        text=instruction + "\n\n" + render_memory(items, with_description),
        item_ids=[item.id for item in items],
    )


def render_step(step: Step, observations: bool = False) -> str:
    """One step as ``<think>...</think><action>...</action>``, the reference code's layout."""
    text = f"<think>\n{step.thought.strip()}\n</think>\n<action>\n{step.action}\n</action>"
    if not observations:
        return text
    feedback = f"\n<feedback>\n{step.result}\n</feedback>" if step.result else ""
    return f"<observation>\n{step.brief}\n</observation>\n{text}{feedback}"


def _collapse(steps: Sequence[Step], observations: bool) -> list[str]:
    """Render steps, merging long runs of one identical action that carry no reasoning.

    A rule policy can repeat an action for dozens of steps. The first and last step
    of such a run are kept and the rest is summarised in one line. Steps with
    reasoning are never merged, so a step-by-step agent's trajectory is unaffected.
    """
    out: list[str] = []
    i = 0
    while i < len(steps):
        j = i
        while (
            j + 1 < len(steps)
            and steps[j + 1].action == steps[i].action
            and not steps[j + 1].thought
            and not steps[i].thought
        ):
            j += 1
        if j - i >= 3:
            out.append(render_step(steps[i], observations))
            out.append(f"[{steps[i].action} repeated {j - i - 1} more times]")
            out.append(render_step(steps[j], observations))
        else:
            out.extend(render_step(s, observations) for s in steps[i : j + 1])
        i = j + 1
    return out


def render_trajectory(
    traj: Trajectory, *, observations: bool = False, max_chars: int = 60000
) -> str:
    """The trajectory as the extractor sees it.

    Trajectories longer than ``max_chars`` are shortened from the middle: the
    beginning and the end are kept in full and a marker says how many step records
    were left out. The paper's episodes are at most 30 steps and need no such limit;
    simulated episodes here can run to well over a hundred.
    """
    blocks = _collapse(traj.steps, observations)
    text = "\n\n".join(blocks)
    if len(text) > max_chars and len(blocks) > 8:
        head: list[str] = []
        tail: list[str] = []
        budget = max_chars
        lo, hi = 0, len(blocks) - 1
        take_head = True
        while lo <= hi:
            block = blocks[lo] if take_head else blocks[hi]
            if len(block) + 2 > budget:
                break
            budget -= len(block) + 2
            if take_head:
                head.append(block)
                lo += 1
            else:
                tail.append(block)
                hi -= 1
            take_head = not take_head
        omitted = hi - lo + 1
        middle = [f"[... {omitted} step records omitted for length ...]"] if omitted > 0 else []
        text = "\n\n".join(head + middle + tail[::-1])
    header = traj.meta.get("trajectory_header", "")
    return f"{header}\n\n{text}" if header else text


def render_actions(traj: Trajectory, max_chars: int = 20000) -> str:
    """The agent's action history, one action per line, as the judge sees it."""
    lines = [f"{step.index + 1}. {step.action}" for step in traj.steps]
    text = "\n".join(lines)
    if len(text) > max_chars:
        keep = max(4, max_chars // (2 * max(len(max(lines, key=len)), 1)))
        omitted = len(lines) - 2 * keep
        if omitted > 0:
            text = "\n".join(
                lines[:keep] + [f"[... {omitted} actions omitted ...]"] + lines[-keep:]
            )
    return text


def final_state(traj: Trajectory) -> str:
    """The last observation, and the feedback to the last action (which says how it ended)."""
    parts = [traj.final_observation.strip()]
    if traj.steps and traj.steps[-1].result:
        parts.append(f"Feedback to the last action: {traj.steps[-1].result}")
    return "\n".join(p for p in parts if p)
