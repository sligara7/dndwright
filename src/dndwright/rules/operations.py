"""Closed set of formula operations for the computation graph DSL.

Every operation is a pure function: (args, lookup_tables) -> value.
No eval(), no lambdas, no side effects. JSON-serializable operation names
map to Python functions here (and will map to TypeScript functions in Phase 3).

Operations fall into three categories:
1. Arithmetic: add, sub, mul, floor_div, max_val, min_val
2. D&D compound ops: ability_mod, prof_bonus, prof_add, hp_at_level, ac_with_armor
3. Logic: if_then_else, eq, gt, gte, in_set, not_op
4. Utility: lookup, format_mod, coalesce, const
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------


def op_add(args: list[Any], _tables: dict) -> int | float:
    """Sum all arguments."""
    return sum(args)


def op_sub(args: list[Any], _tables: dict) -> int | float:
    """Subtract: args[0] - args[1] - args[2] - ..."""
    result = args[0]
    for a in args[1:]:
        result -= a
    return result


def op_mul(args: list[Any], _tables: dict) -> int | float:
    """Multiply all arguments."""
    result = 1
    for a in args:
        result *= a
    return result


def op_union(args: list[Any], _tables: dict) -> tuple:
    """Union of all args into a sorted, de-duplicated tuple.

    Each arg may be a set/list/tuple (its members are unioned in) or a scalar (added
    as one member). ``None`` args are skipped. Used for composing set-valued channels
    (e.g. damage resistances contributed by several items/traits).
    """
    out: set[Any] = set()
    for a in args:
        if isinstance(a, (set, frozenset, list, tuple)):
            out |= set(a)
        elif a is not None:
            out.add(a)
    return tuple(sorted(out))


def op_floor_div(args: list[Any], _tables: dict) -> int:
    """Integer division: args[0] // args[1]."""
    return int(args[0]) // int(args[1])


def op_max_val(args: list[Any], _tables: dict) -> int | float:
    """Maximum of all arguments."""
    return max(args)


def op_min_val(args: list[Any], _tables: dict) -> int | float:
    """Minimum of all arguments."""
    return min(args)


# ---------------------------------------------------------------------------
# D&D compound operations
# ---------------------------------------------------------------------------


def op_ability_mod(args: list[Any], _tables: dict) -> int:
    """(score - 10) // 2. Standard D&D ability modifier."""
    score = int(args[0])
    return (score - 10) // 2


