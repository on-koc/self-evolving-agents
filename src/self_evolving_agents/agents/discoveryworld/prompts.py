"""The prompt templates of DiscoveryWorld's ReAct and Plan-and-Execute agents, verbatim.

Quoted unchanged from ``agents/recoma/prompts/`` of DiscoveryWorld (Apache License 2.0,
Allen Institute for AI); a test compares their SHA-256 with the released files. They
are Jinja templates in the original; :func:`render` fills them in exactly as Jinja's
default settings do (one trailing newline of a template is dropped).
"""

from __future__ import annotations

import re
from typing import Any

#: ``react_prompt.txt``
REACT_TEMPLATE = (
    "You are playing a video game about making scientific discoveries.  The game is in the style of a 2D top-down RPG (you are the agent in the center of the image), and as input you get both an image, as well as information from the user interface (provided in the JSON below) that describes your location, inventory, objects in front of you, the result of your last action, and the task that you're assigned to complete.\n"
    "Because this is a game, the actions that you can complete are limited to a set of actions that are defined by the game. Those are also described below.\n"
    "This game is played step-by-step.  At each step, you get the input that I am providing, and output a single action to take as the next step.\n"
    "\n"
    "Navigation note: \n"
    "Moving forward moves you in the direction you're facing. You are currently facing \"{{ facing_direction }}\"`. From your current location, the directions that you can move to (i.e. they don't have an object blocking them) are: {{ valid_dirs }}. \n"
    "\n"
    "Interaction note:\n"
    "You can only interact (i.e. take actions with) objects that are in your inventory, or directly (i.e. one square) in front of you, in the direction that you're facing.  E.g. if you want to pick an object up, you need to move directly in front of it, and face it, before using the pick-up action on it.\n"
    "\n"
    "Teleportation note: \n"
    'To make moving easier, you can teleport to a list of specific locations in the environment, using the teleport action.  In this case, \'arg1\' is the name of a location. An example teleport action would be: `{"action": "TELEPORT_TO_LOCATION", "arg1": "school"}.\n'
    "\n"
    "\n"
    "Action Format note:\n"
    "{{ additional_instructions }}\n"
    'Your response should ONLY be in JSON.  You could include an additional JSON key, "thought", to describe your reasoning for performing this action and track your knowledge about the world. e.g. `{"action": "USE", "arg1": 5, "arg2": 12, "thought": "I have the seed in hand and need to plant it. Using the shovel on the soil will allow me to dig a hole to plant the seed. I can then grow a plant from this seed to measure the nutrient richness of this soil."}`.\n'
    "\n"
    "Hints:\n"
    "- If your last action failed, or other last recent actions failed, please consider thinking why they failed, and trying different actions unless you believe things have changed to make failed actions work this time.\n"
    "- If you don't see what you're looking for, and anticipate it might be in another location, consider teleporting to that location.\n"
    '- Use verbose "thought" statements to maintain your progress, running hypotheses, your knowledge about the world, etc.\n'
    "- REMEMBER, IF YOU'RE GOING TO AN OBJECT, INSTEAD OF MOVING NORTH/EAST/SOUTH/WEST, or ROTATING, YOU SHOULD TRY TELEPORTING DIRECTLY TO OBJECTS.  IT'S MUCH FASTER AND LESS ERROR-PRONE. YOU CAN TELEPORT TO AN OBJECT NO MATTER WHERE IT IS, EVEN IF ITS NOT LISTED IN THE ACCESSIBLE OBJECTS LIST. JUST REMEBER ITS UUID.\n"
    "- WHEN TELEPORTING, REMEMBER TO LOOK AT THE ENTIRE OBJECT LIST IN THE OBSERVATION, NOT JUST THE ACCESSIBLE OBJECTS LIST.\n"
    "- FOR ACTIONS INVOLVING TWO ARGS (E.G. USE AND PUT), ONE OF THE OBJECTS MUST BE IN YOUR INVENTORY AND YOU MUST BE NEXT TO THE OTHER OBJECT. E.G. TO USE SHOVEL ON THE SOIL, YOU MUST HAVE THE SHOVEL IN YOUR INVENTORY AND BE NEXT TO THE SOIL.\n"
    "- IF YOU FIND YOURSELF WAITING FOR SOMETHING TO HAPPEN, CHECK TO SEE IF IT'S ALREADY HAPPENED.  YOU MIGHT BE WAITING FOR SOMETHING THAT'S ALREADY HAPPENED.\n"
    "- IF YOU FIND YOURSELF WAITING FOR A LONG TIME, YOU MIGHT BE STUCK. TRY TO REEXAMINE YOUR TASK, REASSESS WHERE YOU ARE, AND MAKE A NEW PLAN.\n"
    '- IF YOU THINK YOU ARE DONE, SUBMIT WITH THE ACTION: {"action": "SUBMIT", "arg1": "Task completed!"}.\n'
    '- IF YOU ARE NOT MAKING ANY PROGRESS AND CAN NOT FIGURE OUT HOW TO PROCEED, USE THE SUBMIT ACTION WITH ARG1 EXPLAINING YOUR REASONING, e.g., {"action": "SUBMIT", "arg1": "Task failed! Unable to explore the building!"}.\n'
    "\n"
    "Task: {{ input_str }}\n"
    "\n"
    "Current Environment Observation:\n"
    "```json\n"
    "{{ observation }}\n"
    "```\n"
    "\n"
    "{% if in_dialog %}\n"
    "NOTE: You are currently in a dialog. Choose which option you would like to say in the dialog.\n"
    "For reference, here is the dialog that you are currently in:\n"
    "```json\n"
    "{{ dialog_box }}\n"
    "```\n"
    "\n"
    'The expected response format is JSON as a dictionary with the key: `chosen_dialog_option_int`, e.g. {"chosen_dialog_option_int": 0}. The value should be an integer, corresponding to the dialog option you would like to select. You can still use the "thought" key to describe your reasoning.\n'
    "\n"
    "{% else %}\n"
    "Valid Actions:\n"
    "```json\n"
    "{{ known_actions}}\n"
    "```\n"
    "\n"
    "Valid Teleport Locations:\n"
    "```json\n"
    "{{ teleport_destinations }}\n"
    "```\n"
    "\n"
    "List of objects that are interactable (from your inventory, and directly in front of you):\n"
    "{{ interactable_objects }}\n"
    "\n"
    "{% endif %}\n"
    "\n"
    'Action JSON (using ```json\\n{"action": ..., "arg1": ...}``` format):\n'
)

