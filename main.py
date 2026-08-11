"""
main.py
-------
Main entry point and orchestrator for the Sales Forecasting Engine.
"""

import sys
import pandas as pd
import database
import data_prep
import pipeline_forecast
import backlog_forecast


def main() -> None:
    """
    Main orchestration loop mapping out the step-by-step forecasting execution flow.
    """
    print("\n==================================================")
    print("STARTING SALES FORECASTING ENGINE...")
    print("==================================================\n")

    # STEP 1: Initialize Database
    print("1. Initializing local SQLite database schema & mock records...")
    database.initialize_database()

    # STEP 2: Load Ingest Data
    print("2. Ingesting open quotes & committed backlog from SQLite database...")
    raw_quotes = database.load_quotes_from_db()
    raw_backlog = database.load_backlog_from_db()

    # STEP 3: Data Prep Pipeline
    print("3. Executing data preparation & normalization pipeline...")
    clean_quotes = data_prep.prepare_dataset(raw_quotes)

    # STEP 4: Pipeline Forecast Model
    print("4. Calculating logistic regression win probabilities & weighted pipeline revenue...")
    pipeline_results = pipeline_forecast.run_pipeline_forecast(clean_quotes)

    # STEP 5: Backlog Forecast Model
    print("5. Computing operational lead times & payment offset timelines for backlog...")
    backlog_results = backlog_forecast.run_backlog_forecast(raw_backlog)

    # STEP 6: Consolidate & Persist
    print("6. Consolidating results and writing to 'forecast_results' SQLite table...")
    pipeline_records = pipeline_results.rename(columns={
        "quote_id": "entity_id",
        "expected_won_value": "expected_value",
        "close_date": "expected_date"
    })[["entity_id", "expected_value", "expected_date"]].copy()
    pipeline_records["forecast_type"] = "Pipeline Quote"

    backlog_records = backlog_results.rename(columns={
        "order_id": "entity_id",
        "order_value": "expected_value",
        "expected_invoice_date": "expected_date"
    })[["entity_id", "expected_value", "expected_date"]].copy()
    backlog_records["forecast_type"] = "Committed Backlog"

    master_forecast = pd.concat([pipeline_records, backlog_records], ignore_index=True)
    database.save_forecast_to_db(master_forecast, table_name="forecast_results", if_exists="replace")

    print("\n==================================================")
    print("FORECAST ENGINE EXECUTED SUCCESSFULLY!")
    print(f"Total Records Forecasted: {len(master_forecast)}")
    print(f"Total Projected Value:   ${master_forecast['expected_value'].sum():,.2f}")
    print("==================================================\n")


if __name__ == "__main__":
    main()
