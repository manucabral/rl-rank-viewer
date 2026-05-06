"""Rank helpers."""

_TIER_COLORS = (
    (22, "#e2e8f0"),
    (19, "#ef4444"),
    (16, "#a855f7"),
    (13, "#3b82f6"),
    (10, "#06b6d4"),
    (7, "#eab308"),
    (4, "#94a3b8"),
    (1, "#a16207"),
)

_ROMAN_TO_INT = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}


def rank_image_filename(tier_id: int) -> str:
    """s15rank{tier_id}.png for GC+, else s4-{tier_id}.png. Based on tracker.gg."""
    return f"s15rank{tier_id}.png" if tier_id >= 19 else f"s4-{tier_id}.png"


def rank_tier_color(tier_id: int) -> str:
    """Rank tier hex color."""
    for threshold, color in _TIER_COLORS:
        if tier_id >= threshold:
            return color
    return "#525252"


def parse_division_number(div_name: str) -> int:
    """Division II = 2, otherwise 0."""
    if not div_name.startswith("Division "):
        return 0
    return _ROMAN_TO_INT.get(div_name.split()[-1], 0)


def team_name(team_num: int) -> str:    
    """Team number to name."""
    return "BLUE" if team_num == 0 else "ORANGE" if team_num == 1 else "?"
