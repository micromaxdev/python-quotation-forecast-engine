# Python Quotation Forecast Engine

A Python-based sales forecasting engine designed to project future revenue by processing open quotation pipelines (using logistic regression win probability weighting) and committed order backlogs (using operational lead time datetime calculations).

---

## 📁 Repository Structure

This repository strictly uses a **flat directory layout** (no subfolders for application code) to maintain simplicity, direct visibility, and easy module imports without package resolution issues.

```text
python-quotation-forecast-engine/
├── .gitignore            # Git exclusion rules for Python artifacts, caches, and raw data
├── README.md             # Project overview, architecture guide, and developer instructions
├── requirements.txt      # Project dependencies (pandas, scikit-learn, pytest, etc.)
├── main.py               # Central orchestrator driving step-by-step workflow execution
├── data_prep.py          # Data ingestion, cleaning, and feature mapping functions
├── pipeline_forecast.py  # Logistic regression probability model & expected won value calculations
└── backlog_forecast.py   # Datetime math for delivery lead times and expected invoice scheduling
```

---

## 🛠️ Junior Developer Onboarding & Implementation Guide

All codebase skeleton files contain type annotations, docstrings, and `# TODO` comments outlining exact functionality requirements. As a developer assigned to fill in these modules, follow this sequence:

### Step 1: Implement `data_prep.py`
- **Goal:** Ingest raw CSV/Excel files and convert messy business inputs into clean DataFrames.
- **Tasks:**
  1. Complete `load_raw_data()` to handle different input file extensions.
  2. Implement `standardize_column_names()` to strip whitespaces and convert headers to `snake_case`.
  3. Complete `handle_missing_values()` to drop or impute missing quote amounts or dates.
  4. Fill in `map_quote_bands()` using `pd.cut()` to categorize deal sizes (e.g., Small, Medium, Large).
  5. Complete `map_fiscal_quarters()` using `pd.to_datetime()` to assign fiscal quarter tags (e.g., Q1-2026).
  6. Wire up `prepare_dataset()` to run all prep functions sequentially.

### Step 2: Implement `pipeline_forecast.py`
- **Goal:** Calculate win probability and expected won monetary value for active, open sales quotes.
- **Tasks:**
  1. Complete `load_model_coefficients()` to retrieve weights for features (e.g., quote band, age, customer tier).
  2. Implement `calculate_win_probability()` applying the sigmoid/logistic equation:
     $$\text{Win Probability } p = \frac{1}{1 + e^{-(\beta_0 + \beta_1 x_1 + \dots + \beta_n x_n)}}$$
  3. Implement `calculate_expected_won_value()` to compute:
     $$\text{Expected Won Value} = \text{Quote Value} \times \text{Win Probability}$$
  4. Wire up `run_pipeline_forecast()` to return the enriched open pipeline dataset.

### Step 3: Implement `backlog_forecast.py`
- **Goal:** Calculate delivery and invoice timelines for closed/won committed orders using datetime arithmetic.
- **Tasks:**
  1. Complete `get_lead_time_rules()` to map product categories to standard lead time days.
  2. Implement `calculate_expected_delivery_date()` performing datetime addition:
     $$\text{Expected Delivery Date} = \text{Order Date} + \text{Operational Lead Time (Days)}$$
  3. Implement `calculate_expected_invoice_date()` adding payment terms offset (e.g., Net 30 days):
     $$\text{Expected Invoice Date} = \text{Expected Delivery Date} + \text{Payment Terms (Days)}$$
  4. Wire up `run_backlog_forecast()` to output scheduled revenue timelines.

### Step 4: Implement `main.py`
- **Goal:** Connect all modules into an executable command-line program.
- **Tasks:**
  1. Implement `parse_arguments()` to accept custom input/output file flags via command line.
  2. Implement `combine_forecasts()` to merge pipeline and backlog outputs into a single master summary table.
  3. Implement `export_results()` to write outputs to CSV/Excel and output executive KPIs to console.
  4. Uncomment and verify the main workflow execution chain inside `main()`.

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
- Write unit tests in separate test files named `test_data_prep.py`, `test_pipeline_forecast.py`, and `test_backlog_forecast.py` as you complete each module.
- Run tests using pytest:
  ```bash
  pytest
  ```
