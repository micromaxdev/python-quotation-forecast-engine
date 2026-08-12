# Sales Forecast Engine — Technical Specification

**Source artifact:** `Sale_Forecast_Engine.xlsx` (9 sheets, reverse-engineered from formulas)
**Purpose of this document:** a build spec for a developer to re-implement this workbook as an interactive, dynamic application (web app, notebook, or service) in any stack.

---

## 1. System Overview

The workbook is a **two-limb sales forecasting engine** that predicts monthly invoiced revenue by combining:

1. **Pipeline Forecast** — open quotes, weighted by a logistic-regression-style *predicted win probability*, projected forward through an order-to-invoice lead-time chain.
2. **Backlog Forecast** — already-won/confirmed sales orders, projected forward through a procurement-to-delivery lead-time chain (with PO-matching logic).

Both limbs resolve to a **Forecast Month** per line item, which are then aggregated (pivot-style) into a monthly `Forecast Sales = Pipeline Forecast Sales + Backlog Forecast Sales` time series.

```
Quotation (raw quotes) ─┐
                         ├─▶ Pipeline (win-probability model + lead-time chain) ─▶ Forecast Month ─┐
Predicted Win Proba      │                                                                          │
 (logistic coefficients)─┘                                                                          ├─▶ Sales Forecast
                                                                                                      │   (monthly pivot,
Won (confirmed orders) ──▶ Back Log (PO-matching + lead-time chain) ─▶ Forecast Month ───────────────┘    Pipeline + Backlog)
Backlog assumption
 (per-customer/region
  transit-time lookup)
```

Status/state reference tables (`Status`) feed flags used elsewhere in the model (Active/Won/Closed/Lost).

---

## 2. Data Model (Sheets → Tables)

### 2.1 `Quotation` — raw quote register (source of truth)
Grain: one row per quote.

| Field | Type | Notes |
|---|---|---|
| Quote Ref No | string (PK) | e.g. `QRN7890` |
| Quote Date | date | |
| Month / Quarter | derived | `Quarter` = `"Q{n} /{year}"` string |
| Customer Code, Customer Name | string | |
| Customer Type | enum | `New`, `Repeat` |
| State | enum | AU states + NZ/Singapore/Indonesia/other |
| Account Manager | string | initials |
| Confidence level | enum | `Low/Medium/High` (not currently used in the win-prob formula — candidate input) |
| Quote Value | decimal | AUD |
| Status | enum code | joins to `Status` sheet (`A`=Active, `W`=Won, `C`=Closed, `L`=Lost) |
| **Quote Band** | *derived* | see §3.1 |
| Expected Order Date, Order Received Date, Last Follow Up Date | date | |

### 2.2 `Status` — lookup table
Columns: `Status, Active, Won, Closed, Lost` — a one-hot flag table keyed by status code (e.g. row `A → Active=1, Won=0, Closed=0, Lost=0`). Implement as an enum/dict, not a join table, in code.

### 2.3 `Pipeline` — working table for open quotes (the win-probability engine)
Superset of `Quotation` fields plus derived columns described in §3. This is the core computed table for open opportunities.

### 2.4 `Predicted Win Proba` — model coefficients (logistic regression)
This is a **hand-fit logistic regression** with two categorical predictors, stored as a coefficient lookup:

- `Intercept` = `I2` = **0.996171**
- **Quarter** coefficients (`B3:C8`, categorical dummy-encoded by quarter):
  | Quarter | Estimate |
  |---|---|
  | Q1/2025 | 0.309252 |
  | Q1/2026 | 0.330152 |
  | Q2/2025 | 0.361671 |
  | Q2/2026 | 1.065487 |
  | Q3/2025 | 0.654613 |
  | Q4/2025 | 0 |
- **Quote Band** coefficients (`E3:F7`):
  | Band | Estimate |
  |---|---|
  | Very Small | 0 |
  | Small | -0.49048 |
  | Medium | -0.62943 |
  | Large | -0.79677 |
  | Very Large | -1.35842 |

