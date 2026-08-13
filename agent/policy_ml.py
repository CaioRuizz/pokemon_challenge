"""Política de imitation learning: pontua opções de MAIN select com um
modelo linear (regressão logística por pares) treinado em ~12 mil decisões
reais de jogadores que venceram no ladder (ver docs/11-loop-continuo.md e
scripts/build_imitation_dataset.py / scripts/train_imitation.py).

Pesos hardcoded abaixo — nenhuma dependência externa (numpy/sklearn) em
tempo de execução, só Python puro, para não depender de bibliotecas que
talvez não existam no ambiente de submissão."""
from card_data import get_attack, get_card
from fallback import safe_selection

_MAIN_SELECT_TYPE = 0
_SETUP_ACTIVE_CONTEXT = 1
_SETUP_BENCH_CONTEXT = 2

_AREA_ACTIVE = 4
_AREA_BENCH = 5
_WEAKNESS_MULTIPLIER = 2
_RESISTANCE_PENALTY = 30

_OPTION_TYPES = [13, 9, 10, 11, 7, 8, 12, 14]  # ATTACK,EVOLVE,ABILITY,DISCARD,PLAY,ATTACH,RETREAT,END

# Treinado em scripts/train_imitation.py a partir de scripts/build_imitation_dataset.py
# (275 episódios reais do ladder, 12088 decisões de jogadores vencedores, 210k pares).
# Ajuste manual: o peso aprendido para "ataque de dano zero" (índice 10) saiu
# fortemente positivo (+1.37) porque o dataset genérico tem muitos ataques de
# utilidade (busca, cura, troca) que são bons jogados por quem os tem — mas
# no NOSSO deck isso inclui os primeiros ataques de Genesect/Pinsir, que já
# sabemos (bug corrigido bem no início desta sessão, docs/08) que causam loop
# se priorizados sem critério. Sobrescrito para o mesmo valor conservador que
# a heurística usa, em vez de confiar cegamente no peso aprendido aqui.
_WEIGHTS = [
    -0.587504, 1.563109, 1.225750, 0.000000, 0.769982, -0.457234, -0.636270, -1.877729,
    -0.205574, 0.810502, -0.500000, 0.384919, -0.842138, 0.222282, -0.870171, -0.377846,
    -0.107504, 0.631480, 0.358687, 0.000000,
]


def _active_pokemon(players, index):
    if index >= len(players):
        return None
    active = players[index].get("active") or []
    return active[0] if active else None


def _field_pokemon(players, your_index, area, index):
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


def _attack_damage(attack, attacker_card, defender_card):
    damage = attack.damage
    if attacker_card is not None and defender_card is not None:
        if defender_card.weakness is not None and defender_card.weakness == attacker_card.energyType:
            damage *= _WEAKNESS_MULTIPLIER
        if defender_card.resistance is not None and defender_card.resistance == attacker_card.energyType:
            damage = max(0, damage - _RESISTANCE_PENALTY)
    return damage


_N_FEATURES = len(_OPTION_TYPES) + 12


def _score_option_ml(opt: dict, current: dict, hand: list | None) -> float:
    f = [0.0] * _N_FEATURES
    opt_type = opt.get("type")
    if opt_type in _OPTION_TYPES:
        f[_OPTION_TYPES.index(opt_type)] = 1.0

    your_index = current["yourIndex"]
    opp_index = 1 - your_index
    players = current["players"]
    your_active = _active_pokemon(players, your_index)
    opp_active = _active_pokemon(players, opp_index)
    attacker_card = get_card(your_active["id"]) if your_active else None
    defender_card = get_card(opp_active["id"]) if opp_active else None

    idx = len(_OPTION_TYPES)

    if opt_type == 13:  # ATTACK
        attack = get_attack(opt.get("attackId"))
        if attack is not None:
            damage = _attack_damage(attack, attacker_card, defender_card)
            f[idx] = min(damage, 400) / 400.0
            defender_hp = opp_active["hp"] if opp_active else None
            f[idx + 1] = 1.0 if (defender_hp is not None and damage >= defender_hp) else 0.0
            f[idx + 2] = 1.0 if damage <= 0 else 0.0
            if defender_hp:
                f[idx + 10] = min(damage / defender_hp, 2.0)
    elif opt_type == 8:  # ATTACH
        area = opt.get("inPlayArea")
        f[idx + 3] = 1.0 if area == _AREA_ACTIVE else 0.0
        f[idx + 4] = 1.0 if area == _AREA_BENCH else 0.0
        target = _field_pokemon(players, your_index, area, opt.get("inPlayIndex"))
        hand_index = opt.get("index")
        if target is not None and hand is not None and hand_index is not None and hand_index < len(hand):
            hand_card = get_card(hand[hand_index].get("id"))
            target_card = get_card(target.get("id"))
            if hand_card is not None and target_card is not None and hand_card.cardType == 5:
                f[idx + 5] = 1.0 if hand_card.energyType == target_card.energyType else 0.0
    elif opt_type == 7:  # PLAY
        hand_index = opt.get("index")
        if hand is not None and hand_index is not None and hand_index < len(hand):
            card = get_card(hand[hand_index].get("id"))
            if card is not None:
                f[idx + 6] = 1.0 if card.cardType == 3 else 0.0
                f[idx + 7] = 1.0 if card.cardType == 1 else 0.0
                f[idx + 8] = 1.0 if card.cardType == 4 else 0.0
    elif opt_type == 12:  # RETREAT
        if your_active and your_active.get("maxHp"):
            ratio = your_active["hp"] / your_active["maxHp"]
            f[idx + 9] = 1.0 if ratio < 0.3 else 0.0

    return sum(w * x for w, x in zip(_WEIGHTS, f))


def _score_setup_candidate(opt, hand):
    index = opt.get("index")
    if not hand or index is None or index >= len(hand):
        return 0
    card = get_card(hand[index].get("id"))
    if card is None or not card.attacks:
        return 0
    best = 0.0
    for attack_id in card.attacks:
        attack = get_attack(attack_id)
        if attack is None:
            continue
        n_energy = max(len(attack.energies), 1)
        best = max(best, attack.damage / n_energy)
    return best + card.hp * 0.01


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
    hand = players[your_index].get("hand") if your_index < len(players) else None

    scored = sorted(range(len(options)), key=lambda i: _score_option_ml(options[i], current, hand), reverse=True)
    return safe_selection(min_count, max_count, len(options), scored)
