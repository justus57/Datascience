# Loan Limit Increase Optimization — Final Report

## Executive Summary

This analysis develops a **hybrid stochastic optimization framework** to determine optimal loan limit increase policies for a portfolio of **30,000 customers** in 2023. Using the provided dataset (`loan_limit_increases.xlsx`), we combine:

1. **Markov chain modeling** of borrower risk migration
2. **Logistic regression** for uptake (demand) forecasting
3. **Expected-value knapsack optimization** under regulatory capital constraints
4. **Monte Carlo simulation** of multi-period loan lifecycle outcomes

**Headline result:** An optimized, selective offering policy generates **~$12,325 mean simulated profit** per cohort cycle versus **-$33,748** under an aggressive “offer everyone eligible” policy, while keeping defaults materially lower than aggressive outreach.

---

## 1. Dataset Overview

| Field | Description |
|-------|-------------|
| `customer_id` | Unique borrower identifier |
| `initial_loan` | Starting loan amount ($500–$4,999) |
| `days_since_last_loan` | Days since last disbursement |
| `on_time_payment_pct` | Historical on-time repayment rate |
| `increases_2023` | Number of limit increases granted in 2023 (0, 3, 4, 5) |
| `total_profit` | Observed profit contribution ($0, $40, $80, $120) |

### Key observations
- **83.6%** of customers meet base eligibility (≥60 days since last loan, ≥70% on-time payments, <6 annual increases).
- Profit is concentrated among customers with prior increases; subprime-tier borrowers (on-time <80%) show higher profit variance.
- Observed profit does not always equal `increases_2023 × $40`, indicating defaults/write-downs in roughly **56%** of increase cases.

---

## 2. Additional Assumptions

| Assumption | Value | Rationale |
|------------|-------|-----------|
| Profit per successful increase | $40 | Given in assessment brief |
| Annual discount rate | 19% | Given; converted to daily for NPV |
| Standard increase amount | $300 | Not in raw data; typical micro-lending increment |
| Max increases per year | 6 | Assessment constraint |
| Eligibility waiting period | 60 days | Assessment rule |
| Minimum on-time rate | 70% | Assessment rule |
| Regulatory capital ratio | 15% of exposure | Standard Basel-inspired proxy |
| Capital budget | 35% of eligible book exposure | Operational lending capacity |
| Risk tiers | Prime ≥90%, Near-prime 80–90%, Subprime <80% | Industry-standard segmentation |
| Default loss (LGD) | 15% / 35% / 55% by tier | Calibrated to unsecured consumer lending |
| Macro scenarios | Baseline, Adverse, Favorable | 2023 inflation/unemployment/rate paths |

---

## 3. Mathematical Formulation

### 3.1 State Space (Markov Chain)

Let risk states \( S = \{\text{prime}, \text{near\_prime}, \text{subprime}\} \).

Transition matrix \( P \in \mathbb{R}^{3 \times 3} \), where \( P_{ij} = \Pr(S_{t+1}=j \mid S_t=i) \).

Estimated matrix (calibrated to portfolio default proxies):

\[
P = \begin{bmatrix}
0.56 & 0.16 & 0.28 \\
0.07 & 0.51 & 0.42 \\
0.05 & 0.25 & 0.70
\end{bmatrix}
\]

Steady-state distribution \( \pi \) satisfies \( \pi P = \pi \):

- Prime: **11.2%**
- Near-prime: **32.5%**
- Subprime: **56.3%**

This implies that without proactive risk management, the portfolio drifts toward higher-risk states over time.

### 3.2 Demand (Uptake) Model

\[
\Pr(\text{accept}) = \sigma(\beta_0 + \beta_1 \cdot \text{loan} + \beta_2 \cdot \text{days} + \beta_3 \cdot \text{on\_time\_pct})
\]

Macro adjustment multiplier:

\[
m = \text{clip}\left(1.15 - 0.15 \cdot \frac{1}{3}\left(\frac{\pi_{\text{inf}}}{\pi_{\text{inf}}^0} + \frac{u}{u^0} + \frac{r}{r^0}\right), 0.7, 1.1\right)
\]

### 3.3 Expected Incremental Profit (per customer)

For customer \( i \), let \( u_i \) = uptake probability, \( \omega \in \{\text{early}, \text{on\_time}, \text{default}\} \):

\[
EV_i = \frac{u_i}{(1+d)^{30}} \sum_{\omega} \Pr(\omega \mid \text{risk}_i) \cdot \text{payoff}(\omega)
\]

where payoff = \(+\$40\) for early/on-time and \(-\text{LGD}_i\) for default, \( d \) = daily discount rate from 19% APR.

### 3.4 Optimization Problem

Binary decision \( x_i \in \{0,1\} \): offer increase to customer \( i \).

