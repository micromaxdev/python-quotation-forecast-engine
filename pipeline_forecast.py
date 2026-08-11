"""
pipeline_forecast.py
--------------------
Module for active pipeline forecasting: applying logistic regression win probability weighting
and computing expected won value for open sales opportunities.

INTERN WORKSPACE:
Each function in this module is a PURE FUNCTION:
  - Input: a pandas DataFrame (plus optional model parameters)
  - Output: a NEW modified pandas DataFrame with calculated forecast metrics
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional


# Default logistic regression coefficients for feature weighting
DEFAULT_COEFFICIENTS = {
    "intercept": 0.5,
    "Tier 1": 1.2,
    "Tier 2": 0.5,
    "Tier 3": -0.2,
    "age_penalty_per_day": -0.015
}


def load_model_coefficients() -> Dict[str, float]:
    """Retrieve default logistic regression feature weights."""
    return DEFAULT_COEFFICIENTS.copy()


# =============================================================================
# STEP 5: WIN PROBABILITY CALCULATION (INTERN STEP 5)
# =============================================================================

def calculate_win_probability(
    df: pd.DataFrame, 
    coefficients: Optional[Dict[str, float]] = None
) -> pd.DataFrame:
    """
    Step 5: Compute deal win probabilities using a Logistic Regression (Sigmoid) formula.

    Formula:
      z = intercept + tier_weight + (age_penalty * deal_age_days)
      win_probability = 1 / (1 + e^(-z))

    Goal:
      Add a new column named 'win_probability' containing values between 0.00 and 1.00 (rounded to 4 decimal places).

    Test with: `python workbench.py 5`
    """
    df = df.copy()
    if coefficients is None:
        coefficients = load_model_coefficients()

    # INTERN TODO: Calculate win probability below
    # Hint:
    # 1. Start z with coefficients['intercept']
    # 2. Add customer tier weight based on df['customer_tier']
    # 3. Add (df['deal_age_days'] * coefficients['age_penalty_per_day'])
    # 4. Compute prob = 1 / (1 + np.exp(-z))
    # 5. df['win_probability'] = prob.round(4)

    def compute_p(row):
        z = coefficients.get("intercept", 0.5)
        tier = row.get("customer_tier", "Tier 3")
        z += coefficients.get(tier, 0.0)
        age = row.get("deal_age_days", 0)
        z += age * coefficients.get("age_penalty_per_day", -0.015)
        prob = 1.0 / (1.0 + np.exp(-z))
        return round(float(prob), 4)

    df["win_probability"] = df.apply(compute_p, axis=1)

    return df


# =============================================================================
# STEP 6: EXPECTED WON VALUE CALCULATION (INTERN STEP 6)
# =============================================================================

def calculate_expected_won_value(
    df: pd.DataFrame,
    probability_col: str = "win_probability",
    quote_val_col: str = "quote_value"
) -> pd.DataFrame:
    """
    Step 6: Compute the Expected Won Value for active pipeline deals.

    Formula:
      Expected Won Value = Quote Value * Win Probability

    Goal:
      Add a new column named 'expected_won_value' rounded to 2 decimal places.

    Test with: `python workbench.py 6`
    """
    df = df.copy()

    # INTERN TODO: Multiply quote value by win probability below
    # Hint: df['expected_won_value'] = (df[quote_val_col] * df[probability_col]).round(2)
    if quote_val_col in df.columns and probability_col in df.columns:
        df["expected_won_value"] = (df[quote_val_col] * df[probability_col]).round(2)
    else:
        df["expected_won_value"] = 0.0

    return df


# =============================================================================
# FULL PIPELINE FORECAST MODEL (PRE-BUILT FOR INTERN)
# =============================================================================

def run_pipeline_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """Master orchestrator for active pipeline probability weighting."""
    # Filter for active Open quotes (case-insensitive)
    if "status" in df.columns:
        open_quotes = df[df["status"].astype(str).str.upper() == "OPEN"].copy()
    else:
        open_quotes = df.copy()
    
    df_prob = calculate_win_probability(open_quotes)
    df_forecast = calculate_expected_won_value(df_prob)
    return df_forecast
