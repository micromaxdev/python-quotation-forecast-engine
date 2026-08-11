"""
workbench.py
------------
The Interactive Sandbox & Step-by-Step Test Runner for the Intern Developer.

USAGE INSTRUCTIONS:
  - List all steps:        python workbench.py list
  - Run single step:       python workbench.py 1    (or python workbench.py step1)
  - Run all steps:         python workbench.py run-all
  - Start Web Visualizer:  python workbench.py serve
"""

import sys
import os
import pandas as pd
import database
import data_prep
import pipeline_forecast
import backlog_forecast

# Step Registry detailing each step for the intern
STEPS_REGISTRY = {
    1: {
        "name": "standardize_column_names",
        "module": "data_prep",
        "description": "Step 1: Clean column names (lowercase, strip, snake_case)",
        "function": data_prep.standardize_column_names,
        "input_type": "quotes"
    },
    2: {
        "name": "handle_missing_values",
        "module": "data_prep",
        "description": "Step 2: Drop missing critical values and impute defaults",
        "function": data_prep.handle_missing_values,
        "input_type": "step1"
    },
    3: {
        "name": "map_quote_bands",
        "module": "data_prep",
        "description": "Step 3: Classify deal size into Small, Medium, Large bands",
        "function": data_prep.map_quote_bands,
        "input_type": "step2"
    },
    4: {
        "name": "map_fiscal_quarters",
        "module": "data_prep",
        "description": "Step 4: Map close dates to fiscal quarters (e.g. Q3-2026)",
        "function": data_prep.map_fiscal_quarters,
        "input_type": "step3"
    },
    5: {
        "name": "calculate_win_probability",
        "module": "pipeline_forecast",
        "description": "Step 5: Apply logistic regression weights for win probability",
        "function": pipeline_forecast.calculate_win_probability,
        "input_type": "step4"
    },
    6: {
        "name": "calculate_expected_won_value",
        "module": "pipeline_forecast",
        "description": "Step 6: Compute Expected Won Value (Quote Value * Win Probability)",
        "function": pipeline_forecast.calculate_expected_won_value,
        "input_type": "step5"
    },
    7: {
        "name": "calculate_expected_delivery_date",
        "module": "backlog_forecast",
        "description": "Step 7: Perform datetime addition for expected delivery date",
        "function": backlog_forecast.calculate_expected_delivery_date,
        "input_type": "backlog"
    },
    8: {
        "name": "calculate_expected_invoice_date",
        "module": "backlog_forecast",
        "description": "Step 8: Add payment terms offset (Net 30) for invoice date",
        "function": backlog_forecast.calculate_expected_invoice_date,
        "input_type": "step7"
    }
}


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def list_steps():
    print_banner("INTERN WORKBENCH - GUIDED STEPS")
    print("Run any step with: python workbench.py <step_number>\n")
    for num, info in STEPS_REGISTRY.items():
        print(f"  [Step {num}] {info['module']}.{info['name']}()")
        print(f"           --> {info['description']}\n")
    print("  [Server] python workbench.py serve  (Launch web visualizer)")
    print("  [All]    python workbench.py run-all (Execute complete forecast pipeline)\n")


def get_input_dataframe(input_type: str) -> pd.DataFrame:
    """Fetch input dataset for a step."""
    database.initialize_database()
    if input_type == "quotes":
        return database.load_quotes_from_db()
    elif input_type == "backlog":
        return database.load_backlog_from_db()
    elif input_type.startswith("step"):
        prev_step_num = int(input_type.replace("step", ""))
        return run_step(prev_step_num, save_to_db=False)
    else:
        raise ValueError(f"Unknown input type: {input_type}")


def run_step(step_num: int, save_to_db: bool = True) -> pd.DataFrame:
    """Execute a single step function, print comparison, and update SQLite visualizer."""
    if step_num not in STEPS_REGISTRY:
        print(f"[ERROR] Invalid step number '{step_num}'. Use 1 through 8.")
        sys.exit(1)

    info = STEPS_REGISTRY[step_num]
    print_banner(f"RUNNING STEP {step_num}: {info['module']}.{info['name']}()")
    print(f"Description: {info['description']}\n")

    input_df = get_input_dataframe(info['input_type'])

    print("--- [INPUT DATAFRAME] (Before Function Call) ---")
    print(input_df.head(4).to_string(index=False))

    try:
        # Call the intern's pure function
        output_df = info['function'](input_df)
    except Exception as e:
        print(f"\n[ERROR] STEP {step_num} crashed with exception:")
        print(f"   {type(e).__name__}: {e}")
        sys.exit(1)

    print("\n--- [OUTPUT DATAFRAME] (After Function Call) ---")
    print(output_df.head(4).to_string(index=False))

    if save_to_db:
        # Save output to step table in database for visual inspector
        table_name = f"step{step_num}_output"
        database.save_step_output_to_db(output_df, f"{step_num}_output")
        print(f"\n[SUCCESS] Output saved to SQLite table '{table_name}'.")
        print(f"Web Visualizer: http://localhost:8000")

    return output_df


def run_all_steps():
    print_banner("EXECUTION ENGINE - RUNNING ALL PIPELINE STEPS")
    database.initialize_database()

    # Pipeline branch (Quotes)
    df_quotes = database.load_quotes_from_db()
    df_prep = data_prep.prepare_dataset(df_quotes)
    df_pipeline = pipeline_forecast.run_pipeline_forecast(df_prep)

    # Backlog branch (Orders)
    df_backlog = database.load_backlog_from_db()
    df_backlog_fc = backlog_forecast.run_backlog_forecast(df_backlog)

    print("\n--- [FINAL PIPELINE FORECAST SUMMARY] ---")
    print(df_pipeline[["quote_id", "customer", "quote_value", "quote_band", "win_probability", "expected_won_value"]].to_string(index=False))

    print("\n--- [FINAL BACKLOG FORECAST SUMMARY] ---")
    print(df_backlog_fc[["order_id", "customer", "order_value", "order_date", "expected_delivery_date", "expected_invoice_date"]].to_string(index=False))

    # Save to forecast_results
    pipeline_records = df_pipeline.rename(columns={
        "quote_id": "entity_id",
        "expected_won_value": "expected_value",
        "close_date": "expected_date"
    })[["entity_id", "expected_value", "expected_date"]].copy()
    pipeline_records["forecast_type"] = "Pipeline Quote"

    backlog_records = df_backlog_fc.rename(columns={
        "order_id": "entity_id",
        "order_value": "expected_value",
        "expected_invoice_date": "expected_date"
    })[["entity_id", "expected_value", "expected_date"]].copy()
    backlog_records["forecast_type"] = "Committed Backlog"

    consolidated = pd.concat([pipeline_records, backlog_records], ignore_index=True)
    database.save_forecast_to_db(consolidated, table_name="forecast_results", if_exists="replace")

    print("\n[SUCCESS] CONSOLIDATED FORECAST SAVED TO 'forecast_results' TABLE!")
    print("View full visual comparison on dashboard: http://localhost:8000")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "list"]:
        list_steps()
        return

    cmd = sys.argv[1].lower()

    if cmd == "serve":
        import dashboard
        dashboard.start_server()

    elif cmd == "run-all":
        run_all_steps()

    else:
        # Handle step numbers like "1", "step1", "2", "step2"
        step_str = cmd.replace("step", "")
        if step_str.isdigit():
            run_step(int(step_str))
        else:
            print(f"Unknown command: '{cmd}'. Run 'python workbench.py list' for instructions.")


if __name__ == "__main__":
    main()
