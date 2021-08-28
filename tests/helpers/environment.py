from pombot.config import Pomwars


class Environment:
    """Closure for saving and loading environment variables."""
    @classmethod
    def preserve(cls):
        """Store config variables to be reset after the tests."""
        cls.base_damage_for_normal_attack = Pomwars.BASE_DAMAGE_FOR_NORMAL_ATTACKS
        cls.base_damage_for_heavy_attack  = Pomwars.BASE_DAMAGE_FOR_HEAVY_ATTACKS
        cls.base_chance_for_critical      = Pomwars.BASE_CHANCE_FOR_CRITICAL
        cls.damage_level_for_critical     = Pomwars.DAMAGE_MULTIPLIER_FOR_CRITICAL
        cls.defend_level_multipliers      = Pomwars.DEFEND_LEVEL_MULTIPLIERS

        cls.averaging_period              = Pomwars.AVERAGING_PERIOD_DAYS
        cls.consider_only_successful      = Pomwars.CONSIDER_ONLY_SUCCESSFUL_ACTIONS
        cls.forgiven_days                 = Pomwars.MAX_FORGIVEN_DAYS
        cls.shadow_cap_limit              = Pomwars.SHADOW_CAP_LIMIT_PER_DAY

    @classmethod
    def restore(cls):
        """Restore saved config variables."""
        Pomwars.BASE_DAMAGE_FOR_NORMAL_ATTACKS   = cls.base_damage_for_normal_attack
        Pomwars.BASE_DAMAGE_FOR_HEAVY_ATTACKS    = cls.base_damage_for_heavy_attack
        Pomwars.BASE_CHANCE_FOR_CRITICAL         = cls.base_chance_for_critical
        Pomwars.DAMAGE_MULTIPLIER_FOR_CRITICAL   = cls.damage_level_for_critical
        Pomwars.DEFEND_LEVEL_MULTIPLIERS         = cls.defend_level_multipliers

        Pomwars.AVERAGING_PERIOD_DAYS            = cls.averaging_period
        Pomwars.CONSIDER_ONLY_SUCCESSFUL_ACTIONS = cls.consider_only_successful
        Pomwars.MAX_FORGIVEN_DAYS                = cls.forgiven_days
        Pomwars.SHADOW_CAP_LIMIT_PER_DAY         = cls.shadow_cap_limit
