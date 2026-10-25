import json
from io import BytesIO
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Sales Analytics Dashboard", page_icon="📊", layout="wide")

REQUIRED_METRICS = ["Sales", "Profit", "Quantity"]
COLUMN_ALIASES = {
    "order id": "Order ID", "order_id": "Order ID", "orderid": "Order ID",
    "order date": "Order Date", "order_date": "Order Date", "date": "Order Date",
    "sales": "Sales", "revenue": "Sales", "profit": "Profit",
    "quantity": "Quantity", "qty": "Quantity",
    "category": "Category", "sub-category": "Sub-Category", "subcategory": "Sub-Category",
    "region": "Region", "state": "State", "city": "City",
    "segment": "Segment", "customer name": "Customer Name",
    "ship mode": "Ship Mode", "discount": "Discount"
}

def read_upload(uploaded_file):
    """Load CSV, Excel, or JSON into a DataFrame."""
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file)
    if name.endswith(".json"):
        raw = json.load(uploaded_file)
        if isinstance(raw, dict):
            # Support common JSON records containers.
            for key in ("data", "records", "rows", "items"):
                if key in raw and isinstance(raw[key], list):
                    raw = raw[key]
                    break
        return pd.json_normalize(raw)
    raise ValueError("Unsupported file type. Upload CSV, XLSX, or JSON.")

def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    renamed = {}
    for col in df.columns:
        key = " ".join(col.lower().replace("_", " ").split())
        renamed[col] = COLUMN_ALIASES.get(key, col)
    # Keep original names if aliases would cause duplicate columns.
    values = list(renamed.values())
    if len(values) == len(set(values)):
        df = df.rename(columns=renamed)
    return df

def clean_data(df, missing_strategy, remove_duplicates, standardize_text, parse_dates):
    """Apply user-selected cleanup operations and return data plus an audit log."""
    df = normalize_columns(df)
    log = []
    before = len(df)
    if remove_duplicates:
        count = int(df.duplicated().sum())
        df = df.drop_duplicates().copy()
        log.append(f"Removed {count} duplicate row(s).")
    else:
        log.append(f"Kept {int(df.duplicated().sum())} duplicate row(s).")
    if standardize_text:
        text_cols = df.select_dtypes(include=["object", "string"]).columns
        for col in text_cols:
            df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
            df[col] = df[col].replace({"": pd.NA, "NA": pd.NA, "N/A": pd.NA, "null": pd.NA})
        log.append("Trimmed text fields and normalized common blank markers.")
    if parse_dates:
        for col in df.columns:
            if "date" in str(col).lower():
                parsed = pd.to_datetime(df[col], errors="coerce")
                if parsed.notna().any():
                    df[col] = parsed
                    log.append(f"Parsed date column: {col}.")
    missing_before = int(df.isna().sum().sum())
    if missing_strategy == "Drop rows":
        df = df.dropna().copy()
        log.append(f"Dropped rows containing missing values ({before - len(df)} row(s) total removed including duplicates).")
    elif missing_strategy == "Fill numeric with median / text with mode":
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                if df[col].isna().any():
                    median = df[col].median()
                    df[col] = df[col].fillna(median if pd.notna(median) else 0)
            elif df[col].isna().any():
                modes = df[col].mode(dropna=True)
                df[col] = df[col].fillna(modes.iloc[0] if not modes.empty else "Unknown")
        log.append(f"Filled missing values ({missing_before} missing cell(s) before filling).")
    else:
        log.append(f"Left {missing_before} missing cell(s) unchanged.")
    return df, log

def profile_data(df):
    """Return shape, data types, missing values, duplicates, and numeric summaries."""
    overview = pd.DataFrame({
        "Column": df.columns,
        "Data type": [str(df[c].dtype) for c in df.columns],
        "Missing values": [int(df[c].isna().sum()) for c in df.columns],
        "Missing (%)": [round(float(df[c].isna().mean() * 100), 2) for c in df.columns],
        "Unique values": [int(df[c].nunique(dropna=True)) for c in df.columns],
    })
    return overview, int(df.duplicated().sum()), df.describe(include="all").transpose()

def metric_column(df, canonical):
    aliases = {
        "Sales": ["Sales", "Revenue", "Amount", "Total Sales"],
        "Profit": ["Profit", "Net Profit"],
        "Quantity": ["Quantity", "Qty", "Units"],
        "Order ID": ["Order ID", "Order_ID", "OrderID", "Order Number"]
    }
    for candidate in aliases.get(canonical, [canonical]):
        if candidate in df.columns:
            return candidate
    return None