A secondary scratch area (cols B–L, rows ~11+) recomputes the same sigmoid per quarter/band combination and produces a *Quote Band* re-classification using **different thresholds** than the main one (`1075.4 / 2606.04 / 5527.8 / 12827.2` vs. the primary `928.04 / 2209 / 4681 / 10408.84`) — this looks like a model-validation/backtest area rather than production logic. **Recommendation:** implement only the primary threshold set in production; keep the secondary set behind a "model diagnostics" flag if reproduced at all.

### 2.5 `Won` — confirmed/won sales orders
Grain: one row per sale order linked to its source quote (`Quote Ref No`). Same `Quote Band` derivation as `Quotation`. Feeds into `Back Log`.

### 2.6 `Backlog assumption` — lookup/reference tables
Two independent lookup tables on one sheet:
- **Customer → State/Country** (`A:B`, 32 rows) — used to resolve a sale order's destination when not explicitly stated.
- **Timing assumption ranges** (`I:K`) — min/max day ranges used as the *basis* for the RANDBETWEEN simulation in `Back Log` (Warehouse processing 1–3d, PO processing 1–5d, Supplier lead time 7–90d, Invoice delay 0–3d). A separate **Destination → Assumed Transit Time** band table (`E:F`, keyed by state) supplies transit-time ranges (e.g. NSW/ACT 0-1 day, WA/NT 5-8 days, Singapore 8-12 days, international 7-10 days default).

### 2.7 `Back Log` — open sales orders vs. purchase orders (procurement chain)
Grain: two parallel tables sharing a sheet — a Part/PO ledger (`A:E`) and a Sale-Order backlog ledger (`H:AM`) — joined by `Part Code`.

### 2.8 `Sales Forecast` — output aggregation
Two PivotTables:
- **Pivot 1** (`A:F`): Pipeline Forecast Sales + Backlog Forecast Sales by month → `Forecast Sales`.
- **Pivot 2** (`I:M`): raw sum of Expected Invoiced Value / Outstanding Value by Forecast Month, used to build Pivot 1's source data.

---

## 3. Business Logic / Formulas (the part that matters)

### 3.1 Quote Band classification (used in `Quotation`, `Pipeline`, `Won`)
```
QuoteBand(QuoteValue):
    if QuoteValue <= 928.04:    return "Very Small"
    elif QuoteValue <= 2209:    return "Small"
    elif QuoteValue <= 4681:    return "Medium"
    elif QuoteValue <= 10408.84: return "Large"
    else:                        return "Very Large"
```
These 5 breakpoints are almost certainly **quintile cut points** derived from historical quote-value distribution — treat as a configurable parameter set (see §5), not a hardcoded constant.

### 3.2 Win-probability model (logistic regression), `Pipeline` cols T–X
```
quarter_coef   = lookup(Quote.Quarter, QUARTER_COEFFICIENTS)      # T
band_coef      = lookup(Quote.QuoteBand, BAND_COEFFICIENTS)       # U
logit          = INTERCEPT + quarter_coef + band_coef             # V
win_prob       = 1 / (1 + exp(-logit))                             # W  (sigmoid)
expected_won_value = win_prob * QuoteValue                         # X
```
This is a standard **logistic regression scoring formula**: `p = sigmoid(β0 + β_quarter + β_band)`. In code, replace the two `XLOOKUP`s with a dict/dataframe join, and keep intercept + coefficients as a versioned config (ideally re-fit periodically from `Won` vs. `Lost` history — the workbook does not show the fitting step, only the scored coefficients).

