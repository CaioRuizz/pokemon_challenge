#!/usr/bin/env python3
"""Extrai decklists reais de episódios do ladder (dataset oficial
kaggle/pokemon-tcg-ai-battle-episodes-YYYY-MM-DD) para usar como
adversários de teste em eval/local_match.py — em vez de só os decks
caseiros que nós mesmos construímos (ver docs/09-meta-real-do-ladder.md).

Cada episódio é um JSON de partida (formato kaggle_environments). Os decks
completos dos dois jogadores aparecem em steps[0][0]['visualize'][0]['action']
(duas listas de 60 Card IDs), já que essa é a visualização com informação
revelada, diferente da Observation real de cada agente.

Uso:
    python scripts/extract_real_decks.py --episodes-dir /caminho/com/jsons --out-dir data/decks
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))

from cg.api import all_card_data  # noqa: E402


def extract_decks(episodes_dir: Path) -> list[dict]:
    cards = {c.cardId: c for c in all_card_data()}
    decks = []
    for path in sorted(episodes_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            step0 = data["steps"][0][0]
            raw_decks = step0["visualize"][0]["action"]
            rewards = data["rewards"]
            names = data["info"]["TeamNames"]
        except (KeyError, IndexError, json.JSONDecodeError):
            continue
        for i, deck in enumerate(raw_decks):
            counts = Counter(deck)
            top_pokemon = [
                cards[cid].name
                for cid, _ in counts.most_common(20)
                if cards.get(cid) and cards[cid].cardType == 0
            ][:3]
            decks.append(
                {
                    "file": path.name,
                    "team": names[i],
                    "won": rewards[i] == 1,
                    "archetype": tuple(top_pokemon),
                    "deck": deck,
                }
            )
    return decks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes-dir", required=True, type=Path)
    parser.add_argument("--out-dir", default=ROOT / "data" / "decks", type=Path)
    parser.add_argument("--prefix", default="real_")
    args = parser.parse_args()

    decks = extract_decks(args.episodes_dir)
    print(f"{len(decks)} decks extraídos de {args.episodes_dir}")

    by_archetype: dict[tuple, list[dict]] = {}
    for d in decks:
        by_archetype.setdefault(d["archetype"], []).append(d)

    print(f"{len(by_archetype)} arquétipos distintos (por assinatura de Pokémon):")
    for archetype, group in sorted(by_archetype.items(), key=lambda t: -len(t[1])):
        wins = sum(1 for d in group if d["won"])
        print(f"  {len(group):3}x  winrate={wins}/{len(group)}  {archetype}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for archetype, group in by_archetype.items():
        winner = next((d for d in group if d["won"]), group[0])
        slug = "_".join(w.lower().replace("'", "").replace(" ", "-") for w in archetype[:2]) or "unknown"
        out_path = args.out_dir / f"{args.prefix}{slug}.csv"
        out_path.write_text("\n".join(str(x) for x in winner["deck"]) + "\n")
        print(f"salvo: {out_path}")


if __name__ == "__main__":
    main()
