# 🧱 Databricks Demo App — Dash

A realistic, interactive Databricks App built with **Plotly Dash** and deployed directly from Git into any Databricks workspace — zero manual setup required.

## Views

| Page | Description | Data Source |
|---|---|---|
| 🏠 Home | Welcome & navigation | — |
| 👤 Identity & Access | Current user, groups, workspace info | Databricks SDK / HTTP headers |
| 💰 Sales Analytics | Revenue trends, regional breakdown, top customers | `samples.tpch` |
| 🚕 NYC Taxi Analytics | Fare distributions, hourly patterns, fare vs distance | `samples.nyctaxi` |
| 🔍 SQL Explorer | Ad-hoc SQL with auto-visualization and CSV export | `samples.*` |
| 📂 Catalog Browser | Browse UC catalogs → schemas → tables → columns | Unity Catalog API |

## Prerequisites

- Databricks workspace with Unity Catalog enabled
- Serverless SQL Warehouse or standard SQL Warehouse
- Foundation Model APIs enabled (pay-per-token, default in most regions)

No tables, volumes, jobs, or dashboards need to be created. The app uses only the built-in `samples` catalog.

## Deploy from Git

1. In your Databricks workspace go to **Compute → Apps → Create App**
2. Choose **Custom App** → **Deploy from Git**
3. Enter this repository URL and set the path to this folder
4. Click **Deploy**

The app auto-discovers an available SQL Warehouse. Optionally pin one by uncommenting `DATABRICKS_WAREHOUSE_ID` in `app.yaml`.

## Run Locally

```bash
pip install -r requirements.txt
export DATABRICKS_HOST=https://your-workspace.azuredatabricks.net
databricks auth login   # or set DATABRICKS_TOKEN
python app.py
```

Then open http://localhost:8080

## Structure

```
.
├── app.py                   # Dash app entry point + Flask server
├── app.yaml                 # Databricks Apps config
├── requirements.txt
├── .gitignore
├── pages/
│   ├── home.py
│   ├── identity.py          # Reads Flask request headers
│   ├── sales.py             # TPC-H analytics with callbacks
│   ├── taxi.py              # NYC Taxi analytics with callbacks
│   ├── sql_explorer.py      # Ad-hoc SQL + DataTable + auto-viz
│   ├── catalog.py           # UC catalog browser (pattern-matching callbacks)
└── utils/
    ├── sql_client.py        # Shared SQL connection with warehouse auto-discovery
    └── components.py        # Shared navbar, KPI cards, theme colours
```

## Key Dash Differences vs Streamlit

- Identity headers come from `flask.request.headers` (not `st.context.headers`)
- State is managed via `dcc.Store` and `@callback` — no page reruns
- `dcc.Interval(max_intervals=1)` triggers one-time data loads on page mount
- Pattern-matching callbacks (`{"type": "...", "index": dash.ALL}`) power the catalog browser's drill-down