### 3.3 Follow-up / expiry workflow, `Pipeline` cols O, Q, R, S
```
first_follow_up   = WORKDAY(QuoteDate, +7)                          # O — next business day +7
expiry_date        = QuoteDate + IFS(                                # Q
                        QuoteBand == "Very Small", 45,
                        QuoteBand == "Small",      90,
                        QuoteBand == "Medium",     150,
                        QuoteBand == "Large",      210,
                        QuoteBand == "Very Large", 330)
next_follow_up      = LastFollowUpDate + 7                           # R
follow_up_status     = "Expired"   if today > expiry_date            # S
                        "Overdue"  elif today > next_follow_up
                        "Due Today" elif today == next_follow_up
                        else "Not Due"
```
Business meaning: bigger quotes are given a longer shelf-life before being treated as expired (45 days for Very Small quotes up to 330 days / ~11 months for Very Large). This is a pure workflow/CRM feature, independent of the win-probability math — implement as a separate "quote lifecycle" service.

### 3.4 Pipeline → invoice lead-time chain, `Pipeline` cols AC–AM
Each open quote, once "won" (probabilistically), is walked through an order-to-cash timeline:
```
ProjectedSalesOrderDate  = ExpectedOrderDate      (AC, from Quotation/Expected Order Date)
ExpectedInvoicedValue    = win_prob * QuoteValue    (AD — same as Expected Won Value)
WarehouseProcessingDays  = random sample in [1,3]   (AE)
POProcessingDays         = random sample in [1,5]    (AF)
SupplierLeadTimeDays     = random sample in [7,90]   (AG)
TransitTimeDays          = random sample by destination band (AH)
InvoiceDelayDays         = random sample in [0,3]    (AI)

ExpectedSupplierDate = ProjectedSalesOrderDate + POProcessingDays + SupplierLeadTimeDays   # AJ
ExpectedDeliveryDate = ExpectedSupplierDate + WarehouseProcessingDays + TransitTimeDays     # AK
ExpectedInvoiceDate  = ExpectedDeliveryDate + InvoiceDelayDays                              # AL
ForecastMonth        = FORMAT(ExpectedInvoiceDate, "MMM-YYYY")                              # AM
```
**Important implementation note:** in the source workbook, columns AE–AI are **static/pasted values**, not live formulas — they were generated once via `RANDBETWEEN()` (visible as live formulas in the analogous `Back Log` sheet, §3.5) and then frozen. A faithful re-implementation should make this an explicit **Monte-Carlo simulation step**: sample each lead-time component from its assumption range (from `Backlog assumption`) every time the forecast is regenerated, ideally running N simulations and reporting a distribution (P50/P10/P90) per forecast month rather than a single point value. This is the single biggest opportunity for the new tool to be more rigorous than the spreadsheet.

### 3.5 Backlog: PO matching + delivery chain, `Back Log` sheet
Ledger 1 (Part/PO, cols A–E): `Part Code, Sale Order Qty, Item No, Purchase Order Qty, Purchase Due Date` — the open purchase-order book.

