"""Load and prepare loan limit increase dataset."""

from pathlib import Path

import numpy as np
import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "loan_limit_increases.csv"

# Assessment parameters
PROFIT_PER_INCREASE = 40.0
DISCOUNT_RATE_ANNUAL = 0.19
DISCOUNT_RATE_DAILY = (1 + DISCOUNT_RATE_ANNUAL) ** (1 / 365) - 1
MAX_INCREASES_PER_YEAR = 6
MIN_DAYS_ELIGIBILITY = 60
MIN_ON_TIME_PCT = 70.0
INCREASE_AMOUNT = 300  # assumed standard offer when not specified in data
CAPITAL_RATIO = 0.15  # regulatory capital as fraction of exposure

# 2023 macro scenarios for sensitivity analysis
MACRO_SCENARIOS = {
    "baseline": {"inflation": 4.1, "unemployment": 3.6, "interest_rate": 5.0},
    "adverse": {"inflation": 6.5, "unemployment": 5.5, "interest_rate": 6.5},
    "favorable": {"inflation": 2.5, "unemployment": 3.0, "interest_rate": 4.0},
}


def load_data(path: Path | None = None) -> pd.DataFrame:
    """Load customer snapshot data."""
    path = path or DATA_PATH
    df = pd.read_csv(path)
    return df.astype(
        {
            "customer_id": int,
            "initial_loan": int,
            "days_since_last_loan": int,
            "on_time_payment_pct": float,
            "increases_2023": int,
            "total_profit": int,
        }
    )


def assign_risk_category(on_time_pct: pd.Series) -> pd.Series:
    """Map repayment performance to risk tiers."""
    return pd.cut(
        on_time_pct,
        bins=[-np.inf, 80, 90, np.inf],
        labels=["subprime", "near_prime", "prime"],
    )


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer model features from raw customer records."""
    out = df.copy()
    out["risk_category"] = assign_risk_category(out["on_time_payment_pct"])
    out["eligible"] = (
        (out["days_since_last_loan"] >= MIN_DAYS_ELIGIBILITY)
        & (out["on_time_payment_pct"] >= MIN_ON_TIME_PCT)
        & (out["increases_2023"] < MAX_INCREASES_PER_YEAR)
    )
    out["remaining_increase_slots"] = MAX_INCREASES_PER_YEAR - out["increases_2023"]
    out["exposure"] = out["initial_loan"] + out["increases_2023"] * INCREASE_AMOUNT
    out["capital_required"] = out["exposure"] * CAPITAL_RATIO
    out["took_increases"] = (out["increases_2023"] > 0).astype(int)
    out["profit_per_increase_observed"] = np.where(
        out["increases_2023"] > 0,
        out["total_profit"] / out["increases_2023"],
        0.0,
    )
    out["default_proxy"] = (
        (out["increases_2023"] > 0)
        & (out["total_profit"] < out["increases_2023"] * PROFIT_PER_INCREASE)
    ).astype(int)

    risk_default = {"prime": 0.03, "near_prime": 0.12, "subprime": 0.35}
    out["default_prob"] = out["risk_category"].map(risk_default)
    out["loss_given_default"] = out["exposure"] * np.where(
        out["risk_category"] == "prime",
        0.15,
        np.where(out["risk_category"] == "near_prime", 0.35, 0.55),
    )
    return out
