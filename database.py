"""
database.py
-----------
Module for SQLite database interactions, schema initialization, multi-table CRUD operations,
and data persistence for the Sales Forecasting Engine.
"""

import os
import sqlite3
import pandas as pd
from typing import Optional, Dict, Any, List

DEFAULT_DB_PATH = "dev_database.db"


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Establish a connection to the local SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Create initial database schema tables if they do not exist,
    and seed datasets from CSV files if tables are empty.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Customers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_code TEXT PRIMARY KEY,
            customer_name TEXT,
            customer_currency TEXT DEFAULT 'AUD',
            sales_employee TEXT,
            payment_term TEXT DEFAULT 'Net 30',
            billing_address TEXT,
            shipping_address TEXT,
            creation_date TEXT,
            first_invoice_date TEXT,
            last_invoice_date TEXT
        )
    """)

    # 2. Suppliers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_code TEXT PRIMARY KEY,
            supplier_name TEXT,
            supplier_currency TEXT DEFAULT 'AUD',
            billing_address TEXT,
            creation_date TEXT,
            default_lead_time_days INTEGER DEFAULT 14
        )
    """)

    # 3. Supplier Settings / Overrides Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier_settings (
            supplier_name TEXT PRIMARY KEY,
            supplier_code TEXT,
            win_rate_modifier REAL DEFAULT 0.0,
            lead_time_offset_days INTEGER DEFAULT 0,
            po_processing_days INTEGER DEFAULT 3,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 4. Quotes Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            quote_id TEXT PRIMARY KEY,
            quote_ref_no TEXT,
            quote_date TEXT,
            customer_code TEXT,
            customer_name TEXT,
            customer_type TEXT DEFAULT 'New',
            state TEXT,
            account_manager TEXT,
            supplier_name TEXT,
            confidence_level TEXT DEFAULT 'Medium',
            quote_value REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Open',
            quote_band TEXT,
            expected_order_date TEXT,
            order_received_date TEXT,
            last_follow_up_date TEXT,
            expiry_date TEXT,
            follow_up_status TEXT DEFAULT 'Not Due',
            deal_age_days INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 5. Backlog Table (Sales Orders)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backlog (
            order_id TEXT PRIMARY KEY,
            so_number TEXT,
            customer_order_no TEXT,
            customer_code TEXT,
            customer_name TEXT,
            sales_employee TEXT,
            part_code TEXT,
            description TEXT,
            stock_qty REAL DEFAULT 0.0,
            outstanding_qty REAL DEFAULT 0.0,
            due_date TEXT,
            order_value REAL DEFAULT 0.0,
            state TEXT DEFAULT 'NSW',
            lead_time_days INTEGER DEFAULT 14,
            match_status TEXT DEFAULT 'Matching PO',
            expected_delivery_date TEXT,
            expected_invoice_date TEXT
        )
    """)

    # 6. Purchase Orders Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchase_orders (
            po_id TEXT PRIMARY KEY,
            part_code TEXT,
            po_qty REAL DEFAULT 0.0,
            po_due_date TEXT,
            supplier_name TEXT
        )
    """)

    # 7. Model Coefficients & What-If Toggles Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_coefficients (
            key TEXT PRIMARY KEY,
            category TEXT,
            value REAL,
            is_enabled INTEGER DEFAULT 1,
            is_fallback INTEGER DEFAULT 1,
            description TEXT
        )
    """)

    # 8. Quote Band Thresholds Table (Quintiles vs Fixed Fallback)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quote_band_thresholds (
            band_name TEXT PRIMARY KEY,
            min_val REAL,
            max_val REAL,
            is_derived INTEGER DEFAULT 0
        )
    """)

    # 9. Forecast Results Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecast_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT,
            forecast_type TEXT,
            customer_name TEXT,
            forecast_month TEXT,
            expected_value REAL,
            win_probability REAL,
            p10_value REAL,
            p50_value REAL,
            p90_value REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    # Seed baseline configurations and CSV data if empty
    seed_default_coefficients(conn)
    seed_default_quote_bands(conn)
    seed_from_csv_files(conn)

    conn.close()


