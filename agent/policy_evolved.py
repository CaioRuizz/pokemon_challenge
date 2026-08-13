"""Política otimizada por busca evolutiva (CMA-ES) direto contra winrate real
— não é imitação de log (ver docs/12), é otimização direta do que importa:
vitórias contra os arquétipos catalogados (ver docs/11, iterações 14-18, e
scripts/evolve_policy.py). Arquitetura de features v2 (26 dimensões: as 20
originais de agent/policy_ml.py + 6 features de interação com contexto —
ver docs/11, iteração 17), Python puro, sem dependência externa em runtime.

Pesos: checkpoint de data/ml/evolved_weights_v2_floor.json (fitness com
piso anti-sacrifício de arquétipo minoritário — ver docs/11, iteração 18),
colado aqui após validação rigorosa (n=60 por arquétipo + generalização em
decks sintéticos, ver docs/11)."""
from card_data import get_attack, get_card
from fallback import safe_selection

_MAIN_SELECT_TYPE = 0
_SETUP_ACTIVE_CONTEXT = 1
_SETUP_BENCH_CONTEXT = 2

_AREA_ACTIVE = 4
_AREA_BENCH = 5
_WEAKNESS_MULTIPLIER = 2
_RESISTANCE_PENALTY = 30
_MAX_TURN_FOR_URGENCY = 30

_OPTION_TYPES = [13, 9, 10, 11, 7, 8, 12, 14]  # ATTACK,EVOLVE,ABILITY,DISCARD,PLAY,ATTACH,RETREAT,END

# scripts/evolve_policy.py, checkpoint v2-floor, geração 6, fitness (winrate
# ponderado com piso anti-sacrifício, ruidoso) 0.8762. Validado a n=60 nos 10
# arquétipos reais: 82.8% ponderado (vs 81.2% da versão anterior, v10), com
# melhora nos dois matchups historicamente mais frágeis (docs/11, iteração 18).
_WEIGHTS = [
    1.0483644600842272, 2.976561355128746, 1.7647301376794005, 3.1408979017670764,
    3.2162030407537108, 1.7448502518447653, -2.7666933573587644, -0.23530201263153686,
    -3.6841933038977563, -2.089823544272792, 1.117201296438104, 1.576765806621201,
    0.07989547337044137, 1.844860606217843, -0.06647986322441798, -1.0798951032052744,
    1.568210393102456, -0.1135192958449321, 2.465395889774743, 3.2175423382669317,
    -0.772284805060298, 1.2280481811987318, 0.640339090150273, 0.29290298996728537,
    -1.1384018874428565, -0.6635405829747308,
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


def _best_ready_or_potential_damage(pokemon, defender_card):
    card = get_card(pokemon.get("id")) if pokemon else None
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


def _defender_scales_with_active_energy(defender_card) -> bool:
    if defender_card is None or not defender_card.attacks:
        return False
    for attack_id in defender_card.attacks:
        attack = get_attack(attack_id)
        if attack is None or not attack.text:
            continue
        text = attack.text.lower()
        if "for each energy attached to" in text and ("opponent's active" in text or "both active" in text):
            return True
    return False


_N_FEATURES = len(_OPTION_TYPES) + 18


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
            lethal = defender_hp is not None and damage >= defender_hp
            f[idx + 1] = 1.0 if lethal else 0.0
            f[idx + 2] = 1.0 if damage <= 0 else 0.0
            if defender_hp:
                f[idx + 10] = min(damage / defender_hp, 2.0)
            defender_is_ex = defender_card is not None and (defender_card.ex or defender_card.megaEx)
            f[idx + 11] = 1.0 if (lethal and defender_is_ex) else 0.0
            turn = current.get("turn") or 0
            f[idx + 15] = f[idx] * min(turn / _MAX_TURN_FOR_URGENCY, 1.0)
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
        if area == _AREA_BENCH and target is not None and your_active is not None:
            active_ready, active_damage = _best_ready_or_potential_damage(your_active, defender_card)
            if active_ready:
                _, bench_damage = _best_ready_or_potential_damage(target, defender_card)
                f[idx + 12] = max(min((bench_damage - active_damage) / 400.0, 2.0), -2.0)
        if area == _AREA_ACTIVE and your_active is not None and your_active.get("maxHp"):
            f[idx + 13] = 1.0 - your_active["hp"] / your_active["maxHp"]
            if _defender_scales_with_active_energy(defender_card):
                f[idx + 14] = 1.0
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
        active_damage = _best_ready_or_potential_damage(your_active, defender_card)[1] if your_active else 0
        bench = players[your_index].get("bench") or []
        better_bench = any(_best_ready_or_potential_damage(b, defender_card)[1] > active_damage for b in bench)
        f[idx + 16] = 1.0 if better_bench else 0.0

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
