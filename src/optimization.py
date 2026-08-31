"""Portfolio optimization and Monte Carlo simulation."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pulp

from data_loader import INCREASE_AMOUNT, MAX_INCREASES_PER_YEAR
from models import expected_incremental_profit, macro_uptake_adjustment, repayment_outcome_probs


def build_optimization_problem(
    df: pd.DataFrame,
    uptake_probs: pd.Series,
    capital_budget: float,
    top_n: int | None = 8000,
    use_milp: bool = False,
) -> dict:
    """
    Select customers for the next limit-increase offer under a capital budget.

    Default: greedy knapsack heuristic (fast at portfolio scale).
    Optional MILP via PuLP for smaller candidate sets.
    """
    work = df.copy()
    work["uptake_p"] = uptake_probs.values
    work["ev_profit"] = work.apply(
        lambda r: expected_incremental_profit(r, r["uptake_p"]), axis=1
    )
    work["incremental_exposure"] = work["exposure"] + INCREASE_AMOUNT
    work = work.sort_values("ev_profit", ascending=False)
    if top_n:
        work = work.head(top_n)

    eligible_mask = work["eligible"].astype(bool)
    candidates = work[eligible_mask].copy()
    candidates["score"] = candidates["ev_profit"] / candidates["incremental_exposure"].clip(lower=1)

    if use_milp and len(candidates) <= 3000:
        return _solve_milp(candidates, capital_budget)

    selected_idx = []
    used_capital = 0.0
    for idx, row in candidates.sort_values("score", ascending=False).iterrows():
        if row["ev_profit"] <= 0:
            continue
        if used_capital + row["incremental_exposure"] > capital_budget:
            continue
        selected_idx.append(idx)
        used_capital += row["incremental_exposure"]

    selected = work.loc[selected_idx] if selected_idx else candidates.iloc[0:0]
    return {
        "selected_ids": selected["customer_id"].tolist(),
        "n_selected": len(selected),
        "expected_profit": selected["ev_profit"].sum() if len(selected) else 0.0,
        "total_exposure": selected["incremental_exposure"].sum() if len(selected) else 0.0,
        "capital_budget": capital_budget,
        "status": "GreedyOptimal",
        "scored_customers": work,
    }


def _solve_milp(candidates: pd.DataFrame, capital_budget: float) -> dict:
    """Solve binary knapsack with PuLP for smaller candidate pools."""
    ev = candidates["ev_profit"].values
    exposure = candidates["incremental_exposure"].values
    ids = candidates["customer_id"].tolist()

    prob = pulp.LpProblem("LoanLimitOptimization", pulp.LpMaximize)
    x = pulp.LpVariable.dicts("offer", range(len(candidates)), cat="Binary")
    prob += pulp.lpSum(x[i] * ev[i] for i in range(len(candidates)))
    prob += pulp.lpSum(x[i] * exposure[i] for i in range(len(candidates))) <= capital_budget
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    selected = [ids[i] for i in range(len(candidates)) if pulp.value(x[i]) == 1]
    return {
        "selected_ids": selected,
        "n_selected": len(selected),
        "expected_profit": pulp.value(prob.objective),
        "total_exposure": sum(exposure[i] for i in range(len(candidates)) if pulp.value(x[i]) == 1),
        "capital_budget": capital_budget,
        "status": pulp.LpStatus[prob.status],
        "scored_customers": candidates,
    }


def simulate_lifecycle(
    df: pd.DataFrame,
    uptake_probs: pd.Series,
    offer_policy: str = "optimized",
    n_periods: int = 4,
    n_simulations: int = 200,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Monte Carlo simulation of multi-period limit increase decisions.

    Policies:
    - conservative: offer only to prime with on_time >= 92
    - aggressive: offer to all eligible
    - optimized: offer if expected incremental profit > 0
    """
    rng = np.random.default_rng(random_state)
    results = []

    sample = df.sample(min(500, len(df)), random_state=random_state).copy()
    sample["uptake_p"] = uptake_probs.loc[sample.index].values
    sample["ev_profit"] = sample.apply(
        lambda r: expected_incremental_profit(r, r["uptake_p"]), axis=1
    )

    for sim in range(n_simulations):
        total_profit = 0.0
        total_defaults = 0
        total_offers = 0

        for row in sample.itertuples():
            increases = int(row.increases_2023)
            risk = str(row.risk_category)
            on_time = row.on_time_payment_pct
            uptake_p = row.uptake_p
            loss = row.loss_given_default

            for _period in range(n_periods):
                if increases >= MAX_INCREASES_PER_YEAR:
                    break

                eligible = row.days_since_last_loan >= 60 and on_time >= 70 and increases < MAX_INCREASES_PER_YEAR
                if not eligible:
                    continue

                if offer_policy == "aggressive":
                    offer = True
                elif offer_policy == "conservative":
                    offer = risk == "prime" and on_time >= 92
                else:
                    offer = row.ev_profit > 0

                if not offer:
                    continue

                total_offers += 1
                if rng.random() < uptake_p:
                    outcomes = repayment_outcome_probs(risk, on_time)
                    draw = rng.choice(
                        ["early", "on_time", "default"],
                        p=[outcomes["early"], outcomes["on_time"], outcomes["default"]],
                    )
                    increases += 1
                    if draw == "default":
                        total_defaults += 1
                        total_profit -= loss
                    else:
                        total_profit += 40

        results.append(
            {
                "simulation": sim,
                "policy": offer_policy,
                "total_profit": total_profit,
                "total_defaults": total_defaults,
                "total_offers": total_offers,
            }
        )

    return pd.DataFrame(results)


def compare_policies(df: pd.DataFrame, uptake_probs: pd.Series) -> pd.DataFrame:
    """Run lifecycle simulation for all policies."""
    frames = []
    for policy in ["conservative", "aggressive", "optimized"]:
        sim = simulate_lifecycle(df, uptake_probs, offer_policy=policy)
        frames.append(sim)
    out = pd.concat(frames, ignore_index=True)
    return (
        out.groupby("policy")
        .agg(
            mean_profit=("total_profit", "mean"),
            std_profit=("total_profit", "std"),
            mean_defaults=("total_defaults", "mean"),
            mean_offers=("total_offers", "mean"),
        )
        .reset_index()
    )


def macro_sensitivity(
    df: pd.DataFrame,
    base_uptake: pd.Series,
    scenarios: dict,
    capital_budget: float,
) -> pd.DataFrame:
    """Evaluate optimization outcomes under macro scenarios."""
    rows = []
    for name, macro in scenarios.items():
        adj = macro_uptake_adjustment(base_uptake, macro)
        opt = build_optimization_problem(df, adj, capital_budget=capital_budget, top_n=8000)
        rows.append(
            {
                "scenario": name,
                "expected_profit": opt["expected_profit"],
                "n_selected": opt["n_selected"],
                "total_exposure": opt["total_exposure"],
                "avg_uptake": adj.mean(),
            }
        )
    return pd.DataFrame(rows)
