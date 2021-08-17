import itertools
import unittest
from collections import ChainMap
from datetime import datetime, timedelta
from unittest.async_case import IsolatedAsyncioTestCase
from unittest.mock import patch

from parameterized import parameterized

from pombot.config import Pomwars
from pombot.lib.pom_wars.common import get_average_poms
from pombot.lib.storage import Storage
from pombot.lib.tiny_tools import flatten
from pombot.lib.types import ActionType, Action
from pombot.lib.pom_wars.team import Team
from tests.helpers import mock_discord


class Environment:
    """Closure for saving and loading environment variables."""
    @classmethod
    def preserve(cls):
        """Store config variables to be reset after the tests."""
        cls.averaging_period = Pomwars.AVERAGING_PERIOD_DAYS
        cls.consider_only_successful = Pomwars.CONSIDER_ONLY_SUCCESSFUL_ACTIONS
        cls.forgiven_days = Pomwars.MAX_FORGIVEN_DAYS
        cls.shadow_cap_limit = Pomwars.SHADOW_CAP_LIMIT_PER_DAY

    @classmethod
    def restore(cls):
        """Restore saved config variables."""
        Pomwars.AVERAGING_PERIOD_DAYS = cls.averaging_period
        Pomwars.CONSIDER_ONLY_SUCCESSFUL_ACTIONS = cls.consider_only_successful
        Pomwars.MAX_FORGIVEN_DAYS = cls.forgiven_days
        Pomwars.SHADOW_CAP_LIMIT_PER_DAY = cls.shadow_cap_limit