def op_prof_bonus(args: list[Any], _tables: dict) -> int:
    """2 + ((level - 1) // 4). Proficiency bonus from character level."""
    level = int(args[0])
    return 2 + ((level - 1) // 4)


def op_prof_add(args: list[Any], _tables: dict) -> int:
    """ability_mod + (prof_bonus if proficient else 0).

    args: [ability_mod, prof_bonus, is_proficient]
    """
    ability_mod = int(args[0])
    prof_bonus = int(args[1])
    is_proficient = bool(args[2])
    return ability_mod + (prof_bonus if is_proficient else 0)


def op_skill_bonus(args: list[Any], _tables: dict) -> int:
    """ability_mod + (prof_bonus * 2 if expertise, prof_bonus if proficient, else 0).

    args: [ability_mod, prof_bonus, is_proficient, has_expertise]
    """
    ability_mod = int(args[0])
    prof_bonus = int(args[1])
    is_proficient = bool(args[2])
    has_expertise = bool(args[3])
    if has_expertise:
        return ability_mod + prof_bonus * 2
    elif is_proficient:
        return ability_mod + prof_bonus
    return ability_mod


def op_hp_at_level(args: list[Any], _tables: dict) -> int:
    """HP = hit_die_max + con_mod + (level-1) * (avg_roll + con_mod), min level.

    args: [hit_die_size, con_mod, level]
    hit_die_size: integer (8 for d8, 10 for d10, etc.)
    """
    hit_die_size = int(args[0])
    con_mod = int(args[1])
    level = int(args[2])
    avg_roll = (hit_die_size // 2) + 1
    hp = hit_die_size + con_mod  # Level 1: max die + CON
    hp += (level - 1) * (avg_roll + con_mod)  # Levels 2+: average
    return max(hp, level)  # Minimum 1 HP per level


def op_multiclass_hp(args: list[Any], _tables: dict) -> int:
    """HP for multiclass character.

    args: [class_levels_json, class_hit_dice_json, con_mod]
    class_levels_json: dict like {"bard": 5, "warlock": 3}
    class_hit_dice_json: dict like {"bard": 8, "warlock": 8}
    con_mod: constitution modifier

    First level of primary class (first in order) gets max die.
    All subsequent levels get average.
    """
    class_levels = args[0]  # dict
    class_hit_dice = args[1]  # dict
    con_mod = int(args[2])

    if not class_levels or not class_hit_dice:
        return 1

    total_hp = 0
    first_class = True

    for class_name, class_level in class_levels.items():
        hit_die_size = class_hit_dice.get(class_name, 8)
        avg_roll = (hit_die_size // 2) + 1

        if first_class:
            # First class, level 1: max die + CON
            total_hp += hit_die_size + con_mod
            # Remaining levels in first class: average
            total_hp += (class_level - 1) * (avg_roll + con_mod)
            first_class = False
        else:
            # All levels in secondary classes: average
            total_hp += class_level * (avg_roll + con_mod)

    character_level = sum(class_levels.values())
    return max(total_hp, character_level)


def op_ac_with_armor(args: list[Any], tables: dict) -> int:
    """Compute AC from armor type + dex mod.

    args: [armor_type, dex_mod, magic_bonus, has_shield]
    Uses lookup tables: armor_base_ac, armor_max_dex
    """
    armor_type = str(args[0]).lower().replace(" ", "_") if args[0] else "none"
    dex_mod = int(args[1])
    magic_bonus = int(args[2]) if len(args) > 2 else 0
    has_shield = bool(args[3]) if len(args) > 3 else False

    armor_base_ac = tables.get("armor_base_ac", {})
    armor_max_dex = tables.get("armor_max_dex", {})

    base_ac = armor_base_ac.get(armor_type, 10)
    max_dex = armor_max_dex.get(armor_type)

    if max_dex == 0:  # Heavy armor
        ac = base_ac
    elif max_dex is not None:  # Medium armor
        ac = base_ac + min(dex_mod, max_dex)
    else:  # Light armor or unarmored
        ac = base_ac + dex_mod

    ac += magic_bonus
    if has_shield:
        ac += 2

    return ac


def op_spell_slots(args: list[Any], tables: dict) -> dict[str, int]:
    """Look up spell slots from progression table.

    args: [spellcasting_type, level, class_name]
    Uses lookup tables: spell_slots_full, spell_slots_half, spell_slots_warlock
    """
    spellcasting_type = str(args[0]) if args[0] else "none"
    level = int(args[1])
    class_name = str(args[2]).lower() if len(args) > 2 and args[2] else ""

    if class_name == "warlock":
        table = tables.get("spell_slots_warlock", {})
        return table.get(level, {})
    elif spellcasting_type == "half_caster":
        table = tables.get("spell_slots_half", {})
        return table.get(level, {})
    elif spellcasting_type in ("full_caster", "prepared_caster"):
        table = tables.get("spell_slots_full", {})
        return table.get(level, {})
    return {}


def op_multiclass_spell_slots(args: list[Any], tables: dict) -> dict[str, int]:
    """Compute spell slots for multiclass characters.

    Per D&D 5e multiclass rules: sum full caster levels + floor(half caster levels / 2),
    look up on the full caster table. Warlock pact slots are separate.

    args: [class_levels_json, class_spellcasting_types_json]
    class_levels_json: {"wizard": 5, "fighter": 3}
    class_spellcasting_types_json: {"wizard": "full_caster", "fighter": "none"}
    """
    class_levels = args[0]  # dict
    class_types = args[1]  # dict

    if not class_levels or not class_types:
        return {}

    # Calculate effective caster level
    effective_caster_level = 0
    warlock_level = 0
    has_warlock = False

    for class_name, level in class_levels.items():
        casting_type = class_types.get(class_name, "none")
        if class_name.lower() == "warlock":
            warlock_level = level
            has_warlock = True
        elif casting_type in ("full_caster", "prepared_caster"):
            effective_caster_level += level
        elif casting_type == "half_caster":
            effective_caster_level += level // 2

    result = {}

    # Standard spell slots from effective caster level
    if effective_caster_level > 0:
        full_table = tables.get("spell_slots_full", {})
        result = dict(full_table.get(effective_caster_level, {}))

    # Warlock pact slots are separate (added alongside)
    if has_warlock and warlock_level > 0:
        warlock_table = tables.get("spell_slots_warlock", {})
        pact_info = warlock_table.get(warlock_level, {})
        if pact_info:
            result["pact"] = pact_info.get("pact", 0)
            result["pact_level"] = pact_info.get("pact_level", 0)

    return result


# ---------------------------------------------------------------------------
# Logic
# ---------------------------------------------------------------------------


def op_if_then_else(args: list[Any], _tables: dict) -> Any:
    """args: [condition, true_value, false_value]."""
    return args[1] if args[0] else args[2]


def op_eq(args: list[Any], _tables: dict) -> bool:
    """args[0] == args[1]."""
    return args[0] == args[1]


def op_gt(args: list[Any], _tables: dict) -> bool:
    """args[0] > args[1]."""
    return args[0] > args[1]


def op_gte(args: list[Any], _tables: dict) -> bool:
    """args[0] >= args[1]."""
    return args[0] >= args[1]


def op_in_set(args: list[Any], _tables: dict) -> bool:
    """args[0] in args[1] (where args[1] is a list/set)."""
    return args[0] in args[1]


def op_not(args: list[Any], _tables: dict) -> bool:
    """not args[0]."""
    return not args[0]


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def op_lookup(args: list[Any], tables: dict) -> Any:
    """Look up a value from a named table.

    args: [table_name, key] or [table_name, key, default]
    """
    table_name = str(args[0])
    key = args[1]
    default = args[2] if len(args) > 2 else None
    table = tables.get(table_name, {})
    # Try direct lookup, then string version of key
    result = table.get(key)
    if result is None:
        result = table.get(str(key))
    if result is None:
        result = default
    return result


def op_format_mod(args: list[Any], _tables: dict) -> str:
    """Format an integer as a modifier string: +X or -X."""
    val = int(args[0])
    return f"+{val}" if val >= 0 else str(val)


def op_coalesce(args: list[Any], _tables: dict) -> Any:
    """Return first non-None argument."""
    for a in args:
        if a is not None:
            return a
    return None


def op_const(args: list[Any], _tables: dict) -> Any:
    """Return a constant value. args: [value]."""
    return args[0]


def op_passive_score(args: list[Any], _tables: dict) -> int:
    """10 + skill_bonus. Standard passive score formula."""
    return 10 + int(args[0])


def op_spell_mod_resolve(args: list[Any], _tables: dict) -> int:
    """Resolve spellcasting modifier from ability name + all 6 modifiers.

    args: [spell_ability_name, str_mod, dex_mod, con_mod, int_mod, wis_mod, cha_mod]
    spell_ability_name is e.g. "intelligence", "wisdom", "charisma"
    """
    ability_name = str(args[0]).lower() if args[0] else "charisma"
    ability_order = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
    try:
        idx = ability_order.index(ability_name)
    except ValueError:
        idx = 5  # default to charisma
    return int(args[1 + idx])


def op_hit_dice_str(args: list[Any], _tables: dict) -> str:
    """Format hit dice as string: '5d8' or '5d8 + 3d10' for multiclass.

    args: [class_levels_json, class_hit_dice_json]
    """
    class_levels = args[0]  # dict
    class_hit_dice = args[1]  # dict

    if not class_levels:
        return "1d8"

    parts = []
    for class_name, class_level in class_levels.items():
        die_size = class_hit_dice.get(class_name, 8)
        parts.append(f"{class_level}d{die_size}")

    return " + ".join(parts)


# ---------------------------------------------------------------------------
# Operation registry
# ---------------------------------------------------------------------------

Operation = Callable[[list[Any], dict], Any]

OPERATIONS: dict[str, Operation] = {
    # Arithmetic
    "add": op_add,
    "sub": op_sub,
    "mul": op_mul,
    "union": op_union,
    "floor_div": op_floor_div,
    "max_val": op_max_val,
    "min_val": op_min_val,
    # D&D compound
    "ability_mod": op_ability_mod,
    "prof_bonus": op_prof_bonus,
    "prof_add": op_prof_add,
    "skill_bonus": op_skill_bonus,
    "hp_at_level": op_hp_at_level,
    "multiclass_hp": op_multiclass_hp,
    "ac_with_armor": op_ac_with_armor,
    "spell_slots": op_spell_slots,
    "multiclass_spell_slots": op_multiclass_spell_slots,
    "hit_dice_str": op_hit_dice_str,
    # Logic
    "if_then_else": op_if_then_else,
    "eq": op_eq,
    "gt": op_gt,
    "gte": op_gte,
    "in_set": op_in_set,
    "not": op_not,
    # Utility
    "lookup": op_lookup,
    "format_mod": op_format_mod,
    "coalesce": op_coalesce,
    "const": op_const,
    "passive_score": op_passive_score,
    "spell_mod_resolve": op_spell_mod_resolve,
}

# Names present at import time — the rules a built-in op may never be silently replaced.
_BUILTIN_OPERATIONS = frozenset(OPERATIONS)


def register_operation(name: str, fn: Operation, *, overwrite: bool = False) -> None:
    """Register a custom operation for use in formulas (the DSL extension point).

    ``fn`` must be a pure function ``(args: list, tables: dict) -> value`` — the same
    shape as the built-ins. Once registered, ``name`` may be used as a ``FormulaSpec.op``
    and is recognised everywhere the registry is consulted (``evaluate``,
    ``validate_ruleset``, ``known_operations``). Lets custom rulesets extend the DSL
    without forking the package.

    Args:
        name: The op name a formula will reference. Must be non-empty.
        fn: The operation callable.
        overwrite: Allow replacing an already-registered name. Built-in operation names
            can never be overwritten (raises regardless of this flag).

    Raises:
        ValueError: empty name, replacing a built-in, or replacing an existing custom
            op without ``overwrite=True``.
        TypeError: ``fn`` is not callable.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("operation name must be a non-empty string")
    if not callable(fn):
        raise TypeError("operation must be callable")
    if name in _BUILTIN_OPERATIONS:
        raise ValueError(f"cannot overwrite built-in operation {name!r}")
    if name in OPERATIONS and not overwrite:
        raise ValueError(
            f"operation {name!r} already registered; pass overwrite=True to replace"
        )
    OPERATIONS[name] = fn


def describe_operations() -> dict[str, str]:
    """Map each operation name to the first line of its docstring.

    A public, read-only view of the operation registry's metadata — for building an
    operations reference / UI without importing the mutable ``OPERATIONS`` dict.
    """
    return {
        name: (fn.__doc__ or "").strip().split("\n")[0]
        for name, fn in sorted(OPERATIONS.items())
    }
