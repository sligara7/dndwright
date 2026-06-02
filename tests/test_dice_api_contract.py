"""API contract for the dndwright.dice subpackage — pins its public surface."""

import dndwright.dice as dice

EXPECTED_DICE_PUBLIC = {
    "DiceEngine",
    "DiceEngineProtocol",
    "DiceGroup",
    "ParsedExpression",
    "RollResult",
    "ExpressionResult",
    "AdvantageData",
    "AttackRoll",
    "SaveRoll",
    "DamageRoll",
    "DeathSave",
    "StatArray",
    "AbilityScoreRoll",
    "HitDiceResult",
    "HitDieRoll",
}


def test_dice_all_matches_contract():
    assert set(dice.__all__) == EXPECTED_DICE_PUBLIC


def test_everything_in_dice_all_is_importable():
    for name in dice.__all__:
        assert hasattr(dice, name), f"{name} missing from dndwright.dice"