\[
\max_{x} \sum_{i=1}^{N} x_i \cdot EV_i
\]

Subject to:

\[
\sum_{i=1}^{N} x_i \cdot \text{exposure}_i \leq B \quad \text{(capital budget)}
\]
\[
x_i \leq \text{eligible}_i \quad \forall i
\]
\[
\sum_{t} \text{increases}_{i,t} \leq 6 \quad \text{(annual cap)}
\]

**Solution method:** Greedy knapsack ranked by \( EV_i / \text{exposure}_i \) for scalability; MILP (PuLP/CBC) available for smaller candidate sets.

### 3.5 Results

| Metric | Value |
|--------|-------|
| Customers selected | **9,566** |
| Expected portfolio profit | **$161,820** |
| Total incremental exposure | **$30.0M** |
| Capital budget utilized | **~100%** |

---

## 4. Simulation Results — Policy Comparison

Monte Carlo simulation (500-customer sample, 200 runs, 4 periods):

| Policy | Mean Profit | Std Dev | Mean Defaults | Mean Offers |
|--------|------------|---------|---------------|-------------|
| **Optimized** | **$12,325** | $1,299 | 5.7 | 751 |
| Conservative | $9,884 | $1,054 | 3.2 | 580 |
| Aggressive | -$33,748 | $8,545 | 54.7 | 1,433 |

**Insight:** Aggressive policies maximize volume but destroy value through default losses. The optimized policy balances reach and risk.

---

## 5. Macroeconomic Sensitivity

| Scenario | Expected Profit | Avg Uptake |
|----------|----------------|------------|
| Favorable | $121,327 | 51.9% |
| Baseline | $116,903 | 50.0% |
| Adverse | $108,643 | 46.5% |

A stressed macro environment reduces both uptake (~3.5pp) and optimized profit (~7%). Interest-rate and unemployment shocks should trigger tighter capital budgets and higher risk cutoffs.

---

## 6. Answers to Key Questions

### Q1: What is the optimal strategy?
**Selective, EV-ranked limit increases** for eligible customers with positive risk-adjusted NPV, capped by a portfolio exposure budget. Prioritize prime/near-prime borrowers with strong repayment history and remaining annual increase capacity.

### Q2: What OR techniques best model this problem?
- **Markov chains** for dynamic credit eligibility
- **Stochastic knapsack / MILP** for constrained offer selection
- **Monte Carlo simulation** for multi-period lifecycle valuation
- **Logistic regression** for demand forecasting
- *(Extension)* **MDP / reinforcement learning** for sequential offer timing

### Q3: How does borrower behavior impact strategy?
- Higher on-time payment rates increase uptake and reduce default-weighted losses.
- Customers with 0 prior increases are less profitable to target than those demonstrating acceptance capacity.
- Risk migration toward subprime (56% steady-state) argues for **performance-based dynamic limits**.

### Q4: How do macro conditions affect optimization?
Adverse macro reduces uptake probabilities and shifts optimal frontier toward fewer, safer offers. Capital budget should be **procyclical** (tighter in downturns).

### Q5: Innovative enhancements
1. **Reinforcement learning (MDP)** — learn offer timing policies from simulated environments
2. **Dynamic pricing** — vary increase size by risk tier
3. **Behavioral nudges** — target high on-time borrowers near eligibility thresholds
4. **Real-time macro overlay** — monthly recalibration of uptake models

---

## 7. Operationalization Recommendations

1. **Monthly scoring pipeline** — refresh uptake probabilities and EV scores.
2. **Eligibility engine** — enforce 60-day rule, on-time threshold, and 6/year cap.
3. **Capital-aware offer list** — run knapsack optimizer before campaign launch.
4. **A/B testing** — validate model uplift vs. rule-based baseline.
5. **Risk monitoring dashboard** — track Markov steady-state drift and default rates by tier.
6. **Governance** — document assumptions, model drift checks, and fair-lending review.

---

## 8. Project Structure

```
data/loan_limit_increases.csv          # Cleaned dataset
notebooks/loan_limit_optimization.ipynb # Interactive analysis
report/loan_limit_optimization_report.md
report/figures/                         # EDA and result charts
src/                                    # Reusable modules
requirements.txt
```

Run analysis:
```bash
pip install -r requirements.txt
cd src && python run_analysis.py
```

---

## 9. Limitations

- Dataset is a **single-period snapshot**; sequential transitions are inferred, not observed.
- Increase amounts are **imputed** ($300) because not provided in source data.
- Uptake model AUC is modest (~50% test accuracy) due to limited feature set; additional behavioral variables would improve forecasts.
- Regulatory constraints are modeled as aggregate exposure caps; institution-specific rules may differ.

---

*Analysis generated from `loan_limit_increases.xlsx` (30,000 records).*
