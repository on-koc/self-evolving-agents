"""DiscoveryWorld's Plan-and-Execute baseline, ported to this repository's agent interface.

A planner writes one step of a plan at a time ("Step 3: Find the key to the door"),
seeing the task and every earlier step with its result. An executor, a ReAct
controller with its own prompt, carries the step out in the game until it submits
("Task completed! ..." or "Task failed! ..."); its submission is the step's result.
The episode ends when the planner writes a step ending in "Done!", when the task is
complete, or at the step limit. Decoding is greedy; the planner writes at most 100
tokens and stops at a line break, the executor at most 400, stopped at a closing code
fence (``agents/recoma/configs/plan_and_execute.jsonnet``).

Both prompts are byte-identical to the released agent's (a test compares fingerprints
of prompts produced by the original code). Departures and memory placement:
``docs/agents.md``.
"""

from __future__ import annotations

import re
import time
from typing import Any

from ...envs.base import TextEnv
from ...types import Action, Observation, Step, Trajectory
from ..base import Agent, MemoryBlock, run_episode
from . import prompts, recoma
from .react import (
    MEMORY_SLOT,
    UNUSABLE_REPLY,
    Controller,
    Reads,
    at_step_limit,
    knowledge_text,
    required_env,
    to_action,
    with_memory,
)

PLAN_ANCHOR = "\n\nNow solve this task:"
_STEP = re.compile("Step [0-9]+: (.*)")
MEMORY_IN = ("both", "planner", "executor", "none")


def extract_step(plan_step: str) -> str:
    """``DiscoveryworldPlanAndExecute.extract_step``: the text after "Step N: "."""
    match = _STEP.match(plan_step)
    return match.group(1) if match else plan_step


def planner_input(task: str, plan: list[tuple[str, str]]) -> str:
    """``create_planner_input``: the task and the steps so far, as conversation turns."""
    text = task + "\n\nPlan:\n"
    for step, result in plan:
        text += "ASSISTANT:\n"
        text += step
        text += "\nUSER:\n"
        text += " --" + result + "\n"
    return text


def executer_input(current: str, plan: list[tuple[str, str]]) -> str:
    """``create_executer_input``: the step to carry out and the earlier steps' results."""
    text = "**" + current + "**\n\nPrevious Sub-Tasks:\n"
    for index, (step, result) in enumerate(plan):
        text += f"Subtask {index + 1}: {extract_step(step)}\n"
        text += " Result: " + result + "\n"
    return text


