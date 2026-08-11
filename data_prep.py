"""
data_prep.py
------------
Module for data ingestion, cleaning, normalization, and feature mapping for the Sales Forecasting Engine.

INTERN WORKSPACE:
Each function in this module is a PURE FUNCTION:
  - Input: a pandas DataFrame (plus optional helper arguments)
  - Output: a NEW modified pandas DataFrame (return df.copy() modifications)
  - Rules: Do NOT edit database connections or file loading here! Just transform the DataFrame.
"""

import pandas as pd


# =============================================================================
# BOILERPLATE (PRE-BUILT FOR INTERN)
# =============================================================================

def load_raw_data(file_path: str) -> pd.DataFrame:
    """Load raw quotation or order backlog data from a CSV or Excel file."""
    if file_path.lower().endswith(".csv"):
        return pd.read_csv(file_path)
    elif file_path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path}")


# =============================================================================
# STEP 1: COLUMN STANDARDIZATION (INTERN STEP 1)
# =============================================================================

def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Step 1: Clean and standardize DataFrame column headers.

    Goal:
      - Convert column names to lowercase
      - Strip leading and trailing whitespace
      - Replace spaces with underscores '_'

    Example Input Columns:  [' Quote ID ', 'Quote Value', 'CLOSE DATE']
    Example Output Columns: ['quote_id', 'quote_value', 'close_date']
    
    Test with: `python workbench.py 1`
    """
    df = df.copy()
    
    # INTERN TODO: Implement column cleaning logic below
    # Hint: df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    return df


# =============================================================================
# STEP 2: MISSING VALUE HANDLING (INTERN STEP 2)
# =============================================================================

def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Step 2: Filter out or impute rows with missing values in critical columns.

    Goal:
      - Remove any row where 'quote_value' or 'close_date' is missing (NaN)
      - Fill missing 'customer_tier' values with "Tier 3" default

    Test with: `python workbench.py 2`
    """
    df = df.copy()

    # INTERN TODO: Handle missing values below
    # Hint 1: df = df.dropna(subset=['quote_value', 'close_date'])
    # Hint 2: df['customer_tier'] = df['customer_tier'].fillna('Tier 3')
    if 'quote_value' in df.columns:
        df = df.dropna(subset=['quote_value'])
    if 'close_date' in df.columns:
        df = df.dropna(subset=['close_date'])
    if 'customer_tier' in df.columns:
        df['customer_tier'] = df['customer_tier'].fillna('Tier 3')

    return df


# =============================================================================
# STEP 3: QUOTE VALUE BAND MAPPING (INTERN STEP 3)
# =============================================================================

def map_quote_bands(df: pd.DataFrame, value_column: str = "quote_value") -> pd.DataFrame:
    """
    Step 3: Categorize sales quotes into value size bands.

    Goal:
      Add a new column named 'quote_band' based on 'quote_value':
        - 'Small'  : quote_value < 10,000
        - 'Medium' : 10,000 <= quote_value < 50,000
        - 'Large'  : quote_value >= 50,000

    Test with: `python workbench.py 3`
    """
    df = df.copy()

    # INTERN TODO: Categorize quote sizes below
    # Hint: You can use pd.cut() or a custom helper function with df[value_column].apply(...)
    def classify(val):
        if val < 10000:
            return "Small"
        elif val < 50000:
            return "Medium"
        else:
            return "Large"

    if value_column in df.columns:
        df["quote_band"] = df[value_column].apply(classify)
    else:
        df["quote_band"] = "Unknown"

    return df


# =============================================================================
# STEP 4: FISCAL QUARTER MAPPING (INTERN STEP 4)
# =============================================================================

def map_fiscal_quarters(df: pd.DataFrame, date_column: str = "close_date") -> pd.DataFrame:
    """
    Step 4: Map date strings to Fiscal Quarter tags (e.g. "Q1-2026", "Q3-2026").

    Goal:
      - Convert date_column to pandas datetime: pd.to_datetime(df[date_column])
      - Extract year and quarter (e.g. Quarter 1 -> "Q1", Year 2026 -> "2026")
      - Add a new column named 'fiscal_quarter' with format "Q{quarter}-{year}"

    Test with: `python workbench.py 4`
    """
    df = df.copy()

    # INTERN TODO: Parse datetime and add 'fiscal_quarter' column below
    # Hint:
    # dates = pd.to_datetime(df[date_column])
    # df['fiscal_quarter'] = "Q" + dates.dt.quarter.astype(str) + "-" + dates.dt.year.astype(str)
    if date_column in df.columns:
        dates = pd.to_datetime(df[date_column], errors="coerce")
        df["fiscal_quarter"] = "Q" + dates.dt.quarter.astype(str) + "-" + dates.dt.year.astype(str)
    else:
        df["fiscal_quarter"] = "N/A"

    return df


# =============================================================================
# FULL DATA PREP PIPELINE (PRE-BUILT FOR INTERN)
# =============================================================================

def prepare_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Master orchestrator executing data prep Steps 1 -> 4 sequentially."""
    df = standardize_column_names(df)
    df = handle_missing_values(df)
    df = map_quote_bands(df)
    df = map_fiscal_quarters(df)
    return df
