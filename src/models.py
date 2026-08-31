"""Markov chain, demand forecasting, and risk models."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

RISK_STATES = ["prime", "near_prime", "subprime"]
STATE_INDEX = {s: i for i, s in enumerate(RISK_STATES)}


def estimate_markov_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calibrate risk transition matrix using repayment performance mix.

    Cross-sectional data lacks sequential states, so we anchor transitions to
    industry benchmarks and adjust row probabilities toward observed risk mix.
    """
    observed_mix = df["risk_category"].value_counts(normalize=True).reindex(RISK_STATES, fill_value=0)

    # Benchmark transition matrix (rows: from, cols: to)
    base = np.array(
        [
            [0.78, 0.18, 0.04],  # prime
            [0.22, 0.58, 0.20],  # near_prime
            [0.08, 0.27, 0.65],  # subprime
        ]
    )

    # Nudge transitions using default proxy rates within each risk bucket
    for i, state in enumerate(RISK_STATES):
        bucket = df[df["risk_category"] == state]
        if len(bucket) == 0:
            continue
        default_rate = bucket["default_proxy"].mean()
        base[i, 2] = np.clip(base[i, 2] + 0.5 * default_rate, 0.02, 0.75)
        base[i, 0] = np.clip(base[i, 0] - 0.25 * default_rate, 0.05, 0.9)
        base[i] = base[i] / base[i].sum()

    matrix = pd.DataFrame(base, index=RISK_STATES, columns=RISK_STATES)
    matrix.attrs["observed_mix"] = observed_mix
    return matrix


def steady_state_distribution(transition_matrix: pd.DataFrame) -> pd.Series:
    """Compute stationary distribution of Markov chain."""
    eigvals, eigvecs = np.linalg.eig(transition_matrix.T.values)
    idx = np.argmin(np.abs(eigvals - 1))
    vec = np.real(eigvecs[:, idx])
    vec = np.abs(vec)
    return pd.Series(vec / vec.sum(), index=transition_matrix.index)


def fit_uptake_model(df: pd.DataFrame) -> dict:
    """Train logistic model for P(customer accepts another limit increase)."""
    features = [
        "initial_loan",
        "days_since_last_loan",
        "on_time_payment_pct",
    ]
    X = df[features].copy()
    y = df["took_increases"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_train_s, y_train)

    train_acc = model.score(X_train_s, y_train)
    test_acc = model.score(X_test_s, y_test)

    probs = model.predict_proba(scaler.transform(X))[:, 1]
    return {
        "model": model,
        "scaler": scaler,
        "features": features,
        "train_accuracy": train_acc,
        "test_accuracy": test_acc,
        "uptake_probability": pd.Series(probs, index=df.index),
    }


def macro_uptake_adjustment(
    base_prob: pd.Series, scenario: dict, baseline: dict | None = None
) -> pd.Series:
    """Adjust uptake probabilities for macroeconomic stress."""
    baseline = baseline or {"inflation": 4.1, "unemployment": 3.6, "interest_rate": 5.0}
    stress = (
        (scenario["inflation"] / baseline["inflation"])
        + (scenario["unemployment"] / baseline["unemployment"])
        + (scenario["interest_rate"] / baseline["interest_rate"])
    ) / 3.0
    multiplier = np.clip(1.15 - 0.15 * stress, 0.7, 1.1)
    return np.clip(base_prob * multiplier, 0.01, 0.99)


def repayment_outcome_probs(risk: str, on_time_pct: float) -> dict[str, float]:
    """Conditional repayment outcome distribution after accepting an increase."""
    base = {
        "prime": {"early": 0.18, "on_time": 0.79, "default": 0.03},
        "near_prime": {"early": 0.10, "on_time": 0.75, "default": 0.15},
        "subprime": {"early": 0.05, "on_time": 0.55, "default": 0.40},
    }[risk]
    bonus = (on_time_pct - 80) / 100
    early = np.clip(base["early"] + 0.1 * bonus, 0.01, 0.5)
    default = np.clip(base["default"] - 0.12 * bonus, 0.01, 0.6)
    on_time = max(1 - early - default, 0.01)
    total = early + on_time + default
    return {
        "early": early / total,
        "on_time": on_time / total,
        "default": default / total,
    }


def expected_incremental_profit(row: pd.Series, uptake_p: float, discount_days: int = 30) -> float:
    """Expected NPV of offering one additional limit increase."""
    from data_loader import DISCOUNT_RATE_DAILY, PROFIT_PER_INCREASE

    outcomes = repayment_outcome_probs(str(row["risk_category"]), row["on_time_payment_pct"])
    gross = (
        (outcomes["early"] + outcomes["on_time"]) * PROFIT_PER_INCREASE
        - outcomes["default"] * row["loss_given_default"]
    )
    discount = (1 + DISCOUNT_RATE_DAILY) ** discount_days
    return uptake_p * gross / discount