class PlanExecuteAgent(Agent):
    """DiscoveryWorld's Plan-and-Execute agent, with an optional memory from a method.

    Args:
        llm: the model, for planner and executor.
        temperature: 0.0 (greedy), as released.
        plan_max_tokens: reply limit of a planner call (100).
        act_max_tokens: reply limit of an executor call (400).
        max_output_length: characters of subtask and history in an executor prompt
            (10,000).
        termination_divisor: the executor is asked whether it wants to give up once
            its subtask has taken more than step limit / this many actions (5).
        max_llm_calls: the episode ends once this many calls have been made (1,000).
        memory_in: which prompts carry a method's memory: ``both`` (default),
            ``planner``, ``executor`` or ``none``.
        released_reads: read the observation as often as the released runs did (see
            :class:`.react.ReActAgent`).
        released_step_limit: stop at DiscoveryWorld's own step count, as released (see
            :class:`.react.ReActAgent`).
    """

    kind = "plan_execute"

    def __init__(
        self,
        llm: Any,
        *,
        temperature: float | None = 0.0,
        plan_max_tokens: int = 100,
        act_max_tokens: int = 400,
        max_output_length: int = 10000,
        termination_divisor: float = 5,
        max_llm_calls: int = 1000,
        memory_in: str = "both",
        released_reads: bool = True,
        released_step_limit: bool = True,
    ):
        if memory_in not in MEMORY_IN:
            raise ValueError(f"memory_in must be one of {MEMORY_IN}")
        self.llm = llm
        self.temperature = temperature
        self.plan_max_tokens = plan_max_tokens
        self.act_max_tokens = act_max_tokens
        self.max_output_length = max_output_length
        self.termination_divisor = termination_divisor
        self.max_llm_calls = max_llm_calls
        self.memory_in = memory_in
        self.released_reads = released_reads
        self.released_step_limit = released_step_limit

    @property
    def descriptor(self) -> dict[str, Any]:
        return {
            "id": f"plan_execute:{getattr(self.llm, 'model', 'model')}",
            "kind": self.kind,
            "model": getattr(self.llm, "model", None),
            "temperature": self.temperature,
            "plan_max_tokens": self.plan_max_tokens,
            "act_max_tokens": self.act_max_tokens,
            "max_output_length": self.max_output_length,
            "memory_in": self.memory_in,
            "released_reads": self.released_reads,
            "released_step_limit": self.released_step_limit,
        }

    def _plan(
        self,
        env: Any,
        reads: Reads,
        task: str,
        plan: list[tuple[str, str]],
        memory: str,
        sample: int,
        step: int,
    ) -> tuple[str, str | None]:
        reads.observation(env)  # the original reads the observation for this call too
        template = prompts.PLANNER_TEMPLATE
        values = {"input_str": planner_input(task, plan)}
        if memory and self.memory_in in ("both", "planner"):
            prompt = prompts.render(with_memory(template, PLAN_ANCHOR), values)
            prompt = prompt.replace(MEMORY_SLOT, memory, 1)
        else:
            prompt = prompts.render(template, values)
        return recoma.generate(
            self.llm,
            prompt,
            max_tokens=self.plan_max_tokens,
            stop=["\n"],
            temperature=self.temperature,
            purpose="plan",
            sample=sample,
            meta={"step": step, "plan_step": len(plan) + 1},
        )

    def run(
        self,
        env: TextEnv,
        *,
        first_observation: Observation | None = None,
        memory: MemoryBlock | None = None,
        notes: str = "",
        sample: int = 0,
        meta: dict[str, Any] | None = None,
    ) -> Trajectory:
        required_env(env)
        if first_observation is None:
            first_observation = env.reset()
        env.read_after_action = self.released_reads  # type: ignore[attr-defined]
        memory = memory or MemoryBlock()
        memory_text = "\n\n".join(p for p in (memory.text.strip(), notes.strip()) if p)
        executor_memory = memory_text if self.memory_in in ("both", "executor") else ""
        task = recoma.task_description(env.api_observation())  # type: ignore[attr-defined]
        max_steps = float(getattr(env, "params", {}).get("max_steps", 100))
        reads = Reads(released=self.released_reads)
        plan: list[tuple[str, str]] = []
        state: dict[str, Any] = {"current": None, "controller": None, "calls": 0}
        thoughts: list[str] = []
        planner_log: list[dict[str, Any]] = []
        started = time.time()

        def new_controller() -> Controller:
            return Controller(
                self.llm,
                prompts.EXECUTER_TEMPLATE,
                self.temperature,
                self.act_max_tokens,
                self.max_output_length,
                termination_suggestion=max_steps / self.termination_divisor,
            )

        def stop(reason: str, text: str = "") -> Action:
            return Action("SUBMIT", {"arg1": text, "reason": reason})

        def decide(
            observation: Observation, steps: list[Step]
        ) -> tuple[str, Action, str | None, dict[str, Any]]:
            if steps and steps[-1].info.get("sent_to_game") and state["controller"] is not None:
                state["controller"].observe(env)
            if self.released_step_limit and at_step_limit(env):
                return "", stop("env_call_limit"), None, {"plan": list(plan)}
            while True:
                if state["calls"] >= self.max_llm_calls:
                    return "", stop("llm_call_limit"), None, {"plan": list(plan)}
                if state["current"] is None:
                    output, call_id = self._plan(
                        env, reads, task, plan, memory_text, sample, len(steps)
                    )
                    state["calls"] += 1
                    planner_log.append({"step": len(steps), "plan_step": output})
                    if output.endswith("Done!"):
                        return (
                            output,
                            Action("SUBMIT", {"arg1": output}),
                            call_id,
                            {"plan": list(plan), "planner": output},
                        )
                    state["current"] = output
                    state["controller"] = new_controller()
                    continue
                controller: Controller = state["controller"]
                decision = controller.act(
                    env,
                    reads,
                    executer_input(state["current"], plan),
                    memory_text=executor_memory,
                    sample=sample,
                    step=len(steps),
                )
                state["calls"] += 1
                diagnostics: dict[str, Any] = {
                    "sent_to_game": False,
                    "subtask": state["current"],
                    "plan_step": len(plan) + 1,
                }
                if not decision.usable:
                    diagnostics.update(parse_failure=True, parse_error=UNUSABLE_REPLY)
                    reads.after_step()
                    return (
                        "",
                        Action("NOOP", {"reason": UNUSABLE_REPLY}),
                        decision.call_id,
                        diagnostics,
                    )
                if decision.submitted:
                    # The subtask is over; its submission is the result the planner sees.
                    plan.append((state["current"], decision.output))
                    state["current"] = None
                    state["controller"] = None
                    continue
                if state["calls"] >= self.max_llm_calls:
                    return decision.thought, stop("llm_call_limit"), decision.call_id, diagnostics
                assert decision.action_json is not None
                if "thought" in decision.action_json:
                    thoughts.append(decision.thought)
                diagnostics["sent_to_game"] = True
                reads.after_step()
                return (
                    decision.thought,
                    to_action(decision.action_json),
                    decision.call_id,
                    diagnostics,
                )

        traj = run_episode(
            env,
            decide,
            agent=self.descriptor,
            first_observation=first_observation,
            memory_item_ids=memory.item_ids,
            meta=meta,
        )
        traj.meta["knowledge_text"] = knowledge_text(thoughts)
        traj.meta["plan"] = [{"step": s, "result": r} for s, r in plan]
        traj.meta["planner_calls"] = planner_log
        traj.meta["llm_calls"] = state["calls"]
        traj.meta["agent_seconds"] = round(time.time() - started, 2)
        return traj
