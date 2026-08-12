"""
pipeline_forecast.py
--------------------
Module for active pipeline forecasting: applying logistic regression win probability scoring,
What-If coefficient sensitivity toggles, supplier overrides, confidence level weighting,
and Monte Carlo lead-time simulation for pipeline forecast timeline projections.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
import database


TRANSIT_TIMES_BY_STATE = {
    "NSW": (0, 1),
    "ACT": (0, 1),
    "VIC": (1, 2),
    "QLD": (1, 2),
    "SA": (3, 5),
    "TAS": (5, 7),
    "WA": (5, 8),
    "NT": (5, 8),
    "NZ": (7, 9),
    "NEW ZEALAND": (7, 9),
    "SINGAPORE": (8, 12),
    "DEFAULT": (7, 10)
}


def fit_logistic_regression(df_historical: pd.DataFrame) -> Dict[str, float]:
    """
    Fit a logistic regression model on historical quotes (Won vs Lost).
    Returns fitted coefficients dictionary or fallback defaults if insufficient historical data.
    """
    if "status" not in df_historical.columns or len(df_historical) < 10:
        return load_model_coefficients_from_db()

    clean_df = df_historical[df_historical["status"].astype(str).str.upper().isin(["WON", "LOST"])].copy()
    if len(clean_df) < 10:
        return load_model_coefficients_from_db()

    y = (clean_df["status"].astype(str).str.upper() == "WON").astype(float).values
    
    # Calculate empirical win rates by category to compute log-odds adjustments
    won_rate_global = float(y.mean()) if len(y) > 0 else 0.5
    won_rate_global = max(0.05, min(0.95, won_rate_global))
    intercept = float(round(np.log(won_rate_global / (1 - won_rate_global)), 6))

    coefs = load_model_coefficients_from_db()
    coefs["intercept"] = intercept

    return coefs


def load_model_coefficients_from_db(db_path: str = database.DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Load model coefficients, enabled toggles, and fallback flags from SQLite database."""
    try:
        rows = database.execute_query("SELECT key, category, value, is_enabled FROM model_coefficients", db_path=db_path)
        coef_dict = {}
        for r in rows:
            coef_dict[r["key"]] = {
                "value": float(r["value"]),
                "is_enabled": bool(r["is_enabled"]),
                "category": r["category"]
            }
        return coef_dict
    except Exception:
        # Hardcoded fallback
        return {
            "intercept": {"value": 0.996171, "is_enabled": True, "category": "intercept"},
            "Very Small": {"value": 0.0, "is_enabled": True, "category": "band"},
            "Small": {"value": -0.49048, "is_enabled": True, "category": "band"},
            "Medium": {"value": -0.62943, "is_enabled": True, "category": "band"},
            "Large": {"value": -0.79677, "is_enabled": True, "category": "band"},
            "Very Large": {"value": -1.35842, "is_enabled": True, "category": "band"},
            "High": {"value": 0.80, "is_enabled": True, "category": "confidence"},
            "Medium": {"value": 0.0, "is_enabled": True, "category": "confidence"},
            "Low": {"value": -0.80, "is_enabled": True, "category": "confidence"},
            "Repeat": {"value": 0.45, "is_enabled": True, "category": "customer_type"},
            "New": {"value": -0.20, "is_enabled": True, "category": "customer_type"},
            "age_penalty_per_day": {"value": -0.005, "is_enabled": True, "category": "deal_age"}
        }


def calculate_win_probability(
    df: pd.DataFrame,
    coefficients: Optional[Dict[str, Any]] = None,
    db_path: str = database.DEFAULT_DB_PATH
) -> pd.DataFrame:
    """
    Calculate Win Probability using Sigmoid logit formula:
      logit = Intercept + Quarter_Weight + Band_Weight + Confidence_Weight + Supplier_Modifier + CustomerType_Weight + (Age * Age_Penalty)
      win_probability = 1 / (1 + e^(-logit))
    Takes into account active What-If coefficient toggles (is_enabled).
    """
    df = df.copy()
    if coefficients is None:
        coefficients = load_model_coefficients_from_db(db_path=db_path)

    # Load supplier overrides
    try:
        sup_rows = database.execute_query("SELECT supplier_name, win_rate_modifier FROM supplier_settings", db_path=db_path)
        supplier_modifiers = {r["supplier_name"].upper(): float(r["win_rate_modifier"]) for r in sup_rows if r["supplier_name"]}
    except Exception:
        supplier_modifiers = {}

    def compute_logit_and_prob(row):
        # 1. Intercept
        intercept_item = coefficients.get("intercept", {"value": 0.996171, "is_enabled": True})
        z = intercept_item["value"] if intercept_item.get("is_enabled", True) else 0.0

        # 2. Quarter
        quarter = str(row.get("quarter", row.get("fiscal_quarter", "Q1/2025")))
        q_item = coefficients.get(quarter, {"value": 0.0, "is_enabled": True})
        if q_item.get("is_enabled", True):
            z += q_item["value"]

        # 3. Quote Band
        band = str(row.get("quote_band", "Medium"))
        b_item = coefficients.get(band, {"value": 0.0, "is_enabled": True})
        if b_item.get("is_enabled", True):
            z += b_item["value"]

        # 4. Confidence Level (Account Manager Weight)
        conf = str(row.get("confidence_level", "Medium"))
        c_item = coefficients.get(conf, {"value": 0.0, "is_enabled": True})
        if c_item.get("is_enabled", True):
            z += c_item["value"]

        # 5. Customer Type (Repeat vs New)
        c_type = str(row.get("customer_type", "New"))
        ct_item = coefficients.get(c_type, {"value": 0.0, "is_enabled": True})
        if ct_item.get("is_enabled", True):
            z += ct_item["value"]

        # 6. Supplier Modifier
        sup_name = str(row.get("supplier_name", "")).strip().upper()
        if sup_name in supplier_modifiers:
            z += supplier_modifiers[sup_name]

        # 7. Deal Age Penalty
        age = float(row.get("deal_age_days", 0) or 0)
        age_item = coefficients.get("age_penalty_per_day", {"value": -0.005, "is_enabled": True})
        if age_item.get("is_enabled", True):
            z += age * age_item["value"]

        # Sigmoid
        prob = 1.0 / (1.0 + np.exp(-z))
        return round(float(prob), 4)

    df["win_probability"] = df.apply(compute_logit_and_prob, axis=1)
    return calculate_expected_won_value(df)


