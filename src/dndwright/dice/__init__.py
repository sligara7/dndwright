"""D&D 5e dice expression engine — parse and roll, with a typed, frozen result surface.

    from dndwright.dice import DiceEngine

    eng = DiceEngine(seed=42)                 # reproducible (stdlib RNG)
    eng.roll("2d6+3")                         # -> ExpressionResult
    eng.roll("1d20", advantage=True)          # advantage on a single d20
    eng.roll_attack(modifier=5, target_ac=15) # -> AttackRoll (.is_hit)
    eng.roll_damage("2d8", is_critical=True)  # crit doubles the dice
    eng.roll_stat_array("4d6kh3")             # -> StatArray (six scores)

For unpredictable production rolls, inject ``secrets.SystemRandom()`` (a ``random.Random``
subclass) via ``DiceEngine(rng=...)``. See :mod:`dndwright.dice.engine`.
"""

from .engine import (
    AbilityScoreRoll,
    AdvantageData,
    AttackRoll,
    DamageRoll,
    DeathSave,
    DiceEngine,
    DiceEngineProtocol,
    DiceGroup,
    ExpressionResult,
    HitDiceResult,
    HitDieRoll,
    ParsedExpression,
    RollResult,
    SaveRoll,
    StatArray,
)

__all__ = [
    "DiceEngine",
    "DiceEngineProtocol",
    # parsed spec + core roll results
    "DiceGroup",
    "ParsedExpression",
    "RollResult",
    "ExpressionResult",
    "AdvantageData",
    # higher-level roll results
    "AttackRoll",
    "SaveRoll",
    "DamageRoll",
    "DeathSave",
    "StatArray",
    "AbilityScoreRoll",
    "HitDiceResult",
    "HitDieRoll",
]
