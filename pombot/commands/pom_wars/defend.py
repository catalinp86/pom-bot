from datetime import datetime

from discord.ext.commands import Context

import pombot.lib.pom_wars.errors as war_crimes
from pombot.config import Debug, Reactions
from pombot.data.pom_wars.actions import Defends
from pombot.lib.errors import DescriptionTooLongError
from pombot.lib.messages import send_embed_message
from pombot.lib.pom_wars.action_chances import is_action_successful
from pombot.lib.pom_wars.common import (check_user_add_pom, get_average_poms,
                                        get_user_team)
from pombot.lib.pom_wars.types import Outcome
from pombot.lib.storage import Storage
from pombot.lib.types import ActionType


async def do_defend(ctx: Context, *args):
    """Defend your team."""
    description = " ".join(args)
    timestamp = datetime.now()

    try:
        defender = await check_user_add_pom(ctx, description, timestamp)
    except (war_crimes.UserDoesNotExistError, DescriptionTooLongError):
        return

    team = get_user_team(ctx.author)

    action = {
        "user":           ctx.author,
        "team":           team.value,
        "action_type":    ActionType.DEFEND,
        "was_successful": False,
        "was_critical":   None,
        "items_dropped":  "",
        "damage":         None,
        "time_set":       timestamp,
    }

    action["was_successful"] = await is_action_successful(ctx.author, timestamp)

    if action["was_successful"]:
        await ctx.message.add_reaction(Reactions.SHIELD)

    defend = Defends.get_random(
        user=defender,
        team=team,
        outcome=Outcome.REGULAR if action["was_successful"] else Outcome.MISSED,
        average_daily_actions=await get_average_poms(ctx.author, timestamp),
    )

    await Storage.add_pom_war_action(**action)

    await send_embed_message(
        None,
        title=defend.title,
        description=defend.message,
        colour=defend.colour,
        icon_url=None,
        _func=ctx.reply,
    )

    if Debug.POMWARS_ACTIONS_ALWAYS_SUCCEED:
        print(f"!defend took: {datetime.now() - timestamp}")
