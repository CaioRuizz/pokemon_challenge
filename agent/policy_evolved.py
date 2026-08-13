"""Política otimizada por busca evolutiva (CMA-ES) direto contra winrate real
— não é imitação de log (ver docs/12), é otimização direta do que importa:
vitórias contra os arquétipos catalogados (ver docs/11, iteração 14, e
scripts/evolve_policy.py). Mesma arquitetura de features de agent/policy_ml.py
(20 dimensões, Python puro, sem dependência externa em runtime).

Pesos: checkpoint de data/ml/evolved_weights.json, colado aqui após validação
rigorosa (n=60 por arquétipo, ver docs/11)."""
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

# scripts/evolve_policy.py, geração 22, fitness (winrate ponderado, ruidoso) 0.9262.
_WEIGHTS = [
    0.028199712094570166, 2.244651755698088, 1.969112247052527, 0.6179228425851113,
    0.5214294062893576, 1.0760307536693987, -2.4225964963297333, -1.645597351920833,
    -1.1829596900233201, -0.5724325573685229, -1.080418898523036, 0.6121048671909737,
    -1.1899347201524466, 0.9533362359754569, -0.18444948971222974, -1.3799033428972578,
    1.3010919932850562, -0.0678729214491346, 1.859540777290719, 1.5251892094692587,
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


def _score_option(opt: dict, current: dict, hand: list | None) -> float:
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

    scored = sorted(range(len(options)), key=lambda i: _score_option(options[i], current, hand), reverse=True)
    return safe_selection(min_count, max_count, len(options), scored)
