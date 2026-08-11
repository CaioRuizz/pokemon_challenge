from cg.api import all_attack, all_card_data

_cards: dict[int, object] | None = None
_attacks: dict[int, object] | None = None


def get_card(card_id: int):
    global _cards
    if _cards is None:
        _cards = {c.cardId: c for c in all_card_data()}
    return _cards.get(card_id)


def get_attack(attack_id: int):
    global _attacks
    if _attacks is None:
        _attacks = {a.attackId: a for a in all_attack()}
    return _attacks.get(attack_id)
