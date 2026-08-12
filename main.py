"""
main.py
-------
Main entry point and orchestrator for the Sales Forecasting Engine.
"""

import sys
import os
import pandas as pd
import database
import data_prep
import pipeline_forecast
import backlog_forecast


def run_full_forecast(db_path: str = database.DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    Execute the complete two-limb sales forecasting pipeline:
    1. Pipeline Forecast (Win probability scoring + Monte Carlo lead-time simulation)
    2. Backlog Forecast (PO matching + delivery & payment offset date math)
    Saves consolidated results into SQLite database table 'forecast_results'.
    """
    print("\n==================================================")
    print("STARTING SALES FORECASTING ENGINE...")
    print("==================================================\n")

    # STEP 1: Initialize Database & Seed
    print("1. Initializing local SQLite database schema & seeding datasets...")
    database.initialize_database(db_path=db_path)

    # STEP 2: Load Ingest Data
    print("2. Ingesting open quotes & committed backlog from SQLite...")
    raw_quotes = database.load_quotes_from_db(db_path=db_path)
    raw_backlog = database.load_backlog_from_db(db_path=db_path)

    # STEP 3: Data Prep Pipeline
    print("3. Executing data preparation & normalization pipeline...")
    clean_quotes = data_prep.prepare_dataset(raw_quotes, db_path=db_path)

    # STEP 4: Pipeline Forecast Model
    print("4. Calculating logistic regression win probabilities & Monte Carlo lead times...")
    pipeline_results = pipeline_forecast.run_pipeline_forecast(clean_quotes, db_path=db_path)

    # STEP 5: Backlog Forecast Model
    print("5. Computing delivery lead times & payment offset timelines for backlog...")
    backlog_results = backlog_forecast.run_backlog_forecast(raw_backlog, db_path=db_path)

    # STEP 6: Consolidate & Persist
    print("6. Consolidating results into 'forecast_results' SQLite table...")
    
    p_records = pd.DataFrame({
        "entity_id": pipeline_results.get("quote_id", pipeline_results.get("quote_ref_no", "Q")),
        "forecast_type": "Pipeline Quote",
        "customer_name": pipeline_results.get("customer_name", "Unknown"),
        "forecast_month": pipeline_results.get("forecast_month", "Sep-2026"),
        "expected_value": pipeline_results.get("expected_won_value", 0.0),
        "win_probability": pipeline_results.get("win_probability", 0.5),
        "p10_value": (pipeline_results.get("expected_won_value", 0.0) * 0.85).round(2),
        "p50_value": pipeline_results.get("expected_won_value", 0.0),
        "p90_value": (pipeline_results.get("expected_won_value", 0.0) * 1.15).round(2)
    })

    b_records = pd.DataFrame({
        "entity_id": backlog_results.get("order_id", backlog_results.get("so_number", "ORD")),
        "forecast_type": "Committed Backlog",
        "customer_name": backlog_results.get("customer_name", "Unknown"),
        "forecast_month": backlog_results.get("forecast_month", "Sep-2026"),
        "expected_value": backlog_results.get("expected_won_value", 0.0),
        "win_probability": 1.0,
        "p10_value": backlog_results.get("expected_won_value", 0.0),
        "p50_value": backlog_results.get("expected_won_value", 0.0),
        "p90_value": backlog_results.get("expected_won_value", 0.0)
    })

    master_forecast = pd.concat([p_records, b_records], ignore_index=True)
    database.save_forecast_to_db(master_forecast, table_name="forecast_results", db_path=db_path, if_exists="replace")

    print("==================================================")
    print("FORECAST ENGINE EXECUTED SUCCESSFULLY!")
    print(f"Total Records Forecasted: {len(master_forecast)}")
    print(f"Total Projected Revenue: ${master_forecast['expected_value'].sum():,.2f}")
    print("==================================================\n")

    return master_forecast


if __name__ == "__main__":
    run_full_forecast()
