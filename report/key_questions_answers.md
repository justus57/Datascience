# Key Questions — Loan Limit Increase Optimization

Answers based on analysis of **30,000 customer records** for 2023, using Markov risk modeling, uptake forecasting, constrained portfolio optimization, and Monte Carlo simulation.

---

## 1. What is the optimal loan limit increase strategy that balances profitability and risk?

**Offer selectively by expected value (EV), not by eligibility alone.**

The optimal strategy is:

1. **Enforce hard eligibility gates**
   - ≥60 days since last disbursement  
   - ≥70% on-time repayment rate  
   - Fewer than 6 increases in the current year  

2. **Score every eligible customer** on risk-adjusted expected profit:
   - Uptake probability × (expected repayment payoff − expected default loss)  
   - Discounted at **19% annual rate**  

3. **Rank and select** customers with positive EV, prioritizing highest EV per dollar of exposure, until the capital / exposure budget is exhausted.

4. **Prefer** prime and near-prime borrowers with strong repayment history and remaining increase capacity.

### Simulation evidence

| Policy | Mean Profit | Mean Defaults | Mean Offers |
|--------|-------------|----------------|-------------|
| **Optimized (EV-ranked)** | Highest | Moderate | Targeted |
| Conservative (prime-only, high on-time) | Lower | Lowest | Fewest |
| Aggressive (all eligible) | **Negative** | Highest | Most |

**Takeaway:** Mass offering destroys value through defaults. Conservative offering is safer but leaves profit on the table. The EV-ranked strategy maximizes profit while controlling risk.

---

## 2. What advanced operations research techniques best model this problem?

This is a **hybrid OR / ML problem**. The techniques that fit best:

| Technique | Role |
|-----------|------|
| **Markov chains** | Model dynamic credit eligibility — borrowers move between prime, near-prime, and subprime based on repayment performance |
| **Logistic regression (stochastic demand)** | Forecast probability that a customer accepts a limit increase |
| **Expected-value / knapsack optimization (MILP)** | Select which customers to offer under capital and exposure constraints |
| **Monte Carlo simulation** | Evaluate multi-period loan lifecycle outcomes under uncertainty |
| **Markov Decision Process (MDP) / RL** *(extension)* | Learn sequential offer-timing policies over a borrower’s lifetime |

### Why this combination works

- The problem is **stochastic** (uptake and repayment are random).  
- It is **dynamic** (risk state changes over time).  
- It is **constrained** (capital, annual increase caps, eligibility rules).  
- Pure heuristics (offer everyone / offer only prime) fail under simulation; constrained optimization with probabilistic scoring does not.

---

## 3. How does borrower behavior impact the optimal strategy?

Borrower behavior is the main driver of who should get an increase.

### Repayment patterns
- Higher on-time payment rates → higher uptake and lower default-weighted losses → higher EV → more likely to be offered.  
- Subprime borrowers (on-time &lt; 80%) carry much higher loss-given-default, so they rarely clear the EV &gt; 0 bar.

### Limit acceptance (uptake)
- Acceptance is modeled as a function of loan size, days since last loan, and on-time rate.  
- Customers who never took an increase historically are harder to predict; those with prior increases demonstrate demand capacity.

### Risk migration / churn
- Markov steady-state distribution (long-run mix without intervention):
  - Prime: **~11%**  
  - Near-prime: **~33%**  
  - Subprime: **~56%**  

Without performance-based limit management, the portfolio **drifts toward riskier states**. That supports:
- Tightening or freezing limits after missed payments  
- Rewarding early / on-time payers with measured increases  
- Treating limit increases as a retention and quality tool, not only a volume tool

### Practical impact on strategy
- **Do not** treat all eligible customers equally.  
- **Do** weight offers toward strong repayment behavior.  
- **Do** update risk tiers after each repayment outcome before the next offer cycle.

---

## 4. How do varying external economic conditions affect loan limit optimization?

External conditions (inflation, unemployment, interest rates) change **demand (uptake)** and, indirectly, **optimal offer volume**.

### Scenario results (relative pattern)

| Scenario | Effect on uptake | Effect on expected profit |
|----------|------------------|---------------------------|
| **Favorable** (lower inflation / unemployment / rates) | Higher | Highest |
| **Baseline** (2023-like macro) | Mid | Mid |
| **Adverse** (higher inflation / unemployment / rates) | Lower (~3–4 pp) | Lower (~5–7%) |

### Implications for optimization
- In **adverse** conditions: tighten capital budget, raise EV cutoffs, favor prime/near-prime only.  
- In **favorable** conditions: expand offers within capital limits; still avoid zero-EV customers.  
- Capital allocation should be **procyclical in risk control** — more conservative when macro stress rises.  
- Recalibrate uptake models monthly with current inflation, unemployment, and rate inputs.

---

## 5. What innovative strategies can enhance profitability while reducing default rates?

Beyond the core EV optimizer, these strategies can further improve the risk–return tradeoff:

### 1. Reinforcement learning / MDP
- Treat each customer as a sequential decision process: *offer / wait / freeze*.  
- Optimize lifetime value over many periods instead of a single offer decision.  
- Useful when timing (not only who) matters under the 60-day eligibility rule.

### 2. Dynamic increase sizing (not just yes/no)
- Offer smaller increases to near-prime, larger to prime.  
- Cap exposure growth for customers near default thresholds.  
- Improves capital efficiency vs. a flat $300 (or fixed) increase for everyone.

### 3. Behavioral nudges
- Message high on-time customers approaching the 60-day window about “next limit review.”  
- Tie small limit bumps to consecutive on-time payments (habit reinforcement).  
- Reduce churn among good customers without expanding high-risk exposure.

### 4. Real-time macro and risk overlays
- Auto-shrink campaign size when unemployment or rates spike.  
- Freeze new offers for customers who migrate into subprime mid-cycle.  
- Keep the Markov transition monitor as a portfolio early-warning dashboard.

### 5. Fair lending and governance controls
- Monitor approval rates and EV scores by protected / demographic segments (where legally required).  
- Document model assumptions, drift checks, and override rules for credit ops.

---

## Deliverables map

| Required deliverable | Location |
|----------------------|----------|
| Comprehensive report (methodology, assumptions, insights) | `report/loan_limit_optimization_report.md` |
| Mathematical formulation | Report §3 |
| Python notebook | `notebooks/loan_limit_optimization.ipynb` |
| Simulation results | `report/policy_comparison.csv`, `report/figures/policy_comparison.png` |
| Operational recommendations | Report §7 and this file §5 |

---

## Bottom-line recommendation

**Operationalize a monthly EV-ranked offer engine:**  
score eligible customers → optimize under capital → simulate / monitor defaults → adjust for macro conditions.  

This balances profitability and risk better than either aggressive volume growth or overly conservative prime-only rules.
