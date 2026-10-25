import pandas as pd
from app import clean_data, profile_data, metric_column, numeric_series

def test_profile_data_counts_missing_and_duplicates():
    df = pd.DataFrame({"Sales": [10, 10, None], "Region": ["East", "East", "West"]})
    overview, duplicates, summary = profile_data(df)
    assert duplicates == 1
    assert int(overview.loc[overview["Column"] == "Sales", "Missing values"].iloc[0]) == 1

def test_clean_data_removes_duplicates_and_parses_dates():
    df = pd.DataFrame({"Order Date": ["2025-01-01", "2025-01-01"], "Category": [" A ", " A "]})
    cleaned, log = clean_data(df, "Leave missing values unchanged", True, True, True)
    assert len(cleaned) == 1
    assert pd.api.types.is_datetime64_any_dtype(cleaned["Order Date"])

def test_metric_column_aliases():
    df = pd.DataFrame({"Revenue": [100], "Qty": [2]})
    assert metric_column(df, "Sales") == "Revenue"
    assert metric_column(df, "Quantity") == "Qty"

def test_numeric_series_handles_currency():
    df = pd.DataFrame({"Sales": ["$1,200.50", "bad"]})
    values = numeric_series(df, "Sales")
    assert values.tolist() == [1200.5, 0.0]
