"""
dashboard.py
------------
Zero-dependency Python HTTP Server to serve the Live SQLite Database Inspector Web UI.
Launch via terminal: `python dashboard.py` or `python workbench.py serve`
"""

import http.server
import json
import os
import sqlite3
import socketserver
from urllib.parse import parse_qs, urlparse

PORT = 8000
DB_PATH = "dev_database.db"
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class DatabaseInspectorHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP Handler exposing SQLite REST API endpoints and static web assets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        parsed_path = urlparse(self.path)

        # API: List all SQLite tables
        if parsed_path.path == "/api/tables":
            self.send_json_response(self.get_tables())
            return

        # API: Get content of a specific SQLite table
        elif parsed_path.path.startswith("/api/table/"):
            table_name = parsed_path.path.replace("/api/table/", "")
            self.send_json_response(self.get_table_data(table_name))
            return

        # Serve static HTML/JS UI files
        return super().do_GET()

    def get_tables(self):
        """Fetch list of all SQLite tables."""
        if not os.path.exists(DB_PATH):
            return {"tables": []}
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            return {"tables": tables}
        except Exception as e:
            return {"error": str(e)}

    def get_table_data(self, table_name: str):
        """Fetch all rows from a given table."""
        if not os.path.exists(DB_PATH):
            return {"error": "Database file not found"}

        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Sanitize table name to avoid SQL injection
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                conn.close()
                return {"error": f"Table '{table_name}' does not exist"}

            cursor.execute(f'SELECT * FROM "{table_name}"')
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description] if cursor.description else []
            data = [dict(row) for row in rows]
            conn.close()

            return {
                "table_name": table_name,
                "columns": columns,
                "row_count": len(data),
                "data": data
            }
        except Exception as e:
            return {"error": str(e)}

    def send_json_response(self, data):
        """Send JSON response with CORS headers."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_server(port=PORT):
    """Launch the Web Database Inspector server."""
    # Ensure database is initialized before serving
    import database
    database.initialize_database()

    print(f"\n==================================================")
    print(f"LIVE DATABASE VISUAL INSPECTOR RUNNING!")
    print(f"Open in browser: http://localhost:{port}")
    print(f"==================================================\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), DatabaseInspectorHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    start_server()
