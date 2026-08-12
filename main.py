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
<<<<<<< Updated upstream
=======
import database

import argparse
def parse_arguments() -> Tuple[str, str]:
    parser = argparse.ArgumentParser(description="Sales Forecasting Engine")
    parser.add_argument(
        "--input",
         type=str, required=True, help= "D:\Intern\Quotation mock (version 1).xlsx"
    )
    parser.add_argument(
        "--output",
        type=str, required=True, help="D:\Intern\Sale Forecasting Engine.xlsx"
    )
    args = parser.parse_args()
    return args.input, args.output

    """
    Parse command-line arguments for input dataset path and output destination path.

    Returns:
        Tuple[str, str]: (input_file_path, output_file_path)
    """
    # TODO (Junior Dev): Implement argument parsing (e.g., using argparse or sys.argv)
    pass


def combine_forecasts(pipeline_df: pd.DataFrame, backlog_df: pd.DataFrame) -> pd.DataFrame:
    pipeline_df = pipeline_df.copy()
    backlog_df = backlog_df.copy()
    pipeline_df["forecast_type"] = "pipeline"
    backlog_df["forecast_type"] = "backlog"
    #Backlog entries are considered fully committed, so we can set win_probability to 1.0
    backlog_df["predicted_win_probability"] = 1.0
    #Pipeline has no delivery/invoice dates yet (deal hasn't closed), so leave them blank
    pipeline_df["expected_delivery_date"] = pd.NaT
    pipeline_df["expected_invoice_date"] = pd.NaT
    common_columns = [
        "fiscal_year",
        "fiscal_quarter",
        "expected_won_value",
        "predicted_win_probability",
        "expected_delivery_date",
        "expected_invoice_date",
        "forecast_type",
    ]
    master_df = pd.concat([pipeline_df, backlog_df], ignore_index=True)
    return master_df
    """
    Combine active pipeline forecast results and committed backlog forecast results
    into a unified forecast summary dataset.

    Args:
        pipeline_df (pd.DataFrame): Forecasted active pipeline data with predicted win probabilities and expected won values.
        backlog_df (pd.DataFrame): Forecasted backlog data with expected delivery and invoice dates.

    Returns:
        pd.DataFrame: Consolidated master forecast DataFrame.
    """
    # TODO (Junior Dev): Standardize schema across both models and concatenate/join into single master dataset
    pass


def export_results(master_df: pd.DataFrame, output_path: str) -> None:
    if output_path.lower().endswith(".csv"):
        master_df.to_csv(output_path, index=False)
    elif output_path.lower().endswith((".xlsx", ".xls")):
        master_df.to_excel(output_path, index=False)
    else:
        raise ValueError(f"Unsupported output file type: {output_path}")

    print(f"Forecast results saved to: {output_path}")
    total_expected_value = (master_df["expected_won_value"] * master_df["predicted_win_probability"]).sum()
    print(f"Total weighted forecasted revenue: {total_expected_value:,.2f}")
    print("\nForecast by fiscal quarter:")
    summary = (
        master_df
        .assign(weighted_value=master_df["expected_won_value"] * master_df["predicted_win_probability"])
        .groupby(["fiscal_year", "fiscal_quarter"])["weighted_value"]
        .sum()
    )
    print(summary)

    print("\nForecast by type (pipeline vs backlog):")
    print(master_df.groupby("forecast_type")["expected_won_value"].sum())
    """
    Export consolidated forecast results to disk (CSV/Excel) and display summary metrics.

    Args:
        master_df (pd.DataFrame): Consolidated master forecast dataset.
        output_path (str): File destination path.
    """
    # TODO (Junior Dev): Save DataFrame to CSV/Excel and print top-line summary stats to console
    pass
>>>>>>> Stashed changes


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
