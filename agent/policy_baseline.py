from fallback import safe_selection

# SelectType.MAIN = 0 (cg/api.py). Only relevant for the main turn decision.
_MAIN_SELECT_TYPE = 0

# OptionType priority for a MAIN selection (cg/api.py): prefer attacking and
# developing the board over passing. ATTACK=13, EVOLVE=9, ABILITY=10, PLAY=7,
# ATTACH=8, RETREAT=12, END=14.
_MAIN_PRIORITY = [13, 9, 10, 7, 8, 12, 14]


def choose(select: dict) -> list[int]:
    options = select["option"]
    min_count = select["minCount"]
    max_count = select["maxCount"]

    if select["type"] != _MAIN_SELECT_TYPE:
        return safe_selection(min_count, max_count, len(options))

    ranked: list[int] = []
    for opt_type in _MAIN_PRIORITY:
        ranked.extend(i for i, opt in enumerate(options) if opt.get("type") == opt_type)
    return safe_selection(min_count, max_count, len(options), ranked)
