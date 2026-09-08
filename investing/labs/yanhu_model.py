"""Recompute the textbook's Yanhu case using the frozen source-traceable JSON.

Run: python yanhu_model.py yanhu.json
Facts are CNY yuan; model cash flows are CNY 100 million (亿元).
Scenario assumptions are educational, not management guidance or price forecasts.
"""
import json
from math import isclose, isfinite
from pathlib import Path
import sys


def scenario(s, assumptions, shares_100m):
    if assumptions["growth"] != 0 or assumptions["terminal_residual"] != 0:
        raise ValueError("This finite-life teaching model supports zero growth and zero residual only.")
    numbers = [v for v in s.values() if isinstance(v, (int, float))]
    numbers += [assumptions[k] for k in
                ("years", "tax_rate", "potash_parent_weight", "lithium_parent_weight")]
    if not all(isfinite(v) for v in numbers + [shares_100m]) or shares_100m <= 0:
        raise ValueError("Model inputs must be finite; share count must be positive.")
    years, rate = assumptions["years"], s["discount_rate"]
    if not isinstance(years, int) or not 1 <= years <= 200 or not 0 < rate <= 1:
        raise ValueError("Use 1-200 integer years and 0 < discount rate <= 1.")
    if not all(0 <= assumptions[k] <= 1 for k in
               ("tax_rate", "potash_parent_weight", "lithium_parent_weight")):
        raise ValueError("Tax and ownership weights must lie in [0, 1].")
    if any(s[k] < 0 for k in ("k_volume_10kt", "li_volume_10kt",
                              "k_price_cny_t", "k_cost_cny_t",
                              "li_price_10kcny_t", "li_cost_10kcny_t")):
        raise ValueError("Volumes, prices and unit costs cannot be negative.")
    k_ebit = s["k_volume_10kt"] * (s["k_price_cny_t"] - s["k_cost_cny_t"]) / 10000
    li_ebit = s["li_volume_10kt"] * (s["li_price_10kcny_t"] - s["li_cost_10kcny_t"])
    # ponytail: average economic weights; upgrade to legal-entity cash flows for precision.
    cash = (k_ebit * assumptions["potash_parent_weight"] +
            li_ebit * assumptions["lithium_parent_weight"]) * (1 - assumptions["tax_rate"])
    cash -= s["cash_deduction_100m"]
    factor = sum(1 / (1 + rate) ** year for year in range(1, years + 1))
    value = (cash * factor + s["extra_assets_100m"]) / shares_100m
    perpetual = (cash / rate + s["extra_assets_100m"]) / shares_100m
    if not all(map(isfinite, [cash, value, perpetual])):
        raise ValueError("Model result overflow.")
    return cash, value, perpetual, factor


def report(d):
    quote = d["quote"]
    shares = quote["shares"] / 1e8
    cap = quote["price_cny"] * shares
    current = d["interim_comparable"]["2026H1"]
    prior = d["interim_comparable"]["2025H1_restated"]
    balance = d["balance_2026H1"]
    print(f'{d["company"]} | frozen {quote["timestamp"]} | market cap {cap:.2f} 亿元')
    for key in ("revenue", "parent_profit", "adjusted_parent_profit", "cfo", "capex_cash"):
        print(f"{key}: {prior[key]/1e8:.2f} -> {current[key]/1e8:.2f} 亿元; "
              f"YoY {(current[key]/prior[key]-1):.2%}")
    fcf, old_fcf = current["cfo"] - current["capex_cash"], prior["cfo"] - prior["capex_cash"]
    print(f"CFO-capex proxy: {fcf/1e8:.2f} 亿元; YoY {fcf/old_fcf-1:.2%}")
    original = d["historical_original"]
    print(f"Original FY2025 revenue YoY: {original['2025']['revenue']/original['2024']['revenue']-1:.2%}")
    print(f"Original FY2025 parent profit YoY: {original['2025']['parent_profit']/original['2024']['parent_profit']-1:.2%}")
    print(f"Original FY2025 CFO-capex: {(original['2025']['cfo']-original['2025']['capex_cash'])/1e8:.2f} 亿元")
    print(f"PB: {cap/(balance['parent_equity']/1e8):.4f}; "
          f"old-basis FY2025 PE: {cap/(original['2025']['parent_profit']/1e8):.4f} (NOT comparable TTM)")
    print(f"Liabilities/assets: {balance['liabilities']/balance['assets']:.2%}; "
          f"current ratio: {balance['current_assets']/balance['current_liabilities']:.2f}")
    print(f"CFO/group profit: {current['cfo']/current['group_profit']:.4f}; "
          f"CFO/parent profit (mixed attribution): {current['cfo']/current['parent_profit']:.4f}")
    for period in ("2025_original", "2026H1"):
        product = d["products"][period]
        for name in ("potash", "lithium"):
            gross = product[name + "_revenue"] - product[name + "_cost"]
            print(f"{period} {name}: gross {gross/1e8:.2f} 亿元; margin {gross/product[name+'_revenue']:.2%}")
    gap = balance["cash_funds"] - balance["cash_equivalents"] - balance["excluded_cash_listed"]
    print(f"Unresolved cash-note difference: {gap:.2f} yuan. Do not fabricate a balancing item.")
    assumptions = d["model_assumptions"]
    for s in assumptions["scenarios"]:
        cash, value, perpetual, factor = scenario(s, assumptions, shares)
        implied = (cap - s["extra_assets_100m"]) / factor
        print(f"{s['name']}: FCFE={cash:.4f} 亿元, finite={value:.4f} yuan/share, "
              f"perpetual={perpetual:.4f}, price-implied FCFE={implied:.4f} 亿元")
    # Source accounting identities, not a claim that every disclosure has been reconciled.
    assert isclose(balance["assets"], balance["liabilities"] + balance["parent_equity"] +
                   balance["minority_equity"], abs_tol=0.02, rel_tol=0)
    assert isclose(current["group_profit"], current["parent_profit"] +
                   current["minority_profit"], abs_tol=0.02, rel_tol=0)
    assert isclose(current["cash_equivalents_change"], current["cfo"] +
                   current["investing_cashflow"] + current["financing_cashflow"] +
                   current["fx_effect"], abs_tol=0.02, rel_tol=0)
    assert isclose(sum(balance["excluded_components"].values()),
                   balance["excluded_cash_listed"], abs_tol=0.02, rel_tol=0)
    for tax in (d["tax"]["2025_original"], d["tax"]["2026H1"]):
        assert isclose(tax["total_tax"], tax["current_tax"] + tax["deferred_tax"],
                       abs_tol=0.02, rel_tol=0)
    # One-period, 10,000 tonnes x CNY 100/t = 0.01 亿元; hand-worked unit/discount check.
    sample = dict(assumptions["scenarios"][0], k_volume_10kt=1, k_price_cny_t=100,
                  k_cost_cny_t=0, li_volume_10kt=0, cash_deduction_100m=0,
                  extra_assets_100m=0, discount_rate=0.1)
    simple = dict(assumptions, years=1, tax_rate=0, potash_parent_weight=1)
    assert isclose(scenario(sample, simple, 1)[1], 0.01 / 1.1)
    print("PASS: accounting identities and hand-worked unit/discount check.")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parents[1] / "data/yanhu.json"
    try:
        report(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f"Cannot calculate: {error}\nUsage: python yanhu_model.py yanhu.json")
