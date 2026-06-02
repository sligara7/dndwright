"""D&D 5e dice expression engine — parse and roll, with a typed, frozen result surface.

Supports basic rolls (``1d20``, ``2d6+3``), multiple groups (``2d6+1d4+5``), keep/drop
highest/lowest (``4d6kh3``, ``4d6dl1``), rerolls (``2d6r1``, ``2d6ro2``), exploding dice
(``1d6!``), negative modifiers, and advantage/disadvantage on single d20 rolls.

**Determinism.** Each engine owns a private RNG. ``DiceEngine(seed=42)`` is reproducible
(stdlib Mersenne Twister) — ideal for tests, replay, and audit trails. The RNG is
*stateful*: each roll advances the stream, so a sequence of rolls from one seed is a fixed
sequence (that's the point), not a violation of purity.

**Production unpredictability.** For live play that must resist prediction, inject an
unpredictable generator instead of seeding::

    import secrets
    DiceEngine(rng=secrets.SystemRandom())   # OS entropy; not state-reconstructable

``secrets.SystemRandom`` is a ``random.Random`` subclass, so it drops in with no extra
dependency. (Mersenne Twister's state can be reconstructed from enough observed outputs;
``SystemRandom`` closes that for adversarial multiplayer settings.) The library never pulls
in NumPy — inject a PCG64-backed ``Random`` yourself if you need simulation-grade streams.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Protocol

# Hard safety bound on reroll/explode loops so a pathological group (e.g. a die
# whose every face is in the reroll set, or ``1d1!``) can never hang the engine.
_MAX_DIE_ITERATIONS = 100


# ---------------------------------------------------------------------------
# Parsed spec + roll results (immutable value types — sequence fields are tuples,
# so every result is genuinely frozen *and* hashable / usable as a dict key).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DiceGroup:
    """A single ``XdY`` group in an expression, plus its keep/drop/reroll/explode flags."""

    count: int
    sides: int
    keep_highest: int | None = None
    keep_lowest: int | None = None
    drop_highest: int | None = None
    drop_lowest: int | None = None
    reroll_on: tuple[int, ...] = ()
    reroll_once: bool = False
    exploding: bool = False

    def __str__(self) -> str:
        s = f"{self.count}d{self.sides}"
        if self.keep_highest:
            s += f"kh{self.keep_highest}"
        if self.keep_lowest:
            s += f"kl{self.keep_lowest}"
        if self.drop_highest:
            s += f"dh{self.drop_highest}"
        if self.drop_lowest:
            s += f"dl{self.drop_lowest}"
        if self.reroll_on:
            s += f"r{','.join(map(str, self.reroll_on))}"
        if self.exploding:
            s += "!"
        return s


@dataclass(frozen=True)
class ParsedExpression:
    """A dice expression broken into its groups and flat modifier."""

    dice_groups: tuple[DiceGroup, ...]
    modifier: int
    original: str


@dataclass(frozen=True)
class RollResult:
    """The outcome of rolling one :class:`DiceGroup`."""

    dice_group: DiceGroup
    all_rolls: tuple[int, ...]  # every die rolled, including dropped/exploded
    kept_rolls: tuple[int, ...]  # the dice that count toward the subtotal
    dropped_rolls: tuple[int, ...]  # dice removed by keep/drop
    rerolled_from: tuple[int, ...]  # original values that were rerolled away
    exploded_rolls: tuple[int, ...]  # extra dice from exploding
    subtotal: int


@dataclass(frozen=True)
class AdvantageData:
    """The two d20s and the choice made under advantage/disadvantage."""

    roll1: int
    roll2: int
    advantage: bool
    disadvantage: bool
    chosen: str  # "roll1" | "roll2"


@dataclass(frozen=True)
class ExpressionResult:
    """The full result of evaluating a dice expression (return type of :meth:`DiceEngine.roll`)."""

    expression: str
    dice_results: tuple[RollResult, ...]
    modifier: int
    total: int
    individual_rolls: tuple[int, ...]  # flat list of all kept rolls
    is_critical: bool = False  # natural 20 on a single d20
    is_fumble: bool = False  # natural 1 on a single d20
    natural_roll: int | None = None  # the d20 face, for single d20 rolls
    advantage_data: AdvantageData | None = None
    had_advantage: bool = False
    had_disadvantage: bool = False


# ---------------------------------------------------------------------------
# Higher-level roll results (attack / save / damage / death save / arrays / HD)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttackRoll:
    """An attack roll and, if a target AC was given, whether it hit."""

    roll: ExpressionResult
    target_ac: int | None = None
    is_hit: bool | None = None


@dataclass(frozen=True)
class SaveRoll:
    """A saving throw or ability/skill check and, if a DC was given, whether it succeeded."""

    roll: ExpressionResult
    dc: int | None = None
    is_success: bool | None = None


@dataclass(frozen=True)
class DamageRoll:
    """A damage roll; crits double the dice (not the flat modifier)."""

    roll: ExpressionResult
    is_critical_damage: bool
    original_expression: str


@dataclass(frozen=True)
class DeathSave:
    """A death saving throw outcome (5e: nat 20 = regain 1 HP, nat 1 = two failures)."""

    roll: int | None
    total: int
    outcome: str  # "success" | "failure" | "critical_success" | "critical_failure"
    is_critical_success: bool
    is_critical_failure: bool
    successes: int  # 0 or 1
    failures: int  # 0, 1, or 2


@dataclass(frozen=True)
class AbilityScoreRoll:
    """One generated ability score and the dice behind it."""

    total: int
    rolls: tuple[int, ...]


@dataclass(frozen=True)
class StatArray:
    """Six generated ability scores (sorted high→low) and their per-score detail."""

    method: str
    scores: tuple[int, ...]
    roll_details: tuple[AbilityScoreRoll, ...]
    total: int


@dataclass(frozen=True)
class HitDieRoll:
    """One hit-die roll and the HP it granted (minimum 1)."""

    roll: int
    con_mod: int
    hp_gained: int


@dataclass(frozen=True)
class HitDiceResult:
    """Total HP from rolling ``level`` hit dice."""

    hit_die: str
    con_modifier: int
    level: int
    rolls: tuple[HitDieRoll, ...]
    total_hp: int


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class DiceEngineProtocol(Protocol):
    """Structural interface for a dice engine (parse + roll)."""

    def parse_expression(self, expression: str) -> ParsedExpression: ...

    def roll(
        self, expression: str, advantage: bool = False, disadvantage: bool = False
    ) -> ExpressionResult: ...


class DiceEngine:
    """Parse and roll D&D 5e dice expressions.

    Args:
        seed: Seed for the default reproducible RNG. Ignored if ``rng`` is given.
        rng: An explicit ``random.Random``-compatible generator to use instead of the
            default seeded one — e.g. ``secrets.SystemRandom()`` for unpredictable
            production rolls. See the module docstring on determinism.
    """

    # Dice groups: XdY with optional kh/kl/dh/dl, reroll (r/ro), and explode (!).
    DICE_GROUP_PATTERN = re.compile(
        r"(\d+)?d(\d+)"  # Base dice: XdY
        r"(?:kh(\d+))?"  # Keep highest
        r"(?:kl(\d+))?"  # Keep lowest
        r"(?:dh(\d+))?"  # Drop highest
        r"(?:dl(\d+))?"  # Drop lowest
        r"(?:ro?(\d+(?:,\d+)*))?"  # Reroll (r or ro for once)
        r"(!)?",  # Exploding
        re.IGNORECASE,
    )

    # Standalone +/- modifiers (not part of dice notation).
    MODIFIER_PATTERN = re.compile(r"([+-]\d+)(?![d\d])")

    def __init__(self, seed: int | None = None, *, rng: random.Random | None = None):
        # A private generator per engine isolates streams between instances.
        self._rng: random.Random = rng if rng is not None else random.Random(seed)

    def _roll_die(self, sides: int) -> int:
        """Roll a single die. Subclass/override hook for deterministic tests."""
        return self._rng.randint(1, sides)

    def _roll_dice_group(self, group: DiceGroup) -> RollResult:
        """Roll a dice group with all its modifiers."""
        all_rolls: list[int] = []
        rerolled_from: list[int] = []
        exploded_rolls: list[int] = []

        # If every face of the die is in the reroll set, rerolling can never escape
        # it — skip rerolling for this group rather than loop forever.
        reroll_covers_all = bool(group.reroll_on) and set(range(1, group.sides + 1)).issubset(
            group.reroll_on
        )

        for _ in range(group.count):
            roll = self._roll_die(group.sides)

            # Handle rerolls (capped; no-op when the reroll set covers every face)
            if group.reroll_on and roll in group.reroll_on and not reroll_covers_all:
                rerolled_from.append(roll)
                if group.reroll_once:
                    roll = self._roll_die(group.sides)
                else:
                    iterations = 0
                    while roll in group.reroll_on and iterations < _MAX_DIE_ITERATIONS:
                        rerolled_from.append(roll)
                        roll = self._roll_die(group.sides)
                        iterations += 1

            all_rolls.append(roll)

            # Handle exploding dice. A 1-sided die always shows its max, so it would
            # explode forever — guard on sides > 1 and cap the chain either way.
            if group.exploding and group.sides > 1 and roll == group.sides:
                iterations = 0
                while roll == group.sides and iterations < _MAX_DIE_ITERATIONS:
                    roll = self._roll_die(group.sides)
                    exploded_rolls.append(roll)
                    all_rolls.append(roll)
                    iterations += 1

        sorted_desc = sorted(all_rolls, reverse=True)
        sorted_asc = sorted(all_rolls)
        kept_rolls = list(all_rolls)
        dropped_rolls: list[int] = []

        if group.keep_highest and group.keep_highest < len(all_rolls):
            kept_rolls = sorted_desc[: group.keep_highest]
            dropped_rolls = sorted_desc[group.keep_highest :]
        elif group.keep_lowest and group.keep_lowest < len(all_rolls):
            kept_rolls = sorted_asc[: group.keep_lowest]
            dropped_rolls = sorted_asc[group.keep_lowest :]
        elif group.drop_highest and group.drop_highest < len(all_rolls):
            dropped_rolls = sorted_desc[: group.drop_highest]
            kept_rolls = sorted_desc[group.drop_highest :]
        elif group.drop_lowest and group.drop_lowest < len(all_rolls):
            dropped_rolls = sorted_asc[: group.drop_lowest]
            kept_rolls = sorted_asc[group.drop_lowest :]

        return RollResult(
            dice_group=group,
            all_rolls=tuple(all_rolls),
            kept_rolls=tuple(kept_rolls),
            dropped_rolls=tuple(dropped_rolls),
            rerolled_from=tuple(rerolled_from),
            exploded_rolls=tuple(exploded_rolls),
            subtotal=sum(kept_rolls),
        )

    def parse_expression(self, expression: str) -> ParsedExpression:
        """Parse a dice expression into groups + a flat modifier."""
        expr = expression.lower().replace(" ", "")
        dice_groups: list[DiceGroup] = []
        modifier = 0

        for match in self.DICE_GROUP_PATTERN.finditer(expr):
            count = int(match.group(1)) if match.group(1) else 1
            sides = int(match.group(2))

            reroll_on: tuple[int, ...] = ()
            reroll_once = False
            if match.group(7):
                reroll_on = tuple(int(x) for x in match.group(7).split(","))
                # "ro" = reroll once; "r" = keep rerolling. Detect from THIS group's
                # matched text, not the whole expression, so a later 'ro' group can't
                # flip an earlier 'r' group to reroll-once.
                reroll_once = re.search(r"ro\d", match.group(0)) is not None

            dice_groups.append(
                DiceGroup(
                    count=count,
                    sides=sides,
                    keep_highest=int(match.group(3)) if match.group(3) else None,
                    keep_lowest=int(match.group(4)) if match.group(4) else None,
                    drop_highest=int(match.group(5)) if match.group(5) else None,
                    drop_lowest=int(match.group(6)) if match.group(6) else None,
                    reroll_on=reroll_on,
                    reroll_once=reroll_once,
                    exploding=match.group(8) == "!",
                )
            )

        # Standalone modifiers: strip dice parts first, then sum +/- numbers.
        cleaned = self.DICE_GROUP_PATTERN.sub("", expr)
        for match in self.MODIFIER_PATTERN.finditer(cleaned):
            modifier += int(match.group(1))

        return ParsedExpression(
            dice_groups=tuple(dice_groups), modifier=modifier, original=expression
        )

    def roll(
        self, expression: str, advantage: bool = False, disadvantage: bool = False
    ) -> ExpressionResult:
        """Evaluate ``expression``; advantage/disadvantage apply to a single d20 only."""
        parsed = self.parse_expression(expression)
        dice_results: list[RollResult] = []
        all_kept_rolls: list[int] = []
        advantage_data: AdvantageData | None = None

        is_d20_single = (
            len(parsed.dice_groups) == 1
            and parsed.dice_groups[0].sides == 20
            and parsed.dice_groups[0].count == 1
        )

        for group in parsed.dice_groups:
            if (
                is_d20_single
                and group.sides == 20
                and group.count == 1
                and (advantage or disadvantage)
            ):
                result1 = self._roll_dice_group(group)
                result2 = self._roll_dice_group(group)

                if advantage:
                    pick1 = result1.subtotal >= result2.subtotal
                else:
                    pick1 = result1.subtotal <= result2.subtotal
                result = result1 if pick1 else result2

                advantage_data = AdvantageData(
                    roll1=result1.kept_rolls[0] if result1.kept_rolls else 0,
                    roll2=result2.kept_rolls[0] if result2.kept_rolls else 0,
                    advantage=advantage,
                    disadvantage=disadvantage,
                    chosen="roll1" if pick1 else "roll2",
                )
                dice_results.append(result)
                all_kept_rolls.extend(result.kept_rolls)
            else:
                result = self._roll_dice_group(group)
                dice_results.append(result)
                all_kept_rolls.extend(result.kept_rolls)

        total = sum(r.subtotal for r in dice_results) + parsed.modifier

        is_critical = False
        is_fumble = False
        natural_roll = None
        if is_d20_single and dice_results:
            natural_roll = dice_results[0].kept_rolls[0] if dice_results[0].kept_rolls else None
            if natural_roll == 20:
                is_critical = True
            elif natural_roll == 1:
                is_fumble = True

        return ExpressionResult(
            expression=expression,
            dice_results=tuple(dice_results),
            modifier=parsed.modifier,
            total=total,
            individual_rolls=tuple(all_kept_rolls),
            is_critical=is_critical,
            is_fumble=is_fumble,
            natural_roll=natural_roll,
            advantage_data=advantage_data,
            had_advantage=advantage,
            had_disadvantage=disadvantage,
        )

    def roll_attack(
        self,
        modifier: int = 0,
        advantage: bool = False,
        disadvantage: bool = False,
        target_ac: int | None = None,
    ) -> AttackRoll:
        """Roll an attack (1d20 + modifier); resolve the hit if ``target_ac`` is given."""
        result = self.roll(f"1d20+{modifier}", advantage, disadvantage)
        is_hit: bool | None = None
        if target_ac is not None:
            if result.is_critical:
                is_hit = True
            elif result.is_fumble:
                is_hit = False
            else:
                is_hit = result.total >= target_ac
        return AttackRoll(roll=result, target_ac=target_ac, is_hit=is_hit)

    def roll_save(
        self,
        modifier: int = 0,
        dc: int | None = None,
        advantage: bool = False,
        disadvantage: bool = False,
    ) -> SaveRoll:
        """Roll a saving throw (1d20 + modifier); resolve success if ``dc`` is given."""
        result = self.roll(f"1d20+{modifier}", advantage, disadvantage)
        is_success = result.total >= dc if dc is not None else None
        return SaveRoll(roll=result, dc=dc, is_success=is_success)

    def roll_check(
        self,
        modifier: int = 0,
        dc: int | None = None,
        advantage: bool = False,
        disadvantage: bool = False,
    ) -> SaveRoll:
        """Roll an ability/skill check — mechanically identical to a saving throw."""
        return self.roll_save(modifier, dc, advantage, disadvantage)

    def roll_damage(self, expression: str, is_critical: bool = False) -> DamageRoll:
        """Roll damage; on a crit, double the dice counts (the flat modifier is unchanged)."""
        if is_critical:
            parsed = self.parse_expression(expression)
            doubled_groups = [f"{g.count * 2}d{g.sides}" for g in parsed.dice_groups]
            if doubled_groups:
                doubled_expr = "+".join(doubled_groups)
                if parsed.modifier:
                    doubled_expr += (
                        f"+{parsed.modifier}" if parsed.modifier > 0 else str(parsed.modifier)
                    )
            else:
                doubled_expr = expression
            result = self.roll(doubled_expr)
            return DamageRoll(roll=result, is_critical_damage=True, original_expression=expression)

        result = self.roll(expression)
        return DamageRoll(roll=result, is_critical_damage=False, original_expression=expression)

    def roll_initiative(self, modifier: int = 0) -> ExpressionResult:
        """Roll initiative (1d20 + modifier)."""
        return self.roll(f"1d20+{modifier}")

    def roll_stat_array(self, method: str = "4d6kh3") -> StatArray:
        """Roll six ability scores via ``method`` (e.g. ``4d6kh3``, ``3d6``, ``2d6+6``)."""
        details: list[AbilityScoreRoll] = []
        for _ in range(6):
            result = self.roll(method)
            details.append(AbilityScoreRoll(total=result.total, rolls=result.individual_rolls))
        scores = sorted((d.total for d in details), reverse=True)
        return StatArray(
            method=method,
            scores=tuple(scores),
            roll_details=tuple(details),
            total=sum(scores),
        )

    def roll_hit_dice(
        self, hit_die: str, con_modifier: int = 0, level: int = 1
    ) -> HitDiceResult:
        """Roll ``level`` hit dice for HP (minimum 1 HP per level)."""
        sides = int(hit_die.replace("d", ""))
        rolls: list[HitDieRoll] = []
        for _ in range(level):
            result = self.roll(f"1d{sides}")
            hp = max(1, result.total + con_modifier)
            rolls.append(HitDieRoll(roll=result.total, con_mod=con_modifier, hp_gained=hp))
        return HitDiceResult(
            hit_die=hit_die,
            con_modifier=con_modifier,
            level=level,
            rolls=tuple(rolls),
            total_hp=sum(r.hp_gained for r in rolls),
        )

    def roll_death_save(self) -> DeathSave:
        """Roll a death saving throw (nat 20 → regain 1 HP, nat 1 → two failures)."""
        result = self.roll("1d20")
        natural = result.natural_roll

        outcome = "failure"
        if natural == 20:
            outcome = "critical_success"
        elif natural == 1:
            outcome = "critical_failure"
        elif natural is not None and natural >= 10:
            outcome = "success"

        return DeathSave(
            roll=natural,
            total=result.total,
            outcome=outcome,
            is_critical_success=natural == 20,
            is_critical_failure=natural == 1,
            successes=1 if outcome in ("success", "critical_success") else 0,
            failures=2 if outcome == "critical_failure" else (1 if outcome == "failure" else 0),
        )
