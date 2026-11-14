"""Prompts of the investigation memory.

A constraint shapes all of them. The DiscoveryWorld experiment measures whether five
investigative behaviours appear without being asked for: introducing controls,
testing alternatives before accepting an explanation, recognising confounding
variables, revisiting conclusions after contradictory observations, and carrying an
investigative strategy to another task. If a prompt named these behaviours, their
appearance would show that the model follows instructions, not that it learned from
experience. So no prompt of this method names them, describes them, or gives an
example of one; ``tests/test_discovery.py`` checks the texts for the words.

The memory's schema does record support and contradiction between hypotheses and
evidence: that is how the memory is organised, not an instruction to the agent. Only
:data:`INSTRUCTED` names the behaviours, and only the control arm that measures what
instruction alone produces uses it.
"""

from __future__ import annotations

import json
from typing import Any

EXTRACTION_SYSTEM = """\
You have just finished an attempt at a scientific task in a simulated world. You will \
be given the task, what you did and observed (each action with its result), the notes \
you kept during the attempt, and how the attempt ended.

Write down what is worth keeping, as three kinds of notes.

1. "evidence": measurements and observations from this attempt, as observed: which \
object, which instrument or action, what result. These are facts about this world only.
2. "hypotheses": statements about how this world works that the evidence bears on. For \
each, give the conditions under which you observed it, its status ("supported", \
"refuted" or "open"), and the evidence that supports it and that contradicts it, by \
number.
3. "strategies": lessons about how to investigate, written so that they could help with \
a different task, in a different world, with different objects. For each, say when it \
applies, describe a test or an action that puts it into practice, and say what in this \
attempt it is based on. A strategy must not just restate the answer of this task.

Write only what this attempt gives reason to write. Empty lists are fine.

Answer with one JSON object and nothing else:
{"evidence": [{"text": "...", "step": 12}],
 "hypotheses": [{"statement": "...", "conditions": "...", "status": "supported", \
"supported_by": [0], "contradicted_by": []}],
 "strategies": [{"statement": "...", "applies_when": "...", "test": "...", "basis": "..."}]%(review)s}
"""

REVIEW_FORMAT = """,
 "strategy_review": [{"id": "S1", "used": true, "outcome": "helped", "reason": "...", \
"revised_statement": null, "revised_applies_when": null}]"""

REVIEW_INSTRUCTIONS = """

At the start of this attempt you were shown the strategies below. For each one, say in \
"strategy_review" whether you used it ("used": true or false) and, if you did, whether \
it "helped" or "did not help" here, with a reason. If it did not help because it does \
not apply in situations like this one, you may give a revised statement and a narrower \
"revised_applies_when"; otherwise leave both null.

Strategies shown:
%s"""


def extraction_system(review: bool) -> str:
    return EXTRACTION_SYSTEM % {"review": REVIEW_FORMAT if review else ""}


def extraction_input(
    task: str,
    trajectory: str,
    notes: str,
    ending: str,
    shown_strategies: list[dict[str, Any]] | None = None,
) -> str:
    text = (
        f"Task:\n{task}\n\nWhat you did and observed:\n{trajectory}\n\n"
        f"Your notes at the end of the attempt:\n{notes or '(none)'}\n\nHow it ended:\n{ending}"
    )
    if shown_strategies:
        listing = "\n".join(
            f"{s['label']}: {s['statement']} (applies when: {s['applies_when']})"
            for s in shown_strategies
        )
        text += REVIEW_INSTRUCTIONS % listing
    return text


#: Placed before the retrieved notes in the agent's prompt. Neutral on purpose.
MEMORY_HEADING = (
    "Below are notes from your earlier investigations, in this task and in others. You can "
    "use them when you feel they are relevant."
)

STRATEGY_HEADING = "Ways of investigating that you noted in earlier tasks:"
SAME_WORLD_HEADING = "Findings from an earlier attempt in this same world:"
ELSEWHERE_HEADING = (
    "Findings from other worlds of this kind, each with the conditions it was observed under:"
)
EVIDENCE_HEADING = "Measurements from an earlier attempt in this same world:"
ANSWERS_HEADING = "What you found in this kind of task before:"

#: The control arm: no memory, the behaviours prescribed. Used by no other arm.
INSTRUCTED = """\
How to investigate:
- Include a control condition: compare against a case where the factor you are testing \
is absent or known.
- Test alternative explanations before you accept one.
- Look for confounding variables: other differences that could explain a result.
- Revisit a conclusion when a new observation contradicts it.
- Reuse investigation strategies that worked in other scientific tasks."""

#: Neutral statements about the setting, for the placebo arm: same place in the prompt
#: and similar length as a real memory, no investigative content and no answers.
PLACEBO_SENTENCES = (
    "The colony on Planet X was founded recently, and its buildings are arranged around a "
    "central square.",
    "Colonists post short updates about their day on the Discovery Feed.",
    "The colony has living quarters, a cafeteria, a school and several laboratories.",
    "Paths connect the buildings, and some areas are reached through doors.",
    "Many objects on Planet X look like their counterparts on Earth.",
    "Tables and shelves in the buildings hold tools and containers.",
    "The colony's characters move between buildings during the day.",
    "Signs near some buildings show their names.",
    "Weather on Planet X is mild in the area around the colony.",
    "The colony keeps a store of general supplies for its residents.",
    "Some colonists work in the fields outside the colony.",
    "The landscape around the colony includes grass, sand and trees.",
)


def render_json(value: Any) -> str:
    return json.dumps(value, indent=1, sort_keys=True)
