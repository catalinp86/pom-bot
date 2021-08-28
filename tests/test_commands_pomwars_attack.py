import unittest
from datetime import timedelta, timezone
from unittest.async_case import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from discord.ext.commands.context import Context
from parameterized import parameterized

from pombot.commands.pom_wars import attack, defend
from pombot.config import Pomwars
from pombot.lib.pom_wars.team import Team
from pombot.lib.storage import Storage
from pombot.lib.types import ActionType
from pombot.state import State
from tests.helpers import mock_discord, semantics
from tests.helpers.environment import Environment


class TestCommandsPomwarsAttack(IsolatedAsyncioTestCase):
    """Test the Pomwars !attack command."""
    ctx = None

    @classmethod
    def setUpClass(cls):
        Environment.preserve()

    async def asyncSetUp(self) -> None:
        """Ensure database tables exist, create contexts for the tests and
        configure reusable mocks.
        """
        Environment.restore()

        self.ctx = mock_discord.MockContext()
        await Storage.create_tables_if_not_exists()
        await Storage.delete_all_rows_from_all_tables()

        for patcher in (
            patch.object(attack,  "is_action_successful"),
            patch.object(State,   "scoreboard"),
        ):
            _ = patcher.start(), self.addAsyncCleanup(patcher.stop)

        return await super().asyncSetUp()

    async def asyncTearDown(self) -> None:
        await Storage.delete_all_rows_from_all_tables()
        return await super().asyncTearDown()

    @classmethod
    def tearDownClass(cls):
        Environment.restore()

    @parameterized.expand([
        ((),          ActionType.NORMAL_ATTACK, True,  ),
        ((),          ActionType.NORMAL_ATTACK, False, ),
        (("heavy", ), ActionType.HEAVY_ATTACK,  True,  ),
        (("heavy", ), ActionType.HEAVY_ATTACK,  False, ),
    ])
    async def test_do_attack_happy_day(
        self,
        user_supplied_args,
        expected_action_type,
        is_action_successful_return_value,
    ):
        """Test `do_attack` does not raise an exception, succeeds, sends an
        embed to the user, updates the scoreboard and adds a pom and action to
        the DB.
        """
        attack.is_action_successful.return_value = is_action_successful_return_value
        State.scoreboard.update = AsyncMock()

        expected_team = Team.KNIGHTS
        role = mock_discord.MockRole(name=expected_team)

        await Storage.add_user(
            user_id=self.ctx.author.id,
            zone=timezone(timedelta(hours=0)),
            team=expected_team.value,
        )
        self.ctx.author.roles.append(role)

        with semantics.assert_not_raises():
            await attack.do_attack(self.ctx, *user_supplied_args)

        actual_poms = await Storage.get_poms()
        self.assertEqual(1, len(actual_poms))
        self.assertEqual(self.ctx.author.id, actual_poms[0].user_id)

        self.assertEqual(1, self.ctx.reply.call_count)
        self.assertIsNotNone(self.ctx.reply.call_args_list[0].kwargs.get("embed"))

        self.assertEqual(1, State.scoreboard.update.call_count)

        actual_actions = await Storage.get_actions()
        self.assertEqual(1, len(actual_actions))

        actual_action, = actual_actions
        self.assertEqual(self.ctx.author.id, actual_action.user_id)
        self.assertEqual(is_action_successful_return_value, actual_action.was_successful)
        self.assertEqual(expected_action_type, ActionType(actual_action.type))
        self.assertEqual(expected_team, Team(actual_action.team))

    @parameterized.expand([
        (0, (),          False, 10.0,  ),
        (1, (),          False,  9.5,  ),
        (2, (),          False,  9.0,  ),
        (0, (),          True,  13.5,  ),
        (1, (),          True,  12.83, ),
        (2, (),          True,  12.15, ),
        (0, ("heavy", ), False, 40.0,  ),
        (1, ("heavy", ), False, 38.0,  ),
        (2, ("heavy", ), False, 36.0,  ),
        (0, ("heavy", ), True,  54.0,  ),
        (1, ("heavy", ), True,  51.3,  ),
        (2, ("heavy", ), True,  48.6,  ),
    ])
    async def test_attack_does_less_damage_after_enemy_defends(
        self,
        number_of_defenders,
        user_supplied_args,
        attack_is_critical,
        expected_damage_output,
    ):
        """Test that the !attack command does less damage after some amount of
        enemies do their own !defend actions.
        """
        Pomwars.BASE_DAMAGE_FOR_NORMAL_ATTACKS = 10
        Pomwars.BASE_DAMAGE_FOR_HEAVY_ATTACKS = 40
        Pomwars.BASE_CHANCE_FOR_CRITICAL = float(attack_is_critical)
        Pomwars.DAMAGE_MULTIPLIER_FOR_CRITICAL = 1.35

        # For this test, all defenders are level 1.
        Pomwars.DEFEND_LEVEL_MULTIPLIERS = {1: 0.05}

        attack.is_action_successful.return_value = True
        State.scoreboard.update = AsyncMock()

        async def add_player(ctx: Context, team: Team):
            await Storage.add_user(user_id=ctx.author.id,
                                   zone=timezone(timedelta(hours=0)),
                                   team=team.value)
            ctx.author.roles.append(mock_discord.MockRole(name=team.value))

        for _ in range(number_of_defenders):
            new_ctx = mock_discord.MockContext()
            await add_player(new_ctx, Team.VIKINGS)
            await defend.do_defend(new_ctx)

        with semantics.assert_not_raises():
            await add_player(self.ctx, Team.KNIGHTS)
            await attack.do_attack(self.ctx, *user_supplied_args)

        all_actions = await Storage.get_actions()
        assert len(all_actions) == number_of_defenders + 1

        attacker_action = next(a for a in all_actions if a.user_id == self.ctx.author.id)
        self.assertEqual(expected_damage_output, attacker_action.damage)


if __name__ == "__main__":
    unittest.main()