Ledger 2 (Sale-order backlog, cols H–AM):
```
State                = XLOOKUP(CustomerName, BacklogAssumption.CustomerName, BacklogAssumption.State)   # K
OrderReceivedDate    = SaleDueDate - (WarehouseDays+OrdersDays+SupplierLeadTime+TransitTime+InvoiceDelay) # L (back-calculated)
SaleStatus           = "Over Due" if SaleDueDate < EarliestPODueDate else "Not Due"                       # N
TotalOutstandingPOQty = SUMIFS(PO_Qty, PO_PartCode, ThisPartCode)                                          # P
MatchStatus          = "Matching PO" if TotalOutstandingPOQty > 0 else "No Matching PO"                    # Q
EarliestPODueDate    = MINIFS(PurchaseDueDate, PO_PartCode==PartCode, PO_Qty>0)  [IFERROR → blank]          # R
POStatus             = "No PO Date" if EarliestPODueDate blank                                              # S
                        "PO Overdue" if EarliestPODueDate < today
                        else "PO Scheduled"
SupplierDelayDays    = RANDBETWEEN(7,60) if POStatus=="PO Overdue" else "" (blank)                          # T

WarehouseProcessingDays = random [1,3]      # U
OrdersProcessingDays    = random [1,5]      # V   (labelled "PO processing days" in assumptions)
SupplierLeadTime        = random [7,90]     # W
TransitTime              = random, by destination-state band (see §2.6)                                     # X
InvoiceDelayDays         = random [0,3]     # Y

ExpectedSupplierDate = IFS(                                                                                  # Z
    POStatus=="No PO Date",  OrderReceivedDate + SupplierLeadTime + TransitTime,
    POStatus=="PO Scheduled", EarliestPODueDate,
    POStatus=="PO Overdue",   EarliestPODueDate + SupplierDelayDays)
ExpectedDeliveryDate = MAX(SaleDueDate, ExpectedSupplierDate + WarehouseProcessingDays + TransitTime)         # AA
ExpectedInvoiceDate  = ExpectedDeliveryDate + InvoiceDelayDays                                                 # AB
ForecastMonth        = FORMAT(ExpectedInvoiceDate, "MMM-YYYY")                                                 # AC
```
Destination-based `CustomerDeliveryDays` (col AF, sampled separately) is a state-keyed random-range table:
```
NSW/ACT: 0–1d   VIC/QLD: 1–2d   SA: 3–5d   TAS: 5–7d   WA/NT: 5–8d
New Zealand: 7–9d   Singapore: 8–12d   default (other intl): 7–10d
```

**Bugs/inconsistencies to fix in re-implementation, not replicate:**
- `Back Log!K` (State/Country lookup) references `'[1]Backlog [1]assumption'` — a broken/external-workbook reference (shows `#ERROR!` in the sample data) in some rows, and a corrupted `xlfn.XLOOKUP` (missing leading `_`) in others. Rebuild as a clean in-app join to the Backlog-assumption customer table.
- `Back Log!R` uses `MINIFS` (a post-2007 function) via an LibreOffice-only `_xludf.` shim — use a native `MIN` over a filtered set in code.
- `OrderReceivedDate` (`L`) is defined *backwards* from `SaleDueDate` minus lead times — this is circular/definitional, not a genuine "received date." Treat it as a derived planning field only, and source the real received date from the transactional system if available.

### 3.6 Forecast aggregation, `Sales Forecast`
```
PivotSourcePipeline = SUM(Pipeline.ExpectedInvoicedValue) GROUP BY Pipeline.ForecastMonth
PivotSourceBacklog  = SUM(BackLog.OutstandingValue)       GROUP BY BackLog.ForecastMonth
ForecastSales[month] = PipelineForecastSales[month] + BacklogForecastSales[month]
```
Output grain: one row per calendar month (`Jan…Dec`), for a given forecast year, three columns: Pipeline$, Backlog$, Total$.

---

## 4. Recommended Application Architecture

| Layer | Responsibility | Suggested approach |
|---|---|---|
| **Data ingestion** | Load Quotation, Won, Back Log/PO ledger, Backlog-assumption reference tables | CSV/DB import or CRM API sync (replace manual quote register) |
| **Reference/config store** | Quote-band thresholds, logistic-regression coefficients (intercept, per-quarter, per-band), lead-time assumption ranges (min/max by stage and by destination state) | Versioned config table (DB or JSON), editable via admin UI — these are business assumptions that should be tunable without a code deploy |
| **Scoring engine** | Quote Band classification, win-probability sigmoid scoring, expected-won-value | Pure function per quote; vectorize with pandas/numpy or equivalent |
| **Simulation engine** | Lead-time chain for Pipeline and Backlog — sample from assumption ranges (ideally per-stage distributions, not just uniform min/max) to produce Expected Invoice Date; run as Monte Carlo (N≥1000 draws) to get a forecast distribution per month, not a single value | Python (numpy random), or any stats-capable backend |
| **Aggregation** | Group scored/simulated line items by Forecast Month; sum Pipeline + Backlog | groupby/pivot equivalent |
| **API layer** | Serve forecast series (monthly totals, P10/P50/P90 bands), plus drill-down to line-item level | REST/GraphQL |
| **Frontend** | Interactive dashboard: monthly forecast chart (stacked Pipeline vs Backlog), quote-band distribution, pipeline follow-up worklist (Expired/Overdue/Due Today), PO-match/backlog risk view, and an assumptions editor for the config store | React + charting lib (e.g. Recharts/D3); table views with filters by Account Manager / State / Customer Type |

