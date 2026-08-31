"""Run full loan limit optimization analysis and export results."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from data_loader import MACRO_SCENARIOS, prepare_features, load_data
from models import estimate_markov_matrix, fit_uptake_model, steady_state_distribution
from optimization import build_optimization_problem, compare_policies, macro_sensitivity

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "report" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def save_fig(name: str):
    plt.tight_layout()
    plt.savefig(FIG_DIR / name, dpi=150, bbox_inches="tight")
    plt.close()


def main():
    sns.set_theme(style="whitegrid")
    df = prepare_features(load_data())

    # EDA plots
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    sns.histplot(df["increases_2023"], bins=6, ax=axes[0, 0])
    axes[0, 0].set_title("Distribution of Limit Increases in 2023")
    sns.boxplot(data=df, x="risk_category", y="total_profit", ax=axes[0, 1])
    axes[0, 1].set_title("Profit by Risk Category")
    sns.scatterplot(
        data=df.sample(3000, random_state=42),
        x="on_time_payment_pct",
        y="increases_2023",
        hue="risk_category",
        alpha=0.4,
        ax=axes[1, 0],
    )
    axes[1, 0].set_title("Repayment Performance vs Increases")
    sns.barplot(
        data=df.groupby("risk_category", observed=True)["eligible"].mean().reset_index(),
        x="risk_category",
        y="eligible",
        ax=axes[1, 1],
    )
    axes[1, 1].set_title("Eligibility Rate by Risk Tier")
    save_fig("eda_overview.png")

    # Markov chain
    markov = estimate_markov_matrix(df)
    steady = steady_state_distribution(markov)
    markov.to_csv(ROOT / "report" / "markov_transition_matrix.csv")
    steady.to_csv(ROOT / "report" / "markov_steady_state.csv")

    plt.figure(figsize=(6, 5))
    sns.heatmap(markov, annot=True, fmt=".2f", cmap="Blues")
    plt.title("Estimated Risk-State Transition Matrix")
    save_fig("markov_transitions.png")

    # Uptake model
    uptake = fit_uptake_model(df)
    df["uptake_probability"] = uptake["uptake_probability"]
    df["expected_profit"] = df.apply(
        lambda r: __import__("models").expected_incremental_profit(r, r["uptake_probability"]),
        axis=1,
    )

    # Optimization
    capital_budget = df.loc[df["eligible"], "exposure"].sum() * 0.35
    opt = build_optimization_problem(df, df["uptake_probability"], capital_budget=capital_budget, top_n=15000)
    opt["scored_customers"].to_csv(ROOT / "report" / "optimization_scores.csv", index=False)

    selected = set(opt["selected_ids"])
    df["optimized_offer"] = df["customer_id"].isin(selected).astype(int)

    # Policy comparison
    policy_results = compare_policies(df, df["uptake_probability"])
    policy_results.to_csv(ROOT / "report" / "policy_comparison.csv", index=False)

    plt.figure(figsize=(8, 5))
    sns.barplot(data=policy_results, x="policy", y="mean_profit", palette="viridis")
    plt.title("Simulated Mean Portfolio Profit by Policy (4 periods)")
    plt.ylabel("Mean Profit ($)")
    save_fig("policy_comparison.png")

    # Macro sensitivity
    macro_results = macro_sensitivity(df, df["uptake_probability"], MACRO_SCENARIOS, capital_budget)
    macro_results.to_csv(ROOT / "report" / "macro_sensitivity.csv", index=False)

    plt.figure(figsize=(8, 5))
    sns.barplot(data=macro_results, x="scenario", y="expected_profit", palette="magma")
    plt.title("Optimized Expected Profit by Macroeconomic Scenario")
    plt.ylabel("Expected Profit ($)")
    save_fig("macro_sensitivity.png")

    # Summary export
    summary = {
        "n_customers": len(df),
        "eligible_pct": df["eligible"].mean(),
        "markov_steady_prime": steady["prime"],
        "markov_steady_near_prime": steady["near_prime"],
        "markov_steady_subprime": steady["subprime"],
        "uptake_model_test_accuracy": uptake["test_accuracy"],
        "optimized_n_selected": opt["n_selected"],
        "optimized_expected_profit": opt["expected_profit"],
        "optimized_total_exposure": opt["total_exposure"],
        "capital_budget": capital_budget,
    }
    pd.Series(summary).to_csv(ROOT / "report" / "analysis_summary.csv")

    print("Analysis complete.")
    print(pd.Series(summary).to_string())
    return df, markov, uptake, opt, policy_results, macro_results


if __name__ == "__main__":
    main()
