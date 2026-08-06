# Python Quotation Forecast Engine

A Python-based sales forecasting engine designed to project future revenue by processing open quotation pipelines (using logistic regression win probability weighting) and committed order backlogs (using operational lead time datetime calculations).

---

## 📁 Repository Structure

This repository strictly uses a **flat directory layout** (no subfolders for application code) to maintain simplicity, direct visibility, and easy module imports without package resolution issues.

```text
python-quotation-forecast-engine/
├── .gitignore            # Git exclusion rules (tracks dev_database.db, ignores secret/prod DBs)
├── README.md             # Project overview, architecture guide, and developer instructions
├── requirements.txt      # Project dependencies (pandas, scikit-learn, pytest, etc.)
├── dev_database.db       # Shared local SQLite database containing non-production mock tables
├── database.py           # SQLite connection, schema creation, and database I/O helper functions
├── main.py               # Central orchestrator driving step-by-step workflow execution
├── data_prep.py          # Data ingestion, cleaning, and feature mapping functions
├── pipeline_forecast.py  # Logistic regression probability model & expected won value calculations
└── backlog_forecast.py   # Datetime math for delivery lead times and expected invoice scheduling
```

---

## 🗄️ Database Solution (SQLite)

For local development and junior developer ease-of-use, **SQLite** is selected as the lightweight database layer for this project:

- **Zero Configuration:** Built into the Python standard library (`sqlite3`) — no server, credentials, or installation required.
- **Portability:** The database file `dev_database.db` is tracked in the repository and populated with **non-production sample data** so all developers have immediate access to test data upon cloning.
- **Data Persistence:** Calculated forecast outputs can be saved directly back to SQLite tables (`forecast_results`) using `pandas` and `sqlite3`.

### Database Schema Overview (`dev_database.db`)

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| `quotes` | Open sales opportunities | `quote_id`, `customer`, `quote_value`, `status`, `close_date`, `quote_band` |
| `backlog` | Closed/Won committed orders | `order_id`, `customer`, `order_value`, `order_date`, `lead_time_days` |
| `forecast_results` | Consolidated model outputs | `id`, `entity_id`, `forecast_type`, `expected_value`, `expected_date` |

---

## 🛠️ Junior Developer Onboarding & Implementation Guide

All codebase skeleton files contain type annotations, docstrings, and `# TODO` comments outlining exact functionality requirements. As a developer assigned to fill in these modules, follow this sequence:

### Step 1: Implement `database.py`
- **Goal:** Manage SQLite connection, dataset queries, and saving forecast outputs to the database.
- **Tasks:**
  1. Complete `get_connection()` to open a connection to `dev_database.db`.
  2. Complete `initialize_database()` to execute `CREATE TABLE IF NOT EXISTS` queries for `quotes`, `backlog`, and `forecast_results`.
  3. Implement `load_quotes_from_db()` using `pd.read_sql_query()`.
  4. Implement `load_backlog_from_db()` using `pd.read_sql_query()`.
  5. Complete `save_forecast_to_db()` using `df.to_sql(table_name, con, if_exists='append')`.

### Step 2: Implement `data_prep.py`
- **Goal:** Ingest raw CSV/Excel files and convert messy business inputs into clean DataFrames.
- **Tasks:**
  1. Complete `load_raw_data()` to handle different input file extensions.
  2. Implement `standardize_column_names()` to strip whitespaces and convert headers to `snake_case`.
  3. Complete `handle_missing_values()` to drop or impute missing quote amounts or dates.
  4. Fill in `map_quote_bands()` using `pd.cut()` to categorize deal sizes (e.g., Small, Medium, Large).
  5. Complete `map_fiscal_quarters()` using `pd.to_datetime()` to assign fiscal quarter tags (e.g., Q1-2026).
  6. Wire up `prepare_dataset()` to run all prep functions sequentially.

### Step 3: Implement `pipeline_forecast.py`
- **Goal:** Calculate win probability and expected won monetary value for active, open sales quotes.
- **Tasks:**
  1. Complete `load_model_coefficients()` to retrieve weights for features (e.g., quote band, age, customer tier).
  2. Implement `calculate_win_probability()` applying the sigmoid/logistic equation:
     $$\text{Win Probability } p = \frac{1}{1 + e^{-(\beta_0 + \beta_1 x_1 + \dots + \beta_n x_n)}}$$
  3. Implement `calculate_expected_won_value()` to compute:
     $$\text{Expected Won Value} = \text{Quote Value} \times \text{Win Probability}$$
  4. Wire up `run_pipeline_forecast()` to return the enriched open pipeline dataset.

### Step 4: Implement `backlog_forecast.py`
- **Goal:** Calculate delivery and invoice timelines for closed/won committed orders using datetime arithmetic.
- **Tasks:**
  1. Complete `get_lead_time_rules()` to map product categories to standard lead time days.
  2. Implement `calculate_expected_delivery_date()` performing datetime addition:
     $$\text{Expected Delivery Date} = \text{Order Date} + \text{Operational Lead Time (Days)}$$
  3. Implement `calculate_expected_invoice_date()` adding payment terms offset (e.g., Net 30 days):
     $$\text{Expected Invoice Date} = \text{Expected Delivery Date} + \text{Payment Terms (Days)}$$
  4. Wire up `run_backlog_forecast()` to output scheduled revenue timelines.

### Step 5: Implement `main.py`
- **Goal:** Connect all modules into an executable command-line program.
- **Tasks:**
  1. Implement `parse_arguments()` to accept custom input/output file flags via command line.
  2. Connect `database.py` calls to load dataset tables from `dev_database.db`.
  3. Implement `combine_forecasts()` to merge pipeline and backlog outputs into a single master summary table.
  4. Implement `export_results()` to write outputs to CSV/Excel and call `database.save_forecast_to_db()`.
  5. Uncomment and verify the main workflow execution chain inside `main()`.

---

## 🚀 Getting Started

### 1. Requirements & Setup
Ensure you have Python 3.10+ installed.

```bash
# Clone repository
git clone https://github.com/your-org/python-quotation-forecast-engine.git
cd python-quotation-forecast-engine

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the Engine
Execute the orchestrator script:

```bash
python main.py
```

---

## 🧪 Testing Guidelines
- Write unit tests in separate test files named `test_data_prep.py`, `test_pipeline_forecast.py`, `test_database.py`, etc., as you complete each module.
- Run tests using pytest:
  ```bash
  pytest
  ```
