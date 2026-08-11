# Python Quotation Forecast Engine

A Python-based sales forecasting engine designed to project future revenue by processing open quotation pipelines (using logistic regression win probability weighting) and committed order backlogs (using operational lead time datetime calculations).

Designed with a **step-by-step developer workbench** and **live web database inspector** to help domain architects and beginner programmers build and validate pure data transformation functions one step at a time.

---

## 📁 Repository Structure

This repository uses a clean **flat directory layout** for application code paired with a zero-dependency web visualizer:

```text
python-quotation-forecast-engine/
├── INTERN_GUIDE.md        # Step-by-step onboarding guide for beginner developers
├── README.md              # Project overview, architecture guide, and instructions
├── requirements.txt       # Dependencies (pandas, scikit-learn, pytest, etc.)
├── dev_database.db        # Shared local SQLite database populated with sample data
├── database.py            # SQLite connection boilerplate, schema creation, and seeding
├── workbench.py           # Interactive CLI workbench for running/testing individual steps
├── dashboard.py           # Zero-dependency HTTP server hosting the Live DB Inspector API
├── static/                # Dark-mode Web UI assets for the database visualizer
│   ├── index.html
│   ├── style.css
│   └── script.js
├── data_prep.py           # Pure functions for data cleaning & feature mapping (Steps 1–4)
├── pipeline_forecast.py   # Pure functions for logistic regression probability (Steps 5–6)
├── backlog_forecast.py    # Pure functions for lead time & payment offset math (Steps 7–8)
└── main.py                # Central orchestrator driving end-to-end execution
```

---

## 🖥️ Live Database Visual Inspector & Interactive Workbench

To make building and validating data transformation functions effortless, the repository includes two tools:

### 1. Live Visual Database Inspector (`http://localhost:8000`)
Launch a local browser-based database browser with live auto-refreshing table views:

```bash
python workbench.py serve
# OR
python dashboard.py
```
Open your browser to **`http://localhost:8000`** to visually inspect SQLite tables (`quotes`, `backlog`, `forecast_results`, and step outputs) in real time as calculations run.

### 2. Interactive CLI Workbench (`workbench.py`)
Run individual pure functions in isolation with instant terminal comparison (`INPUT DF` vs `OUTPUT DF`) and automatic database persistence:

```bash
# List all 8 guided steps
python workbench.py list

# Run a single step function (e.g. Step 1, Step 5)
python workbench.py 1
python workbench.py 5

# Run all 8 steps end-to-end
python workbench.py run-all
```

---

## 🗄️ Database Solution (SQLite)

- **Zero Configuration:** Built into Python (`sqlite3`) — no external database server or credentials needed.
- **Auto-Seeding:** Automatically seeds realistic sample data into `quotes` and `backlog` tables inside `dev_database.db` upon initial execution.

### Key Database Tables

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| `quotes` | Open sales opportunities | `quote_id`, `customer`, `quote_value`, `status`, `close_date`, `customer_tier`, `deal_age_days` |
| `backlog` | Closed/Won committed orders | `order_id`, `customer`, `order_value`, `order_date`, `product_category`, `lead_time_days` |
| `forecast_results` | Consolidated model outputs | `id`, `entity_id`, `forecast_type`, `expected_value`, `expected_date`, `created_at` |
| `step<N>_output` | Intermediate step outputs | Dynamic columns saved during step-by-step workbench testing |

---

## 🎓 Developer Step-by-Step Curriculum

The math and data transformation logic is broken into **8 pure functions** across 3 modules:

| Step | Function | Module | Goal / Formula |
| :---: | :--- | :--- | :--- |
| **1** | `standardize_column_names(df)` | [data_prep.py](./data_prep.py) | Clean headers (lowercase, strip whitespace, snake_case) |
| **2** | `handle_missing_values(df)` | [data_prep.py](./data_prep.py) | Filter missing critical columns; default missing tier to "Tier 3" |
| **3** | `map_quote_bands(df)` | [data_prep.py](./data_prep.py) | Categorize deal size (`Small <$10k`, `Medium $10k-$50k`, `Large >$50k`) |
| **4** | `map_fiscal_quarters(df)` | [data_prep.py](./data_prep.py) | Parse dates and tag fiscal quarters (e.g. `Q3-2026`) |
| **5** | `calculate_win_probability(df)` | [pipeline_forecast.py](./pipeline_forecast.py) | Logit win probability: $p = \frac{1}{1 + e^{-z}}$ |
| **6** | `calculate_expected_won_value(df)` | [pipeline_forecast.py](./pipeline_forecast.py) | Weighted revenue: $\text{Quote Value} \times \text{Win Probability}$ |
| **7** | `calculate_expected_delivery_date(df)` | [backlog_forecast.py](./backlog_forecast.py) | Datetime addition: $\text{Order Date} + \text{Lead Time Days}$ |
| **8** | `calculate_expected_invoice_date(df)` | [backlog_forecast.py](./backlog_forecast.py) | Payment offset: $\text{Delivery Date} + \text{Net 30 Days}$ |

For detailed instructions, refer to the [INTERN_GUIDE.md](./INTERN_GUIDE.md).

---

## 🚀 Getting Started

### 1. Requirements & Setup
Ensure Python 3.10+ is installed:

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Running the Full Forecast Engine

```bash
python main.py
```
Outputs total projected revenue and writes consolidated outputs directly to the SQLite `forecast_results` table.
