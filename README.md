# Sales Analytics Dashboard

A Streamlit dashboard for uploading, validating, preprocessing, and exploring sales data.

## Features
- Upload CSV, Excel (`.xlsx`), and JSON files.
- Validation: dimensions, column names, data types, missing values, unique values, duplicates, and statistical summaries.
- Preprocessing: duplicate removal, text cleanup, common blank-marker normalization, date parsing, and optional missing-value handling.
- Interactive Region, Category, Segment, and date-range filters when those fields exist.
- Five dynamic KPIs: Total Sales, Total Profit, Total Orders (unique Order IDs), Total Quantity Sold, and Profit Margin.
- Interactive Plotly charts and cleaned/filtered CSV downloads.
- Built-in sample dataset for testing.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Expected columns
For all five KPIs, provide columns equivalent to `Sales`, `Profit`, `Quantity`, and `Order ID`. The app recognizes several common aliases. `Region`, `Category`, `Segment`, and `Order Date` are optional but enable additional filters and charts.

## Deploy to Streamlit Community Cloud
1. Create a new public GitHub repository, e.g. `sales-analytics-dashboard`.
2. Upload `app.py`, `requirements.txt`, and this `README.md` to the repository root.
3. Push/commit the files to the default branch.
4. Open https://share.streamlit.io/ and sign in with GitHub.
5. Select **Create app**, choose your repository and branch, set the main file path to `app.py`, then deploy.
6. Open the deployed URL and test sample data plus one CSV, XLSX, and JSON file.
7. Confirm that filters update all KPIs and charts, downloads work, and malformed files produce a readable error.

## Testing checklist
- [ ] Start app with sample data.
- [ ] Upload valid CSV, XLSX, and JSON files.
- [ ] Upload an empty or malformed file and verify error handling.
- [ ] Check missing-value and duplicate counts before cleanup.
- [ ] Toggle cleanup options and inspect the preprocessing log.
- [ ] Change each available filter and verify KPIs/charts update.
- [ ] Test zero total sales (profit margin should display as 0%).
- [ ] Download cleaned and filtered CSV files.
- [ ] Deploy and test the public URL in a private/incognito browser.

## Notes
This is a starter implementation. Review the column aliases and cleaning rules against your assignment dataset. Do not claim deployment is complete until the public URL has been tested.
