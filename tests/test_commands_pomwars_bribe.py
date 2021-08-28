import unittest
from datetime import timedelta, timezone
from unittest.async_case import IsolatedAsyncioTestCase

from pombot.commands.pom_wars import bribe
from pombot.lib.pom_wars.team import Team
from pombot.lib.storage import Storage
from pombot.lib.types import ActionType
from tests.helpers import mock_discord, semantics


class TestCommandsPomwarsBribe(IsolatedAsyncioTestCase):
    """Test the Pomwars !bribe command."""
    ctx = None

    async def asyncSetUp(self) -> None:
        """Ensure database tables exist and create contexts for the tests."""
        self.ctx = mock_discord.MockContext()
        await Storage.create_tables_if_not_exists()
        await Storage.delete_all_rows_from_all_tables()
        return await super().asyncSetUp()

    async def asyncTearDown(self) -> None:
        await Storage.delete_all_rows_from_all_tables()
        return await super().asyncTearDown()

    async def test_do_bribe_happy_day(self):
        """Test `do_bribe` does not raise an exception, fails, replies to the
        user and adds a bribe action to the DB.

        Check that no pom is added to the user session.
        """
        expected_team = Team.KNIGHTS
        role = mock_discord.MockRole(name=expected_team)

        await Storage.add_user(
            user_id=self.ctx.author.id,
            zone=timezone(timedelta(hours=0)),
            team=expected_team.value,
        )
        self.ctx.author.roles.append(role)

        with semantics.assert_not_raises():
            await bribe.do_bribe(self.ctx)

        actual_poms = await Storage.get_poms()
        self.assertEqual(0, len(actual_poms))

        self.assertEqual(1, self.ctx.reply.call_count)

        actual_actions = await Storage.get_actions()
        self.assertEqual(1, len(actual_actions))

        actual_action, = actual_actions
        self.assertEqual(self.ctx.author.id, actual_action.user_id)
        self.assertEqual(ActionType.BRIBE, ActionType(actual_action.type))
        self.assertEqual(expected_team, Team(actual_action.team))
        self.assertFalse(actual_action.was_successful)


if __name__ == "__main__":
    unittest.main()
