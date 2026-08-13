#!/usr/bin/env python3
"""Otimização evolutiva (CMA-ES) dos pesos de scoring da política, usando
winrate real contra os arquétipos catalogados como fitness — em vez de
imitar dados de log (docs/12), otimiza direto o que importa.

Arquitetura de features idêntica a agent/policy_ml.py (mesma função
option_features), mas os pesos são o genoma evoluído em vez de constantes
aprendidas por regressão logística.

Uso:
    python scripts/evolve_policy.py --generations 200 --pop-size 16 \
        --checkpoint data/ml/evolved_weights.json
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import cma
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "agent"))

from cg.game import battle_start, battle_select, battle_finish  # noqa: E402
from cg.api import all_card_data, all_attack  # noqa: E402
import policy_heuristic  # noqa: E402

_cards = {c.cardId: c for c in all_card_data()}
_attacks = {a.attackId: a for a in all_attack()}

_OPTION_TYPES = [13, 9, 10, 11, 7, 8, 12, 14]
_AREA_ACTIVE = 4
_AREA_BENCH = 5
_WEAKNESS_MULTIPLIER = 2
_RESISTANCE_PENALTY = 30
N_FEATURES = len(_OPTION_TYPES) + 18  # v2: +6 features de interação (ver docs/11, iteração 17)
_MAX_STEPS = 800
_MAX_TURN_FOR_URGENCY = 30


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
    """(está pronto para atacar agora?, maior dano potencial do seu melhor ataque).

    Mirror de agent/policy_heuristic.py::_best_ready_or_potential_damage."""
    card = _cards.get(pokemon.get("id")) if pokemon else None
    if card is None or not card.attacks:
        return (False, 0)
    attached = pokemon.get("energies") or []
    ready = False
    best_damage = 0
    for attack_id in card.attacks:
        attack = _attacks.get(attack_id)
        if attack is None:
            continue
        damage = _attack_damage(attack, card, defender_card)
        best_damage = max(best_damage, damage)
        if len(attached) >= len(attack.energies):
            ready = True
    return (ready, best_damage)


def _defender_scales_with_active_energy(defender_card) -> bool:
    """Detecta por texto se o ativo do oponente tem um ataque cujo dano escala
    com energia anexada no NOSSO ativo (docs/11, iteração 8: Ogerpon "Myriad
    Leaf Shower" escala com os dois ativos; Alakazam "Psychic" escala com a
    energia do ativo do oponente do ponto de vista de quem ataca, ou seja, a
    nossa). Pega a versão mais ampla (ambos os padrões) — na iteração 8 essa
    versão ampla tinha sinal mais forte no matchup-alvo (Ogerpon), mesmo com
    ruído maior nos matchups de controle; aqui vira feature aprendível em vez
    de penalidade fixa, deixando o CMA-ES decidir o peso certo."""
    if defender_card is None or not defender_card.attacks:
        return False
    for attack_id in defender_card.attacks:
        attack = _attacks.get(attack_id)
        if attack is None or not attack.text:
            continue
        text = attack.text.lower()
        if "for each energy attached to" in text and (
            "opponent's active" in text or "both active" in text
        ):
            return True
    return False


def option_features(opt, current, hand):
    f = [0.0] * N_FEATURES
    opt_type = opt.get("type")
    if opt_type in _OPTION_TYPES:
        f[_OPTION_TYPES.index(opt_type)] = 1.0

    your_index = current["yourIndex"]
    opp_index = 1 - your_index
    players = current["players"]
    your_active = _active_pokemon(players, your_index)
    opp_active = _active_pokemon(players, opp_index)
    attacker_card = _cards.get(your_active["id"]) if your_active else None
    defender_card = _cards.get(opp_active["id"]) if opp_active else None
    idx = len(_OPTION_TYPES)

    if opt_type == 13:
        attack = _attacks.get(opt.get("attackId"))
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
    elif opt_type == 8:
        area = opt.get("inPlayArea")
        f[idx + 3] = 1.0 if area == _AREA_ACTIVE else 0.0
        f[idx + 4] = 1.0 if area == _AREA_BENCH else 0.0
        target = _field_pokemon(players, your_index, area, opt.get("inPlayIndex"))
        hand_index = opt.get("index")
        if target is not None and hand is not None and hand_index is not None and hand_index < len(hand):
            hand_card = _cards.get(hand[hand_index].get("id"))
            target_card = _cards.get(target.get("id"))
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
    elif opt_type == 7:
        hand_index = opt.get("index")
        if hand is not None and hand_index is not None and hand_index < len(hand):
            card = _cards.get(hand[hand_index].get("id"))
            if card is not None:
                f[idx + 6] = 1.0 if card.cardType == 3 else 0.0
                f[idx + 7] = 1.0 if card.cardType == 1 else 0.0
                f[idx + 8] = 1.0 if card.cardType == 4 else 0.0
    elif opt_type == 12:
        if your_active and your_active.get("maxHp"):
            ratio = your_active["hp"] / your_active["maxHp"]
            f[idx + 9] = 1.0 if ratio < 0.3 else 0.0
        _, active_damage = _best_ready_or_potential_damage(your_active, defender_card) if your_active else (False, 0)
        bench = players[your_index].get("bench") or []
        better_bench = any(
            _best_ready_or_potential_damage(b, defender_card)[1] > active_damage for b in bench
        )
        f[idx + 16] = 1.0 if better_bench else 0.0

    return f


_MAIN_SELECT_TYPE = 0
_SETUP_ACTIVE_CONTEXT = 1
_SETUP_BENCH_CONTEXT = 2


def _score_setup_candidate(opt, hand):
    index = opt.get("index")
    if not hand or index is None or index >= len(hand):
        return 0
    card = _cards.get(hand[index].get("id"))
    if card is None or not card.attacks:
        return 0
    best = 0.0
    for attack_id in card.attacks:
        attack = _attacks.get(attack_id)
        if attack is None:
            continue
        n_energy = max(len(attack.energies), 1)
        best = max(best, attack.damage / n_energy)
    return best + card.hp * 0.01


def safe_selection(min_count, max_count, n_options, ranked_indices=None):
    if n_options <= 0:
        return []
    max_count = max(0, min(max_count, n_options))
    min_count = max(0, min(min_count, max_count))
    ranked_indices = [i for i in (ranked_indices or []) if 0 <= i < n_options]
    target = max(min_count, min(len(ranked_indices), max_count)) if ranked_indices else min_count
    chosen = []
    for i in ranked_indices:
        if len(chosen) >= target:
            break
        if i not in chosen:
            chosen.append(i)
    for i in range(n_options):
        if len(chosen) >= target:
            break
        if i not in chosen:
            chosen.append(i)
    return chosen


def make_weighted_choose(weights):
    def choose(obs):
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
                ranked = sorted(
                    range(len(options)), key=lambda i: _score_setup_candidate(options[i], hand), reverse=True
                )
                return safe_selection(min_count, max_count, len(options), ranked)
            return safe_selection(min_count, max_count, len(options))

        current = obs.get("current") or {}
        players = current.get("players") or []
        your_index = current.get("yourIndex", 0)
        hand = players[your_index].get("hand") if your_index < len(players) else None

        def score(i):
            feats = option_features(options[i], current, hand)
            return sum(w * x for w, x in zip(weights, feats))

        scored = sorted(range(len(options)), key=score, reverse=True)
        return safe_selection(min_count, max_count, len(options), scored)

    return choose


def play_game(deck_a, deck_b, choose_a, choose_b):
    obs, _ = battle_start(deck_a, deck_b)
    steps = 0
    errors = 0
    while obs["current"]["result"] == -1 and steps < _MAX_STEPS:
        your_index = obs["current"]["yourIndex"]
        fn = choose_a if your_index == 0 else choose_b
        try:
            choice = fn(obs)
        except Exception:
            errors += 1
            choice = []
        obs = battle_select(choice)
        steps += 1
    result = obs["current"]["result"]
    battle_finish()
    return result, errors, steps >= _MAX_STEPS


def load_archetypes(decks_dir: Path, weights_csv: Path | None):
    archetypes = []
    default_weight = {
        "real_munkidori_impidimp.csv": 21.4,
        "real_abra_kadabra_alakazam.csv": 16.6,
        "real_dunsparce_dudunsparce.csv": 14.8,
        "real_dwebble_crustle_kangaskhan.csv": 8.5,
        "real_cynthias-roselia_gible.csv": 5.8,
        "real_grookey_thwackey_applin.csv": 5.3,
        "real_ogerpon_chikorita-meganium.csv": 4.5,
        "real_dreepy_dragapult.csv": 3.5,
        "real_ogerpon_solo.csv": 2.5,
        "real_mega-lucario_solrock.csv": 1.5,
    }
    for name, weight in default_weight.items():
        path = decks_dir / name
        if path.exists():
            archetypes.append((path, weight))
    return archetypes


_FLOOR_WINRATE = 0.40  # ver docs/11, iteração 18: media ponderada por uso deixa o CMA-ES
_FLOOR_PENALTY_SCALE = 0.3  # sacrificar arquétipos minoritários (baixo peso) por ganho nos majoritários


def fitness(weights, our_deck, archetypes, games_per_archetype, opponent_choose):
    choose_a = make_weighted_choose(weights)
    total_weight = 0.0
    total_score = 0.0
    floor_penalty = 0.0
    for path, weight in archetypes:
        opp_deck = [int(x) for x in path.read_text().split()]
        wins = 0
        errors_total = 0
        for i in range(games_per_archetype):
            if i % 2 == 0:
                result, errors, _ = play_game(our_deck, opp_deck, choose_a, opponent_choose)
                won = result == 0
            else:
                result, errors, _ = play_game(opp_deck, our_deck, opponent_choose, choose_a)
                won = result == 1
            wins += 1 if won else 0
            errors_total += errors
        winrate = wins / games_per_archetype
        penalty = 0.05 * errors_total  # penaliza erro de política (rede de segurança acionada)
        total_score += weight * (winrate - penalty)
        total_weight += weight
        # penalidade absoluta (não escalada pelo peso de uso) por arquétipo abaixo do piso —
        # sem isso, a média ponderada permite trocar arquétipos de baixo uso por ganho nos
        # majoritários, mesmo que isso reverta melhorias já validadas (docs/11, iteração 18).
        if winrate < _FLOOR_WINRATE:
            floor_penalty += (_FLOOR_WINRATE - winrate) * _FLOOR_PENALTY_SCALE
    return total_score / total_weight - floor_penalty


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generations", type=int, default=100)
    parser.add_argument("--pop-size", type=int, default=12)
    parser.add_argument("--games-per-archetype", type=int, default=6)
    parser.add_argument("--sigma", type=float, default=0.3)
    parser.add_argument("--checkpoint", default=str(ROOT / "data" / "ml" / "evolved_weights.json"))
    parser.add_argument("--init-weights", default=None, help="JSON com pesos iniciais (senão usa policy_ml)")
    parser.add_argument("--deck", default=str(ROOT / "agent" / "deck.csv"))
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    our_deck = [int(x) for x in Path(args.deck).read_text().split()]
    archetypes = load_archetypes(ROOT / "data" / "decks", None)
    print(f"{len(archetypes)} arquétipos carregados, {args.games_per_archetype} partidas cada por avaliação")

    if args.init_weights:
        x0 = json.loads(Path(args.init_weights).read_text())["weights"]
    else:
        import policy_ml

        x0 = list(policy_ml._WEIGHTS)
    assert len(x0) == N_FEATURES, f"esperado {N_FEATURES} pesos, achei {len(x0)}"

    opponent_choose = policy_heuristic.choose

    es = cma.CMAEvolutionStrategy(x0, args.sigma, {"popsize": args.pop_size, "seed": args.seed})

    checkpoint_path = Path(args.checkpoint)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    best_fitness = -1.0
    best_weights = x0
    if checkpoint_path.exists():
        prev = json.loads(checkpoint_path.read_text())
        best_fitness = prev.get("fitness", -1.0)
        best_weights = prev.get("weights", x0)
        print(f"checkpoint existente encontrado: fitness={best_fitness:.4f}")

    t0 = time.time()
    for gen in range(args.generations):
        solutions = es.ask()
        fitnesses = [fitness(w, our_deck, archetypes, args.games_per_archetype, opponent_choose) for w in solutions]
        es.tell(solutions, [-f for f in fitnesses])  # cma minimiza

        gen_best_idx = max(range(len(fitnesses)), key=lambda i: fitnesses[i])
        gen_best_fitness = fitnesses[gen_best_idx]
        if gen_best_fitness > best_fitness:
            best_fitness = gen_best_fitness
            best_weights = list(solutions[gen_best_idx])
            checkpoint_path.write_text(
                json.dumps({"fitness": best_fitness, "weights": best_weights, "generation": gen}, indent=2)
            )

        elapsed = time.time() - t0
        print(
            f"gen {gen:4d}  fitness_geração={gen_best_fitness:.4f}  melhor_global={best_fitness:.4f}  "
            f"t={elapsed:.0f}s"
        )
        sys.stdout.flush()

    print(f"\nmelhor fitness encontrado: {best_fitness:.4f}")
    print(f"salvo em: {checkpoint_path}")


if __name__ == "__main__":
    main()
