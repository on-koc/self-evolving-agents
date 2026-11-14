"""Prompts of DiscoveryWorld's Hypothesizer agent, as released.

Source: ``agents/HypothesizerAgent.py`` of https://github.com/allenai/discoveryworld
(commit ``fd59132``, 2025-03-10), Copyright Allen Institute for AI, Apache License
2.0 (see THIRD_PARTY_NOTICES.md). The text below is quoted unchanged, typing errors
included ("invesgiations", "You seen to confuse", "REMEBER"), because a baseline
should be the published agent and not an improved one.

Two passages are kept although they look wrong:

* The prompt tells the model it receives an image. Like the original run with
  ``includeImages=False``, no image is sent: the models used here read text only.
* The dialog addition is built by four assignments in a row, so in the original only
  the last one survives and the dialog itself is never shown. :func:`dialog_text`
  reproduces that; ``fixed=True`` gives the evidently intended version.

The one addition, :data:`CROSS_EPISODE_MEMORY_HEADING`, is not from the original: it
is where a memory method (ReasoningBank, the investigation memory) places what it
retrieved. With no memory it is absent and the prompt is the published one.
"""

from __future__ import annotations

import json
from typing import Any


def _dump(value: Any) -> str:
    return json.dumps(value, indent=4, sort_keys=True)


def action_prompt_head(
    observation: dict[str, Any],
    actions: dict[str, Any],
    action_help: str,
    last_actions: list[dict[str, Any]],
    teleports: dict[str, Any],
    facing: str,
    directions: list[str],
) -> str:
    """``promptStr0``: the environment, the actions and the last three actions."""
    s = "You are playing a video game about making scientific discoveries.  The game is in the style of a 2D top-down RPG (you are the agent with green hair in the center of the image), and as input you get both an image, as well as information from the user interface (provided in the JSON below) that describes your location, inventory, objects in front of you, the result of your last action, and the task that you're assigned to complete.\n"
    s += "Because this is a game, the actions that you can complete are limited to a set of actions that are defined by the game. Those are also described below.\n"
    s += "This game is played step-by-step.  At each step, you get the input that I am providing, and output a single action to take as the next step.\n"
    s += "\n"
    s += "Note that this game has a spatial component, given that it's played on a 2D map.  The objects shown in `nearbyObjects` are objects that are near you.  If you can't see an object you're looking for, you'll have to move to find it (or, it may be located in a closed container).\n"
    s += "Environment Observation (as JSON):\n"
    s += "```json\n"
    s += _dump(observation)
    s += "```\n"
    s += "\n"
    s += "Actions:\n"
    s += "```json\n"
    s += _dump(actions)
    s += "```\n"
    s += "\n"
    s += "Additional information on actions, and how to format your response:\n"
    s += action_help + "\n"
    s += "\n"
    s += "Your last few action(s), explanation for those action(s), and messages you've left in your scratchpad:\n"
    s += "```json\n"
    for idx, action in enumerate(last_actions[-3:]):
        s += "Action " + str(idx) + ":\n"
        s += _dump(action)
        s += "\n"
    s += "```\n"
    s += "\n"
    s += 'Teleporting: To make moving easier, you can teleport to a list of specific locations in the environment, using the teleport action.  In this case, \'arg1\' is the name of a location, from the list below. An example teleport action would be: `{"action": "TELEPORT_TO_LOCATION", "arg1": "school"}).\n'
    s += "```json\n"
    s += _dump(teleports)
    s += "```\n"
    s += "\n"
    s += 'VERY IMPORTANT: You can also teleport to OBJECTS.  This is probably the easiest way for you to move to new locations, because it\'s fast and error-free.  You can teleport to any object, including objects you can\'t see. In this case, \'arg1\' is the UUID of the object you want to teleport to. An example teleport action would be: `{"action": "TELEPORT_TO_OBJECT", "arg1": 123}).\n'
    s += "\n"
    s += (
        "Navigation note: In the image, you are in the center, north is the top, south is the bottom, east is the right, and west is the left. Moving forward moves you in the direction you're facing. You are currently facing `"
        + facing
        + "`. From your current location, the directions that you can move to (i.e. they don't have an object blocking them) are: "
        + str(directions)
        + ". You seen to confuse directions a lot.  Directions are relative to the center of the image. Things above the center are north of the agent. Things left of the center are east of the agent.\n"
    )
    s += "Interaction note: You can only interact (i.e. take actions with) objects that are in your inventory, or directly (i.e. one square) in front of you, in the direction that you're facing.  E.g. if you want to pick an object up, you need to move directly in front of it, and face it, before using the pick-up action on it.\n"
    s += "\n"
    return s


