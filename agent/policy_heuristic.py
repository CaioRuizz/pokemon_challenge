from dataclasses import dataclass

from card_data import get_attack, get_card
from fallback import safe_selection

_MAIN_SELECT_TYPE = 0

# OptionType categories for a MAIN selection (cg/api.py). Higher = preferred.
# ATTACK and PLAY get a dynamic sub-score on top of their category.
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

# Cartas do deck atual (docs/08-status-implementacao.md) cujo efeito conhecemos.
_DRAW_SUPPORTER_IDS = {1224, 1236}  # Cheren, Urbain: "Draw 3 cards."
_SEARCH_ITEM_IDS = {1125, 1142}  # Master Ball, Fighting Gong: buscam Pokémon/energia
_SWITCH_ITEM_ID = 1123  # Switch: troca o ativo de graça (sem custo de retreat)
_LOW_HAND_THRESHOLD = 3
_LOW_BENCH_THRESHOLD = 3


@dataclass
class _Context:
    attacker_card: object | None
    defender_card: object | None
    defender_hp: int | None
    active_hp_ratio: float | None
    hand: list | None
    bench_count: int


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


def _score_play(opt: dict, ctx: _Context) -> float:
    if not ctx.hand:
        return _CATEGORY[7]
    hand_index = opt.get("index")
    if hand_index is None or hand_index >= len(ctx.hand):
        return _CATEGORY[7]
    card_id = ctx.hand[hand_index].get("id")

    if card_id in _DRAW_SUPPORTER_IDS:
        return _CATEGORY[7] + (1.5 if len(ctx.hand) <= _LOW_HAND_THRESHOLD else 0.3)

    if card_id == _SWITCH_ITEM_ID:
        danger = ctx.active_hp_ratio is not None and ctx.active_hp_ratio < _RETREAT_DANGER_HP_RATIO
        return _RETREAT_DANGER_CATEGORY + 0.1 if danger else _CATEGORY[7] - 0.5

    if card_id in _SEARCH_ITEM_IDS:
        return _CATEGORY[7] + (1.0 if ctx.bench_count < _LOW_BENCH_THRESHOLD else 0.2)

    return _CATEGORY[7]


def _score_option(opt: dict, ctx: _Context) -> tuple[float, float]:
    opt_type = opt.get("type")

    if opt_type == 13:  # ATTACK
        attack = get_attack(opt.get("attackId"))
        if attack is None:
            return (_CATEGORY[13], 0)
        damage = _attack_damage(attack, ctx.attacker_card, ctx.defender_card)
        lethal = ctx.defender_hp is not None and damage >= ctx.defender_hp
        return (_CATEGORY[13] + (0.5 if lethal else 0), damage)

    if opt_type == 7:  # PLAY
        return (_score_play(opt, ctx), 0)

    if opt_type == 12 and ctx.active_hp_ratio is not None and ctx.active_hp_ratio < _RETREAT_DANGER_HP_RATIO:
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
    your_player = players[your_index] if your_index < len(players) else {}

    active_hp_ratio = None
    if your_active and your_active.get("maxHp"):
        active_hp_ratio = your_active["hp"] / your_active["maxHp"]

    ctx = _Context(
        attacker_card=get_card(your_active["id"]) if your_active else None,
        defender_card=get_card(opp_active["id"]) if opp_active else None,
        defender_hp=opp_active["hp"] if opp_active else None,
        active_hp_ratio=active_hp_ratio,
        hand=your_player.get("hand"),
        bench_count=len(your_player.get("bench") or []),
    )

    scored = sorted(
        range(len(options)),
        key=lambda i: _score_option(options[i], ctx),
        reverse=True,
    )
    return safe_selection(min_count, max_count, len(options), scored)
