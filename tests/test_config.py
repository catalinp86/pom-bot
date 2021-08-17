import pytest

from pombot.config import Config, Pomwars, Secrets


def test_loading_config_gives_no_errors():
    """Test Config attributes that are specified in the .env file."""
    assert Config.ERRORS_CHANNEL_NAME is not None
    assert Config.POM_CHANNEL_NAMES is not None


def test_all_secrets_exist_in_env():
    """Test Secrets attributes that must be specified in the .env file."""
    for attr in vars(Secrets):
        name, *_ = attr.split("__")

        if not name:
            continue

        assert hasattr(Secrets, name), f"{name} must be specified in .env"
        assert getattr(Secrets, name), f"{name} must not be blank in .env"

def test_averaging_values_are_valid():
    """Test that the averaging period and the number of forgiven days are valid
    relative to each other.
    """
    assert 0 <= Pomwars.MAX_FORGIVEN_DAYS < Pomwars.AVERAGING_PERIOD_DAYS
    assert Pomwars.SHADOW_CAP_LIMIT_PER_DAY is None or (
        isinstance(Pomwars.SHADOW_CAP_LIMIT_PER_DAY, int)
        and Pomwars.SHADOW_CAP_LIMIT_PER_DAY >= 0)


# NOTE: Debug attributes are tested defensively insteand of in a unit test
# because the __debug__ symbol will change with optimization levels. The test
# will always pass and some options might still be set (eg. clearing all MySQL
# tables).

if __name__ == "__main__":
    pytest.main([__file__])