### Suggested normalized schema
- `quotes` (id, quote_ref, quote_date, customer_id, customer_type, state, account_manager, confidence_level, quote_value, status, expected_order_date, order_received_date, last_follow_up_date)
- `won_orders` (id, sale_order_no, quote_ref FK, quote_value, order_received_date, expected_order_date, last_follow_up_date)
- `purchase_orders` (part_code, item_no, po_qty, po_due_date)
- `sale_order_backlog` (part_code, customer_id, state, order_received_date, sale_due_date, outstanding_value)
- `customers` (id, name, state_country)
- `model_config` (key, value, effective_date) — stores intercept, quarter coefficients, band coefficients, quote-band thresholds
- `leadtime_assumptions` (stage, min_days, max_days) and `transit_time_assumptions` (destination_state, min_days, max_days)

### Key interactive features to add beyond the spreadsheet
1. **Editable assumptions** — let a user tune lead-time ranges, thresholds, and regression coefficients and see the forecast recompute live.
2. **Confidence intervals** — replace the frozen single-sample lead times with a live Monte Carlo simulation producing P10/P50/P90 bands per forecast month.
3. **Model refresh** — a periodic re-fit of the logistic regression against actual Won/Lost outcomes (the workbook only stores fitted coefficients, not the fitting process).
4. **Drill-through** — click a forecast month to see the underlying quotes/orders driving it.
5. **Pipeline health worklist** — surface `Follow Up Status` (Expired/Overdue/Due Today) and PO Status (Overdue/Scheduled/No PO Date) as actionable queues for Account Managers and procurement.

---

## 5. Configurable Parameters (extract these as settings, not constants)

| Parameter | Current value(s) |
|---|---|
| Quote Band thresholds | 928.04 / 2209 / 4681 / 10408.84 |
| Logistic regression intercept | 0.996171 |
| Quarter coefficients | Q1/2025: 0.309, Q1/2026: 0.330, Q2/2025: 0.362, Q2/2026: 1.065, Q3/2025: 0.655, Q4/2025: 0 |
| Band coefficients | Very Small: 0, Small: -0.490, Medium: -0.629, Large: -0.797, Very Large: -1.358 |
| Quote expiry window by band | 45 / 90 / 150 / 210 / 330 days |
| Follow-up cadence | first follow-up = quote date + 7 business days; subsequent = last follow-up + 7 days |
| Lead-time ranges (days) | Warehouse 1–3, PO processing 1–5, Supplier lead time 7–90, Invoice delay 0–3 |
| Transit time by destination | NSW/ACT 0–1, VIC/QLD 1–2, SA 3–5, TAS 5–7, WA/NT 5–8, NZ 7–9, Singapore 8–12, other intl 7–10 |
| Supplier delay (if PO overdue) | random 7–60 days |

---

## 6. Open Questions for the Intern / Business Owner
- What data was the logistic regression fit on, and how often should it be refit?
- Are the Quote-Band thresholds fixed policy or statistically derived (e.g. quintiles) — and from what population?
- Should lead-time ranges vary by supplier/part rather than being global constants?
- Is `Confidence level` (Quotation col J) intended to feed the win-probability model? It's captured but currently unused in the scoring formula.
