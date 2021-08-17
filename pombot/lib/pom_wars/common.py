from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from discord.ext.commands import Context
from discord.user import User as DiscordUser

import pombot.lib.pom_wars.errors as war_crimes
from pombot.config import Config, Pomwars, Reactions
from pombot.lib.errors import DescriptionTooLongError
from pombot.lib.storage import Storage
from pombot.lib.types import ActionType, DateRange, User as BotUser


async def check_user_add_pom(
    ctx: Context,
    description: str,
    timestamp: datetime,
) -> BotUser:
    """Based on `ctx` verify a user exists, ensure the pom description is
    within limits and add their pom to the DB.

    @param ctx The context to use for reading author and replying.
    @param description Pom description provided by the user via args.
    @param timestamp The time a user issued the command.
    @raises UserDoesNotExistError, DescriptionTooLongError.
    @return The user from the DB based on their ID.
    """
    try:
        user = await Storage.get_user_by_id(ctx.author.id)
    except war_crimes.UserDoesNotExistError:
        await ctx.reply("How did you get in here? You haven't joined the war!")
        await ctx.message.add_reaction(Reactions.ROBOT)
        raise

    if len(description) > Config.DESCRIPTION_LIMIT:
        await ctx.message.add_reaction(Reactions.WARNING)
        await ctx.send(f"{ctx.author.mention}, your pom description must "
                       f"be fewer than {Config.DESCRIPTION_LIMIT} characters.")
        raise DescriptionTooLongError()

    await Storage.add_poms_to_user_session(
        ctx.author,
        descript=description,
        count=1,
        time_set=timestamp,
    )
    await ctx.message.add_reaction(Reactions.TOMATO)

    return user


async def get_average_poms(
    user: DiscordUser,
    timestamp: datetime,
) -> int:
    """Return user's average number of pom wars actions per day."""
    kwargs = dict(user=user, date_range=DateRange(_offset(timestamp), timestamp))

    if only_successful := Pomwars.CONSIDER_ONLY_SUCCESSFUL_ACTIONS:
        kwargs.update(was_successful=only_successful)

    actions = await Storage.get_actions(**kwargs) + [_PlaceholderAction(timestamp)]

    actions = (a for a in actions if a.type in (
        ActionType.DEFEND,
        ActionType.NORMAL_ATTACK,
        ActionType.HEAVY_ATTACK,
        ActionType.PLACEHOLDER,
    ))

    period = Pomwars.AVERAGING_PERIOD_DAYS - Pomwars.MAX_FORGIVEN_DAYS
    counter = Counter(a.timestamp.date() for a in actions)
    counts = (count for _, count in counter.most_common()[:period])

    if not only_successful and (limit := Pomwars.SHADOW_CAP_LIMIT_PER_DAY):
        counts = (count if count < limit else limit for count in counts)

    return round(sum(counts) / period)


def _offset(timestamp):
    """Return a truncated timestamp of the passed timestamp minus the
    configured averaging period.
    """
    date = (timestamp - timedelta(days=Pomwars.AVERAGING_PERIOD_DAYS)).date()
    return datetime(date.year, date.month, date.day)


@dataclass
class _PlaceholderAction:
    """An object that acts enough like an Action to be averaged.

    We need to append one extra action to the list of actions returned from
    the DB because the current action has not yet been added to the DB.
    """
    timestamp: datetime
    type: ActionType = ActionType.PLACEHOLDER
