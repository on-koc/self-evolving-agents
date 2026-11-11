"""Turn trajectories into text for the judge, the extractor and the selector.

Only agent-visible information is rendered: what the agent was shown, what it
thought, what it did and the feedback it got. Ground-truth outcome metrics are
never included, because at test time nobody hands the agent the answer.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..types import Step, Trajectory
from .schema import MemoryItem


def render_memory(items: Sequence[MemoryItem]) -> str:
    """Memory block for a system prompt, in the reference implementation's layout."""
    return "\n\n".join(item.render(i) for i, item in enumerate(items, 1))


def _step_text(step: Step, with_thought: bool = True) -> str:
    lines = [f"[step {step.index + 1}] {step.brief}"]
    if with_thought and step.thought:
        lines.append(f"<think>{step.thought.strip()}</think>")
    lines.append(f"<action>{step.action}</action>")
    if step.result:
        lines.append(f"-> {step.result}")
    return "\n".join(lines)


def _collapse(steps: Sequence[Step]) -> list[str]:
    """Render steps, merging runs of an identical action that carry no reasoning.

    A rule policy can repeat one action for dozens of steps; showing the first and
    last of each run keeps what changed without the repetition.
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
            total = sum(s.reward for s in steps[i : j + 1])
            out.append(_step_text(steps[i]))
            out.append(
                f"[steps {steps[i].index + 2}-{steps[j].index}] {steps[i].action} repeated "
                f"{j - i - 1} more times"
            )
            out.append(_step_text(steps[j]))
            out.append(
                f"(reward over steps {steps[i].index + 1}-{steps[j].index + 1}: {total:+.4f})"
            )
        else:
            out.extend(_step_text(s) for s in steps[i : j + 1])
        i = j + 1
    return out


def render_trajectory(traj: Trajectory, max_chars: int = 24000) -> str:
    """Step-by-step account of an episode, shortened from the middle if it is too long.

    The beginning (how the agent set out) and the end (how it finished or failed) are
    kept in full; steps in between are dropped with an explicit marker saying how
    many were left out.
    """
    blocks = _collapse(traj.steps)
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

    header = []
    strategy = traj.meta.get("policy_text")
    if strategy:
        header.append("The agent committed to this policy before the episode:\n" + strategy)
        rationale = traj.meta.get("policy_rationale")
        if rationale:
            header.append("Its stated rationale: " + rationale)
    footer = [f"Total reward received: {traj.total_reward:+.4f} over {len(traj.steps)} steps."]
    return "\n\n".join(header + [text] + footer)


def render_task(query: str, traj: Trajectory | None = None) -> str:
    return f"**Task:** {query}"


def render_for_extraction(
    query: str, traj: Trajectory, verdict_thoughts: str = "", verdict_label: str = ""
) -> str:
    """User message for single-trajectory extraction.

    As in the reference implementation, the judge's reasoning is appended so that
    the extractor knows why the episode was labelled the way it was.
    """
    text = f"**Task:** {query}\n\n**Trajectory:**\n{render_trajectory(traj)}"
    if traj.final_observation:
        text += f"\n\n**Final state:**\n{traj.final_observation}"
    if verdict_thoughts and verdict_label:
        outcome = "succeeded" if verdict_label == "success" else "failed"
        text += f"\n\nThe task {outcome} because: {verdict_thoughts}"
    return text


def render_many(query: str, trajs: Sequence[Trajectory], per_traj_chars: int = 12000) -> str:
    """User message showing several attempts at the same task."""
    parts = [f"**Task:** {query}"]
    for i, traj in enumerate(trajs, 1):
        body = render_trajectory(traj, max_chars=per_traj_chars)
        final = f"\n\nFinal state:\n{traj.final_observation}" if traj.final_observation else ""
        parts.append(f"**Trajectory {i}:**\n{body}{final}")
    return "\n\n".join(parts)
