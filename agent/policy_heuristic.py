from dataclasses import dataclass

from card_data import get_attack, get_card
from fallback import safe_selection

_MAIN_SELECT_TYPE = 0

# SelectContext (cg/api.py): escolha do Pokémon ativo/banco inicial no setup.
_SETUP_ACTIVE_CONTEXT = 1
_SETUP_BENCH_CONTEXT = 2

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


_AREA_ACTIVE = 4  # AreaType.ACTIVE
_AREA_BENCH = 5  # AreaType.BENCH
_BENCH_REDIRECT_RATIO = 1.4  # só desvia energia se o banco valer >=1.4x mais que o ativo


@dataclass
class _Context:
    attacker_card: object | None
    defender_card: object | None
    defender_hp: int | None
    active_hp_ratio: float | None
    hand: list | None
    bench_count: int
    players: list
    your_index: int


def _active_pokemon(players: list, index: int):
    if index >= len(players):
        return None
    active = players[index].get("active") or []
    return active[0] if active else None


def _field_pokemon(players: list, your_index: int, area, index):
    if area is None or index is None or your_index >= len(players):
        return None
    player = players[your_index]
    if area == _AREA_ACTIVE:
        active = player.get("active") or []
        return active[0] if active else None
    if area == _AREA_BENCH:
        bench = player.get("bench") or []
        return bench[index] if index < len(bench) else None
    return None


def _attack_damage(attack, attacker_card, defender_card) -> int:
    damage = attack.damage
    if attacker_card is not None and defender_card is not None:
        if defender_card.weakness is not None and defender_card.weakness == attacker_card.energyType:
            damage *= _WEAKNESS_MULTIPLIER
        if defender_card.resistance is not None and defender_card.resistance == attacker_card.energyType:
            damage = max(0, damage - _RESISTANCE_PENALTY)
    return damage


def _best_ready_or_potential_damage(pokemon: dict, defender_card) -> tuple[bool, int]:
    """(está pronto para atacar agora?, maior dano potencial do seu melhor ataque)."""
    card = get_card(pokemon.get("id"))
    if card is None or not card.attacks:
        return (False, 0)
    attached = pokemon.get("energies") or []
    ready = False
    best_damage = 0
    for attack_id in card.attacks:
        attack = get_attack(attack_id)
        if attack is None:
            continue
        damage = _attack_damage(attack, card, defender_card)
        best_damage = max(best_damage, damage)
        if len(attached) >= len(attack.energies):
            ready = True
    return (ready, best_damage)


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


def _score_attach(opt: dict, ctx: _Context) -> float:
    """Normalmente indiferente entre alvos de ATTACH (deixa a ordem natural da
    lista, que tende a favorecer o ativo). Só desvia para um Pokémon no banco
    quando o ativo já está pronto para atacar (não precisa mais da energia
    agora) E o banco tem um atacante com potencial de dano bem maior
    (>= _BENCH_REDIRECT_RATIO) — evita repetir o problema da tentativa anterior
    (docs/09), que redirecionava cedo demais e atrapalhava o ativo."""
    target = _field_pokemon(ctx.players, ctx.your_index, opt.get("inPlayArea"), opt.get("inPlayIndex"))
    if target is None:
        return _CATEGORY[8]
    if opt.get("inPlayArea") != _AREA_BENCH:
        return _CATEGORY[8]

    your_active = _active_pokemon(ctx.players, ctx.your_index)
    if your_active is None:
        return _CATEGORY[8]

    active_ready, active_damage = _best_ready_or_potential_damage(your_active, ctx.defender_card)
    if not active_ready:
        return _CATEGORY[8]  # ativo ainda precisa da energia — não desviar

    _, bench_damage = _best_ready_or_potential_damage(target, ctx.defender_card)
    if active_damage > 0 and bench_damage >= active_damage * _BENCH_REDIRECT_RATIO:
        return _CATEGORY[8] + 0.9  # topo da categoria ATTACH — prioriza esse alvo
    return _CATEGORY[8]


def _score_setup_candidate(opt: dict, hand: list | None) -> float:
    """Prefere, para o Pokémon ativo/banco inicial, o básico com melhor ataque
    (dano do golpe mais barato por energia), com HP como desempate leve."""
    index = opt.get("index")
    if not hand or index is None or index >= len(hand):
        return 0
    card = get_card(hand[index].get("id"))
    if card is None or not card.attacks:
        return 0
    best_efficiency = 0.0
    for attack_id in card.attacks:
        attack = get_attack(attack_id)
        if attack is None:
            continue
        n_energy = max(len(attack.energies), 1)
        best_efficiency = max(best_efficiency, attack.damage / n_energy)
    return best_efficiency + card.hp * 0.01


def _score_option(opt: dict, ctx: _Context) -> tuple[float, float]:
    opt_type = opt.get("type")

    if opt_type == 13:  # ATTACK
        attack = get_attack(opt.get("attackId"))
        if attack is None:
            return (_CATEGORY[13], 0)
        damage = _attack_damage(attack, ctx.attacker_card, ctx.defender_card)
        if damage <= 0:
            # Ataque sem dano (ex.: efeito de utilidade) não vale mais que
            # simplesmente anexar energia para um ataque de verdade depois —
            # senão o bot "ataca" à toa todo turno e nunca acumula energia.
            return (_CATEGORY[8] - 0.5, damage)
        lethal = ctx.defender_hp is not None and damage >= ctx.defender_hp
        return (_CATEGORY[13] + (0.5 if lethal else 0), damage)

    if opt_type == 7:  # PLAY
        return (_score_play(opt, ctx), 0)

    if opt_type == 8:  # ATTACH
        return (_score_attach(opt, ctx), 0)

    if opt_type == 12 and ctx.active_hp_ratio is not None and ctx.active_hp_ratio < _RETREAT_DANGER_HP_RATIO:
        return (_RETREAT_DANGER_CATEGORY, 0)

    return (_CATEGORY.get(opt_type, -2), 0)


def choose(obs: dict) -> list[int]:
    select = obs["select"]
    options = select["option"]
    min_count = select["minCount"]
    max_count = select["maxCount"]

    if select["type"] != _MAIN_SELECT_TYPE:
        if select.get("context") in (_SETUP_ACTIVE_CONTEXT, _SETUP_BENCH_CONTEXT):
            current = obs.get("current") or {}
            players = current.get("players") or []
            your_index = current.get("yourIndex", 0)
            hand = players[your_index].get("hand") if your_index < len(players) else None
            ranked = sorted(range(len(options)), key=lambda i: _score_setup_candidate(options[i], hand), reverse=True)
            return safe_selection(min_count, max_count, len(options), ranked)
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
        players=players,
        your_index=your_index,
    )

    scored = sorted(
        range(len(options)),
        key=lambda i: _score_option(options[i], ctx),
        reverse=True,
    )
    return safe_selection(min_count, max_count, len(options), scored)
