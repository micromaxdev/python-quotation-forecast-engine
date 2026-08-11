"""
backlog_forecast.py
-------------------
Module for committed order backlog forecasting: datetime arithmetic for expected delivery 
and invoice recognition dates based on lead times and payment terms.

INTERN WORKSPACE:
Each function in this module is a PURE FUNCTION:
  - Input: a pandas DataFrame with order details
  - Output: a NEW modified pandas DataFrame with scheduled datetime metrics
"""

import pandas as pd


# Default payment term offset in days (Net 30)
DEFAULT_PAYMENT_TERMS_DAYS = 30


# =============================================================================
# STEP 7: EXPECTED DELIVERY DATE CALCULATION (INTERN STEP 7)
# =============================================================================

def calculate_expected_delivery_date(
    df: pd.DataFrame, 
    order_date_col: str = "order_date", 
    lead_time_col: str = "lead_time_days"
) -> pd.DataFrame:
    """
    Step 7: Perform datetime math to calculate expected delivery dates.

    Formula:
      Expected Delivery Date = Order Date + Lead Time (Days)

    Goal:
      - Convert order_date_col to pandas datetime: pd.to_datetime(df[order_date_col])
      - Add timedelta days: pd.to_timedelta(df[lead_time_col], unit='D')
      - Add a new column named 'expected_delivery_date' formatted as string "YYYY-MM-DD"

    Test with: `python workbench.py 7`
    """
    df = df.copy()

    # INTERN TODO: Calculate expected delivery date below
    # Hint:
    # order_dt = pd.to_datetime(df[order_date_col])
    # delivery_dt = order_dt + pd.to_timedelta(df[lead_time_col], unit='D')
    # df['expected_delivery_date'] = delivery_dt.dt.strftime('%Y-%m-%d')

    if order_date_col in df.columns and lead_time_col in df.columns:
        order_dt = pd.to_datetime(df[order_date_col], errors="coerce")
        lead_days = pd.to_timedelta(df[lead_time_col], unit="D")
        df["expected_delivery_date"] = (order_dt + lead_days).dt.strftime("%Y-%m-%d")
    else:
        df["expected_delivery_date"] = "N/A"

    return df


# =============================================================================
# STEP 8: EXPECTED INVOICE DATE CALCULATION (INTERN STEP 8)
# =============================================================================

def calculate_expected_invoice_date(
    df: pd.DataFrame, 
    delivery_date_col: str = "expected_delivery_date", 
    payment_terms_days: int = DEFAULT_PAYMENT_TERMS_DAYS
) -> pd.DataFrame:
    """
    Step 8: Perform datetime math to calculate expected cash flow / invoicing date.

    Formula:
      Expected Invoice Date = Expected Delivery Date + Payment Terms Offset (Days)

    Goal:
      - Convert delivery_date_col to pandas datetime
      - Add payment terms offset (e.g. 30 days): pd.Timedelta(days=payment_terms_days)
      - Add a new column named 'expected_invoice_date' formatted as string "YYYY-MM-DD"

    Test with: `python workbench.py 8`
    """
    df = df.copy()

    # INTERN TODO: Add payment terms offset to delivery date below
    # Hint:
    # deliv_dt = pd.to_datetime(df[delivery_date_col])
    # inv_dt = deliv_dt + pd.Timedelta(days=payment_terms_days)
    # df['expected_invoice_date'] = inv_dt.dt.strftime('%Y-%m-%d')

    if delivery_date_col in df.columns:
        deliv_dt = pd.to_datetime(df[delivery_date_col], errors="coerce")
        df["expected_invoice_date"] = (deliv_dt + pd.Timedelta(days=payment_terms_days)).dt.strftime("%Y-%m-%d")
    else:
        df["expected_invoice_date"] = "N/A"

    return df


# =============================================================================
# FULL BACKLOG FORECAST MODEL (PRE-BUILT FOR INTERN)
# =============================================================================

def run_backlog_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """Master orchestrator for backlog delivery and invoicing schedule projections."""
    df_deliv = calculate_expected_delivery_date(df)
    df_forecast = calculate_expected_invoice_date(df_deliv)
    return df_forecast