#: ``executer_prompt.txt``
EXECUTER_TEMPLATE = (
    "You are playing a video game about making scientific discoveries.  The game is in the style of a 2D top-down RPG (you are the agent in the center of the image), and as input you get both an image, as well as information from the user interface (provided in the JSON below) that describes your location, inventory, objects in front of you, the result of your last action, and the task that you're assigned to complete.\n"
    "Because this is a game, the actions that you can complete are limited to a set of actions that are defined by the game. Those are also described below.\n"
    "This game is played step-by-step.  At each step, you get the input that I am providing, and output a single action to take as the next step.\n"
    "\n"
    "Navigation note:\n"
    "Moving forward moves you in the direction you're facing. You are currently facing \"{{ facing_direction }}\"`. From your current location, the directions that you can move to (i.e. they don't have an object blocking them) are: {{ valid_dirs }}.\n"
    "\n"
    "Interaction note:\n"
    "You can only interact (i.e. take actions with) objects that are in your inventory, or directly (i.e. one square) in front of you, in the direction that you're facing.  E.g. if you want to pick an object up, you need to move directly in front of it, and face it, before using the pick-up action on it.\n"
    "\n"
    "Teleportation note:\n"
    'To make moving easier, you can teleport to a list of specific locations in the environment, using the teleport action.  In this case, \'arg1\' is the name of a location. An example teleport action would be: `{"action": "TELEPORT_TO_LOCATION", "arg1": "school"}.\n'
    "\n"
    "\n"
    "Action Format note:\n"
    "{{ additional_instructions }}\n"
    'Your response should ONLY be in JSON.  You could include an additional JSON key, "thought", to describe your reasoning for performing this action and track your knowledge about the world. e.g. `{"action": "USE", "arg1": 5, "arg2": 12, "thought": "I have the seed in hand and need to plant it. Using the shovel on the soil will allow me to dig a hole to plant the seed. I can then grow a plant from this seed to measure the nutrient richness of this soil."}`.\n'
    'When you are done with the task, use the SUBMIT action with "Task completed!" or "Task failed!" as the arg1 with an associated "thought" describing what was achieved or why the task could not be completed in detail.\n'
    "\n"
    "Hints:\n"
    "- If your last action failed, or other last recent actions failed, please consider thinking why they failed, and trying different actions unless you believe things have changed to make failed actions work this time.\n"
    "- If you don't see what you're looking for, and anticipate it might be in another location, consider teleporting to that location.\n"
    '- Use verbose "thought" statements to maintain your progress, running hypotheses, your knowledge about the world, etc.\n'
    "- REMEMBER, IF YOU'RE GOING TO AN OBJECT, INSTEAD OF MOVING NORTH/EAST/SOUTH/WEST, or ROTATING, YOU SHOULD TRY TELEPORTING DIRECTLY TO OBJECTS.  IT'S MUCH FASTER AND LESS ERROR-PRONE. YOU CAN TELEPORT TO AN OBJECT NO MATTER WHERE IT IS, EVEN IF ITS NOT LISTED IN THE ACCESSIBLE OBJECTS LIST. JUST REMEBER ITS UUID.\n"
    "- WHEN TELEPORTING, REMEMBER TO LOOK AT THE ENTIRE OBJECT LIST IN THE OBSERVATION, NOT JUST THE ACCESSIBLE OBJECTS LIST.\n"
    "- FOR ACTIONS INVOLVING TWO ARGS (E.G. USE AND PUT), ONE OF THE OBJECTS MUST BE IN YOUR INVENTORY AND YOU MUST BE NEXT TO THE OTHER OBJECT. E.G. TO USE SHOVEL ON THE SOIL, YOU MUST HAVE THE SHOVEL IN YOUR INVENTORY AND BE NEXT TO THE SOIL.\n"
    "- IF YOU FIND YOURSELF WAITING FOR SOMETHING TO HAPPEN, CHECK TO SEE IF IT'S ALREADY HAPPENED.  YOU MIGHT BE WAITING FOR SOMETHING THAT'S ALREADY HAPPENED.\n"
    "- IF YOU FIND YOURSELF WAITING FOR A LONG TIME, YOU MIGHT BE STUCK. TRY TO REEXAMINE YOUR TASK, REASSESS WHERE YOU ARE, AND MAKE A NEW PLAN.\n"
    '- IF YOU THINK YOU ARE DONE, SUBMIT WITH THE ACTION: {"action": "SUBMIT", "arg1": "Task completed!", "thought": "Planted seed in the soil at (12, 13)"}. Use "thought" to explain what was achieved.\n'
    '- IF YOU ARE NOT MAKING ANY PROGRESS, USE THE SUBMIT ACTION WITH A THOUGHT EXPLAINING YOUR EXPLANATION OF THE FAILURE, e.g., {"action": "SUBMIT", "arg1": "Task failed!", "thought": "Unable to find the flag!"}.\n'
    "\n"
    "Task: {{ input_str }}\n"
    "\n"
    "Current Environment Observation:\n"
    "```json\n"
    "{{ observation }}\n"
    "```\n"
    "\n"
    "{% if in_dialog %}\n"
    "NOTE: You are currently in a dialog. Choose which option you would like to say in the dialog.\n"
    "For reference, here is the dialog that you are currently in:\n"
    "```json\n"
    "{{ dialog_box }}\n"
    "```\n"
    "\n"
    'The expected response format is JSON as a dictionary with the key: `chosen_dialog_option_int`, e.g. {"chosen_dialog_option_int": 0}. The value should be an integer, corresponding to the dialog option you would like to select. You can still use the "thought" key to describe your reasoning.\n'
    "\n"
    "{% else %}\n"
    "Valid Actions:\n"
    "```json\n"
    "{{ known_actions}}\n"
    "```\n"
    "\n"
    "Valid Teleport Locations:\n"
    "```json\n"
    "{{ teleport_destinations }}\n"
    "```\n"
    "\n"
    "List of objects that are interactable (from your inventory, and directly in front of you):\n"
    "{{ interactable_objects }}\n"
    "\n"
    "{% endif %}\n"
    "\n"
    'Action JSON (using ```json\\n{"action": ..., "arg1": ...}``` format):\n'
)

