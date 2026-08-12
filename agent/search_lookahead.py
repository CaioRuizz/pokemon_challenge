"""Lookahead defensivo usando a API nativa de busca (search_begin/search_step,
ver vendor/cg/api.py e docs/11-loop-continuo.md, iteração 3).

Ideia: em vez de decidir RETREAT com uma regra estática sobre a energia já
anexada do oponente (3 tentativas, todas sem ganho comprovado — docs/08,
docs/11), simula de fato o próximo turno do oponente (incluindo o que ele
ainda pode jogar da mão) e verifica se o nosso ativo atual seria nocauteado.

A informação oculta do oponente (mão e resto do baralho) é prevista por
reamostragem das cartas dele já reveladas na própria partida (descarte,
board, energias/ferramentas anexadas) — não é uma predição exata, é a melhor
aproximação disponível sem trapacear.
"""
import random

from cg.api import search_begin, search_end, search_release, search_step, to_observation_class

_MAX_SIM_STEPS = 80
_FALLBACK_CARD_ID = 1  # Basic {G} Energy — usado só se nada foi revelado ainda.


def _revealed_opponent_card_ids(current: dict, opp_index: int) -> list[int]:
    opp = current["players"][opp_index]
    ids = [c["id"] for c in (opp.get("discard") or [])]
    mons = list(opp.get("bench") or [])
    active = opp.get("active") or []
    if active and active[0] is not None:
        mons.append(active[0])
    for mon in mons:
        ids.append(mon["id"])
        ids.extend(c["id"] for c in (mon.get("energyCards") or []))
        ids.extend(c["id"] for c in (mon.get("tools") or []))
    stadium = current.get("stadium") or []
    ids.extend(c["id"] for c in stadium)
    return ids


def _predicted_pool(current: dict, opp_index: int, count: int) -> list[int]:
    revealed = _revealed_opponent_card_ids(current, opp_index)
    if not revealed:
        return [_FALLBACK_CARD_ID] * count
    return [random.choice(revealed) for _ in range(count)]


def active_survives_next_turn(obs: dict, choose_fn, rollouts: int = 3) -> bool:
    """True se em NENHUMA das simulações o nosso ativo atual é nocauteado
    durante o resto desta jogada + o próximo turno completo do oponente.
    Usa choose_fn (mesma política real) como proxy de jogada para os dois
    lados dentro da busca — não sabemos a política real do oponente, mas é
    uma aproximação melhor que jogadas aleatórias."""
    current = obs.get("current")
    if current is None:
        return True
    your_index = current["yourIndex"]
    opp_index = 1 - your_index
    players = current["players"]
    your_active = (players[your_index].get("active") or [None])[0]
    if your_active is None:
        return True
    your_serial = your_active["serial"]

    for _ in range(rollouts):
        if not _one_rollout_kills_active(obs, choose_fn, your_index, your_serial):
            continue
        return False  # achou uma linha plausível que nos nocauteia — não é seguro ficar
    return True


def _one_rollout_kills_active(obs: dict, choose_fn, your_index: int, your_serial: int) -> bool:
    current = obs["current"]
    opp_index = 1 - your_index
    players = current["players"]

    your_deck_n = players[your_index]["deckCount"]
    your_prize_n = len(players[your_index]["prize"])
    opp_deck_n = players[opp_index]["deckCount"]
    opp_prize_n = len(players[opp_index]["prize"])
    opp_hand_n = players[opp_index]["handCount"]

    your_deck_pred = _predicted_pool(current, your_index, your_deck_n) if your_deck_n else []
    your_prize_pred = _predicted_pool(current, your_index, your_prize_n) if your_prize_n else []
    opp_deck_pred = _predicted_pool(current, opp_index, opp_deck_n) if opp_deck_n else [1]
    opp_prize_pred = _predicted_pool(current, opp_index, opp_prize_n) if opp_prize_n else []
    opp_hand_pred = _predicted_pool(current, opp_index, opp_hand_n) if opp_hand_n else [1]

    obs_dc = to_observation_class(obs)
    try:
        state = search_begin(
            obs_dc,
            your_deck=your_deck_pred,
            your_prize=your_prize_pred,
            opponent_deck=opp_deck_pred or [1],
            opponent_prize=opp_prize_pred,
            opponent_hand=opp_hand_pred or [1],
            opponent_active=[],
        )
    except Exception:
        return False  # não deu pra simular — não bloqueia a decisão normal

    sid = state.searchId
    try:
        turns_seen = {current["turn"], current["turn"] + 1}
        steps = 0
        s = state
        while steps < _MAX_SIM_STEPS:
            sim_obs = s.observation
            if sim_obs.current is None or sim_obs.current.result != -1:
                break
            if sim_obs.current.turn not in turns_seen:
                break  # já passamos do próximo turno do oponente

            sim_players = sim_obs.current.players
            if your_index < len(sim_players):
                sim_active = sim_players[your_index].active
                if not sim_active or sim_active[0] is None or sim_active[0].serial != your_serial:
                    return True  # nosso ativo de referência não está mais lá (trocado/nocauteado)
                if sim_active[0].hp <= 0:
                    return True

            opts = sim_obs.select.option if sim_obs.select else []
            if not opts:
                break
            choice = _safe_choice(sim_obs, choose_fn)
            s = search_step(sid, choice)
            steps += 1
        return False
    except Exception:
        return False
    finally:
        try:
            search_release(sid)
        except Exception:
            pass
        try:
            search_end()
        except Exception:
            pass


def _safe_choice(sim_observation, choose_fn) -> list[int]:
    from dataclasses import asdict

    obs_dict = asdict(sim_observation)
    try:
        choice = choose_fn(obs_dict)
        if isinstance(choice, list) and choice:
            return choice
    except Exception:
        pass
    return [0]
