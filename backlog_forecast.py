"""
backlog_forecast.py
-------------------
Module for committed order backlog forecasting, executing datetime calculations for expected 
delivery and invoice dates based on operational lead times and payment terms.
"""

from typing import Dict, Optional
import pandas as pd


def get_lead_time_rules() -> Dict[str, int]:
    """
    Retrieve operational lead time rules (in days) categorized by product type or quote band.

    Returns:
        Dict[str, int]: Dictionary mapping product categories/quote bands to standard lead times (days).
    """
    # TODO (Junior Dev): Return lookup table for operational lead times by category
    pass


def calculate_expected_delivery_date(
    df: pd.DataFrame, 
    order_date_col: str = "order_date", 
    lead_time_col: str = "lead_time_days"
) -> pd.DataFrame:
    """
    Perform datetime arithmetic to calculate expected delivery date based on order date and lead times.
    
    Formula: Expected Delivery Date = Order Date + Operational Lead Time (Business/Calendar Days)

    Args:
        df (pd.DataFrame): Order backlog dataset containing order dates and lead time values.
        order_date_col (str): Column name containing the order date.
        lead_time_col (str): Column name containing lead time in days.

    Returns:
        pd.DataFrame: DataFrame enriched with an 'expected_delivery_date' column.
    """
    # TODO (Junior Dev): Perform pd.to_datetime parsing and apply pd.Timedelta / BusinessDay addition
    pass


def calculate_expected_invoice_date(
    df: pd.DataFrame, 
    delivery_date_col: str = "expected_delivery_date", 
    payment_terms_days: int = 30
) -> pd.DataFrame:
    """
    Perform datetime arithmetic to calculate expected revenue invoicing/recognition date based on delivery date.

    Formula: Expected Invoice Date = Expected Delivery Date + Payment Terms Offset

    Args:
        df (pd.DataFrame): Backlog DataFrame containing expected delivery dates.
        delivery_date_col (str): Column name for expected delivery date.
        payment_terms_days (int): Default payment terms offset in days (e.g., Net 30).

    Returns:
        pd.DataFrame: DataFrame enriched with an 'expected_invoice_date' column.
    """
    # TODO (Junior Dev): Add payment term offset days to delivery date to project cash flow timing
    pass


def run_backlog_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """
    Master backlog forecasting function orchestrating delivery and invoicing schedule projections.

    Args:
        df (pd.DataFrame): Prepared backlog data from data_prep module.

    Returns:
        pd.DataFrame: Backlog dataset containing expected delivery and invoice dates.
    """
    # Step 1: Apply lead time rules to determine delivery timeline
    # Step 2: Compute expected delivery dates
    # Step 3: Compute expected invoice / revenue recognition dates
    # Step 4: Return forecasted backlog dataset
    pass