#: Where retrieved cross-episode memory goes. Not in the original agent.
CROSS_EPISODE_MEMORY_HEADING = ""


def action_prompt_tail(knowledge: dict[str, Any], interactable: str, memory_text: str = "") -> str:
    """``promptStr1``: current knowledge and the output instructions.

    ``memory_text`` (not in the original) is placed after the knowledge and before the
    output instructions.
    """
    s = ""
    s += "You are also explicitly keeping track of your scientific knowledge, that I'll ask you about separately (not in this prompt or response).  But, for reference, here's what you think you know so far:\n"
    s += "```json\n"
    s += _dump(knowledge)
    s += "```\n"
    s += "\n"
    if memory_text.strip():
        s += memory_text.strip() + "\n"
        s += "\n"
    s += 'Please create your output (the next action you\'d like to take) below.  It should be in the JSON form expected above e.g.(`{"action": "USE", "arg1": 5, "arg2": 12}`). \n'
    s += 'Your response should ONLY be in JSON.  You should include an additional JSON key, "explanation", to describe your reasoning for performing this action. e.g. `{"action": "USE", "arg1": 5, "arg2": 12, "explanation": "Using the shovel on the soil will allow me to dig a hole to plant a seed"}`.  Note that even though this explanation is short, yours can be a few hundred tokens, if you\'d like. Your explanation should say: (1) What your subgoal is, (2) What you see around you, (3) What you see in front of you, (4) What you are doing to progress towards your immediate subgoal.\n'
    s += 'Lastly, your response should also include an additional JSON key, "memory", that includes any information you\'d like to write down and pass on to yourself for the future.  This can be helpful in remembering important results, high-level tasks, low-level subtasks, or anything else you\'d like to remember or think would be helpful. e.g. `{"action": "USE", "arg1": 5, "arg2": 12, "explanation": "...", "memory": "..."}`\n'
    s += "To make your memory helpful, you might consider including things learned from attempting your last action -- e.g. adding in that certain actions were useful, or not useful, and retaining (and adding to) this information over time.\n"
    s += 'To help frame your investigations scientifically, and also evaluate your invesgiations, please include an additional JSON key, "running_hypotheses", that includes your current running hypothesis/hypotheses that you\'re working on developing and/or testing. \n'
    s += "If your last action failed, or other last recent actions failed, please consider thinking why they failed, and trying different actions unless you believe things have changed to make failed actions work this time.\n"
    s += "If you don't see what you're looking for, and anticipate it might be in another location, consider teleporting to that location. \n"
    s += (
        "For reference again, here is a list of the objects that are interactable (from your inventory, and directly in front of you): "
        + interactable
        + "\n"
    )
    return s


def dialog_text(dialog: dict[str, Any], fixed: bool = False) -> str:
    """``promptDialogStr``, added while the agent is in a dialog.

    In the original each line overwrites the previous one, so only the response format
    survives. ``fixed=True`` keeps all of it.
    """
    note = "*** NOTE: You are currently in a dialog.  Please ignore the above instructions about choosing an action, and instead choose which option you would like to say in the dialog. ***\n"
    shown = "For reference, here is the dialog that you are currently in:\n"
    shown += "```json\n"
    shown += _dump(dialog)
    shown += "```\n"
    form = "The expected response format is JSON, in between code brackets (```), as a dictionary with a single key: `chosen_dialog_option_int` (as well as `memory` and `running_hypothesis`).  The value should be an integer, corresponding to the dialog option you would like to select. You can write prose before the JSON code block, if that helps you think.\n"
    return note + shown + form if fixed else form


