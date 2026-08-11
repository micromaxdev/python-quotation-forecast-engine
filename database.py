"""
database.py
-----------
Module for SQLite database interactions, schema initialization, and data persistence 
for the Sales Forecasting Engine.
"""

import sqlite3
import pandas as pd
from typing import Optional

DEFAULT_DB_PATH = "dev_database.db"


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """
    Establish a connection to the local SQLite database.

    Args:
        db_path (str): File path to the SQLite database.

    Returns:
        sqlite3.Connection: SQLite connection object.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Create initial database schema tables (quotes, backlog, forecast_results) if they do not exist,
    and seed realistic mock data if tables are empty.

    Args:
        db_path (str): File path to the SQLite database.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Drop legacy tables if schema needs upgrade
    cursor.execute("DROP TABLE IF EXISTS quotes")
    cursor.execute("DROP TABLE IF EXISTS backlog")
    cursor.execute("DROP TABLE IF EXISTS forecast_results")

    # 1. Quotes Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            quote_id TEXT PRIMARY KEY,
            customer TEXT,
            quote_value REAL,
            status TEXT,
            close_date TEXT,
            customer_tier TEXT,
            deal_age_days INTEGER
        )
    """)

    # 2. Backlog Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backlog (
            order_id TEXT PRIMARY KEY,
            customer TEXT,
            order_value REAL,
            order_date TEXT,
            product_category TEXT,
            lead_time_days INTEGER
        )
    """)

    # 3. Forecast Results Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecast_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT,
            forecast_type TEXT,
            expected_value REAL,
            expected_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    # Seed initial mock data if quotes has fewer than 3 rows
    cursor.execute("SELECT COUNT(*) FROM quotes")
    if cursor.fetchone()[0] < 3:
        seed_mock_data(conn)

    conn.close()


def seed_mock_data(conn: sqlite3.Connection) -> None:
    """Seed sample data for quotes and backlog into SQLite."""
    cursor = conn.cursor()

    cursor.execute("DELETE FROM quotes")
    cursor.execute("DELETE FROM backlog")

    quotes_data = [
        ("Q-1001", "Acme Corp", 8500.0, "Open", "2026-09-15", "Tier 1", 25),
        ("Q-1002", "Beta Tech", 45000.0, "Open", "2026-10-01", "Tier 2", 40),
        ("Q-1003", "Gamma Global", 120000.0, "Open", "2026-11-20", "Tier 1", 60),
        ("Q-1004", "Delta Logistics", 7500.0, "Won", "2026-08-01", "Tier 3", 10),
        ("Q-1005", "Epsilon Systems", 65000.0, "Open", "2026-09-30", "Tier 2", 15),
        ("Q-1006", "Zeta Solutions", 3500.0, "Lost", "2026-07-10", "Tier 3", 90),
        ("Q-1007", "Eta Holdings", 95000.0, "Open", "2026-12-15", "Tier 1", 30),
    ]

    cursor.executemany("""
        INSERT INTO quotes (quote_id, customer, quote_value, status, close_date, customer_tier, deal_age_days)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, quotes_data)

    backlog_data = [
        ("ORD-501", "Acme Corp", 50000.0, "2026-08-01", "Hardware", 14),
        ("ORD-502", "Gamma Global", 180000.0, "2026-08-05", "Enterprise Software", 30),
        ("ORD-503", "Omega Retail", 25000.0, "2026-08-10", "Consulting", 7),
        ("ORD-504", "Apex Manufacturing", 95000.0, "2026-07-28", "Hardware", 21),
    ]

    cursor.executemany("""
        INSERT INTO backlog (order_id, customer, order_value, order_date, product_category, lead_time_days)
        VALUES (?, ?, ?, ?, ?, ?)
    """, backlog_data)

    conn.commit()


def load_quotes_from_db(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Read quotation dataset from SQLite into pandas DataFrame."""
    conn = get_connection(db_path)
    df = pd.read_sql_query("SELECT * FROM quotes", conn)
    conn.close()
    return df


def load_backlog_from_db(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Read order backlog dataset from SQLite into pandas DataFrame."""
    conn = get_connection(db_path)
    df = pd.read_sql_query("SELECT * FROM backlog", conn)
    conn.close()
    return df


def save_forecast_to_db(
    df: pd.DataFrame, 
    table_name: str = "forecast_results", 
    db_path: str = DEFAULT_DB_PATH,
    if_exists: str = "append"
) -> None:
    """Write or append calculated forecast results DataFrame to SQLite database."""
    conn = get_connection(db_path)
    df.to_sql(table_name, con=conn, if_exists=if_exists, index=False)
    conn.close()


def save_step_output_to_db(
    df: pd.DataFrame,
    step_name: str,
    db_path: str = DEFAULT_DB_PATH
) -> None:
    """Save an intermediate step DataFrame to SQLite so it can be viewed on the web visualizer."""
    table_name = f"step_{step_name}"
    conn = get_connection(db_path)
    df.to_sql(table_name, con=conn, if_exists="replace", index=False)
    conn.close()