#: ``planner_prompt.txt``
PLANNER_TEMPLATE = (
    "USER:\n"
    "You are playing a video game about making scientific discoveries.  The game is in the style of a 2D top-down RPG (you are the agent in the center), and as input you get information from the user interface (provided in the JSON below) that describes your location, inventory, objects in front of you, the result of your last action, and the task that you're assigned to complete.\n"
    "Because this is a game, the actions that you can complete are limited to a set of actions that are defined by the game. This game is played step-by-step.\n"
    "\n"
    "You will be given a discovery task and your goal is to iteratively come up with a plan to solve the task. Each step in the plan will be assigned to an executer that will interact with the game to achieve this plan step.\n"
    "It will return whether it succeeded or failed and information about what was achieved or why it failed. Based on this information, you need to come up with the next step of the plan till you can achieve the goal.\n"
    'After you are done, use "Done!" as the last step in your plan.\n'
    "\n"
    "For example:\n"
    "\n"
    "Task: Open the door and exit the building.\n"
    "\n"
    "Plan:\n"
    "ASSISTANT:\n"
    "Step 1: Go to the door that leads to the exit\n"
    "USER:\n"
    " -- Task completed! I am at the door that leads to the exit\n"
    "ASSISTANT:\n"
    "Step 2: Open the door\n"
    "USER:\n"
    " -- Task failed! Door is locked and I don't have the key\n"
    "ASSISTANT:\n"
    "Step 3: Find the key to the door\n"
    "USER:\n"
    " -- Task completed! The chef has the key to the door and is willing to give it to use for some food\n"
    "ASSISTANT:\n"
    "Step 4: Find food\n"
    "USER:\n"
    " -- Task completed! I found some mushroom soup in the kitchen\n"
    "ASSISTANT:\n"
    "Step 5: Give the mushroom soup to the chef and get the key\n"
    "USER:\n"
    " -- Task completed! I gave the mushroom soup and got a key in return\n"
    "ASSISTANT:\n"
    "Step 6: Use the key to unlock the door\n"
    "USER:\n"
    " -- Task completed! I used the key to unlock the door\n"
    "ASSISTANT:\n"
    "Step 7: Exit the building\n"
    "USER:\n"
    " -- Task completed! I am outside the building\n"
    "ASSISTANT:\n"
    "Step 8: Done!\n"
    "\n"
    "USER:\n"
    "**Key instructions**:\n"
    '(1) Make sure to include all the relevant information in each step e.g. "Give the mushroom soup" instead of "Give food".\n'
    "\n"
    '(2) Each step of the plan should be clear and complete and should be executable independently. E.g. dont use references such as  "previous item" or "repeat step 1".\n'
    "\n"
    "(3) When unsure, use smaller incremental steps in the plan rather than more complex steps.\n"
    "\n"
    '(4) Make sure to end the plan with the "Done!" step. If you can\'t make any progress, just generate "Done!" as the plan step.\n'
    "\n"
    "Now solve this task:\n"
    "\n"
    "Task: {{ input_str }}"
)


_BLOCK = re.compile(r"\{% if (\w+) %\}(.*?)\{% else %\}(.*?)\{% endif %\}", re.DOTALL)
_VARIABLE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render(template: str, values: dict[str, Any]) -> str:
    """Fill in a template as ``jinja2.Template(template).render(values)`` does.

    Only what these templates use is supported: ``{{ name }}`` and one
    ``{% if name %}...{% else %}...{% endif %}``. Values are inserted with ``str``, as
    Jinja does without autoescaping, and one trailing newline of the template is
    dropped (Jinja's ``keep_trailing_newline=False``).
    """
    if template.endswith("\n"):
        template = template[:-1]
    match = _BLOCK.search(template)
    if match:
        chosen = match.group(2) if values[match.group(1)] else match.group(3)
        template = template[: match.start()] + chosen + template[match.end() :]
    return _VARIABLE.sub(lambda m: str(values[m.group(1)]), template)
