from card_data import get_attack, get_card
from fallback import safe_selection

_MAIN_SELECT_TYPE = 0

# OptionType categories for a MAIN selection (cg/api.py). Higher = preferred.
# ATTACK gets a dynamic sub-score (damage/lethality) on top of its category.
_CATEGORY = {
    13: 5,  # ATTACK
    9: 4,  # EVOLVE
    10: 3,  # ABILITY
    11: 0.5,  # DISCARD
    7: 2,  # PLAY
    8: 1,  # ATTACH
    12: 0,  # RETREAT
    14: -1,  # END
}
_WEAKNESS_MULTIPLIER = 2
_RESISTANCE_PENALTY = 30
_RETREAT_DANGER_HP_RATIO = 0.3
_RETREAT_DANGER_CATEGORY = 3.5


def _active_pokemon(players: list, index: int):
    if index >= len(players):
        return None
    active = players[index].get("active") or []
    return active[0] if active else None


def _attack_damage(attack, attacker_card, defender_card) -> int:
    damage = attack.damage
    if attacker_card is not None and defender_card is not None:
        if defender_card.weakness is not None and defender_card.weakness == attacker_card.energyType:
            damage *= _WEAKNESS_MULTIPLIER
        if defender_card.resistance is not None and defender_card.resistance == attacker_card.energyType:
            damage = max(0, damage - _RESISTANCE_PENALTY)
    return damage


def _score_option(opt: dict, attacker_card, defender_card, defender_hp, active_hp_ratio) -> tuple[float, float]:
    opt_type = opt.get("type")

    if opt_type == 13:  # ATTACK
        attack = get_attack(opt.get("attackId"))
        if attack is None:
            return (_CATEGORY[13], 0)
        damage = _attack_damage(attack, attacker_card, defender_card)
        lethal = defender_hp is not None and damage >= defender_hp
        return (_CATEGORY[13] + (0.5 if lethal else 0), damage)

    if opt_type == 12 and active_hp_ratio is not None and active_hp_ratio < _RETREAT_DANGER_HP_RATIO:
        return (_RETREAT_DANGER_CATEGORY, 0)

    return (_CATEGORY.get(opt_type, -2), 0)


def choose(obs: dict) -> list[int]:
    select = obs["select"]
    options = select["option"]
    min_count = select["minCount"]
    max_count = select["maxCount"]

    if select["type"] != _MAIN_SELECT_TYPE:
        return safe_selection(min_count, max_count, len(options))

    current = obs.get("current") or {}
    players = current.get("players") or []
    your_index = current.get("yourIndex", 0)
    opp_index = 1 - your_index

    your_active = _active_pokemon(players, your_index)
    opp_active = _active_pokemon(players, opp_index)

    attacker_card = get_card(your_active["id"]) if your_active else None
    defender_card = get_card(opp_active["id"]) if opp_active else None
    defender_hp = opp_active["hp"] if opp_active else None
    active_hp_ratio = None
    if your_active and your_active.get("maxHp"):
        active_hp_ratio = your_active["hp"] / your_active["maxHp"]

    scored = sorted(
        range(len(options)),
        key=lambda i: _score_option(options[i], attacker_card, defender_card, defender_hp, active_hp_ratio),
        reverse=True,
    )
    return safe_selection(min_count, max_count, len(options), scored)
