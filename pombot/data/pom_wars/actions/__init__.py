import datetime
import random
from enum import Enum
from typing import Union

from lxml import etree
import discord.user as DiscordUser

from pombot.data import Locations
from pombot.lib.pom_wars.team import Team
from pombot.lib.pom_wars.types import Attack, Bribe, Defend, Outcome
from pombot.lib.tiny_tools import flatten
from pombot.lib.types import User as BotUser

ACTIONS_SCHEMA = Locations.POMWARS_ACTIONS_DIR / "actions.xsd"


class _XMLTags(str, Enum):
    NORMAL_ATTACK = "normal_attack"
    HEAVY_ATTACK = "heavy_attack"
    DEFEND = "defend"
    BRIBE = "bribe"


class _XMLLoader:
    def __init__(self) -> None:
        # pylint: disable=c-extension-no-member
        schema = etree.XMLSchema(etree.parse(str(ACTIONS_SCHEMA)))
        parser = etree.XMLParser(schema=schema)

        self._xmls = [
            etree.parse(str(path), parser=parser).getroot()
            for path in Locations.POMWARS_ACTIONS_DIR.rglob("*.xml")
        ]
        # pylint: enable=c-extension-no-member

    @staticmethod
    def _get_tier_from_average_actions(average_daily_actions: Union[float, int]) -> int:
        """Calculate a user's tier based on their average daily Pom Wars
        actions, rather than their total number of poms.
        """
        for tier, criteria in {
            1: average_daily_actions <= 3,
            2: average_daily_actions <= 7,
            3: average_daily_actions > 7,
        }.items():
            if criteria:
                return tier

        raise RuntimeError(f'No eligible tier for criteria: "{average_daily_actions=}"')


class _Attacks(_XMLLoader):
    def get_random(
        self,
        *,
        timestamp: datetime,
        team: Team,
        average_daily_actions: int,
        outcome: Outcome,
        heavy: bool,
    ) -> Attack:
        """Return a random Attack from the XMLs."""
        tags = {False: _XMLTags.NORMAL_ATTACK, True: _XMLTags.HEAVY_ATTACK}
        tier = self._get_tier_from_average_actions(average_daily_actions)

        choice = random.choice([
            action for action in flatten(
                xml.xpath(
                    f".//team[@name='{team}']/tier[@level='{tier}']/{tags[heavy]}"
                ) for xml in self._xmls)
            if action.attrib.get("outcome", Outcome.REGULAR) == outcome
        ])

        return Attack(
            team=team,
            timestamp=timestamp,
            story=choice.text.strip(),
            outcome=outcome,
            is_heavy=heavy,
        )


class _Defends(_XMLLoader):
    def get_random(
        self,
        user: BotUser,
        team: Team,
        average_daily_actions: int,
        outcome: Outcome,
    ):
        """Return a random Defend from the XMLs."""
        tag = _XMLTags.DEFEND
        tier = self._get_tier_from_average_actions(average_daily_actions)

        choice = random.choice([
            action for action in flatten(
                x.xpath(f".//team[@name='{team}']/tier[@level='{tier}']/{tag}")
                for x in self._xmls)
            if action.attrib.get("outcome", Outcome.REGULAR) == outcome])

        return Defend(user, team, outcome, story=choice.text.strip())


class _Bribes(_XMLLoader):
    def get_random(self):
        """Return a random Bribe from the XMLs."""
        choice = random.choice(
            flatten(x.xpath(f".//{_XMLTags.BRIBE}") for x in self._xmls))

        return Bribe(story=choice.text.strip())


# Exports
Attacks = _Attacks()
Defends = _Defends()
Bribes = _Bribes()
