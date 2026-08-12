"""
data_prep.py
------------
Module for data ingestion, cleaning, normalization, quintile breakpoint calculation,
and feature mapping for the Sales Forecasting Engine.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import database


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize DataFrame column headers."""
    df = df.copy()
    df.columns = [
        str(col).strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")
        for col in df.columns
    ]
    return df


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Impute or drop rows with missing values in essential columns."""
    df = df.copy()
    
    # Ensure numeric quote_value
    val_col = "quote_value" if "quote_value" in df.columns else ("value" if "value" in df.columns else None)
    if val_col:
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce").fillna(0.0)
    
    # Impute missing textual fields
    if "customer_name" in df.columns:
        df["customer_name"] = df["customer_name"].fillna("Unknown Customer").astype(str)
    if "confidence_level" in df.columns:
        df["confidence_level"] = df["confidence_level"].fillna("Medium").astype(str)
    if "state" in df.columns:
        df["state"] = df["state"].fillna("NSW").astype(str)
    if "status" in df.columns:
        df["status"] = df["status"].fillna("Open").astype(str)

    return df


def classify_customer_type(df: pd.DataFrame, db_path: str = database.DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    Cross-reference customer_code / customer_name against the customers database table.
    Tag existing customers as 'Repeat' and unknown customers as 'New'.
    """
    df = df.copy()
    try:
        customers_df = database.load_table_as_df("customers", db_path)
        existing_codes = set(customers_df["customer_code"].dropna().astype(str).str.upper())
        existing_names = set(customers_df["customer_name"].dropna().astype(str).str.upper())

        def get_type(row):
            c_code = str(row.get("customer_code", "")).strip().upper()
            c_name = str(row.get("customer_name", "")).strip().upper()
            if (c_code and c_code in existing_codes) or (c_name and c_name in existing_names):
                return "Repeat"
            return str(row.get("customer_type", "New"))

        df["customer_type"] = df.apply(get_type, axis=1)
    except Exception as e:
        if "customer_type" not in df.columns:
            df["customer_type"] = "New"
            
    return df


def derive_quintiles_or_fallback(
    values: pd.Series, 
    fallback_thresholds: Optional[Dict[str, Tuple[float, float]]] = None
) -> Dict[str, Tuple[float, float]]:
    """
    Derive 5 quintile cut-point thresholds from historical quote values.
    If historical values are insufficient (< 10 non-zero rows), return spec fallback thresholds.
    """
    if fallback_thresholds is None:
        fallback_thresholds = {
            "Very Small": (0.0, 928.04),
            "Small": (928.04, 2209.0),
            "Medium": (2209.0, 4681.0),
            "Large": (4681.0, 10408.84),
            "Very Large": (10408.84, 99999999.0)
        }

    clean_vals = values.dropna()
    clean_vals = clean_vals[clean_vals > 0]

    if len(clean_vals) < 10:
        return fallback_thresholds

    try:
        q20, q40, q60, q80 = np.quantile(clean_vals, [0.2, 0.4, 0.6, 0.8])
        return {
            "Very Small": (0.0, float(round(q20, 2))),
            "Small": (float(round(q20, 2)), float(round(q40, 2))),
            "Medium": (float(round(q40, 2)), float(round(q60, 2))),
            "Large": (float(round(q60, 2)), float(round(q80, 2))),
            "Very Large": (float(round(q80, 2)), 99999999.0)
        }
    except Exception:
        return fallback_thresholds


