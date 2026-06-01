"""Theme-specific scaling overrides for the computation graph.

Allows themes (sci_fi, modern_warfare, steampunk, cosmic_horror, etc.) to override
input node values and lookup table entries so the same computation graph produces
mechanically appropriate results for any setting.

Example: in a modern_warfare theme, "plate" armor becomes "tactical body armor"
with the same mechanical AC 18, but weapon ranges and mount speeds change.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ThemeScalingLayer(BaseModel):
    """Theme-specific overrides for computation graph input values."""

    theme: str = Field(..., description="Theme identifier (e.g., 'modern_warfare', 'sci_fi')")
    description: str = Field("", description="Human-readable description of the theme")
    input_overrides: dict[str, Any] = Field(
        default_factory=dict,
        description="Computation node ID -> override value. Applied before evaluation.",
    )
    lookup_overrides: dict[str, dict] = Field(
        default_factory=dict,
        description="Lookup table name -> {key: new_value}. Merged into ruleset tables.",
    )
    flavor_renames: dict[str, str] = Field(
        default_factory=dict,
        description="Original term -> themed term for display (e.g., 'plate' -> 'power armor').",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="DM-facing notes about how the theme changes mechanics.",
    )


# =============================================================================
# Predefined scaling profiles
# =============================================================================

PREDEFINED_THEME_SCALING: dict[str, ThemeScalingLayer] = {
    "traditional_dnd": ThemeScalingLayer(
        theme="traditional_dnd",
        description="Standard D&D 5e rules. No mechanical overrides.",
        input_overrides={},
        lookup_overrides={},
        flavor_renames={},
        notes=["Default ruleset, no scaling applied."],
    ),
    "modern_warfare": ThemeScalingLayer(
        theme="modern_warfare",
        description="Modern military setting. Firearms, ballistic vests, vehicles.",
        input_overrides={},
        lookup_overrides={
            "armor_base_ac": {
                "leather": 11,
                "studded_leather": 12,
                "chain_shirt": 14,
                "breastplate": 15,
                "half_plate": 16,
                "plate": 18,
            },
            "weapon_ranges": {
                "shortbow": 300,
                "longbow": 600,
                "light_crossbow": 400,
                "heavy_crossbow": 800,
                "hand_crossbow": 200,
            },
        },
        flavor_renames={
            "plate": "tactical body armor",
            "chain_mail": "flak jacket",
            "breastplate": "kevlar vest",
            "leather": "light ballistic vest",
            "studded_leather": "reinforced ballistic vest",
            "shield": "riot shield",
            "longbow": "assault rifle",
            "shortbow": "submachine gun",
            "heavy_crossbow": "sniper rifle",
            "light_crossbow": "carbine",
            "hand_crossbow": "pistol",
            "longsword": "combat knife",
            "greatsword": "machete",
            "mount_warhorse": "armored vehicle",
            "mount_riding_horse": "jeep",
        },
        notes=[
            "Firearms use crossbow/bow mechanics with extended ranges.",
            "Armor retains AC values but is re-flavored as modern equipment.",
            "Mounts become vehicles with equivalent movement.",
            "Spellcasting can be re-flavored as tech gadgets or psionics.",
        ],
    ),
    "sci_fi": ThemeScalingLayer(
        theme="sci_fi",
        description="Science fiction setting. Energy weapons, force shields, starships.",
        input_overrides={},
        lookup_overrides={
            "armor_base_ac": {
                "leather": 12,
                "studded_leather": 13,
                "chain_shirt": 14,
                "breastplate": 15,
                "half_plate": 16,
                "plate": 19,
            },
        },
        flavor_renames={
            "plate": "power armor",
            "chain_mail": "medium exosuit",
            "breastplate": "light exosuit",
            "leather": "enviro-suit",
            "studded_leather": "reinforced enviro-suit",
            "shield": "energy shield generator",
            "longbow": "plasma rifle",
            "shortbow": "laser carbine",
            "heavy_crossbow": "rail gun",
            "light_crossbow": "blaster pistol",
            "longsword": "energy blade",
            "greatsword": "plasma sword",
            "mount_warhorse": "hoverbike",
            "mount_riding_horse": "speeder",
        },
        notes=[
            "Energy weapons use existing damage types (radiant for lasers, force for plasma).",
            "Shields are energy-based but use the same +2 AC bonus.",
            "Heavy armor is powered exosuits; no STR requirement change.",
            "Starship combat uses a separate encounter framework.",
        ],
    ),
    "steampunk": ThemeScalingLayer(
        theme="steampunk",
        description="Victorian-era clockwork and steam-powered technology.",
        input_overrides={},
        lookup_overrides={
            "armor_base_ac": {
                "chain_shirt": 14,
                "breastplate": 15,
                "plate": 19,
            },
        },
        flavor_renames={
            "plate": "clockwork full-plate",
            "chain_mail": "riveted iron chassis",
            "breastplate": "brass cuirass",
            "leather": "oiled duster",
            "studded_leather": "reinforced duster",
            "shield": "pneumatic buckler",
            "heavy_crossbow": "steam cannon",
            "light_crossbow": "clockwork repeater",
            "hand_crossbow": "derringer",
            "longbow": "aether rifle",
            "shortbow": "spring-bolt pistol",
            "mount_warhorse": "steam walker",
            "mount_riding_horse": "velocipede",
        },
        notes=[
            "Clockwork mechanisms replace magic for non-spellcasters.",
            "Steam-powered armor may overheat (DM discretion for flavor).",
            "Alchemy replaces standard potion mechanics.",
        ],
    ),
    "cosmic_horror": ThemeScalingLayer(
        theme="cosmic_horror",
        description="Lovecraftian horror. Sanity mechanics, reality distortion, eldritch entities.",
        input_overrides={},
        lookup_overrides={},
        flavor_renames={
            "plate": "warded armor",
            "shield": "elder sign ward",
            "longbow": "bolt-action rifle",
            "shortbow": "revolver",
            "heavy_crossbow": "elephant gun",
            "greatsword": "ritual blade",
        },
        notes=[
            "Optional sanity mechanic: WIS saves against cosmic horror (DC 12-20).",
            "Failure costs 1d4 to 1d10 'Insight' (tracked separately from HP).",
            "At 0 Insight, character gains a short-term madness.",
            "Eldritch spells may require Insight instead of spell slots.",
            "Reality distortion can impose disadvantage on perception checks.",
        ],
    ),
}


def get_theme_scaling(theme: str) -> ThemeScalingLayer | None:
    """Get a predefined theme scaling layer, or None if not predefined."""
    return PREDEFINED_THEME_SCALING.get(theme)


def list_predefined_themes() -> list[dict]:
    """Return summaries of all predefined theme scaling profiles."""
    return [
        {
            "theme": layer.theme,
            "description": layer.description,
            "override_count": len(layer.input_overrides) + len(layer.lookup_overrides),
            "rename_count": len(layer.flavor_renames),
        }
        for layer in PREDEFINED_THEME_SCALING.values()
    ]
