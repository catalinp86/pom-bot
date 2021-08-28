from datetime import datetime, timedelta
from enum import Enum
from string import Template

from discord.ext.commands import Bot
from discord.user import User as DiscordUser

from pombot.config import Pomwars
from pombot.lib.pom_wars.team import Team
from pombot.lib.storage import Storage
from pombot.lib.tiny_tools import normalize_newlines
from pombot.lib.types import ActionType, DateRange, User as BotUser


class Outcome(str, Enum):
    """The result of a Pom Wars action after consulting DB and rolling dice.
    """
    REGULAR = "__default_outcome__"
    CRITICAL = "critical"
    MISSED = "missed"


class Attack:
    """An attack constructable from an actions XML element."""
    def __init__(
        self,
        team: Team,
        timestamp: datetime,
        story: str,
        outcome: Outcome,
        is_heavy: bool,
    ):
        self._team = team
        self._timestamp = timestamp
        self._story = story
        self._outcome = outcome
        self._is_heavy = is_heavy

        # Prevent unnecessary DB hits.
        self._damage = None

    @property
    async def damage(self):
        """Return the total damage this attack produces after heavy, critical
        and defensive modifiers.
        """
        if self._damage is not None:
            return self._damage

        if self._outcome == Outcome.MISSED:
            self._damage = 0
        else:
            normal_dmg = Pomwars.BASE_DAMAGE_FOR_NORMAL_ATTACKS
            heavy_dmg = Pomwars.BASE_DAMAGE_FOR_HEAVY_ATTACKS
            base_damage = heavy_dmg if self._is_heavy else normal_dmg
            adjusted_damage = base_damage * await self.defensive_multiplier

            if self._outcome == Outcome.CRITICAL:
                self._damage =  adjusted_damage * Pomwars.DAMAGE_MULTIPLIER_FOR_CRITICAL
            else:
                self._damage = adjusted_damage

        return self._damage

    @property
    async def defensive_multiplier(self) -> float:
        """Return the cumulative effect of the opposing team's Defend actions.
        """
        defend_actions = await Storage.get_actions(
            action_type=ActionType.DEFEND,
            team=(~self._team).value,
            was_successful=True,
            date_range=DateRange(
                self._timestamp - timedelta(minutes=Pomwars.DEFEND_DURATION_MINUTES),
                self._timestamp + timedelta(seconds=1),
            ),
        )
        defenders = await Storage.get_users_by_id([a.user_id for a in defend_actions])
        multipliers = [Pomwars.DEFEND_LEVEL_MULTIPLIERS[d.defend_level] for d in defenders]
        multiplier = min([sum(multipliers), Pomwars.MAXIMUM_TEAM_DEFENCE])

        return 1 - multiplier

    @property
    async def message(self) -> str:
        """Return the effect and the markdown-formatted story for this attack as
        a combined string.
        """
        message_lines = [f"{Pomwars.Emotes.ATTACK} `{{}} damage!`".format(
            ("{:.1f}" if await self.damage % 1 else "{}").format(self._damage)
        )]

        if self._outcome == Outcome.CRITICAL:
            message_lines += [f"{Pomwars.Emotes.CRITICAL} `Critical attack!`"]

        action_result = "\n".join(message_lines)
        formatted_story = "*" + normalize_newlines(self._story) + "*"

        return ("\n\n".join([action_result, formatted_story])
                if self._outcome != Outcome.MISSED else formatted_story)

    @property
    def title(self) -> str:
        """Title that includes the name of the team user attacked."""
        return "You have used{indicator}Attack against {team}!".format(
            indicator = " Heavy " if self._is_heavy else " ",
            team=f"{(~self._team)}s",
        )

    @property
    def colour(self) -> int:
        """Return an embed colour based on whether the attack is heavy."""
        return (Pomwars.HEAVY_ATTACK_COLOUR
                if self._is_heavy else Pomwars.NORMAL_ATTACK_COLOUR)


class Defend:
    """A defend constructable from an actions XML element."""
    def __init__(
        self,
        user: BotUser,
        team: Team,
        outcome: Outcome,
        story: str
    ):
        self._user = user
        self._team = team
        self._outcome = outcome
        self._story = story

    @property
    def message(self) -> str:
        """Return the effect and the markdown-formatted story for this defend
        as a combined string.
        """
        action_result = "{emt} `{dfn:.0f}% team damage reduction!`".format(
            emt=Pomwars.Emotes.DEFEND,
            dfn=100 * Pomwars.DEFEND_LEVEL_MULTIPLIERS[self._user.defend_level],
        )
        formatted_story = "*" + normalize_newlines(self._story) + "*"

        return ("\n\n".join([action_result, formatted_story])
                if self._outcome != Outcome.MISSED else formatted_story)

    @property
    def title(self) -> str:
        """Title that includes the name of the team user attacked."""
        return "You have used Defend against {team}s!".format(
            team=~self._team)

    @property
    def colour(self) -> int:
        """Return an embed colour based on whether the attack is heavy."""
        return Pomwars.DEFEND_COLOUR


class Bribe:
    """A bribe constructable from an actions XML element."""
    def __init__(self, story: str):
        self._story = story

    def get_message(self, user: DiscordUser, bot: Bot) -> str:
        """Return the markdown-formatted story for this bribe as a combined
        string.
        """
        story = Template(normalize_newlines(self._story))

        return story.safe_substitute(
            NAME=user.name,
            DISPLAY_NAME=user.display_name,
            DISCRIMINATOR=user.discriminator,
            BOTNAME=bot.user.name
        )
