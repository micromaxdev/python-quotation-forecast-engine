# 🎓 Sales Forecasting Engine - Intern Developer Guide

Welcome! This guide is designed specifically for you. You are the architect of the model and math calculations. We have pre-built all the database connections, web visualizer, file loading, and terminal testing tools so that **you only need to write simple, pure Python functions—one step at a time.**

---

## 🚀 Quickstart: How Your Developer Environment Works

### 1. Launch Your Live Visual Database Inspector
Open a terminal and run:
```bash
python workbench.py serve
```
Then open your web browser to: **`http://localhost:8000`**

This will display a live view of your SQLite database tables. Whenever you run a step, the output automatically appears in your browser!

---

### 2. The 8-Step Pure Function Model
Your work is broken into 8 small steps across 3 Python files:
- `data_prep.py` (Steps 1 – 4)
- `pipeline_forecast.py` (Steps 5 – 6)
- `backlog_forecast.py` (Steps 7 – 8)

Each function is **pure**:
- **Input:** A pandas DataFrame (`df`) containing data rows and columns.
- **Transform:** Perform your specific calculation or clean column values.
- **Output:** Return the modified DataFrame (`return df`).

---

## 🛠️ Step-by-Step Curriculum & Testing Guide

### Step 1: Clean & Standardize Column Headers
- **File:** [data_prep.py](./data_prep.py)
- **Function:** `standardize_column_names(df)`
- **Goal:** Convert column names to lowercase, strip spaces, and replace inner spaces with underscores `_`.
- **Test Command:**
  ```bash
  python workbench.py 1
  ```

---

### Step 2: Clean Missing Data Points
- **File:** [data_prep.py](./data_prep.py)
- **Function:** `handle_missing_values(df)`
- **Goal:** Drop any row where `quote_value` or `close_date` is missing, and default missing `customer_tier` to `"Tier 3"`.
- **Test Command:**
  ```bash
  python workbench.py 2
  ```

---

### Step 3: Categorize Quotation Deal Sizes
- **File:** [data_prep.py](./data_prep.py)
- **Function:** `map_quote_bands(df)`
- **Goal:** Add a `quote_band` column:
  - `< 10,000` $\rightarrow$ `"Small"`
  - `10,000 to 50,000` $\rightarrow$ `"Medium"`
  - `>= 50,000` $\rightarrow$ `"Large"`
- **Test Command:**
  ```bash
  python workbench.py 3
  ```

---

### Step 4: Map Dates to Fiscal Quarters
- **File:** [data_prep.py](./data_prep.py)
- **Function:** `map_fiscal_quarters(df)`
- **Goal:** Convert `close_date` strings to datetime objects and create a `fiscal_quarter` column (e.g. `"Q3-2026"`).
- **Test Command:**
  ```bash
  python workbench.py 4
  ```

---

### Step 5: Win Probability (Logistic Regression)
- **File:** [pipeline_forecast.py](./pipeline_forecast.py)
- **Function:** `calculate_win_probability(df, coefficients)`
- **Math Formula:**
  $$z = \beta_{\text{intercept}} + \beta_{\text{tier}} + (\text{deal\_age\_days} \times \beta_{\text{age\_penalty}})$$
  $$\text{win\_probability} = \frac{1}{1 + e^{-z}}$$
- **Test Command:**
  ```bash
  python workbench.py 5
  ```

---

### Step 6: Expected Won Value
- **File:** [pipeline_forecast.py](./pipeline_forecast.py)
- **Function:** `calculate_expected_won_value(df)`
- **Math Formula:**
  $$\text{Expected Won Value} = \text{Quote Value} \times \text{Win Probability}$$
- **Test Command:**
  ```bash
  python workbench.py 6
  ```

---

### Step 7: Expected Delivery Date Arithmetic
- **File:** [backlog_forecast.py](./backlog_forecast.py)
- **Function:** `calculate_expected_delivery_date(df)`
- **Math Formula:**
  $$\text{Expected Delivery Date} = \text{Order Date} + \text{Lead Time Days}$$
- **Test Command:**
  ```bash
  python workbench.py 7
  ```

---

### Step 8: Expected Invoicing / Payment Offset
- **File:** [backlog_forecast.py](./backlog_forecast.py)
- **Function:** `calculate_expected_invoice_date(df)`
- **Math Formula:**
  $$\text{Expected Invoice Date} = \text{Expected Delivery Date} + \text{Net 30 Payment Offset}$$
- **Test Command:**
  ```bash
  python workbench.py 8
  ```

---

### 🏆 Master Pipeline Run
Once all 8 steps pass individual verification, run the full end-to-end forecast engine:
```bash
python workbench.py run-all
```
Check `http://localhost:8000` to see your final `forecast_results` table populated directly inside SQLite!
