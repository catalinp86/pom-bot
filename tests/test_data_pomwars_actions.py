import shutil
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Tuple

from parameterized import parameterized

from pombot.config import Pomwars
from pombot.data import Locations
from pombot.data.pom_wars import actions
from pombot.lib.pom_wars.team import Team
from pombot.lib.pom_wars.types import Outcome
from tests.helpers.semantics import assert_not_raises

# For the purposes of `get_random`, these values are simply passed through to
# the returned `Attack` or `Defend` object.  So they need to exist, but their
# values are arbitrary.
DUMMY_USER = object()
DUMMY_TIMESTAMP = object()

# pylint: disable=protected-access


class TestActionsData(unittest.TestCase):
    """Test reading the various action descriptions from XML."""
    @classmethod
    def setUpClass(cls):
        cls.pomwars_actions_dir_orig = Locations.POMWARS_ACTIONS_DIR

        cls.temp_actions_dir = TemporaryDirectory()  # pylint: disable=consider-using-with
        Locations.POMWARS_ACTIONS_DIR = Path(cls.temp_actions_dir.name)

        shutil.copy(actions.ACTIONS_SCHEMA, Locations.POMWARS_ACTIONS_DIR)

    def setUp(self):
        # Invalid XMLs will cause valid XML tests to fail.
        for item in Locations.POMWARS_ACTIONS_DIR.rglob("*.xml"):
            item.unlink()

    @classmethod
    def tearDownClass(cls):
        cls.temp_actions_dir.cleanup()
        Locations.POMWARS_ACTIONS_DIR = cls.pomwars_actions_dir_orig

    @staticmethod
    def write_actions_xml(xml_content: str, filename: str = "actions.xml"):
        """Write xml_content to an XML file in the actions directory."""
        xml_path = Locations.POMWARS_ACTIONS_DIR / filename
        xml_path.write_text(xml_content)

    @staticmethod
    def instantiate_actions() -> Tuple:
        """Create new instances of the protected actions generators."""
        return actions._Attacks(), actions._Defends(), actions._Bribes()

    def test_actions_get_random_story_from_correct_node(self):
        """Test actions can be retrieved from correctly formed actions XMLs."""
        average_daily_actions = 1

        stories = {
            "kn_crit_nrm": "knight critical normal attack",
            "kn_crit_hvy": "knight critical heavy attack",
            "kn_miss_nrm": "knight missed normal attack",
            "kn_miss_hvy": "knight missed heavy attack",
            "kn_nrm":      "knight normal attack",
            "kn_hvy":      "knight heavy attack",
            "kn_miss_dfn": "knight missed defend",
            "kn_dfn":      "knight defend",
            "vk_crit_nrm": "viking critical normal attack",
            "vk_crit_hvy": "viking critical heavy attack",
            "vk_miss_nrm": "viking missed normal attack",
            "vk_miss_hvy": "viking missed heavy attack",
            "vk_nrm":      "viking normal attack",
            "vk_hvy":      "viking heavy attack",
            "vk_miss_dfn": "viking missed defend",
            "vk_dfn":      "viking defend",
            "br":          "bribe",
        }

        self.write_actions_xml(textwrap.dedent(f"""\
            <actions>
                <team name="{Pomwars.KNIGHT_ROLE}">
                    <tier level="{average_daily_actions}">
                        <normal_attack outcome="critical">{stories["kn_crit_nrm"]}</normal_attack>
                        <heavy_attack outcome="critical">{stories["kn_crit_hvy"]}</heavy_attack>
                        <normal_attack outcome="missed">{stories["kn_miss_nrm"]}</normal_attack>
                        <heavy_attack outcome="missed">{stories["kn_miss_hvy"]}</heavy_attack>
                        <normal_attack>{stories["kn_nrm"]}</normal_attack>
                        <heavy_attack>{stories["kn_hvy"]}</heavy_attack>
                        <defend outcome="missed">{stories["kn_miss_dfn"]}</defend>
                        <defend>{stories["kn_dfn"]}</defend>
                    </tier>
                </team>
                <team name="{Pomwars.VIKING_ROLE}">
                    <tier level="{average_daily_actions}">
                        <normal_attack outcome="critical">{stories["vk_crit_nrm"]}</normal_attack>
                        <heavy_attack outcome="critical">{stories["vk_crit_hvy"]}</heavy_attack>
                        <normal_attack outcome="missed">{stories["vk_miss_nrm"]}</normal_attack>
                        <heavy_attack outcome="missed">{stories["vk_miss_hvy"]}</heavy_attack>
                        <normal_attack>{stories["vk_nrm"]}</normal_attack>
                        <heavy_attack>{stories["vk_hvy"]}</heavy_attack>
                        <defend outcome="missed">{stories["vk_miss_dfn"]}</defend>
                        <defend>{stories["vk_dfn"]}</defend>
                    </tier>
                </team>
                <bribe>{stories["br"]}</bribe>
            </actions>
        """))

        with assert_not_raises():
            attacks, defends, bribes = self.instantiate_actions()

        average = {"average_daily_actions": average_daily_actions}
        user = {"user": DUMMY_USER}
        timestamp = {"timestamp": DUMMY_TIMESTAMP}

        for action, kwargs, expected_story in (
            # pylint: disable=line-too-long
            (attacks, {**timestamp, "team": Team.KNIGHTS, **average, "outcome": Outcome.REGULAR,  "heavy": False}, stories["kn_nrm"]),
            (attacks, {**timestamp, "team": Team.KNIGHTS, **average, "outcome": Outcome.REGULAR,  "heavy": True},  stories["kn_hvy"]),
            (attacks, {**timestamp, "team": Team.KNIGHTS, **average, "outcome": Outcome.CRITICAL, "heavy": False}, stories["kn_crit_nrm"]),
            (attacks, {**timestamp, "team": Team.KNIGHTS, **average, "outcome": Outcome.CRITICAL, "heavy": True},  stories["kn_crit_hvy"]),
            (attacks, {**timestamp, "team": Team.KNIGHTS, **average, "outcome": Outcome.MISSED,   "heavy": False}, stories["kn_miss_nrm"]),
            (attacks, {**timestamp, "team": Team.KNIGHTS, **average, "outcome": Outcome.MISSED,   "heavy": True},  stories["kn_miss_hvy"]),
            (attacks, {**timestamp, "team": Team.VIKINGS, **average, "outcome": Outcome.REGULAR,  "heavy": False}, stories["vk_nrm"]),
            (attacks, {**timestamp, "team": Team.VIKINGS, **average, "outcome": Outcome.REGULAR,  "heavy": True},  stories["vk_hvy"]),
            (attacks, {**timestamp, "team": Team.VIKINGS, **average, "outcome": Outcome.CRITICAL, "heavy": False}, stories["vk_crit_nrm"]),
            (attacks, {**timestamp, "team": Team.VIKINGS, **average, "outcome": Outcome.CRITICAL, "heavy": True},  stories["vk_crit_hvy"]),
            (attacks, {**timestamp, "team": Team.VIKINGS, **average, "outcome": Outcome.MISSED,   "heavy": False}, stories["vk_miss_nrm"]),
            (attacks, {**timestamp, "team": Team.VIKINGS, **average, "outcome": Outcome.MISSED,   "heavy": True},  stories["vk_miss_hvy"]),

            (defends, {**user, "team": Team.KNIGHTS, **average, "outcome": Outcome.REGULAR}, stories["kn_dfn"]),
            (defends, {**user, "team": Team.KNIGHTS, **average, "outcome": Outcome.MISSED},  stories["kn_miss_dfn"]),
            (defends, {**user, "team": Team.VIKINGS, **average, "outcome": Outcome.REGULAR}, stories["vk_dfn"]),
            (defends, {**user, "team": Team.VIKINGS, **average, "outcome": Outcome.MISSED},  stories["vk_miss_dfn"]),

            (bribes,  {}, stories["br"])
            # pylint: enable=line-too-long
        ):
            actual_story = action.get_random(**kwargs)._story
            self.assertEqual(expected_story, actual_story)

    @parameterized.expand([
        # You're in tier 1.
        (0,  1),
        (1,  1),
        (2,  1),
        (3,  1),
                    # You're in tier 2.
                    (4,  2),
                    (5,  2),
                    (6,  2),
                    (7,  2),
                                # You're in tier 3.
                                (8,  3),
                                (9,  3),
                                (10, 3),
                                (11, 3),
                                (12, 3),
                                # ...
    ])
    def test_actions_get_random_story_from_correct_tier(
        self,
        average_daily_actions,
        expected_tier,
    ):
        """Test actions are retrieved from the correct tier in the actions XMLs
        given a player's average number of daily actions.
        """
        team_name = Pomwars.KNIGHT_ROLE

        tiered_stories = {
            1: {
                "nrm": "tier 1 normal attack",
                "hvy": "tier 1 heavy attack",
                "dfn": "tier 1 defend",
            },
            2: {
                "nrm": "tier 2 normal attack",
                "hvy": "tier 2 heavy attack",
                "dfn": "tier 2 defend",
            },
            3: {
                "nrm": "tier 3 normal attack",
                "hvy": "tier 3 heavy attack",
                "dfn": "tier 3 defend",
            },
        }

        tiers = "".join([f"""\
            <tier level="{tier}">
                <normal_attack>{stories["nrm"]}</normal_attack>
                <heavy_attack>{stories["hvy"]}</heavy_attack>
                <defend>{stories["dfn"]}</defend>
            </tier>
        """ for tier, stories in tiered_stories.items()])

        self.write_actions_xml(textwrap.dedent(f"""\
            <actions>
                <team name="{team_name}">
                    {tiers}
                </team>
            </actions>
        """))

        with assert_not_raises():
            attacks, defends, _ = self.instantiate_actions()

        user = {"user": DUMMY_USER}
        timestamp = {"timestamp": DUMMY_TIMESTAMP}
        common_kwargs = {
            "average_daily_actions": average_daily_actions,
            "team": team_name,
            "outcome": Outcome.REGULAR,
        }

        actual_nrm = attacks.get_random(**common_kwargs, **timestamp, heavy=False)
        actual_hvy = attacks.get_random(**common_kwargs, **timestamp, heavy=True)
        actual_dfn = defends.get_random(**common_kwargs, **user)

        self.assertEqual(tiered_stories[expected_tier]["nrm"], actual_nrm._story)
        self.assertEqual(tiered_stories[expected_tier]["hvy"], actual_hvy._story)
        self.assertEqual(tiered_stories[expected_tier]["dfn"], actual_dfn._story)


if __name__ == "__main__":
    unittest.main()
