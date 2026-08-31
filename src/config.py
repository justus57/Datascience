"""Configuration and assumptions for loan limit optimization."""

PROFIT_PER_INCREASE = 40.0
DISCOUNT_RATE_ANNUAL = 0.19
DISCOUNT_RATE_DAILY = (1 + DISCOUNT_RATE_ANNUAL) ** (1 / 365) - 1
MAX_INCREASES_PER_YEAR = 6
ELIGIBILITY_DAYS = 60
MIN_ON_TIME_PCT = 70.0
CAPITAL_EXPOSURE_LIMIT = 85_000_000  # total portfolio exposure cap ($)
AVG_TERM_EXTENSION_DAYS = 45

# 2023 macro scenarios (base, adverse, favorable)
MACRO_SCENARIOS = {
    "base": {"inflation": 4.1, "unemployment": 3.6, "interest_rate": 5.0},
    "adverse": {"inflation": 6.5, "unemployment": 5.5, "interest_rate": 6.5},
    "favorable": {"inflation": 2.5, "unemployment": 3.0, "interest_rate": 4.0},
}

# Default loss rates by risk tier (fraction of exposure)
DEFAULT_LOSS_RATE = {
    "prime": 0.08,
    "near_prime": 0.18,
    "subprime": 0.35,
}

# Repayment outcome probabilities by risk tier: (early, on_time, default)
REPAYMENT_PROBS = {
    "prime": (0.18, 0.79, 0.03),
    "near_prime": (0.10, 0.78, 0.12),
    "subprime": (0.05, 0.62, 0.33),
}

RISK_BINS = [0, 80, 90, 100.01]
RISK_LABELS = ["subprime", "near_prime", "prime"]
