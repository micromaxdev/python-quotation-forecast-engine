# 📊 Sales Forecast Engine (Full-Stack UI/UX Web Application)

An interactive, dynamic two-limb sales forecasting engine built in Python and HTML/CSS/JS. It predicts monthly invoiced revenue by combining:
1. **Weighted Pipeline Forecast:** Scored via logistic regression win probability models and projected forward through Monte Carlo order-to-cash lead time chains.
2. **Committed Backlog Forecast:** Projected forward through PO-matching procurement lead-time chains and payment term offsets (Net 30).

---

## 🚀 Key Application Features

### 1. Modern Glassmorphic Web Dashboard
- Built following the **Laws of UX** (Hick's Law, Fitts's Law, Miller's Law, Aesthetic-Usability Effect).
- Interactive stacked monthly forecast revenue chart (Pipeline vs. Backlog) with **P10 / P50 / P90 Monte Carlo confidence bounds**.
- Key Executive KPI Metrics: Total Projected Revenue, Weighted Pipeline Value, Committed Backlog Revenue, Weighted Win Rate %.
- Automated **Pipeline Health Queues**: Overdue quote follow-up queue and unmatched sales order PO-matching risk queue.

### 2. Multi-Dataset Ingestion & Dynamic Column Header Mapper
- Drag-and-drop file uploader accepting **`.csv`**, **`.xlsx`**, and **`.xls`** files.
- Supports 4 primary data entities:
  - **Quotations Register (`KS Quotations.csv` / custom):** Open and closed quote register.
  - **Customer Directory (`customer.csv`):** Ingests existing customer directory (`customerCode`, `customerName`, `paymentTerm`, `shippingAddress`). Automatically classifies quote customers as `"Repeat"` (Existing) vs. `"New"`.
  - **Supplier Directory (`supplier.csv`):** Ingests suppliers (`supplierCode`, `supplierName`) to build lead-time lookup rules and supplier win-rate modifiers.
  - **Order Book Backlog (`F6 - Order Book by Item.csv`):** Ingests open sales orders (`soNumber`, `customerCode`, `partCode`, `outstandingQty`, `dueDate`) directly into the backlog delivery and invoicing timeline engine.
- Interactive **Column Mapping Modal** allowing users to map uploaded file headers to system target fields with real-time sample previews.

### 3. Full UI CRUD Workbench
- Live Create, Read, Update, and Delete (CRUD) operations for Quotes, Backlog, Customers, and Suppliers.
- Search bar filter, status pills (`Open`, `Won`, `Lost`), add quote modal, and deletion confirmation.

### 4. What-If Coefficient Sensitivity Engine
- Interactive toggle panel allowing users to turn individual probability factors **ON or OFF**:
  - Quarter Influences (`Q1/2025`, `Q2/2025`, etc.)
  - Quote Size Bands (`Very Small`, `Small`, `Medium`, `Large`, `Very Large`)
  - Account Manager Confidence Levels (`High`, `Medium`, `Low`)
  - Repeat vs. New Customer Modifier
  - Deal Age Penalty per Day
- Dynamic forecast recalculation and overlay on toggle change.

### 5. Logistic Regression Model Fitting & Fallback Management
- Automated logistic regression refitting on historical Won vs. Lost quote data.
- **Dynamic Quintile Derivation:** Calculates 5 quintile breakpoints from historical quote distributions, with automated fallback to spec baseline values (`$928.04 / $2,209 / $4,681 / $10,408.84`).
- **Supplier-Specific Overrides:** Configure individual supplier win-rate modifiers and lead-time offsets.

### 6. Live SQLite Database Inspector
- Integrated visual inspector to view raw SQLite database tables (`quotes`, `backlog`, `customers`, `suppliers`, `supplier_settings`, `model_coefficients`, `quote_band_thresholds`, `forecast_results`).

---

## 🛠️ Quickstart Guide

### 1. Launch the Application Server
Run the HTTP server via terminal:
```bash
python dashboard.py
```
Or launch via the workbench CLI:
```bash
python workbench.py serve
```

Open your browser and navigate to:
👉 **`http://localhost:8000`**

### 2. Run Command-Line Forecast Pipeline
To run the end-to-end forecast calculation directly in Python:
```bash
python main.py
```

---

## 📁 System Architecture & Directory Structure

```
python-quotation-forecast-engine/
├── dashboard.py               # REST API HTTP Backend Server (routes for forecast, upload, CRUD, settings)
├── database.py                # SQLite database connection, schema initialization, multi-table seeding
├── data_prep.py               # Standardization, repeat customer auto-tagging, quintile derivation, lifecycle
├── pipeline_forecast.py       # Logistic regression win probability scoring & Monte Carlo lead time simulation
├── backlog_forecast.py        # Order book backlog PO-matching & delivery/payment offset date arithmetic
├── main.py                    # Master CLI orchestrator
├── static/
│   ├── index.html             # Single-Page UI layout based on Laws of UX
│   ├── style.css              # Glassmorphism dark mode CSS theme
│   └── script.js              # Modular frontend client JS (API fetch, charting, What-If toggles, CRUD, mapper)
├── customer.csv               # Existing customer register
├── supplier.csv               # Supplier directory & lead times
├── F6 - Order Book by Item.csv # Sales order backlog items
└── KS Quotations.csv          # Sample quote register
```

---

## 🧪 Verification & Manual Testing

1. **Upload Data:** Click **Import & Header Mapping** tab, drag & drop `KS Quotations.csv`, `customer.csv`, or `F6 - Order Book by Item.csv`, map column headers, and confirm ingestion.
2. **What-If Sensitivity:** Navigate to **What-If Sensitivity**, toggle coefficients ON or OFF, and observe real-time forecast chart adjustments.
3. **CRUD Operations:** Open **Quote & Backlog CRUD**, add a new quote or edit confidence levels, and observe live updates across the dashboard.
4. **Inspect Database:** Open **Live DB Inspector** to browse raw SQLite tables.
