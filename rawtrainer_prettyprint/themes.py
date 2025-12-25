from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

DescriptionStyle = Literal["plain", "highlight"]

@dataclass(frozen=True)
class Palette:
    bg: str
    bg_alt: str
    plain_fg: str | None
    dim: str

    key_name: str
    value_name: str
    value_exercise_name: str
    value_enum: str
    value_number: str
    bool_true: str
    bool_false: str | None
    null: str | None = None
    value_description: str | None = None
    value_cadence: str | None = None


@dataclass(frozen=True)
class Rules:
    name_value_keys: tuple[str, ...] = ("name",)
    enum_value_keys: tuple[str, ...] = ("mode",)
    description_keys: tuple[str, ...] = ("description",)
    
    cadence_value_keys: tuple[str, ...] = ("cadence",)

    exercise_list_keys: tuple[str, ...] = ("exercises",)
    exercise_name_keys: tuple[str, ...] = ("name",)

    description_value: DescriptionStyle = "plain"
    description_block: DescriptionStyle = "plain"

    use_terminal_fg: bool = True
    cadence_value_keys: tuple[str, ...] = ("cadence",)


@dataclass(frozen=True)
class ThemeSpec:
    name: str
    palette: Palette
    rules: Rules = Rules()


def _lower_set(xs: Iterable[str]) -> set[str]:
    return {x.strip().lower() for x in xs}


def validate_theme(t: ThemeSpec) -> None:

    p = t.palette
    r = t.rules

    required_strings = [
        ("bg", p.bg),
        ("bg_alt", p.bg_alt),
        ("dim", p.dim),
        ("key_name", p.key_name),
        ("value_name", p.value_name),
        ("value_exercise_name", p.value_exercise_name),
        ("value_enum", p.value_enum),
        ("value_number", p.value_number),
        ("bool_true", p.bool_true),
    ]
    missing = [name for name, val in required_strings if not isinstance(val, str) or not val.strip()]
    if missing:
        raise ValueError(f"[{t.name}] missing required palette fields: {', '.join(missing)}")

    if not r.use_terminal_fg:
        if not (p.plain_fg and isinstance(p.plain_fg, str) and p.plain_fg.strip()):
            raise ValueError(f"[{t.name}] rules.use_terminal_fg=False requires palette.plain_fg")

    if r.description_value == "highlight" and not (p.value_description and p.value_description.strip()):
        raise ValueError(f"[{t.name}] rules.description_value='highlight' requires palette.value_description")

    name_keys = _lower_set(r.name_value_keys)
    enum_keys = _lower_set(r.enum_value_keys)
    desc_keys = _lower_set(r.description_keys)

    overlaps = []
    if name_keys & enum_keys:
        overlaps.append(f"name_value_keys ∩ enum_value_keys = {sorted(name_keys & enum_keys)}")
    if name_keys & desc_keys:
        overlaps.append(f"name_value_keys ∩ description_keys = {sorted(name_keys & desc_keys)}")
    if enum_keys & desc_keys:
        overlaps.append(f"enum_value_keys ∩ description_keys = {sorted(enum_keys & desc_keys)}")
    if overlaps:
        raise ValueError(f"[{t.name}] overlapping rule key sets: " + " | ".join(overlaps))
    
# =============================================================================
# Themes
# =============================================================================

THEMES: dict[str, ThemeSpec] = {
    "raw_yamltools_blue": ThemeSpec(
        name="raw_yamltools_blue",
        palette=Palette(
            bg="#252821",
            bg_alt="#3D4133",
            plain_fg="#dcdbdb",        # only used if use_terminal_fg=False
            dim="#A0A29D",
            key_name="#C62CFB",
            value_name="#C62CFB",      # (tu set actual; no lo toco)
            value_exercise_name="#2cfb5f",
            value_enum="#C62CFB",
            #value_enum="#538df0",
            value_number="#2cfb5f",
            bool_true="#2cfb5f",
            bool_false="#FF3B30",
            null=None,
            value_description=None,
            value_cadence= None ,
        ),
        rules=Rules(
            description_value="plain",
            description_block="plain",
            use_terminal_fg=False,
        ),
    ),

    "base_green_terminal": ThemeSpec(
        name="base_green_term"
             "kkjhinal",
        palette=Palette(
            bg="#08140E",
            bg_alt="#0F2A1B",
            plain_fg="#d7ddd8",
            dim="#6B8F7A",
            key_name="#00FF7A",
            value_name="#FFD166",
            value_exercise_name="#00E5FF",
            value_enum="#00D7FF",
            value_number="#00D7FF",
            bool_true="#B6FF00",
            bool_false="#FF3B30",
            null="#6B8F7A",
        ),
        rules=Rules(description_value="plain", description_block="plain", use_terminal_fg=True),
    ),

    "base_blue_terminal": ThemeSpec(
        name="base_blue_terminal",
        palette=Palette(
            bg="#07111F",
            bg_alt="#0E223D",
            plain_fg="#d7dde6",
            dim="#8AA0B8",
            key_name="#2D7DFF",
            value_name="#FFD166",
            value_exercise_name="#00E5FF",
            value_enum="#C62CFB",
            value_number="#C62CFB",
            bool_true="#00FF3B",
            bool_false="#FF3B30",
            null="#8AA0B8",
        ),
        rules=Rules(description_value="plain", description_block="plain", use_terminal_fg=True),
    ),

    "base_amber_terminal": ThemeSpec(
        name="base_amber_terminal",
        palette=Palette(
            bg="#15110A",
            bg_alt="#2A1E10",
            plain_fg="#e3d7c7",
            dim="#B59C7A",
            key_name="#FFB000",
            value_name="#D7E274",
            value_exercise_name="#00E5FF",
            value_enum="#00E5FF",
            value_number="#00E5FF",
            bool_true="#00FF3B",
            bool_false="#FF3B30",
            null="#B59C7A",
        ),
        rules=Rules(description_value="plain", description_block="plain", use_terminal_fg=True),
    ),

    "base_synth_purple": ThemeSpec(
        name="base_synth_purple",
        palette=Palette(
            bg="#140B1F",
            bg_alt="#2A1342",
            plain_fg="#e2d9f0",
            dim="#A99BC2",
            key_name="#FF4DFF",
            value_name="#FFE066",
            value_exercise_name="#00E5FF",
            value_enum="#00E5FF",
            value_number="#00E5FF",
            bool_true="#00FF3B",
            bool_false="#FF3B30",
            null="#A99BC2",
        ),
        rules=Rules(description_value="plain", description_block="plain", use_terminal_fg=True),
    ),

    "base_cyan_black": ThemeSpec(
        name="base_cyan_black",
        palette=Palette(
            bg="#000000",
            bg_alt="#141414",
            plain_fg="#C7C7C7",
            dim="#707070",
            key_name="#00FFFF",
            value_name="#C7C7C7",
            value_exercise_name="#00E5FF",
            value_enum="#00B7FF",
            value_number="#FF00FC",
            bool_true="#00FF3B",
            bool_false="#FF3B30",
            null="#707070",
        ),
        rules=Rules(description_value="plain", description_block="plain", use_terminal_fg=False),
    ),
}

for _t in THEMES.values():
    validate_theme(_t)