def numeric_series(df, col):
    if col is None:
        return pd.Series(dtype="float64", index=df.index)
    return pd.to_numeric(df[col].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce").fillna(0)

def make_sample_data():
    return pd.DataFrame({
        "Order ID": ["O-1001", "O-1002", "O-1003", "O-1004", "O-1005", "O-1006"],
        "Order Date": pd.to_datetime(["2025-01-03", "2025-01-05", "2025-02-11", "2025-02-18", "2025-03-02", "2025-03-09"]),
        "Region": ["West", "East", "Central", "West", "South", "East"],
        "Category": ["Technology", "Furniture", "Office Supplies", "Technology", "Furniture", "Office Supplies"],
        "Sales": [850.0, 320.0, 95.0, 1250.0, 440.0, 180.0],
        "Profit": [170.0, -25.0, 22.0, 310.0, 60.0, 36.0],
        "Quantity": [2, 4, 5, 3, 2, 6],
        "Segment": ["Consumer", "Corporate", "Consumer", "Home Office", "Corporate", "Consumer"]
    })

st.title("Sales Analytics Dashboard")
st.caption("Upload sales data, validate its quality, clean it, and explore key business metrics.")

with st.sidebar:
    st.header("1. Upload data")
    uploaded = st.file_uploader("Choose CSV, Excel (.xlsx), or JSON", type=["csv", "xlsx", "json"])
    use_sample = st.checkbox("Use built-in sample data", value=uploaded is None)
    st.divider()
    st.header("2. Preprocessing")
    missing_strategy = st.selectbox("Missing-value strategy", [
        "Leave missing values unchanged",
        "Fill numeric with median / text with mode",
        "Drop rows"
    ])
    remove_duplicates = st.checkbox("Remove duplicate rows", value=True)
    standardize_text = st.checkbox("Trim text / normalize blank markers", value=True)
    parse_dates = st.checkbox("Parse date columns", value=True)

try:
    if uploaded is not None:
        raw_df = read_upload(uploaded)
    elif use_sample:
        raw_df = make_sample_data()
    else:
        st.info("Upload a file or select the sample dataset to begin.")
        st.stop()
    if raw_df.empty:
        st.error("The uploaded file contains no rows.")
        st.stop()
    if len(raw_df.columns) == 0:
        st.error("No columns were detected in the uploaded file.")
        st.stop()
except Exception as exc:
    st.error(f"Could not read this file: {exc}")
    st.stop()

st.subheader("Data validation")
overview, duplicate_count, summary = profile_data(raw_df)
a, b, c = st.columns(3)
a.metric("Rows", f"{raw_df.shape[0]:,}")
b.metric("Columns", f"{raw_df.shape[1]:,}")
c.metric("Duplicate records", f"{duplicate_count:,}")
with st.expander("Column names and data types", expanded=True):
    st.dataframe(overview, use_container_width=True, hide_index=True)
with st.expander("Statistical summary"):
    st.dataframe(summary, use_container_width=True)

clean_df, cleaning_log = clean_data(raw_df, missing_strategy, remove_duplicates, standardize_text, parse_dates)
with st.expander("Preprocessing log", expanded=False):
    for item in cleaning_log:
        st.write(f"- {item}")

sales_col = metric_column(clean_df, "Sales")
profit_col = metric_column(clean_df, "Profit")
quantity_col = metric_column(clean_df, "Quantity")
order_col = metric_column(clean_df, "Order ID")
if sales_col is None or profit_col is None or quantity_col is None:
    st.warning("To calculate all required KPIs, your file needs Sales, Profit, and Quantity columns. An Order ID column is also needed for unique-order counts. Common aliases are recognized.")
    st.write("Detected columns:", ", ".join(map(str, clean_df.columns)))
    st.download_button("Download cleaned data (CSV)", clean_df.to_csv(index=False).encode("utf-8"), "cleaned_data.csv", "text/csv")
    st.stop()

# Standardize numeric fields safely for metrics and charts.
clean_df[sales_col] = numeric_series(clean_df, sales_col)
clean_df[profit_col] = numeric_series(clean_df, profit_col)
clean_df[quantity_col] = numeric_series(clean_df, quantity_col)

st.subheader("Interactive analysis")
filter_cols = st.columns(3)
filtered = clean_df.copy()
for idx, candidate in enumerate(["Region", "Category", "Segment"]):
    if candidate in filtered.columns:
        options = sorted(filtered[candidate].dropna().astype(str).unique().tolist())
        chosen = filter_cols[idx].multiselect(candidate, options, default=options, key=f"filter_{candidate}")
        filtered = filtered[filtered[candidate].astype(str).isin(chosen)]
    else:
        filter_cols[idx].info(f"Filter unavailable: '{candidate}' column not found.")

if "Order Date" in filtered.columns:
    valid_dates = pd.to_datetime(filtered["Order Date"], errors="coerce").dropna()
    if not valid_dates.empty:
        min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
        date_range = st.date_input("Order date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
        if isinstance(date_range, tuple) and len(date_range) == 2:
            dates = pd.to_datetime(filtered["Order Date"], errors="coerce")
            filtered = filtered[(dates.dt.date >= date_range[0]) & (dates.dt.date <= date_range[1])]

total_sales = float(filtered[sales_col].sum())
total_profit = float(filtered[profit_col].sum())
total_orders = int(filtered[order_col].nunique(dropna=True)) if order_col else len(filtered)
total_quantity = float(filtered[quantity_col].sum())
profit_margin = (total_profit / total_sales * 100) if total_sales else 0.0

st.subheader("Key performance indicators")
kpis = st.columns(5)
kpis[0].metric("Total Sales", f"{total_sales:,.2f}")
kpis[1].metric("Total Profit", f"{total_profit:,.2f}")
kpis[2].metric("Total Orders", f"{total_orders:,}")
kpis[3].metric("Quantity Sold", f"{total_quantity:,.0f}")
kpis[4].metric("Profit Margin", f"{profit_margin:.2f}%")

if filtered.empty:
    st.warning("No rows match the selected filters.")
else:
    st.subheader("Interactive visualizations")
    chart1, chart2 = st.columns(2)
    if "Category" in filtered.columns:
        category_sales = filtered.groupby("Category", dropna=False)[sales_col].sum().reset_index()
        chart1.plotly_chart(px.bar(category_sales, x="Category", y=sales_col, title="Sales by Category", text_auto=".2s"), use_container_width=True)
    else:
        chart1.info("Sales by Category chart requires a Category column.")
    if "Region" in filtered.columns:
        region_profit = filtered.groupby("Region", dropna=False)[profit_col].sum().reset_index()
        chart2.plotly_chart(px.bar(region_profit, x="Region", y=profit_col, title="Profit by Region", color="Region"), use_container_width=True)
    else:
        chart2.info("Profit by Region chart requires a Region column.")

    if "Order Date" in filtered.columns:
        temporal = filtered.dropna(subset=["Order Date"]).copy()
        temporal["Order Date"] = pd.to_datetime(temporal["Order Date"], errors="coerce")
        temporal = temporal.dropna(subset=["Order Date"])
        if not temporal.empty:
            trend = temporal.set_index("Order Date").resample("MS")[sales_col].sum().reset_index()
            st.plotly_chart(px.line(trend, x="Order Date", y=sales_col, markers=True, title="Monthly Sales Trend"), use_container_width=True)
        else:
            st.info("No valid dates are available for the sales trend.")
    else:
        st.info("Monthly sales trend requires an Order Date column.")

    if "Category" in filtered.columns:
        qty = filtered.groupby("Category", dropna=False)[quantity_col].sum().reset_index()
        st.plotly_chart(px.pie(qty, names="Category", values=quantity_col, title="Quantity Mix by Category", hole=0.4), use_container_width=True)

    # Correlation heatmap for numeric columns.
    st.subheader("Correlation analysis")
    numeric_df = filtered.select_dtypes(include="number")
    if numeric_df.shape[1] >= 2:
        corr = numeric_df.corr(numeric_only=True)
        heatmap = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            aspect="auto",
            title="Numeric Feature Correlation Heatmap",
            labels={"x": "Feature", "y": "Feature", "color": "Correlation"}
        )
        st.plotly_chart(heatmap, use_container_width=True)
        st.caption("Pearson correlation ranges from -1 (strong negative linear relationship) to +1 (strong positive linear relationship). Correlation does not imply causation.")
    else:
        st.info("At least two numeric columns are required to calculate a correlation heatmap.")

    # User-selectable scatter plot.
    if numeric_df.shape[1] >= 2:
        st.subheader("Scatter plot explorer")
        scatter_cols = st.columns(3)
        numeric_columns = numeric_df.columns.tolist()
        x_feature = scatter_cols[0].selectbox("X-axis", numeric_columns, index=0, key="scatter_x")
        y_feature = scatter_cols[1].selectbox("Y-axis", numeric_columns, index=1, key="scatter_y")
        color_options = ["None"] + [
            col for col in ["Category", "Region", "Segment"]
            if col in filtered.columns and filtered[col].nunique(dropna=True) <= 30
        ]
        color_feature = scatter_cols[2].selectbox("Color by", color_options, key="scatter_color")
        scatter_data = filtered.copy()
        scatter_args = {"x": x_feature, "y": y_feature, "title": f"{y_feature} vs {x_feature}", "opacity": 0.75}
        if color_feature != "None":
            scatter_args["color"] = color_feature
        if len(scatter_data) > 5000:
            st.caption("Showing a random sample of 5,000 rows for responsiveness.")
            scatter_data = scatter_data.sample(5000, random_state=42)
        scatter_fig = px.scatter(scatter_data, **scatter_args)
        st.plotly_chart(scatter_fig, use_container_width=True)
    else:
        st.info("At least two numeric columns are required to create a scatter plot.")

with st.expander("Filtered data preview"):
    st.dataframe(filtered, use_container_width=True, hide_index=True)
st.download_button("Download cleaned data (CSV)", clean_df.to_csv(index=False).encode("utf-8"), "cleaned_data.csv", "text/csv")
st.download_button("Download filtered data (CSV)", filtered.to_csv(index=False).encode("utf-8"), "filtered_data.csv", "text/csv")
