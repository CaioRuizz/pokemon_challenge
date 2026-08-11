import os

import policy_baseline
import policy_heuristic
from fallback import safe_selection

_POLICIES = [policy_heuristic.choose, policy_baseline.choose]


def read_deck_csv() -> list[int]:
    file_path = "deck.csv"
    if not os.path.exists(file_path):
        file_path = "/kaggle_simulations/agent/" + file_path
    with open(file_path) as f:
        lines = f.read().split("\n")
    return [int(lines[i]) for i in range(60)]


def agent(obs_dict: dict) -> list[int]:
    select = obs_dict.get("select")
    if select is None:
        return read_deck_csv()

    for choose in _POLICIES:
        try:
            return choose(obs_dict)
        except Exception:
            continue

    options = select.get("option", [])
    return safe_selection(select.get("minCount", 0), select.get("maxCount", 0), len(options))
