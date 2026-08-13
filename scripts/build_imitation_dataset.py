#!/usr/bin/env python3
"""Extrai pares (features das opções, índice escolhido) de episódios reais
do ladder para treinar um modelo de imitation learning (ver docs/11-loop-continuo.md,
seção sobre a tentativa de rede neural / imitation learning).

Só usa decisões de MAIN select (type=0) de escolha única (maxCount=1) feitas
pelo jogador que **venceu** a partida — imita jogadores reais que ganharam,
não qualquer jogada.

Uso:
    python scripts/build_imitation_dataset.py --episodes-dir DIR [--episodes-dir DIR2 ...] --out data/ml/dataset.npz
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "agent"))

from cg.api import all_card_data, all_attack  # noqa: E402

_OPTION_TYPES = [13, 9, 10, 11, 7, 8, 12, 14]  # ATTACK,EVOLVE,ABILITY,DISCARD,PLAY,ATTACH,RETREAT,END
_AREA_ACTIVE = 4
_AREA_BENCH = 5
_WEAKNESS_MULTIPLIER = 2
_RESISTANCE_PENALTY = 30

_cards = None
_attacks = None


def _load_card_data():
    global _cards, _attacks
    if _cards is None:
        _cards = {c.cardId: c for c in all_card_data()}
        _attacks = {a.attackId: a for a in all_attack()}


def _get_card(cid):
    return _cards.get(cid)


def _get_attack(aid):
    return _attacks.get(aid)


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


N_FEATURES = len(_OPTION_TYPES) + 12


def option_features(opt: dict, current: dict, hand: list | None) -> np.ndarray:
    """Vetor de features de UMA opção dentro de um MAIN select."""
    f = np.zeros(N_FEATURES, dtype=np.float32)
    opt_type = opt.get("type")
    if opt_type in _OPTION_TYPES:
        f[_OPTION_TYPES.index(opt_type)] = 1.0

    your_index = current["yourIndex"]
    opp_index = 1 - your_index
    players = current["players"]
    your_active = _active_pokemon(players, your_index)
    opp_active = _active_pokemon(players, opp_index)
    attacker_card = _get_card(your_active["id"]) if your_active else None
    defender_card = _get_card(opp_active["id"]) if opp_active else None

    idx = len(_OPTION_TYPES)

    if opt_type == 13:  # ATTACK
        attack = _get_attack(opt.get("attackId"))
        if attack is not None:
            damage = _attack_damage(attack, attacker_card, defender_card)
            f[idx] = min(damage, 400) / 400.0
            defender_hp = opp_active["hp"] if opp_active else None
            f[idx + 1] = 1.0 if (defender_hp is not None and damage >= defender_hp) else 0.0
            f[idx + 2] = 1.0 if damage <= 0 else 0.0
            if defender_hp:
                f[idx + 10] = min(damage / defender_hp, 2.0)  # dano relativo ao HP atual do defensor
    elif opt_type == 8:  # ATTACH
        area = opt.get("inPlayArea")
        f[idx + 3] = 1.0 if area == _AREA_ACTIVE else 0.0
        f[idx + 4] = 1.0 if area == _AREA_BENCH else 0.0
        target = _field_pokemon(players, your_index, area, opt.get("inPlayIndex"))
        hand_index = opt.get("index")
        if target is not None and hand is not None and hand_index is not None and hand_index < len(hand):
            hand_card = _get_card(hand[hand_index].get("id"))
            target_card = _get_card(target.get("id"))
            if hand_card is not None and target_card is not None and hand_card.cardType == 5:
                f[idx + 5] = 1.0 if hand_card.energyType == target_card.energyType else 0.0
    elif opt_type == 7:  # PLAY
        hand_index = opt.get("index")
        if hand is not None and hand_index is not None and hand_index < len(hand):
            card = _get_card(hand[hand_index].get("id"))
            if card is not None:
                f[idx + 6] = 1.0 if card.cardType == 3 else 0.0  # Supporter
                f[idx + 7] = 1.0 if card.cardType == 1 else 0.0  # Item
                f[idx + 8] = 1.0 if card.cardType == 4 else 0.0  # Stadium
    elif opt_type == 12:  # RETREAT
        if your_active and your_active.get("maxHp"):
            ratio = your_active["hp"] / your_active["maxHp"]
            f[idx + 9] = 1.0 if ratio < 0.3 else 0.0

    return f


def extract_from_episode(path: Path):
    """Retorna lista de (features_por_opcao: list[np.ndarray], escolhido: int)."""
    try:
        data = json.loads(path.read_text())
        steps = data["steps"]
        rewards = data["rewards"]
    except (KeyError, json.JSONDecodeError):
        return []

    examples = []
    for player in (0, 1):
        if rewards[player] != 1:
            continue  # só imita quem venceu
        for i in range(len(steps) - 1):
            try:
                obs = steps[i][player]["observation"]
                sel = obs.get("select")
                current = obs.get("current")
                if sel is None or current is None:
                    continue
                if sel["type"] != 0 or sel["maxCount"] != 1 or len(sel["option"]) < 2:
                    continue
                action = steps[i + 1][player]["action"]
                if not isinstance(action, list) or len(action) != 1:
                    continue
                chosen = action[0]
                if chosen < 0 or chosen >= len(sel["option"]):
                    continue
                hand = current["players"][player].get("hand")
                feats = [option_features(opt, current, hand) for opt in sel["option"]]
                examples.append((feats, chosen))
            except (KeyError, IndexError, TypeError):
                continue
    return examples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes-dir", action="append", required=True, type=Path)
    parser.add_argument("--out", default=ROOT / "data" / "ml" / "dataset.npz", type=Path)
    args = parser.parse_args()

    _load_card_data()

    all_examples = []
    n_files = 0
    for ep_dir in args.episodes_dir:
        for path in sorted(ep_dir.glob("*.json")):
            n_files += 1
            all_examples.extend(extract_from_episode(path))

    print(f"{n_files} episódios lidos, {len(all_examples)} decisões extraídas (só de vencedores)")

    # Monta pares (diferença de features, label=1) para regressão logística
    diffs = []
    labels = []
    for feats, chosen in all_examples:
        chosen_f = feats[chosen]
        for j, f in enumerate(feats):
            if j == chosen:
                continue
            diffs.append(chosen_f - f)
            labels.append(1)
            diffs.append(f - chosen_f)
            labels.append(0)

    X = np.array(diffs, dtype=np.float32)
    y = np.array(labels, dtype=np.int64)
    print(f"{len(X)} pares de treino, {X.shape[1]} features")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out, X=X, y=y, n_decisions=len(all_examples))
    print(f"salvo: {args.out}")


if __name__ == "__main__":
    main()
