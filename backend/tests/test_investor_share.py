"""Unit tests for proportional investor share calculation."""


def _calc_shares(amounts: list[float]) -> list[float]:
    """Mirror of recalculate_active_investor_shares rounding logic."""
    total = sum(amounts)
    running = 0.0
    result = []
    for i, amount in enumerate(amounts):
        if i == len(amounts) - 1:
            result.append(round(100.0 - running, 2))
        else:
            pct = round(amount / total * 100, 2)
            result.append(pct)
            running += pct
    return result


def test_shares_sum_to_100():
    pcts = _calc_shares([2_000_000, 1_750_000, 1_250_000])
    assert sum(pcts) == 100.0
    assert pcts[0] == 40.0
    assert pcts[1] == 35.0
    assert pcts[2] == 25.0


def test_single_investor_gets_100_percent():
    assert _calc_shares([5_000_000]) == [100.0]