DEBUG_TEXT = (
    "REMEMBER, IF YOU'RE GOING TO AN OBJECT, INSTEAD OF MOVING NORTH/EAST/SOUTH/WEST, or ROTATING, YOU SHOULD TRY TELEPORTING DIRECTLY TO OBJECTS.  IT'S MUCH FASTER AND LESS ERROR-PRONE. YOU CAN TELEPORT TO AN OBJECT NO MATTER WHERE IT IS, EVEN IF ITS NOT LISTED IN THE ACCESSIBLE OBJECTS LIST. JUST REMEBER ITS UUID.\n"
    "WHEN TELEPORTING, REMEMBER TO LOOK AT THE ENTIRE OBJECT LIST IN THE OBSERVATION, NOT JUST THE ACCESSIBLE OBJECTS LIST.\n"
    "IF YOU FIND YOURSELF WAITING FOR SOMETHING TO HAPPEN, CHECK TO SEE IF IT'S ALREADY HAPPENED.  YOU MIGHT BE WAITING FOR SOMETHING THAT'S ALREADY HAPPENED.\n"
    "IF YOU FIND YOURSELF WAITING FOR A LONG TIME, YOU MIGHT BE STUCK. TRY TO REEXAMINE YOUR TASK, REASSESS WHERE YOU ARE, AND MAKE A NEW PLAN."
)


def example_hypotheses() -> dict[str, Any]:
    """``mkExampleHypotheses()``."""
    return {
        "scientific_knowledge_examples": [
            {
                "step": 1,
                "measurement": "The tree (uuid: 123) has a temperature of 10 degrees celsius when measured using the thermometer.",
            },
            {
                "step": 3,
                "hypothesis": "if (object:substance) is (action:heated) then (object:substance) will have (property:temperature) increase.",
                "supporting evidence": "...",
                "status": "<confirmed, rejected, or pending>",
            },
        ]
    }


def knowledge_prompt(head: str, knowledge: dict[str, Any]) -> str:
    """The knowledge step that follows every action."""
    s = "You are playing a game about scientific discovery.  For context, below is the environment observation that you just saw, and the action(s) that you just took.  Then, I'll ask you a question about explicitly describing your scientific knowledege from this last few steps.\n"
    s += "---\n"
    s += head + "\n"
    s += "---\n"
    s += "\n"
    s += "It's important to explicitly keep track of scientific knowledge in the scientific discovery process.\n"
    s += "To do this, here, I'd like you to write down any scientific knowledge that you've learned from your last action, or from your last few actions.\n"
    s += "This knowledge will take two forms: measurements, or hypotheses.\n"
    s += "Measurements are observations that you've made about the world.\n"
    s += "Hypotheses are statements that you believe to be true, and that you'd like to test. These should be formulated as IF statements.\n"
    s += "Both measurements and hypotheses should be written in terms of: objects (either specific objects and their UUIDs, or their types), object properties (like temperature), and actions (like eating). \n"
    s += "Here's a toy example of a hypothesis and a measurement, mostly to give an example of the output format:\n"
    s += "```json\n"
    s += _dump(example_hypotheses())
    s += "```\n"
    s += "\n"
    s += "Here are the measurements and hypotheses that you've written down so far (if blank, then it's likely very early in the process):\n"
    s += "```json\n"
    s += _dump(knowledge)
    s += "```\n"
    s += "\n"
    s += "Please write down any measurements or hypotheses that you've learned from your last action, or from your last few actions, below.  Please write them in the JSON form expected above.\n"
    s += "You can write any number of measurements and/or hypotheses, or revisions of earlier measurements/hypotheses, and they will be automatically appended to the existing list.\n"
    s += "Remember, the important thing here is to keep track of your scientific knowledge, so you can guide your future actions.\n"
    s += "This is not a record of everything you do, only relevant scientific knowledge (like measurements and hypotheses). NOTE: for example, moving to a new location is not a measurement or hypothesis, unless there is something clearly relevant or unexpected you should not write this down.\n"
    s += "Similarly, to keep the knowledge store somewhat compact, you do not need to repeat previous scientific knowledge unless you're adding to it, or modifying it.\n"
    s += "If you have no new knowledge to add or modify, leave this section blank.\n"
    s += "It is also critically important that your output is valid JSON.  Please be careful in generating valid JSON.  You should generate a dictionary with a single top-level key (`scientific_knowledge`), which is an array of new measurements and/or hypotheses to add.\n"
    s += "You can write prose before writing the JSON.  Only the last codeblock (```) in your response will be parsed for the JSON.\n"
    return s