def map_quote_bands(
    df: pd.DataFrame, 
    value_column: str = "quote_value",
    thresholds: Optional[Dict[str, Tuple[float, float]]] = None
) -> pd.DataFrame:
    """Categorize sales quotes into size bands using quintiles or baseline spec fallbacks."""
    df = df.copy()

    if thresholds is None:
        if value_column in df.columns:
            thresholds = derive_quintiles_or_fallback(df[value_column])
        else:
            thresholds = derive_quintiles_or_fallback(pd.Series([]))

    def classify_band(val):
        try:
            val = float(val)
        except (ValueError, TypeError):
            return "Small"

        for band, (min_v, max_v) in thresholds.items():
            if min_v <= val < max_v or (band == "Very Large" and val >= min_v):
                return band
        return "Very Large"

    if value_column in df.columns:
        df["quote_band"] = df[value_column].apply(classify_band)
    else:
        df["quote_band"] = "Medium"

    return df


def map_fiscal_quarters(df: pd.DataFrame, date_column: str = "quote_date") -> pd.DataFrame:
    """Map quote date to Fiscal Quarter string format (e.g. 'Q1/2025', 'Q3/2026')."""
    df = df.copy()
    
    col = date_column if date_column in df.columns else ("close_date" if "close_date" in df.columns else None)
    if col:
        dates = pd.to_datetime(df[col], errors="coerce")
        quarters = "Q" + dates.dt.quarter.fillna(1).astype(int).astype(str) + "/" + dates.dt.year.fillna(2025).astype(int).astype(str)
        df["quarter"] = quarters
        df["fiscal_quarter"] = quarters
    else:
        df["quarter"] = "Q1/2025"
        df["fiscal_quarter"] = "Q1/2025"

    return df


def calculate_quote_lifecycle_and_followup(df: pd.DataFrame, date_column: str = "quote_date") -> pd.DataFrame:
    """
    Calculate quote expiry date based on Quote Band shelf-life guidelines:
      - Very Small: +45 days
      - Small: +90 days
      - Medium: +150 days
      - Large: +210 days
      - Very Large: +330 days
    Determine Follow Up Status: 'Expired', 'Overdue', 'Due Today', or 'Not Due'.
    """
    df = df.copy()
    today = pd.Timestamp.now().normalize()
    
    col = date_column if date_column in df.columns else ("close_date" if "close_date" in df.columns else None)
    
    band_shelf_life = {
        "Very Small": 45,
        "Small": 90,
        "Medium": 150,
        "Large": 210,
        "Very Large": 330
    }

    if col:
        q_dates = pd.to_datetime(df[col], errors="coerce").fillna(today)
    else:
        q_dates = pd.Series([today] * len(df))

    bands = df["quote_band"] if "quote_band" in df.columns else pd.Series(["Medium"] * len(df))
    
    expiry_dates = []
    followup_statuses = []
    deal_ages = []

    for q_dt, band, last_fu in zip(q_dates, bands, df.get("last_follow_up_date", [None]*len(df))):
        days_add = band_shelf_life.get(band, 150)
        exp_dt = q_dt + pd.Timedelta(days=days_add)
        expiry_dates.append(exp_dt.strftime("%Y-%m-%d"))

        age = (today - q_dt).days
        deal_ages.append(max(0, age))

        if last_fu and pd.notna(last_fu):
            next_fu = pd.to_datetime(last_fu, errors="coerce") + pd.Timedelta(days=7)
        else:
            next_fu = q_dt + pd.Timedelta(days=7)

        if today > exp_dt:
            status = "Expired"
        elif today > next_fu:
            status = "Overdue"
        elif today == next_fu:
            status = "Due Today"
        else:
            status = "Not Due"
            
        followup_statuses.append(status)

    df["expiry_date"] = expiry_dates
    df["follow_up_status"] = followup_statuses
    df["deal_age_days"] = deal_ages

    return df


def prepare_dataset(df: pd.DataFrame, db_path: str = database.DEFAULT_DB_PATH) -> pd.DataFrame:
    """Master data prep orchestrator applying all standardization and feature derivation steps."""
    df = standardize_column_names(df)
    df = handle_missing_values(df)
    df = classify_customer_type(df, db_path=db_path)
    df = map_quote_bands(df)
    df = map_fiscal_quarters(df)
    df = calculate_quote_lifecycle_and_followup(df)
    return df

