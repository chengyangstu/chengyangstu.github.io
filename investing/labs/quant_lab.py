"""Chapter 44: synthetic returns, lagged signals, drift and per-notional costs.

Run: python quant_lab.py
No market data or investment recommendation. Returns have no calendar frequency.
Assumes period-start fills after the preceding period's signal is available.
"""
from math import ceil, isclose, isfinite
from statistics import mean, stdev

DATA = [(0.04, -0.02), (-0.01, 0.03), (0.02, 0.01), (0.01, -0.04),
        (-0.03, 0.02), (0.02, 0.02), (0.01, -0.01), (-0.02, 0.01)]


def backtest(data, fee=0.001):
    if not data or not isfinite(fee) or not 0 <= fee < 1:
        raise ValueError("Need data and a finite nonnegative fee below 1.")
    if any(len(row) != 2 or any(not isfinite(r) or r < -1 for r in row)
           for row in data):
        raise ValueError("Each row needs two finite simple returns >= -1.")
    nav, peak, max_drawdown = 1.0, 1.0, 0.0
    drifted, rows = (0.0, 0.0), []
    # ponytail: teaching fill model; real research needs borrowing, volume and timing data.
    for t, returns in enumerate(data):
        if t == 0 or data[t - 1][0] == data[t - 1][1]:
            weights = (0.0, 0.0)
        else:
            direction = 1 if data[t - 1][0] > data[t - 1][1] else -1
            weights = (0.5 * direction, -0.5 * direction)
        turnover = sum(abs(w - old) for w, old in zip(weights, drifted))
        net_return = sum(w * r for w, r in zip(weights, returns)) - fee * turnover
        if net_return <= -1 or not isfinite(net_return):
            raise ValueError("Account insolvent or numerical overflow: stop the simulation.")
        nav *= 1 + net_return
        if not isfinite(nav):
            raise ValueError("Net asset value overflow.")
        drifted = tuple(w * (1 + r) / (1 + net_return)
                        for w, r in zip(weights, returns))
        peak = max(peak, nav)
        max_drawdown = max(max_drawdown, 1 - nav / peak)
        rows.append((t + 1, weights, turnover, net_return, nav))
    exit_cost = fee * sum(abs(w) for w in drifted)
    if exit_cost >= 1:
        raise ValueError("Final liquidation exhausts account equity.")
    nav *= 1 - exit_cost
    max_drawdown = max(max_drawdown, 1 - nav / peak)
    return rows, nav, max_drawdown


def empirical_tail(losses, alpha=0.9):
    """Empirical quantile and quantile-integral ES, including fractional tail mass."""
    if not losses or not 0 < alpha < 1 or not all(map(isfinite, losses)):
        raise ValueError("Need finite losses and 0 < alpha < 1.")
    ordered = sorted(losses)
    n = len(ordered)
    var = ordered[ceil(alpha * n) - 1]
    es = sum(x * max(0, (i + 1) / n - max(alpha, i / n))
             for i, x in enumerate(ordered)) / (1 - alpha)
    return var, es


def demo():
    rows, nav, drawdown = backtest(DATA)
    assert rows[0][1] == (0.0, 0.0) and isclose(rows[1][3], -0.021)
    assert isclose(backtest([(0.04, -0.02), (-0.01, 0.03)], 0)[1], 0.98)
    assert isclose(backtest([(0.04, -0.02), (-0.01, 0.03)])[1], 0.97799)
    assert backtest(DATA, 0)[1] > nav > backtest(DATA, 0.003)[1]
    var, es = empirical_tail([0, 0, 1, 1, 2, 2, 3, 4, 8, 20])
    assert var == 8 and isclose(es, 20)
    assert isclose(empirical_tail([0, 10], 0.25)[1], 20 / 3)
    for bad in [[], [(float("nan"), 0)], [(-2, 0)]]:
        try:
            backtest(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid data accepted")
    for period, weights, turnover, net_return, value in rows:
        print(f"{period}: w={weights}, turnover={turnover:.4f}, "
              f"return={net_return:.3%}, NAV={value:.6f}")
    excess = [r[3] for r in rows]  # Zero cash/financing rate in this teaching model.
    sample_sharpe = mean(excess) / stdev(excess) if stdev(excess) else None
    print(f"After final exit: return={nav - 1:.3%}, max drawdown={drawdown:.3%}")
    print(f"Per-period sample Sharpe before exit={sample_sharpe:.4f}; NOT annualized.")
    print(f"Tail example: 90% VaR={var}, ES={es:.2f}. PASS: hand-worked checks.")


if __name__ == "__main__":
    demo()