def seed_default_coefficients(conn: sqlite3.Connection) -> None:
    """Seed baseline logistic regression model coefficients and What-If toggles."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM model_coefficients")
    if cursor.fetchone()[0] == 0:
        coefficients = [
            ("intercept", "intercept", 0.996171, 1, 1, "Base model intercept"),
            # Quarters
            ("Q1/2025", "quarter", 0.309252, 1, 1, "Q1 2025 quarter modifier"),
            ("Q1/2026", "quarter", 0.330152, 1, 1, "Q1 2026 quarter modifier"),
            ("Q2/2025", "quarter", 0.361671, 1, 1, "Q2 2025 quarter modifier"),
            ("Q2/2026", "quarter", 1.065487, 1, 1, "Q2 2026 quarter modifier"),
            ("Q3/2025", "quarter", 0.654613, 1, 1, "Q3 2025 quarter modifier"),
            ("Q4/2025", "quarter", 0.0, 1, 1, "Q4 2025 quarter modifier"),
            # Quote Bands
            ("Very Small", "band", 0.0, 1, 1, "Very Small deal size weight"),
            ("Small", "band", -0.49048, 1, 1, "Small deal size weight"),
            ("Medium", "band", -0.62943, 1, 1, "Medium deal size weight"),
            ("Large", "band", -0.79677, 1, 1, "Large deal size weight"),
            ("Very Large", "band", -1.35842, 1, 1, "Very Large deal size weight"),
            # Confidence Levels
            ("High", "confidence", 0.80, 1, 1, "High Confidence AM weighting"),
            ("Medium", "confidence", 0.0, 1, 1, "Medium Confidence AM weighting"),
            ("Low", "confidence", -0.80, 1, 1, "Low Confidence AM weighting"),
            # Customer Types
            ("Repeat", "customer_type", 0.45, 1, 1, "Repeat customer modifier"),
            ("New", "customer_type", -0.20, 1, 1, "New customer modifier"),
            # Age penalty
            ("age_penalty_per_day", "deal_age", -0.005, 1, 1, "Per-day deal age decay penalty")
        ]
        cursor.executemany("""
            INSERT OR REPLACE INTO model_coefficients (key, category, value, is_enabled, is_fallback, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, coefficients)
        conn.commit()


