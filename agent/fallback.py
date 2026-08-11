def safe_selection(min_count: int, max_count: int, n_options: int, ranked_indices: list[int] | None = None) -> list[int]:
    """Guaranteed-legal selection: length in [min_count, max_count], indices in
    range(n_options), no duplicates. Prefers ranked_indices (in order) when given.
    """
    if n_options <= 0:
        return []

    max_count = max(0, min(max_count, n_options))
    min_count = max(0, min(min_count, max_count))
    ranked_indices = [i for i in (ranked_indices or []) if 0 <= i < n_options]

    target = max(min_count, min(len(ranked_indices), max_count)) if ranked_indices else min_count

    chosen: list[int] = []
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
