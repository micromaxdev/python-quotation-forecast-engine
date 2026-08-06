"""
database.py
-----------
Module for SQLite database interactions, schema initialization, and data persistence 
for the Sales Forecasting Engine.
"""

import sqlite3
from typing import Optional
import pandas as pd

DEFAULT_DB_PATH = "dev_database.db"


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """
    Establish a connection to the local SQLite database.

    Args:
        db_path (str): File path to the SQLite database.

    Returns:
        sqlite3.Connection: SQLite connection object.
    """
    # TODO (Junior Dev): Return sqlite3.connect(db_path)
    pass


def initialize_database(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Create initial database schema tables (quotes, backlog, forecast_results) if they do not exist.

    Args:
        db_path (str): File path to the SQLite database.
    """
    # TODO (Junior Dev): Execute CREATE TABLE IF NOT EXISTS queries for:
    # 1. quotes (quote_id, customer, quote_value, status, close_date, quote_band)
    # 2. backlog (order_id, customer, order_value, order_date, lead_time_days)
    # 3. forecast_results (id, entity_id, forecast_type, expected_value, expected_date)
    pass


def load_quotes_from_db(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    Read quotation dataset from the SQLite 'quotes' table into a pandas DataFrame.

    Args:
        db_path (str): File path to the SQLite database.

    Returns:
        pd.DataFrame: Quotation records.
    """
    # TODO (Junior Dev): Read from 'quotes' table using pd.read_sql_query
    pass


def load_backlog_from_db(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    Read order backlog dataset from the SQLite 'backlog' table into a pandas DataFrame.

    Args:
        db_path (str): File path to the SQLite database.

    Returns:
        pd.DataFrame: Backlog order records.
    """
    # TODO (Junior Dev): Read from 'backlog' table using pd.read_sql_query
    pass


def save_forecast_to_db(
    df: pd.DataFrame, 
    table_name: str = "forecast_results", 
    db_path: str = DEFAULT_DB_PATH
) -> None:
    """
    Write or append calculated forecast results DataFrame to SQLite database.

    Args:
        df (pd.DataFrame): Consolidated forecast results.
        table_name (str): Destination SQLite table name.
        db_path (str): File path to the SQLite database.
    """
    # TODO (Junior Dev): Save DataFrame using df.to_sql(table_name, con, if_exists='append', index=False)
    pass