class TestAveragingActions(IsolatedAsyncioTestCase):
    """Test get_average_poms."""
    ctx = None
    action_id = None

    @classmethod
    def setUpClass(cls):
        Environment.preserve()

    async def asyncSetUp(self):
        Environment.restore()

        self.ctx = mock_discord.MockContext()
        self.action_id = itertools.count(start=1000)

    @classmethod
    def tearDownClass(cls):
        Environment.restore()

    def create_action(self, **kwargs) -> Action:
        """Return a new action with default data and any modifications."""
        defaults = dict(
            action_id=next(self.action_id),
            user_id=self.ctx.author.id,
            team=Team.KNIGHTS,
            type=ActionType.NORMAL_ATTACK,
            was_successful=True,
            was_critical=False,
            items_dropped=None,
            raw_damage=1000,
            timestamp=datetime.now(),
        )

        return Action(**ChainMap(kwargs, defaults))

    @parameterized.expand([
        # Test method    # Shadow  # Max    # Actions per day              # Expected
        # name and       # cap     # hits   # over the last                # resulting
        # description.   # limit.  # /day.  # averaging period.            # average.
        ("sunny day",    None,      5,      ( 2,  2,  2,  2,  2,  2,  1),   2,        ),
        ("forgiveness",  None,      5,      (20, 20,  0,  0, 20, 20, 19),   5,        ),
        ("forgiveness",  None,      5,      (20, 20,  1,  2, 20, 20, 19),   5,        ),
        ("rounding",     None,      5,      (20,  1, 20,  1, 20,  1, 19),   4,        ),
        ("rounding",     None,      5,      (20,  1, 20,  1, 20,  3, 19),   5,        ),
        ("first poms",   None,      5,      ( 0,  0,  0,  0,  0,  0,  0),   0,        ),  # Tier 1
        ("first poms",   None,      5,      ( 0,  0,  0,  0,  0,  0, 16),   1,        ),  # Tier 1
        ("first poms",   None,      5,      ( 0,  0,  0,  0,  0,  0, 17),   1,        ),  # Tier 1
        ("lagged poms",  None,      5,      (10,  0,  0,  0,  0,  0, 10),   2,        ),  # Tier 1

        ("sunny day",    None,     10,      ( 2,  2,  2,  2,  2,  2,  1),   2,        ),
        ("forgiveness",  None,     10,      (20, 20,  0,  0, 20, 20, 19),  10,        ),
        ("forgiveness",  None,     10,      (20, 20,  1,  2, 20, 20, 19),  10,        ),
        ("rounding",     None,     10,      (20,  1, 20,  1, 20,  1, 19),   8,        ),
        ("rounding",     None,     10,      (20,  1, 20,  1, 20,  3, 19),   9,        ),
        ("first poms",   None,     10,      ( 0,  0,  0,  0,  0,  0,  0),   0,        ),  # Tier 1
        ("first poms",   None,     10,      ( 0,  0,  0,  0,  0,  0, 16),   2,        ),  # Tier 1
        ("first poms",   None,     10,      ( 0,  0,  0,  0,  0,  0, 17),   2,        ),  # Tier 1
        ("lagged poms",  None,     10,      (10,  0,  0,  0,  0,  0, 10),   4,        ),  # Tier 2

        ("sunny day",    None,     20,      ( 2,  2,  2,  2,  2,  2,  1),   2,        ),
        ("forgiveness",  None,     20,      (20, 20,  0,  0, 20, 20, 19),  20,        ),
        ("forgiveness",  None,     20,      (20, 20,  1,  2, 20, 20, 19),  20,        ),
        ("rounding",     None,     20,      (20,  1, 20,  1, 20,  1, 19),  16,        ),
        ("rounding",     None,     20,      (20,  1, 20,  1, 20,  3, 19),  17,        ),
        ("first poms",   None,     20,      ( 0,  0,  0,  0,  0,  0,  0),   0,        ),  # Tier 1
        ("first poms",   None,     20,      ( 0,  0,  0,  0,  0,  0, 16),   3,        ),  # Tier 1
        ("first poms",   None,     20,      ( 0,  0,  0,  0,  0,  0, 17),   4,        ),  # Tier 2
        ("lagged poms",  None,     20,      (10,  0,  0,  0,  0,  0, 10),   4,        ),  # Tier 2

        ("sunny day",    0,         0,      ( 2,  2,  2,  2,  2,  2,  1),   2,        ),
        ("forgiveness",  0,         0,      (20, 20,  0,  0, 20, 20, 19),  20,        ),
        ("forgiveness",  0,         0,      (20, 20,  1,  2, 20, 20, 19),  20,        ),
        ("rounding",     0,         0,      (20,  1, 20,  1, 20,  1, 19),  16,        ),
        ("rounding",     0,         0,      (20,  1, 20,  1, 20,  3, 19),  17,        ),
        ("first poms",   0,         0,      ( 0,  0,  0,  0,  0,  0,  0),   0,        ),  # Tier 1
        ("first poms",   0,         0,      ( 0,  0,  0,  0,  0,  0, 16),   3,        ),  # Tier 1
        ("first poms",   0,         0,      ( 0,  0,  0,  0,  0,  0, 17),   4,        ),  # Tier 2
        ("lagged poms",  0,         0,      (10,  0,  0,  0,  0,  0, 10),   4,        ),  # Tier 2

        ("sunny day",    10,        0,      ( 2,  2,  2,  2,  2,  2,  1),   2,        ),
        ("forgiveness",  10,        0,      (20, 20,  0,  0, 20, 20, 19),  10,        ),
        ("forgiveness",  10,        0,      (20, 20,  1,  2, 20, 20, 19),  10,        ),
        ("rounding",     10,        0,      (20,  1, 20,  1, 20,  1, 19),   8,        ),
        ("rounding",     10,        0,      (20,  1, 20,  1, 20,  3, 19),   9,        ),
        ("first poms",   10,        0,      ( 0,  0,  0,  0,  0,  0,  0),   0,        ),  # Tier 1
        ("first poms",   10,        0,      ( 0,  0,  0,  0,  0,  0, 16),   2,        ),  # Tier 1
        ("first poms",   10,        0,      ( 0,  0,  0,  0,  0,  0, 17),   2,        ),  # Tier 1
        ("lagged poms",  10,        0,      (10,  0,  0,  0,  0,  0, 10),   4,        ),  # Tier 2

        ("sunny day",    10,        5,      ( 2,  2,  2,  2,  2,  2,  1),   2,        ),
        ("forgiveness",  10,        5,      (20, 20,  0,  0, 20, 20, 19),  10,        ),
        ("forgiveness",  10,        5,      (20, 20,  1,  2, 20, 20, 19),  10,        ),
        ("rounding",     10,        5,      (20,  1, 20,  1, 20,  1, 19),   8,        ),
        ("rounding",     10,        5,      (20,  1, 20,  1, 20,  3, 19),   9,        ),
        ("first poms",   10,        5,      ( 0,  0,  0,  0,  0,  0,  0),   0,        ),  # Tier 1
        ("first poms",   10,        5,      ( 0,  0,  0,  0,  0,  0, 16),   2,        ),  # Tier 1
        ("first poms",   10,        5,      ( 0,  0,  0,  0,  0,  0, 17),   2,        ),  # Tier 1
        ("lagged poms",  10,        5,      (10,  0,  0,  0,  0,  0, 10),   4,        ),  # Tier 2

        ("sunny day",    10,       10,      ( 2,  2,  2,  2,  2,  2,  1),   2,        ),
        ("forgiveness",  10,       10,      (20, 20,  0,  0, 20, 20, 19),  10,        ),
        ("forgiveness",  10,       10,      (20, 20,  1,  2, 20, 20, 19),  10,        ),
        ("rounding",     10,       10,      (20,  1, 20,  1, 20,  1, 19),   8,        ),
        ("rounding",     10,       10,      (20,  1, 20,  1, 20,  3, 19),   9,        ),
        ("first poms",   10,       10,      ( 0,  0,  0,  0,  0,  0,  0),   0,        ),  # Tier 1
        ("first poms",   10,       10,      ( 0,  0,  0,  0,  0,  0, 16),   2,        ),  # Tier 1
        ("first poms",   10,       10,      ( 0,  0,  0,  0,  0,  0, 17),   2,        ),  # Tier 1
        ("lagged poms",  10,       10,      (10,  0,  0,  0,  0,  0, 10),   4,        ),  # Tier 2

        ("sunny day",    10,       20,      ( 2,  2,  2,  2,  2,  2,  1),   2,        ),
        ("forgiveness",  10,       20,      (20, 20,  0,  0, 20, 20, 19),  10,        ),
        ("forgiveness",  10,       20,      (20, 20,  1,  2, 20, 20, 19),  10,        ),
        ("rounding",     10,       20,      (20,  1, 20,  1, 20,  1, 19),   8,        ),
        ("rounding",     10,       20,      (20,  1, 20,  1, 20,  3, 19),   9,        ),
        ("first poms",   10,       20,      ( 0,  0,  0,  0,  0,  0,  0),   0,        ),  # Tier 1
        ("first poms",   10,       20,      ( 0,  0,  0,  0,  0,  0, 16),   2,        ),  # Tier 1
        ("first poms",   10,       20,      ( 0,  0,  0,  0,  0,  0, 17),   2,        ),  # Tier 1
        ("lagged poms",  10,       20,      (10,  0,  0,  0,  0,  0, 10),   4,        ),  # Tier 2
    ])
    @patch.object(Storage, "get_actions")
    async def test_get_average_poms_with_varying_successes(
        self,
        test_name,
        shadow_cap_limit,
        max_successful_per_day,
        daily_poms,
        expected_average,
        mock_get_actions,
    ):
        """Test get_average_poms with a variety of configurations."""
        Pomwars.AVERAGING_PERIOD_DAYS = len(daily_poms)
        Pomwars.CONSIDER_ONLY_SUCCESSFUL_ACTIONS = shadow_cap_limit is None
        Pomwars.MAX_FORGIVEN_DAYS = 2
        Pomwars.SHADOW_CAP_LIMIT_PER_DAY = shadow_cap_limit

        timestamp = datetime.today()

        actions_from_db = []
        for offset, poms in enumerate(reversed(daily_poms)):
            is_action_successful = itertools.chain(
                iter((True, ) * max_successful_per_day), itertools.repeat(False))

            actions_from_db.extend(
                self.create_action(
                    was_successful=next(is_action_successful),
                    timestamp=timestamp - timedelta(days=offset),
                ) for _ in range(poms))

        # As an implementation detail in the SUT, `Storage.get_actions` will
        # return all actions if `was_successful` is not specified, otherwise
        # it will return only the actions matching the criteria. Therefore we
        # need to modify our behavior to simulate that of the Storage object.
        if Pomwars.CONSIDER_ONLY_SUCCESSFUL_ACTIONS:
            actions_from_db = [a for a in actions_from_db if a.was_successful]

        Storage.get_actions = mock_get_actions
        mock_get_actions.return_value = actions_from_db

        actual_average = await get_average_poms(
            user=self.ctx.author,
            timestamp=timestamp,
        )

        self.assertEqual(expected_average, actual_average, f"{test_name=}")

    @patch.object(Storage, "get_actions")
    async def test_get_average_poms_does_not_consider_bribes(
        self,
        mock_get_actions,
    ):
        """Test get_average_poms only averages attacks and defends."""
        Pomwars.AVERAGING_PERIOD_DAYS = 1
        Pomwars.MAX_FORGIVEN_DAYS = 0

        actions_from_db = [
            self.create_action(type=action_type) for action_type in flatten((
                (normal, heavy, defend, bribe)
                for normal, heavy, defend, bribe in zip(
                    [ActionType.NORMAL_ATTACK] * 10,
                    [ActionType.HEAVY_ATTACK] * 10,
                    [ActionType.DEFEND] * 10,
                    [ActionType.BRIBE] * 10,
                )))
        ]

        Storage.get_actions = mock_get_actions
        mock_get_actions.return_value = actions_from_db

        actual_average = await get_average_poms(
            user=self.ctx.author,
            timestamp=datetime.now(),
        )

        # The SUT will add one placeholder action to the list to be averaged
        # which represents the action currently being processed as it won't
        # yet be in the DB.
        expected_average = 31

        self.assertEqual(expected_average, actual_average)


if __name__ == "__main__":
    unittest.main()