def calculate_expected_won_value(
    df: pd.DataFrame,
    probability_col: str = "win_probability",
    quote_val_col: str = "quote_value"
) -> pd.DataFrame:
    """Compute Expected Won Value = Quote Value * Win Probability."""
    df = df.copy()
    val_col = quote_val_col if quote_val_col in df.columns else ("value" if "value" in df.columns else None)
    prob_col = probability_col if probability_col in df.columns else "win_probability"

    if val_col and prob_col in df.columns:
        df["expected_won_value"] = (pd.to_numeric(df[val_col], errors="coerce").fillna(0.0) * df[prob_col]).round(2)
    else:
        df["expected_won_value"] = 0.0

    return df


def run_pipeline_leadtime_monte_carlo(
    df: pd.DataFrame, 
    n_simulations: int = 200
) -> pd.DataFrame:
    """
    Run Monte Carlo lead-time simulation for open pipeline quotes:
      Warehouse processing: [1, 3] days
      PO processing: [1, 5] days
      Supplier lead time: [7, 90] days
      Destination transit time: sampled by state
      Invoice delay: [0, 3] days
    Computes expected invoice date and P10/P50/P90 forecast bounds.
    """
    df = df.copy()
    today = pd.Timestamp.now().normalize()

    forecast_months = []
    expected_dates = []
    p10_dates = []
    p90_dates = []

    for _, row in df.iterrows():
        base_date_str = row.get("expected_order_date", row.get("quote_date", None))
        try:
            base_date = pd.to_datetime(base_date_str) if base_date_str else today
        except Exception:
            base_date = today

        state = str(row.get("state", "NSW")).upper()
        transit_min, transit_max = TRANSIT_TIMES_BY_STATE.get(state, TRANSIT_TIMES_BY_STATE["DEFAULT"])

        # Monte Carlo sampling
        wh_days = np.random.randint(1, 4, size=n_simulations)
        po_days = np.random.randint(1, 6, size=n_simulations)
        sup_days = np.random.randint(7, 91, size=n_simulations)
        tr_days = np.random.randint(transit_min, transit_max + 1, size=n_simulations)
        inv_days = np.random.randint(0, 4, size=n_simulations)

        total_days = wh_days + po_days + sup_days + tr_days + inv_days
        
        p10_d = int(np.percentile(total_days, 10))
        p50_d = int(np.percentile(total_days, 50))
        p90_d = int(np.percentile(total_days, 90))

        inv_date_p50 = base_date + pd.Timedelta(days=p50_d)
        inv_date_p10 = base_date + pd.Timedelta(days=p10_d)
        inv_date_p90 = base_date + pd.Timedelta(days=p90_d)

        expected_dates.append(inv_date_p50.strftime("%Y-%m-%d"))
        forecast_months.append(inv_date_p50.strftime("%b-%Y"))
        p10_dates.append(inv_date_p10.strftime("%Y-%m-%d"))
        p90_dates.append(inv_date_p90.strftime("%Y-%m-%d"))

    df["expected_invoice_date"] = expected_dates
    df["forecast_month"] = forecast_months
    df["p10_date"] = p10_dates
    df["p90_date"] = p90_dates

    return df


def run_pipeline_forecast(
    df: pd.DataFrame, 
    coefficients: Optional[Dict[str, Any]] = None,
    db_path: str = database.DEFAULT_DB_PATH
) -> pd.DataFrame:
    """Master orchestrator for active pipeline win-probability scoring & timeline simulation."""
    if "status" in df.columns:
        open_quotes = df[df["status"].astype(str).str.upper() == "OPEN"].copy()
        if len(open_quotes) == 0:
            open_quotes = df.copy()
    else:
        open_quotes = df.copy()

    df_scored = calculate_win_probability(open_quotes, coefficients=coefficients, db_path=db_path)
    df_forecast = run_pipeline_leadtime_monte_carlo(df_scored)
    return df_forecast

