# Loan Limit Increase Optimization

This project models a loan limit increase strategy using a data-driven optimization framework. It combines customer-level eligibility, risk-state transition modeling, uptake forecasting, and constrained portfolio optimization to identify which customers should receive limit increases under a capital budget.

## Business objective

The goal is to maximize expected profit while controlling exposure and default risk. The project evaluates:

- borrower eligibility rules
- risk migration across prime / near-prime / subprime states
- expected uptake probability by customer
- optimized offer selection under a capital budget
- macroeconomic sensitivity of the portfolio strategy

## Project structure

- `data/loan_limit_increases.csv` — input customer dataset
- `src/` — Python source code for data processing, modeling, and optimization
- `report/` — generated CSV outputs and visualizations
- `notebooks/loan_limit_optimization.ipynb` — interactive analysis notebook
- `requirements.txt` — Python dependencies

## Setup

1. Create and activate a virtual environment (optional but recommended):

```bash
python -m venv .venv
. .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate  # Windows PowerShell
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the analysis:

```bash
cd src
python run_analysis.py
```

This generates several output files in the `report/` folder, including:

- `analysis_summary.csv`
- `markov_transition_matrix.csv`
- `markov_steady_state.csv`
- `optimization_scores.csv`
- `policy_comparison.csv`
- `macro_sensitivity.csv`
- PNG figures in `report/figures/`

## Core model components

The analysis includes:

- risk transition estimation using a Markov chain
- uptake prediction using a statistical model
- expected incremental profit calculation
- portfolio optimization using a knapsack-style constrained selection approach
- simulations comparing policy alternatives and macro scenarios

## Key output

The project evaluates an optimized offer policy against conservative and aggressive alternatives, producing a final recommendation based on expected profit and risk-adjusted portfolio performance.

## Repository

- GitHub: https://github.com/justus57/Datascience.git

## License

This project is intended for analysis and educational use. Check with the repository owner before reusing it in production or commercial contexts.
