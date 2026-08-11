#!/usr/bin/env python3
"""Roda N partidas locais entre duas políticas usando o engine oficial (vendor/cg).

Uso:
    python eval/local_match.py --deck-a data/decks/fighting_rush_v1.csv \\
        --deck-b vendor/deck_sample_placeholder.csv --games 20
"""
import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "agent"))

from cg.game import battle_start, battle_select, battle_finish  # noqa: E402


def load_policy(module_path: str):
    path = Path(module_path)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.choose


def read_deck(path: str) -> list[int]:
    with open(path) as f:
        ids = [int(x) for x in f.read().split()]
    if len(ids) != 60:
        raise ValueError(f"{path}: esperado 60 cartas, encontrado {len(ids)}")
    return ids


def run_match(deck_a, deck_b, choose_a, choose_b, games: int, max_steps: int = 5000) -> dict:
    wins_a = wins_b = draws = errors = 0
    turn_counts = []
    for i in range(games):
        if i % 2 == 0:
            obs, _ = battle_start(deck_a, deck_b)
            idx_a, idx_b = 0, 1
        else:
            obs, _ = battle_start(deck_b, deck_a)
            idx_a, idx_b = 1, 0

        steps = 0
        while obs["current"]["result"] == -1 and steps < max_steps:
            your_index = obs["current"]["yourIndex"]
            choose_fn = choose_a if your_index == idx_a else choose_b
            try:
                choice = choose_fn(obs)
            except Exception:
                errors += 1
                choice = []
            obs = battle_select(choice)
            steps += 1

        result = obs["current"]["result"]
        turn_counts.append(obs["current"]["turn"])
        if result == idx_a:
            wins_a += 1
        elif result == idx_b:
            wins_b += 1
        else:
            draws += 1
        battle_finish()

    return {
        "games": games,
        "wins_a": wins_a,
        "wins_b": wins_b,
        "draws": draws,
        "policy_errors": errors,
        "avg_turns": sum(turn_counts) / len(turn_counts) if turn_counts else 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deck-a", required=True)
    parser.add_argument("--deck-b", required=True)
    parser.add_argument("--policy-a", default=str(ROOT / "agent" / "policy_baseline.py"))
    parser.add_argument("--policy-b", default=str(ROOT / "agent" / "policy_baseline.py"))
    parser.add_argument("--games", type=int, default=20)
    args = parser.parse_args()

    deck_a = read_deck(args.deck_a)
    deck_b = read_deck(args.deck_b)
    choose_a = load_policy(args.policy_a)
    choose_b = load_policy(args.policy_b)

    stats = run_match(deck_a, deck_b, choose_a, choose_b, args.games)
    print(f"Partidas: {stats['games']}")
    print(f"A ({args.deck_a}) venceu: {stats['wins_a']} ({stats['wins_a'] / stats['games']:.0%})")
    print(f"B ({args.deck_b}) venceu: {stats['wins_b']} ({stats['wins_b'] / stats['games']:.0%})")
    print(f"Empates: {stats['draws']}")
    print(f"Erros de política (fallback acionado): {stats['policy_errors']}")
    print(f"Turnos médios: {stats['avg_turns']:.1f}")

    if stats["policy_errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
