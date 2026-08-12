"""
backlog_forecast.py
-------------------
Module for committed order backlog forecasting: PO-matching logic, destination state transit time
lookups, lead time chain arithmetic, and payment offset date calculations.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
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
    "SINGAPORE": (8, 12),
    "DEFAULT": (7, 10)
}

DEFAULT_PAYMENT_TERMS_DAYS = 30


def check_po_matching(
    df: pd.DataFrame, 
    db_path: str = database.DEFAULT_DB_PATH
) -> pd.DataFrame:
    """
    Match backlog part codes against open Purchase Orders table.
    Determines match_status ('Matching PO' vs 'No Matching PO') and PO status.
    """
    df = df.copy()
    try:
        po_df = database.load_table_as_df("purchase_orders", db_path)
        if len(po_df) > 0 and "part_code" in po_df.columns:
            po_parts = set(po_df["part_code"].dropna().astype(str).str.upper())
            df["match_status"] = df["part_code"].apply(
                lambda p: "Matching PO" if str(p).strip().upper() in po_parts else "No Matching PO"
            )
        else:
            df["match_status"] = "Matching PO"
    except Exception:
        df["match_status"] = "Matching PO"

    return df


def calculate_backlog_delivery_and_invoice_dates(
    df: pd.DataFrame,
    payment_terms_days: int = DEFAULT_PAYMENT_TERMS_DAYS
) -> pd.DataFrame:
    """
    Calculate expected delivery date and expected invoice date for backlog sales orders:
      Expected Delivery Date = max(due_date, today + lead_time + transit_time)
      Expected Invoice Date = Expected Delivery Date + Payment Terms (e.g. Net 30)
    """
    df = df.copy()
    today = pd.Timestamp.now().normalize()

    delivery_dates = []
    invoice_dates = []
    forecast_months = []

    for _, row in df.iterrows():
        due_str = row.get("due_date", row.get("order_date", None))
        try:
            due_dt = pd.to_datetime(due_str) if due_str else today + pd.Timedelta(days=14)
        except Exception:
            due_dt = today + pd.Timedelta(days=14)

        lead_days = int(row.get("lead_time_days", 14) or 14)
        state = str(row.get("state", "NSW")).upper()
        tr_min, tr_max = TRANSIT_TIMES_BY_STATE.get(state, TRANSIT_TIMES_BY_STATE["DEFAULT"])
        transit_days = int(np.mean([tr_min, tr_max]))

        est_deliv = today + pd.Timedelta(days=lead_days + transit_days)
        actual_deliv = max(due_dt, est_deliv)

        inv_dt = actual_deliv + pd.Timedelta(days=payment_terms_days)

        delivery_dates.append(actual_deliv.strftime("%Y-%m-%d"))
        invoice_dates.append(inv_dt.strftime("%Y-%m-%d"))
        forecast_months.append(inv_dt.strftime("%b-%Y"))

    df["expected_delivery_date"] = delivery_dates
    df["expected_invoice_date"] = invoice_dates
    df["forecast_month"] = forecast_months
    df["win_probability"] = 1.0  # Backlog is 100% committed

    val_col = "order_value" if "order_value" in df.columns else ("value" if "value" in df.columns else None)
    if val_col in df.columns:
        df["expected_won_value"] = pd.to_numeric(df[val_col], errors="coerce").fillna(0.0)
    else:
        df["expected_won_value"] = 0.0

    return df


def calculate_expected_delivery_date(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate expected delivery date for backlog items."""
    return calculate_backlog_delivery_and_invoice_dates(df)


def calculate_expected_invoice_date(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate expected invoice date for backlog items."""
    return calculate_backlog_delivery_and_invoice_dates(df)


def run_backlog_forecast(
    df: pd.DataFrame, 
    db_path: str = database.DEFAULT_DB_PATH
) -> pd.DataFrame:
    """Master orchestrator for committed backlog delivery & invoicing schedule projections."""
    df_matched = check_po_matching(df, db_path=db_path)
    df_forecast = calculate_backlog_delivery_and_invoice_dates(df_matched)
    return df_forecast

