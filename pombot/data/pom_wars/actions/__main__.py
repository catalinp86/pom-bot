"""Convenience file to "run" this package from the command line outside of a
test.
"""
from unittest.mock import MagicMock

from pombot.data.pom_wars import actions
from pombot.lib.pom_wars.team import Team
from pombot.lib.pom_wars.types import Outcome

user = MagicMock()
user.defend_level = 1

print(
    actions.Defends.get_random(
        user=user,
        team=Team("Knight"),
        average_daily_actions=1,
        outcome=Outcome.REGULAR,
    ).message)
