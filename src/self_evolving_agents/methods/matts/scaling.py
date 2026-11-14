"""Test-time scaling strategies: several attempts at each task.

Three of these are from the ReasoningBank paper (section 3.3):

* :class:`ParallelScaling` – MaTTS, parallel. k trajectories for the same query under
  the same retrieved memory, one self-contrast extraction over all of them, and the
  result chosen by Best-of-N.
* :class:`VanillaScaling` – the paper's "MaTTS w/o aggregation": k trajectories, each
  judged and turned into memory on its own.
* Either of them with no memory is the paper's "MaTTS w/o memory".

One is not:

* :class:`RestartScaling` – an adaptation of sequential scaling. The published
  procedure re-examines a finished trajectory and lets the agent go on acting in the
  same episode. An episode here ends for good (the time limit is reached, or the
  spacecraft is lost), so instead the agent writes notes on its attempt and starts
  the task again from the same initial state with those notes. See
  ``docs/methods/matts.md``; this is not a reproduction of the paper's sequential
  MaTTS and should not be reported as one.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ...envs.base import EnvSpec, TextEnv
from ...llm import LLMRequest, user
from ...llm.parsing import extract_json_object
from ...types import Task, Trajectory
from ..reasoningbank.method import ReasoningBankMemory
from ..reasoningbank.render import render_trajectory
from ..stream import Attempts, Learned, Retrieval, Scaling, StreamLoop
from . import prompts

SOURCE_CONTRAST = "contrast"  # self-contrast across several trajectories (parallel)
SOURCE_RESTART = "restart"  # from a series of attempts and the notes between them


def render_for_selection(traj: Trajectory, max_chars: int = 20000) -> str:
    """A trajectory in the step format Figure 12 describes."""
    blocks = [
        f"step_num: {s.index + 1}\nthink_output: {' '.join(s.thought.split())}\n"
        f"action_output: {s.action}"
        for s in traj.steps
    ]
    text = "\n\n".join(blocks)
    if len(text) > max_chars and len(blocks) > 8:
        keep = max(2, int(len(blocks) * max_chars / len(text) / 2))
        omitted = len(blocks) - 2 * keep
        text = "\n\n".join(
            blocks[:keep] + [f"[... {omitted} steps omitted for length ...]"] + blocks[-keep:]
        )
    return text


def select_best(
    llm: Any,
    spec: EnvSpec,
    query: str,
    trajs: Sequence[Trajectory],
    *,
    max_tokens: int = 16000,
) -> tuple[int, str, str]:
    """Best-of-N (paper, Appendix A.3): the model is shown all N trajectories and picks one.

    Returns ``(index, analysis, call_id)``. Falls back to the first trajectory when
    the reply names no valid one.
    """
    if len(trajs) == 1:
        return 0, "only one attempt", ""
    response = llm.complete(
        LLMRequest(
            system=prompts.selection_system(spec.domain, len(trajs)),
            messages=[
                user(prompts.trajectories_input(query, [render_for_selection(t) for t in trajs]))
            ],
            purpose="select",
            max_tokens=max_tokens,
            temperature=0.0,
            meta={"trajectories": [t.id for t in trajs]},
        )
    )
    index, analysis = 0, " ".join(response.text.split())[:1000]
    try:
        answer = extract_json_object(response.text)
        picked = answer.get("index")
        if isinstance(picked, list):
            picked = picked[0] if picked else None
        if isinstance(picked, (int, float, str)) and 1 <= int(picked) <= len(trajs):
            index = int(picked) - 1
        analysis = str(answer.get("analysis", analysis))[:1000]
    except (ValueError, TypeError):
        pass
    return index, analysis, response.call_id


class _Repeated(Scaling):
    """k attempts at the same task under the same retrieved memory."""

    def __init__(self, llm: Any, k: int):
        if k < 1:
            raise ValueError("k must be at least 1")
        self.llm = llm
        self.k = k

    def _rollouts(self, loop: StreamLoop, env: TextEnv, task: Task, retrieval: Retrieval):
        group = loop.group(task)
        return [loop.attempt(env, retrieval, sample=i, group=group) for i in range(self.k)]


class ParallelScaling(_Repeated):
    """MaTTS with parallel scaling (paper section 3.3, Figure 3b).

    Extraction is one self-contrast call over all k trajectories, given without
    success labels, for at most ``max_items`` items (5 in the paper). The task's
    result is the trajectory chosen by Best-of-N. Only that trajectory is judged,
    for the record; the published self-contrast does not use the judge.
    """

    name = "parallel"

    def __init__(self, llm: Any, k: int, *, max_items: int = 5):
        super().__init__(llm, k)
        self.max_items = max_items

    def attempts(self, loop, env, task, query, retrieval) -> Attempts:
        trajs = self._rollouts(loop, env, task, retrieval)
        selected, why, _ = select_best(self.llm, env.spec, query, trajs)
        verdicts: list[Any] = [None] * len(trajs)
        verdicts[selected] = loop.judge_trajectory(env, query, trajs[selected])
        return Attempts(trajs, verdicts, selected=selected, selection=why)

    def learn(self, loop, env, task, query, attempts) -> Learned:
        memory = loop.memory
        if not isinstance(memory, ReasoningBankMemory):
            return Learned()
        if len(attempts.trajectories) == 1:  # k = 1 is no scaling
            return loop.learn_single(
                env, task, query, attempts.trajectories[0], attempts.verdicts[0]
            )
        extractor = memory.extractor
        rendered = [
            render_trajectory(t, observations=extractor.observations) for t in attempts.trajectories
        ]
        items, call_id = extractor.complete(
            prompts.parallel_system(env.spec.domain, self.max_items),
            prompts.trajectories_input(query, rendered),
            SOURCE_CONTRAST,
            self.max_items,
            {"trajectories": [t.id for t in attempts.trajectories]},
        )
        experience = memory.consolidate(
            task,
            query,
            attempts.trajectories,
            items,
            call_id,
            "contrast",
            {"scaling": "parallel", "k": self.k, "selection": attempts.selection},
        )
        return Learned([i.id for i in experience.items], [experience.id])


class VanillaScaling(_Repeated):
    """Test-time scaling without aggregation (paper Figure 3a, "MaTTS w/o aggregation").

    Every trajectory is judged and turned into memory independently, so a task adds
    up to k experiences. The task's result is chosen by Best-of-N as for parallel
    scaling.
    """

    name = "vanilla"

    def attempts(self, loop, env, task, query, retrieval) -> Attempts:
        trajs = self._rollouts(loop, env, task, retrieval)
        verdicts = [loop.judge_trajectory(env, query, t) for t in trajs]
        selected, why, _ = select_best(self.llm, env.spec, query, trajs)
        return Attempts(trajs, verdicts, selected=selected, selection=why)

    def learn(self, loop, env, task, query, attempts) -> Learned:
        learned = Learned()
        for traj, verdict in zip(attempts.trajectories, attempts.verdicts, strict=True):
            learned.extend(loop.learn_single(env, task, query, traj, verdict))
        return learned


class RestartScaling(_Repeated):
    """Re-attempt the task k times, carrying the agent's own notes forward. Not from the paper.

    After each attempt the agent is shown its attempts so far and asked to
    re-examine them and write notes; the next attempt starts from the same initial
    state with the notes in its system prompt. The last attempt is the task's result.
    One extraction is made over the whole series and the notes.
    """

    name = "restart"

    def __init__(self, llm: Any, k: int, *, max_items: int = 3):
        super().__init__(llm, k)
        self.max_items = max_items

    def _notes(self, env, query, trajs, notes, observations: bool) -> str:
        spec = env.spec
        body = prompts.trajectories_input(
            query, [render_trajectory(t, observations=observations) for t in trajs]
        )
        for i, note in enumerate(notes, 1):
            body += f"\n\nYour notes after attempt {i}:\n{note}"
        check = prompts.RESTART_CHECK if not notes else prompts.RESTART_CHECK_FOLLOW_UP
        response = self.llm.complete(
            LLMRequest(
                system=f"You are an agent working on {spec.domain}.\n\n{spec.instructions()}",
                messages=[user(body + "\n\n" + check)],
                purpose="refine",
                meta={"trajectories": [t.id for t in trajs]},
            )
        )
        return response.text.strip()

    def attempts(self, loop, env, task, query, retrieval) -> Attempts:
        group = loop.group(task)
        observations = getattr(getattr(loop.memory, "extractor", None), "observations", False)
        trajs: list[Trajectory] = []
        notes: list[str] = []
        for i in range(self.k):
            if i > 0:
                notes.append(self._notes(env, query, trajs, notes, observations))
            carried = ""
            if notes:
                carried = prompts.RESTART_NOTES_HEADER + "\n" + "\n\n".join(notes)
            trajs.append(loop.attempt(env, retrieval, sample=i, notes=carried, group=group))
        verdicts: list[Any] = [None] * len(trajs)
        verdicts[-1] = loop.judge_trajectory(env, query, trajs[-1])
        return Attempts(trajs, verdicts, selected=len(trajs) - 1, notes=notes)

    def learn(self, loop, env, task, query, attempts) -> Learned:
        memory = loop.memory
        if not isinstance(memory, ReasoningBankMemory):
            return Learned()
        if len(attempts.trajectories) == 1:
            return loop.learn_single(
                env, task, query, attempts.trajectories[0], attempts.verdicts[0]
            )
        extractor = memory.extractor
        body = prompts.trajectories_input(
            query,
            [
                render_trajectory(t, observations=extractor.observations)
                for t in attempts.trajectories
            ],
        )
        for i, note in enumerate(attempts.notes, 1):
            body += f"\n\nNotes written after attempt {i}:\n{note}"
        items, call_id = extractor.complete(
            prompts.restart_extraction_system(env.spec.domain, self.max_items),
            body,
            SOURCE_RESTART,
            self.max_items,
            {"trajectories": [t.id for t in attempts.trajectories]},
        )
        experience = memory.consolidate(
            task,
            query,
            attempts.trajectories,
            items,
            call_id,
            "restart",
            {"scaling": "restart", "k": self.k, "notes": attempts.notes},
        )
        return Learned([i.id for i in experience.items], [experience.id])


SCALINGS = {
    "parallel": ParallelScaling,
    "vanilla": VanillaScaling,
    "restart": RestartScaling,
}


def make_scaling(name: str, llm: Any, k: int) -> Scaling:
    """A scaling strategy by name; ``"none"`` or ``k == 1`` is one attempt per task."""
    if name == "none" or k == 1:
        if name not in ("none", *SCALINGS):
            raise ValueError(f"scaling must be 'none' or one of {tuple(SCALINGS)}")
        return Scaling()
    if name not in SCALINGS:
        raise ValueError(f"scaling must be 'none' or one of {tuple(SCALINGS)}")
    return SCALINGS[name](llm, k)
