"""
dashboard.py
------------
Zero-dependency Python HTTP & REST API Server for the Sales Forecast Engine.
Serves static frontend visualizer assets and exposes JSON REST APIs for:
- Database table browsing & inspection
- Multi-dataset file upload & column header mapping (Quotes, Customers, Suppliers, Backlog)
- Table CRUD operations (Create, Read, Update, Delete)
- Real-time forecast recalculation & Monte Carlo lead-time simulation
- What-If coefficient sensitivity toggles
- Logistic regression model fitting & fallback parameter management
"""

import http.server
import json
import os
import re
import sqlite3
import socketserver
import urllib.parse
import io
import pandas as pd
from typing import Dict, Any, List

import database
import data_prep
import pipeline_forecast
import backlog_forecast

PORT = 8000
DB_PATH = database.DEFAULT_DB_PATH
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class ForecastEngineHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP Handler exposing REST API endpoints and serving web visualizer static assets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/tables":
            self.send_json(self.get_tables())

        elif path.startswith("/api/table/"):
            table_name = path.replace("/api/table/", "")
            self.send_json(self.get_table_data(table_name))

        elif path == "/api/forecast":
            self.send_json(self.get_forecast_data())

        elif path == "/api/settings":
            self.send_json(self.get_settings_data())

        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))

        # Handle multipart/form-data for file uploads
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" in content_type:
            body_bytes = self.rfile.read(content_length)
            self.handle_file_upload(content_type, body_bytes)
            return

        # Parse JSON body
        body_str = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            body = json.loads(body_str)
        except Exception:
            body = {}

        if path == "/api/upload/json":
            self.handle_upload_json(body)

        elif path == "/api/ingest/confirm":
            self.handle_ingest_confirm(body)

        elif path.startswith("/api/crud/"):
            table_name = path.replace("/api/crud/", "")
            self.handle_crud(table_name, body)

        elif path == "/api/forecast/recalculate":
            self.handle_forecast_recalculate(body)

        elif path == "/api/settings":
            self.handle_save_settings(body)

        elif path == "/api/model/fit":
            self.handle_model_fit(body)

        else:
            self.send_json({"error": f"Endpoint not found: {path}"}, status=404)

    # =========================================================================
    # GET ENDPOINTS
    # =========================================================================

    def get_tables(self) -> Dict[str, Any]:
        """Fetch list of user database tables."""
        try:
            rows = database.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            return {"tables": [r["name"] for r in rows]}
        except Exception as e:
            return {"error": str(e)}

    def get_table_data(self, table_name: str) -> Dict[str, Any]:
        """Fetch rows from a given table safely."""
        try:
            rows = database.execute_query(f'SELECT * FROM "{table_name}" LIMIT 500')
            columns = list(rows[0].keys()) if rows else []
            return {
                "table_name": table_name,
                "columns": columns,
                "row_count": len(rows),
                "data": rows
            }
        except Exception as e:
            return {"error": str(e)}

    def get_forecast_data(self) -> Dict[str, Any]:
        """Calculate and return consolidated forecast series, KPIs, and risk queues."""
        try:
            quotes_df = database.load_quotes_from_db()
            backlog_df = database.load_backlog_from_db()

            clean_quotes = data_prep.prepare_dataset(quotes_df)
            pipe_results = pipeline_forecast.run_pipeline_forecast(clean_quotes)
            back_results = backlog_forecast.run_backlog_forecast(backlog_df)

            # Consolidate by forecast_month
            month_map = {}
            for _, r in pipe_results.iterrows():
                m = str(r.get("forecast_month", "Sep-2026"))
                val = float(r.get("expected_won_value", 0.0) or 0.0)
                if m not in month_map:
                    month_map[m] = {"month": m, "pipeline": 0.0, "backlog": 0.0, "total": 0.0, "p10": 0.0, "p90": 0.0}
                month_map[m]["pipeline"] += val
                month_map[m]["p10"] += val * 0.85
                month_map[m]["p90"] += val * 1.15

            for _, r in back_results.iterrows():
                m = str(r.get("forecast_month", "Sep-2026"))
                val = float(r.get("expected_won_value", 0.0) or 0.0)
                if m not in month_map:
                    month_map[m] = {"month": m, "pipeline": 0.0, "backlog": 0.0, "total": 0.0, "p10": 0.0, "p90": 0.0}
                month_map[m]["backlog"] += val
                month_map[m]["p10"] += val
                month_map[m]["p90"] += val

            summary_list = []
            for m in sorted(month_map.keys()):
                item = month_map[m]
                item["pipeline"] = round(item["pipeline"], 2)
                item["backlog"] = round(item["backlog"], 2)
                item["total"] = round(item["pipeline"] + item["backlog"], 2)
                item["p10"] = round(item["p10"], 2)
                item["p90"] = round(item["p90"], 2)
                summary_list.append(item)

            tot_pipeline = sum(i["pipeline"] for i in summary_list)
            tot_backlog = sum(i["backlog"] for i in summary_list)

            avg_win_prob = float(pipe_results["win_probability"].mean()) if "win_probability" in pipe_results.columns and len(pipe_results) > 0 else 0.50

            return {
                "monthly_summary": summary_list,
                "kpis": {
                    "total_projected": round(tot_pipeline + tot_backlog, 2),
                    "pipeline_revenue": round(tot_pipeline, 2),
                    "backlog_revenue": round(tot_backlog, 2),
                    "open_quotes_count": len(pipe_results),
                    "backlog_orders_count": len(back_results),
                    "avg_win_rate": round(avg_win_prob * 100, 1)
                },
                "queues": {
                    "overdue_quotes": clean_quotes[clean_quotes["follow_up_status"].isin(["Expired", "Overdue"])].to_dict(orient="records") if "follow_up_status" in clean_quotes.columns else [],
                    "unmatched_po_backlog": back_results[back_results["match_status"] == "No Matching PO"].to_dict(orient="records") if "match_status" in back_results.columns else []
                }
            }
        except Exception as e:
            return {"error": str(e)}

    def get_settings_data(self) -> Dict[str, Any]:
        """Fetch model coefficients, What-If toggles, quintile thresholds, and supplier settings."""
        try:
            coefs = database.execute_query("SELECT * FROM model_coefficients")
            bands = database.execute_query("SELECT * FROM quote_band_thresholds")
            sups = database.execute_query("SELECT * FROM supplier_settings")
            return {
                "coefficients": coefs,
                "quote_bands": bands,
                "suppliers": sups
            }
        except Exception as e:
            return {"error": str(e)}

    # =========================================================================
    # POST & FILE INGESTION ENDPOINTS
    # =========================================================================

    def handle_file_upload(self, content_type: str, body_bytes: bytes):
        """Parse multipart form-data upload for .csv, .xlsx, or .xls files."""
        try:
            # Extract boundary
            boundary = content_type.split("boundary=")[-1].encode("utf-8")
            parts = body_bytes.split(b"--" + boundary)

            file_bytes = None
            filename = "uploaded_file.csv"

            for part in parts:
                if b'filename="' in part:
                    header_part, content_part = part.split(b"\r\n\r\n", 1)
                    header_text = header_part.decode("utf-8", errors="ignore")
                    m = re.search(r'filename="([^"]+)"', header_text)
                    if m:
                        filename = m.group(1)
                    file_bytes = content_part.rsplit(b"\r\n", 1)[0]
                    break

            if not file_bytes:
                self.send_json({"error": "No file content detected in upload"}, status=400)
                return

            # Read via Pandas
            if filename.lower().endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_bytes), encoding_errors="ignore")
            elif filename.lower().endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(file_bytes))
            else:
                self.send_json({"error": "Unsupported file format. Please upload CSV or Excel."}, status=400)
                return

            columns = list(df.columns)
            preview_rows = df.head(5).fillna("").to_dict(orient="records")

            self.send_json({
                "status": "success",
                "filename": filename,
                "columns": columns,
                "preview": preview_rows,
                "total_rows": len(df),
                "raw_data": df.head(200).fillna("").to_dict(orient="records")
            })
        except Exception as e:
            self.send_json({"error": f"File parse error: {str(e)}"}, status=500)

    def handle_upload_json(self, body: Dict[str, Any]):
        """Alternative JSON preview endpoint."""
        data = body.get("raw_text", "")
        try:
            df = pd.read_csv(io.StringIO(data))
            self.send_json({
                "status": "success",
                "columns": list(df.columns),
                "preview": df.head(5).fillna("").to_dict(orient="records"),
                "total_rows": len(df),
                "raw_data": df.head(200).fillna("").to_dict(orient="records")
            })
        except Exception as e:
            self.send_json({"error": str(e)}, status=400)

    def handle_ingest_confirm(self, body: Dict[str, Any]):
        """Confirm column mapping and ingest into quotes, backlog, customers, or suppliers."""
        entity_type = body.get("entity_type", "quotes")
        mapping = body.get("mapping", {})
        raw_data = body.get("raw_data", [])

        if not raw_data:
            self.send_json({"error": "No raw data provided for ingestion"}, status=400)
            return

        try:
            df_raw = pd.DataFrame(raw_data)
            
            # Apply user column mapping
            rename_dict = {v: k for k, v in mapping.items() if v}
            df_mapped = df_raw.rename(columns=rename_dict)

            conn = database.get_connection()
            cursor = conn.cursor()
            inserted_count = 0

            if entity_type == "quotes":
                df_clean = data_prep.prepare_dataset(df_mapped)
                for idx, r in df_clean.iterrows():
                    q_id = str(r.get("quote_id", f"Q-IMP-{idx+1}"))
                    ref = str(r.get("quote_ref_no", f"QRN-{idx+5000}"))
                    val = float(r.get("quote_value", 0.0) or 0.0)
                    c_name = str(r.get("customer_name", "Customer"))
                    c_code = str(r.get("customer_code", ""))
                    c_type = str(r.get("customer_type", "New"))
                    status = str(r.get("status", "Open"))

                    cursor.execute("""
                        INSERT OR REPLACE INTO quotes (
                            quote_id, quote_ref_no, quote_date, customer_code, customer_name,
                            customer_type, state, account_manager, confidence_level, quote_value, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        q_id, ref, str(r.get("quote_date", "2026-06-01")),
                        c_code, c_name, c_type, str(r.get("state", "NSW")),
                        str(r.get("account_manager", "AM")), str(r.get("confidence_level", "Medium")),
                        val, status
                    ))
                    inserted_count += 1

            elif entity_type == "customers":
                for idx, r in df_mapped.iterrows():
                    c_code = str(r.get("customer_code", f"CUST-{idx+100}"))
                    c_name = str(r.get("customer_name", "Customer"))
                    cursor.execute("""
                        INSERT OR REPLACE INTO customers (
                            customer_code, customer_name, customer_currency, sales_employee, payment_term
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        c_code, c_name, str(r.get("customer_currency", "AUD")),
                        str(r.get("sales_employee", "")), str(r.get("payment_term", "Net 30"))
                    ))
                    inserted_count += 1

            elif entity_type == "suppliers":
                for idx, r in df_mapped.iterrows():
                    s_code = str(r.get("supplier_code", f"SUP-{idx+100}"))
                    s_name = str(r.get("supplier_name", "Supplier"))
                    cursor.execute("""
                        INSERT OR REPLACE INTO suppliers (supplier_code, supplier_name, default_lead_time_days)
                        VALUES (?, ?, ?)
                    """, (s_code, s_name, int(r.get("default_lead_time_days", 14) or 14)))
                    cursor.execute("""
                        INSERT OR REPLACE INTO supplier_settings (supplier_name, supplier_code, win_rate_modifier)
                        VALUES (?, ?, 0.0)
                    """, (s_name, s_code))
                    inserted_count += 1

            elif entity_type == "backlog":
                for idx, r in df_mapped.iterrows():
                    o_id = str(r.get("order_id", f"ORD-IMP-{idx+1}"))
                    so_num = str(r.get("so_number", f"SO-{idx+1000}"))
                    cursor.execute("""
                        INSERT OR REPLACE INTO backlog (
                            order_id, so_number, customer_code, customer_name, part_code,
                            outstanding_qty, due_date, order_value, state
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        o_id, so_num, str(r.get("customer_code", "")),
                        str(r.get("customer_name", "Customer")), str(r.get("part_code", "PART-001")),
                        float(r.get("outstanding_qty", 1.0) or 1.0), str(r.get("due_date", "2026-09-30")),
                        float(r.get("order_value", 1000.0) or 1000.0), str(r.get("state", "NSW"))
                    ))
                    inserted_count += 1

            conn.commit()
            conn.close()

            self.send_json({
                "status": "success",
                "message": f"Successfully ingested {inserted_count} records into '{entity_type}'!",
                "count": inserted_count
            })
        except Exception as e:
            self.send_json({"error": f"Ingestion error: {str(e)}"}, status=500)

    def handle_crud(self, table_name: str, body: Dict[str, Any]):
        """Perform Create, Update, or Delete operations on database tables."""
        action = body.get("action", "").lower()
        record = body.get("record", {})

        if not action or not record:
            self.send_json({"error": "Action and record data are required"}, status=400)
            return

        try:
            conn = database.get_connection()
            cursor = conn.cursor()

            if action == "create":
                keys = list(record.keys())
                placeholders = ", ".join(["?"] * len(keys))
                cols = ", ".join([f'"{k}"' for k in keys])
                vals = [record[k] for k in keys]
                query = f'INSERT INTO "{table_name}" ({cols}) VALUES ({placeholders})'
                cursor.execute(query, vals)

            elif action == "update":
                pk_name = "quote_id" if table_name == "quotes" else ("order_id" if table_name == "backlog" else ("customer_code" if table_name == "customers" else ("supplier_name" if table_name == "supplier_settings" else "key")))
                pk_val = record.get(pk_name)
                
                set_clauses = []
                vals = []
                for k, v in record.items():
                    if k != pk_name:
                        set_clauses.append(f'"{k}" = ?')
                        vals.append(v)
                vals.append(pk_val)
                query = f'UPDATE "{table_name}" SET {", ".join(set_clauses)} WHERE "{pk_name}" = ?'
                cursor.execute(query, vals)

            elif action == "delete":
                pk_name = "quote_id" if table_name == "quotes" else ("order_id" if table_name == "backlog" else ("customer_code" if table_name == "customers" else ("supplier_name" if table_name == "supplier_settings" else "key")))
                pk_val = record.get(pk_name)
                query = f'DELETE FROM "{table_name}" WHERE "{pk_name}" = ?'
                cursor.execute(query, (pk_val,))

            conn.commit()
            conn.close()

            self.send_json({"status": "success", "action": action, "table": table_name})
        except Exception as e:
            self.send_json({"error": f"CRUD operation failed: {str(e)}"}, status=500)

    def handle_forecast_recalculate(self, body: Dict[str, Any]):
        """Update coefficient What-If toggles and return recalculated forecast."""
        toggles = body.get("toggles", {})
        try:
            conn = database.get_connection()
            cursor = conn.cursor()
            for key, is_enabled in toggles.items():
                cursor.execute(
                    "UPDATE model_coefficients SET is_enabled = ? WHERE key = ?",
                    (1 if is_enabled else 0, key)
                )
            conn.commit()
            conn.close()

            self.send_json(self.get_forecast_data())
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_save_settings(self, body: Dict[str, Any]):
        """Save settings updates for coefficients, quintiles, or supplier overrides."""
        try:
            conn = database.get_connection()
            cursor = conn.cursor()

            if "coefficients" in body:
                for item in body["coefficients"]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO model_coefficients (key, category, value, is_enabled, is_fallback, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        item["key"], item.get("category", "custom"), float(item["value"]),
                        1 if item.get("is_enabled", True) else 0, 0, item.get("description", "")
                    ))

            if "suppliers" in body:
                for sup in body["suppliers"]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO supplier_settings (supplier_name, supplier_code, win_rate_modifier, lead_time_offset_days)
                        VALUES (?, ?, ?, ?)
                    """, (
                        sup["supplier_name"], sup.get("supplier_code", ""),
                        float(sup.get("win_rate_modifier", 0.0)), int(sup.get("lead_time_offset_days", 0))
                    ))

            conn.commit()
            conn.close()

            self.send_json({"status": "success", "message": "Settings saved successfully!"})
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    def handle_model_fit(self, body: Dict[str, Any]):
        """Refit logistic regression on historical won/lost quotes and derive quintiles."""
        try:
            quotes_df = database.load_quotes_from_db()
            fitted_coefs = pipeline_forecast.fit_logistic_regression(quotes_df)

            conn = database.get_connection()
            cursor = conn.cursor()
            
            # Derive quintiles
            if "quote_value" in quotes_df.columns:
                derived_q = data_prep.derive_quintiles_or_fallback(quotes_df["quote_value"])
                cursor.execute("DELETE FROM quote_band_thresholds")
                for band, (min_v, max_v) in derived_q.items():
                    cursor.execute("""
                        INSERT INTO quote_band_thresholds (band_name, min_val, max_val, is_derived)
                        VALUES (?, ?, ?, 1)
                    """, (band, min_v, max_v))

            conn.commit()
            conn.close()

            self.send_json({
                "status": "success",
                "message": "Logistic regression model successfully refitted on historical quote data!",
                "coefficients": fitted_coefs
            })
        except Exception as e:
            self.send_json({"error": str(e)}, status=500)

    # =========================================================================
    # JSON HELPER
    # =========================================================================

    def send_json(self, data: Any, status: int = 200):
        """Send JSON response with CORS headers."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def start_server(port=PORT):
    """Launch the Sales Forecast Engine web server."""
    database.initialize_database()

    print(f"\n==================================================")
    print(f"SALES FORECAST ENGINE WEB APP RUNNING!")
    print(f"Open in browser: http://localhost:{port}")
    print(f"==================================================\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), ForecastEngineHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    start_server()
