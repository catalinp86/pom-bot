import random
from datetime import datetime
from functools import partial

from discord.ext.commands import Context

import pombot.lib.pom_wars.errors as war_crimes
from pombot.config import Debug, Pomwars, Reactions
from pombot.data.pom_wars.actions import Attacks
from pombot.lib.errors import DescriptionTooLongError
from pombot.lib.messages import send_embed_message
from pombot.lib.pom_wars.action_chances import is_action_successful
from pombot.lib.pom_wars.common import (check_user_add_pom, get_average_poms,
                                        get_user_team)
from pombot.lib.pom_wars.types import Outcome
from pombot.lib.storage import Storage
from pombot.lib.types import ActionType
from pombot.state import State


async def do_attack(ctx: Context, *args):
    """Attack the other team."""
    timestamp = datetime.now()
    heavy_attack = bool(args) and args[0].casefold() in Pomwars.HEAVY_QUALIFIERS
    description = " ".join(args[1:] if heavy_attack else args)

    try:
        _ = await check_user_add_pom(ctx, description, timestamp)
    except (war_crimes.UserDoesNotExistError, DescriptionTooLongError):
        return

    team = get_user_team(ctx.author)
    action = {
        "user":           ctx.author,
        "team":           team.value,
        "action_type":    ActionType.HEAVY_ATTACK
                              if heavy_attack else ActionType.NORMAL_ATTACK,
        "was_successful": False,
        "was_critical":   False,
        "items_dropped":  "",
        "damage":         None,
        "time_set":       timestamp,
    }

    get_random_attack = partial(Attacks.get_random, **dict(
        timestamp=timestamp,
        team=team,
        average_daily_actions=await get_average_poms(ctx.author, timestamp),
        heavy=heavy_attack,
    ))

    if await is_action_successful(ctx.author, timestamp, heavy_attack):
        action["was_successful"] = True
        await ctx.message.add_reaction(Reactions.BOOM)

        action["was_critical"] = random.random() <= Pomwars.BASE_CHANCE_FOR_CRITICAL
        attack = get_random_attack(outcome=Outcome.CRITICAL if
                                   action["was_critical"] else Outcome.REGULAR)

        action["damage"] = await attack.damage
    else:
        attack = get_random_attack(outcome=Outcome.MISSED)

    await Storage.add_pom_war_action(**action)

    await send_embed_message(
        None,
        title=attack.title,
        description=await attack.message,
        icon_url=None,
        colour=attack.colour,
        _func=ctx.reply,
    )

    await State.scoreboard.update()

    if Debug.POMWARS_ACTIONS_ALWAYS_SUCCEED:
        print(f"!attack took: {datetime.now() - timestamp}")
