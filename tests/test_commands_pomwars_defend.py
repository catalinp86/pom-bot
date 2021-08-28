import unittest
from datetime import timedelta, timezone
from unittest.async_case import IsolatedAsyncioTestCase
from unittest.mock import patch

from parameterized import parameterized

from pombot.commands.pom_wars import defend
from pombot.lib.pom_wars.team import Team
from pombot.lib.storage import Storage
from pombot.lib.types import ActionType
from tests.helpers import mock_discord, semantics


class TestCommandsPomwarsDefend(IsolatedAsyncioTestCase):
    """Test the Pomwars !defend command."""
    ctx = None

    async def asyncSetUp(self) -> None:
        """Ensure database tables exist, create contexts for the tests and
        configure reusable mocks.
        """
        self.ctx = mock_discord.MockContext()
        await Storage.create_tables_if_not_exists()
        await Storage.delete_all_rows_from_all_tables()

        patcher = patch.object(defend, "is_action_successful")
        patcher.start()
        self.addAsyncCleanup(patcher.stop)

        return await super().asyncSetUp()

    async def asyncTearDown(self) -> None:
        await Storage.delete_all_rows_from_all_tables()
        return await super().asyncTearDown()

    @parameterized.expand([
        (True,),
        (False,),
    ])
    async def test_do_defend_happy_day(
        self,
        is_action_successful_return_value,
    ):
        """Test `do_defend` does not raise an exception, succeeds, sends an
        embed to the user and adds a pom for the user and a defend action to
        the DB.
        """
        defend.is_action_successful.return_value = is_action_successful_return_value

        expected_team = Team.KNIGHTS
        role = mock_discord.MockRole(name=expected_team)

        await Storage.add_user(
            user_id=self.ctx.author.id,
            zone=timezone(timedelta(hours=0)),
            team=expected_team.value,
        )
        self.ctx.author.roles.append(role)

        with semantics.assert_not_raises():
            await defend.do_defend(self.ctx)

        actual_poms = await Storage.get_poms()
        self.assertEqual(1, len(actual_poms))
        self.assertEqual(self.ctx.author.id, actual_poms[0].user_id)

        self.assertEqual(1, self.ctx.reply.call_count)
        self.assertIsNotNone(self.ctx.reply.call_args_list[0].kwargs.get("embed"))

        actual_actions = await Storage.get_actions()
        self.assertEqual(1, len(actual_actions))

        actual_action, = actual_actions
        self.assertEqual(self.ctx.author.id, actual_action.user_id)
        self.assertEqual(is_action_successful_return_value, actual_action.was_successful)
        self.assertEqual(ActionType.DEFEND, ActionType(actual_action.type))
        self.assertEqual(expected_team, Team(actual_action.team))


if __name__ == "__main__":
    unittest.main()