def seed_default_quote_bands(conn: sqlite3.Connection) -> None:
    """Seed specification default fixed fallback Quote Band quintile breakpoints."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM quote_band_thresholds")
    if cursor.fetchone()[0] == 0:
        bands = [
            ("Very Small", 0.0, 928.04, 0),
            ("Small", 928.04, 2209.0, 0),
            ("Medium", 2209.0, 4681.0, 0),
            ("Large", 4681.0, 10408.84, 0),
            ("Very Large", 10408.84, 99999999.0, 0),
        ]
        cursor.executemany("""
            INSERT OR REPLACE INTO quote_band_thresholds (band_name, min_val, max_val, is_derived)
            VALUES (?, ?, ?, ?)
        """, bands)
        conn.commit()


def seed_from_csv_files(conn: sqlite3.Connection) -> None:
    """Seed initial records into SQLite from customer.csv, supplier.csv, F6 - Order Book by Item.csv, and KS Quotations.csv."""
    cursor = conn.cursor()
    base_dir = os.path.dirname(__file__)

    # 1. Customers
    cust_file = os.path.join(base_dir, "customer.csv")
    if os.path.exists(cust_file):
        cursor.execute("SELECT COUNT(*) FROM customers")
        if cursor.fetchone()[0] == 0:
            try:
                df_cust = pd.read_csv(cust_file, encoding_errors="ignore")
                for _, r in df_cust.iterrows():
                    cursor.execute("""
                        INSERT OR IGNORE INTO customers (
                            customer_code, customer_name, customer_currency, sales_employee, payment_term,
                            billing_address, shipping_address, creation_date, first_invoice_date, last_invoice_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(r.get("customerCode", "")),
                        str(r.get("customerName", "")),
                        str(r.get("customerCurrency", "AUD")),
                        str(r.get("salesEmployeeName", "")),
                        str(r.get("paymentTerm", "Net 30")),
                        str(r.get("billingAddress", "")),
                        str(r.get("shippingAddress", "")),
                        str(r.get("creationDate", "")),
                        str(r.get("firstInvoiceDate", "")),
                        str(r.get("lastInvoiceDate", ""))
                    ))
                conn.commit()
            except Exception as e:
                print(f"Error seeding customer.csv: {e}")

    # 2. Suppliers
    sup_file = os.path.join(base_dir, "supplier.csv")
    if os.path.exists(sup_file):
        cursor.execute("SELECT COUNT(*) FROM suppliers")
        if cursor.fetchone()[0] == 0:
            try:
                df_sup = pd.read_csv(sup_file, encoding_errors="ignore")
                for _, r in df_sup.iterrows():
                    s_code = str(r.get("supplierCode", ""))
                    s_name = str(r.get("supplierName", ""))
                    cursor.execute("""
                        INSERT OR IGNORE INTO suppliers (supplier_code, supplier_name, supplier_currency, billing_address, creation_date)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        s_code, s_name, str(r.get("supplierCurrency", "AUD")),
                        str(r.get("billingAddress", "")), str(r.get("creationDate", ""))
                    ))
                    cursor.execute("""
                        INSERT OR IGNORE INTO supplier_settings (supplier_name, supplier_code, win_rate_modifier, lead_time_offset_days)
                        VALUES (?, ?, 0.0, 0)
                    """, (s_name, s_code))
                conn.commit()
            except Exception as e:
                print(f"Error seeding supplier.csv: {e}")

    # 3. Backlog (Order Book)
    so_file = os.path.join(base_dir, "F6 - Order Book by Item.csv")
    if os.path.exists(so_file):
        cursor.execute("SELECT COUNT(*) FROM backlog")
        if cursor.fetchone()[0] == 0:
            try:
                df_so = pd.read_csv(so_file, encoding_errors="ignore")
                for idx, r in df_so.iterrows():
                    so_num = str(r.get("soNumber", f"SO-{idx+1000}"))
                    part = str(r.get("partCode", "PART-001"))
                    out_qty = float(r.get("outstandingQty", 1.0) or 1.0)
                    order_val = out_qty * 150.0  # estimated order value per item
                    cursor.execute("""
                        INSERT OR IGNORE INTO backlog (
                            order_id, so_number, customer_order_no, customer_code, customer_name,
                            sales_employee, part_code, description, stock_qty, outstanding_qty,
                            due_date, order_value, state
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"ORD-{idx+1}", so_num, str(r.get("customerOrderNo", "")),
                        str(r.get("customerCode", "")), str(r.get("customerName", "")),
                        str(r.get("salesEmployee", "")), part, str(r.get("description", "")),
                        float(r.get("stockQty", 0.0) or 0.0), out_qty,
                        str(r.get("dueDate", "2026-09-30")), order_val, "NSW"
                    ))
                conn.commit()
            except Exception as e:
                print(f"Error seeding order book CSV: {e}")

    # 4. Quotes (KS Quotations.csv)
    quotes_file = os.path.join(base_dir, "KS Quotations.csv")
    if os.path.exists(quotes_file):
        cursor.execute("SELECT COUNT(*) FROM quotes")
        if cursor.fetchone()[0] == 0:
            try:
                df_q = pd.read_csv(quotes_file, encoding_errors="ignore")
                cols = {c.strip().lower().replace(" ", "_"): c for c in df_q.columns}
                for idx, r in df_q.head(150).iterrows():
                    ref = str(r.get(cols.get("quote_ref_no", "Quote Ref No"), f"QRN-{idx+7000}"))
                    val = float(r.get(cols.get("quote_value", "Quote Value"), 5000.0) or 5000.0)
                    q_date = str(r.get(cols.get("quote_date", "Quote Date"), "2026-05-15"))
                    c_name = str(r.get(cols.get("customer_name", "Customer Name"), "Customer Inc"))
                    c_code = str(r.get(cols.get("customer_code", "Customer Code"), ""))
                    status = str(r.get(cols.get("status", "Status"), "Open"))

                    cursor.execute("""
                        INSERT OR IGNORE INTO quotes (
                            quote_id, quote_ref_no, quote_date, customer_code, customer_name,
                            customer_type, state, account_manager, confidence_level, quote_value, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"Q-{idx+1000}", ref, q_date, c_code, c_name,
                        "Repeat" if c_code else "New", "NSW", "AM", "Medium", val, status
                    ))
                conn.commit()
            except Exception as e:
                print(f"Error seeding KS Quotations.csv: {e}")


def load_table_as_df(table_name: str, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Read any table into a pandas DataFrame."""
    conn = get_connection(db_path)
    df = pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)
    conn.close()
    return df


def execute_query(query: str, params: tuple = (), db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Execute a SELECT query and return list of dictionaries."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cols = [desc[0] for desc in cursor.description] if cursor.description else []
    result = [dict(zip(cols, row)) for row in rows]
    conn.close()
    return result


def execute_commit(query: str, params: tuple = (), db_path: str = DEFAULT_DB_PATH) -> int:
    """Execute an INSERT, UPDATE, or DELETE statement and return affected row count."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    count = cursor.rowcount
    conn.close()
    return count


def load_quotes_from_db(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Read quotation dataset from SQLite into pandas DataFrame."""
    return load_table_as_df("quotes", db_path)


def load_backlog_from_db(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Read order backlog dataset from SQLite into pandas DataFrame."""
    return load_table_as_df("backlog", db_path)


def save_forecast_to_db(
    df: pd.DataFrame,
    table_name: str = "forecast_results",
    db_path: str = DEFAULT_DB_PATH,
    if_exists: str = "replace"
) -> None:
    """Write or replace calculated forecast results DataFrame in SQLite database."""
    conn = get_connection(db_path)
    df.to_sql(table_name, con=conn, if_exists=if_exists, index=False)
    conn.close()