def consolidation_prompt(
    knowledge: dict[str, Any],
    tokens: int,
    max_entries: int = 40,
    max_tokens: int = 2000,
) -> str:
    """``consolidateKnowledgeStep``: compress the knowledge store every ten steps."""
    s = ""
    s += "You are an agent playing a game about automated scientific discovery.\n"
    s += "In this game, you are given a task to complete, and you can complete this task by taking actions in the environment.\n"
    s += "While playing the game, you are also explicitly keeping track of your scientific knowledge (shown below), both to help you, but also to help others understand your process.\n"
    s += "This knowledge will take two forms: measurements, or hypotheses.\n"
    s += "Measurements are observations that you've made about the world.\n"
    s += "Hypotheses are statements that you believe to be true, and that you'd like to test. These should be formulated as IF statements.\n"
    s += "Both measurements and hypotheses should be written in terms of: objects (either specific objects and their UUIDs, or their types), object properties (like temperature), and actions (like eating). \n"
    s += "Unfortunately, sometimes this knowledge base gets very large, and contains repeated, duplicated, or irrelevant knowledge, which makes it hard to use in practice, and very expensive to keep. \n"
    s += "Your job is to take the knowledge base below, and consolidate it into a smaller, more compact, and more useful knowledge base, but in exactly the same format (i.e. the list of measurements and hypotheses).\n"
    s += "You can do this by removing any repeated or duplicated knowledge, and by removing any irrelevant knowledge.\n"
    s += "You can also do this by combining multiple measurements or hypotheses into a single measurement or hypothesis, if they are logically equivalent.\n"
    s += "consolidated hypotheses must still have a `status` (i.e. pending, confirmed, rejected) and ideally succinct `supporting evidence` supporting that status.\n"
    s += "The output should be in JSON, and should have a single top-level key (`scientific_knowledge`), which is an array of measurements and/or hypotheses.\n"
    s += "\n"

    entries = len(knowledge["scientific_knowledge"])
    limit = "LIMITS (IMPORTANT!):\n"
    limit += "The current size of your knowledge base is: " + str(entries) + " entries.\n"
    limit += "The MAXIMUM allowable size of your knowledge base is " + str(max_entries) + " entries"
    if entries > max_entries:
        limit += (
            " (WARNING: You have exceeded this limit, meaning you must reduce the memory size by at least "
            + str(entries - max_entries)
            + " entries).\n"
        )
    else:
        limit += ".\n"
    limit += "The current size of your knowledge base is: " + str(tokens) + " tokens.\n"
    limit += "The MAXIMUM allowable size of your knowledge base is " + str(max_tokens) + " tokens"
    if tokens > max_tokens:
        limit += (
            " (WARNING: You have exceeded this limit, meaning you must reduce the memory size by at least "
            + str(tokens - max_tokens)
            + " tokens).\n"
        )
    else:
        limit += ".\n"
    s += limit

    s += "\n"
    s += "Here is the existing knowledge base:\n"
    s += "```json\n"
    s += _dump(knowledge)
    s += "```\n"
    s += "\n"
    s += limit + "\n"
    s += "Please write down your new, SIGNIFICANTLY consolidated knowledge base below. Remember, if something isn't important and your knowledge base is full, you can discard it if you need to meet the knowledge base limit.  Please write it in the JSON form expected above. You can write a short amount of prose before if that's helpful for your thought process, and only the last item in code blocks (```) will be parsed as JSON.\n"
    return s
