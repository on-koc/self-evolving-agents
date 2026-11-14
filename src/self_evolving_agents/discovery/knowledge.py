"""DiscoveryWorld's third measure: does the agent's knowledge contain the discovery?

Each world comes with a few critical questions ("Does it clearly state the rust
remover compound is this compound: `Substance B`?"). A model reads the agent's
knowledge and answers each with 0 or 1; the score is the share answered 1. This is
DiscoveryWorld's own procedure (``scripts/knowledgeScorer.py``), and the prompt below
is quoted from it unchanged (Apache License 2.0, Allen Institute for AI).

Two uses are added here:

* **stale knowledge**: the same questions of an *earlier* world of the same kind,
  asked about the knowledge written in a new world whose answer is different. A 1
  means the agent states the old world's answer: it remembered what was found
  instead of finding it again.
* every grade records the grader model, so that grades from different graders are
  never pooled.

The grader is shown the task, the knowledge and the question, and nothing about which
method produced the knowledge.
"""

from __future__ import annotations

import json
from typing import Any

from ..envs import answer_key
from ..llm import LLMRequest, extract_json_object, user


def grading_prompt(task_description: str, knowledge: Any, question: str) -> str:
    """The prompt of DiscoveryWorld's ``KnowledgeScorer.evaluateKnowledge``, unchanged."""
    p = "Your task is to evaluate the knowledge of an agent playing a game about scientific discovery, to see if they have figured out the discovery required to solve the task.\n"
    p += "I will supply you with: (1) the task description, (2) the agent's knowledge, and (3) a single critical question about the discovery, that you should answer with either true (1) or false (0). \n"
    p += "\n"
    p += "Task Description:\n"
    p += "```\n"
    p += task_description + "\n"
    p += "```\n"
    p += "\n"
    p += "Agent's Knowledge:\n"
    p += "```\n"
    if isinstance(knowledge, str):
        p += knowledge + "\n"
    else:
        p += json.dumps(knowledge, indent=4) + "\n"
    p += "```\n"
    p += "\n"
    p += "Critical Question:\n"
    p += "```\n"
    p += question + "\n"
    p += "```\n"
    p += "\n"
    p += "Please answer this question by responding `1` if the agent's knowledege reflects having discovered the information in the critical question, and `0` otherwise.  This response should be in the `evaluation` key of the response.\n"
    p += "The response format is a JSON dictionary containing three keys: `criticalQuestion`, `evaluation`, and `explanation`. \n"
    p += "```\n"
    p += "{\n"
    p += '    "criticalQuestion": "repeat the critical question",\n'
    p += '    "evaluation": 0 or 1 (as integers),\n'
    p += '    "explanation": "provide a brief explanation for evaluation, making reference to the agent\'s knowledge and whether or not it reflects the critical question."\n'
    p += "}\n"
    p += "```\n"
    return p


class KnowledgeScorer:
    """Grades an agent's knowledge against a world's critical questions.

    Args:
        llm: the grader model. Temperature 0 and 800 reply tokens, as in the original.
    """

    def __init__(self, llm: Any, *, temperature: float = 0.0, max_tokens: int = 800):
        self.llm = llm
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _ask(self, description: str, knowledge: Any, question: str) -> dict[str, Any]:
        response = self.llm.complete(
            LLMRequest(
                system="",
                messages=[user(grading_prompt(description, knowledge, question))],
                purpose="grade_knowledge",
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
        )
        try:
            parsed = extract_json_object(response.text)
        except ValueError:
            parsed = {}
        value = parsed.get("evaluation")
        try:
            evaluation = int(value)
        except (TypeError, ValueError):
            evaluation = None
        return {
            "question": question,
            "evaluation": evaluation if evaluation in (0, 1) else None,
            "explanation": str(parsed.get("explanation", ""))[:500],
            "llm_call_id": response.call_id,
        }

    def grade(self, world: dict[str, Any], knowledge: Any) -> dict[str, Any]:
        """Score in [0, 1] over the world's critical questions; ``None`` if it has none.

        An answer that cannot be read counts as 0, as in the original (which adds
        nothing to the total for it).
        """
        answers = []
        for task in answer_key(world["scenario"], world["difficulty"], int(world["seed"])):
            for question in task["critical_questions"]:
                answers.append(self._ask(task["task_description"], knowledge, question))
        if not answers:
            return {"score": None, "questions": [], "grader": self.llm.model}
        score = sum(a["evaluation"] or 0 for a in answers) / len(answers)
        return {"score": score, "questions": answers, "grader": self.llm.model}

    def stale(
        self, world: dict[str, Any], knowledge: Any, earlier: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Does the knowledge state an earlier world's answer where the answer is different?

        Only questions of earlier worlds that do not occur among the current world's
        questions are asked: an identical question would test current knowledge.
        ``score`` is the largest share over the earlier worlds; ``None`` when no
        earlier world of the same kind has a differing question.
        """
        current = {
            q
            for task in answer_key(world["scenario"], world["difficulty"], int(world["seed"]))
            for q in task["critical_questions"]
        }
        results = []
        for other in earlier:
            if (other["scenario"], other["difficulty"]) != (world["scenario"], world["difficulty"]):
                continue
            if int(other["seed"]) == int(world["seed"]):
                continue
            answers = []
            for task in answer_key(other["scenario"], other["difficulty"], int(other["seed"])):
                for question in task["critical_questions"]:
                    if question not in current:
                        answers.append(self._ask(task["task_description"], knowledge, question))
            if answers:
                results.append(
                    {
                        "world": other,
                        "score": sum(a["evaluation"] or 0 for a in answers) / len(answers),
                        "questions": answers,
                    }
                )
        if not results:
            return {"score": None, "worlds": [], "grader": self.llm.model}
        return {
            "score": max(r["score"] for r in results),
            "worlds": results,
            "grader": self.llm.model,
        }
