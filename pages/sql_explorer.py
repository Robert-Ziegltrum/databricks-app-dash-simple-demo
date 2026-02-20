import dash
from dash import html, dcc, callback, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import io
import base64
from utils.components import navbar, error_alert, RED
from utils.sql_client import run_query, get_warehouse_http_path

dash.register_page(__name__, path="/sql", title="SQL Explorer")

STARTER_QUERIES = {
    "-- Select a starter query --": "",
    "📦 TPC-H: Top 10 orders by value":
        "SELECT o_orderkey, o_custkey, o_totalprice, o_orderdate, o_orderstatus\n"
        "FROM samples.tpch.orders\nORDER BY o_totalprice DESC\nLIMIT 10",
    "🌍 TPC-H: Revenue by nation":
        "SELECT n.n_name AS nation, ROUND(SUM(o.o_totalprice), 0) AS total_revenue\n"
        "FROM samples.tpch.orders o\n"
        "JOIN samples.tpch.customer c ON o.o_custkey = c.c_custkey\n"
        "JOIN samples.tpch.nation n ON c.c_nationkey = n.n_nationkey\n"
        "GROUP BY 1 ORDER BY 2 DESC",
    "📋 TPC-H: Order status breakdown":
        "SELECT o_orderstatus, COUNT(*) AS orders, ROUND(AVG(o_totalprice),2) AS avg_value\n"
        "FROM samples.tpch.orders\nGROUP BY 1 ORDER BY 2 DESC",
    "📊 TPC-H: Monthly revenue trend":
        "SELECT DATE_TRUNC('month', o_orderdate) AS month, ROUND(SUM(o_totalprice),0) AS revenue\n"
        "FROM samples.tpch.orders\nGROUP BY 1 ORDER BY 1",
    "🚕 Taxi: Average fare by trip type":
        "SELECT\n  CASE\n    WHEN trip_distance < 1 THEN 'Short (< 1 mi)'\n"
        "    WHEN trip_distance < 5 THEN 'Medium (1-5 mi)'\n"
        "    ELSE 'Long (5+ mi)'\n  END AS trip_type,\n"
        "  COUNT(*) AS trips, ROUND(AVG(fare_amount),2) AS avg_fare\n"
        "FROM samples.nyctaxi.trips\nWHERE fare_amount > 0 AND trip_distance > 0\n"
        "GROUP BY 1 ORDER BY MIN(trip_distance)",
    "⏱️ Taxi: Busiest pickup hours":
        "SELECT HOUR(tpep_pickup_datetime) AS hour, COUNT(*) AS trips\n"
        "FROM samples.nyctaxi.trips\nGROUP BY 1 ORDER BY 1",
    "🔢 Taxi: Distance bucket distribution":
        "SELECT\n  CASE\n    WHEN trip_distance < 1  THEN '< 1 mile'\n"
        "    WHEN trip_distance < 3  THEN '1-3 miles'\n"
        "    WHEN trip_distance < 5  THEN '3-5 miles'\n"
        "    WHEN trip_distance < 10 THEN '5-10 miles'\n"
        "    ELSE '10+ miles'\n  END AS bucket,\n  COUNT(*) AS trips\n"
        "FROM samples.nyctaxi.trips\nWHERE trip_distance > 0\n"
        "GROUP BY 1 ORDER BY MIN(trip_distance)",
}


def layout():
    if not get_warehouse_http_path():
        return html.Div([navbar("/sql"), dbc.Container(
            error_alert(
                "No SQL Warehouse found. Set DATABRICKS_WAREHOUSE_ID in app.yaml.")
        )])

    return html.Div([
        navbar("/sql"),
        dbc.Container([
            html.H2("🔍 SQL Explorer"),
            html.P("Run ad-hoc SQL against the samples catalog using the connected Serverless SQL Warehouse.",
                   className="text-muted"),

            dbc.Card(dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("💡 Starter Queries"),
                        dcc.Dropdown(id="sql-starter",
                                     options=[{"label": k, "value": k}
                                              for k in STARTER_QUERIES],
                                     value="-- Select a starter query --",
                                     clearable=False),
                    ], md=8),
                    dbc.Col([
                        html.Label("Max Rows"),
                        dcc.Input(id="sql-maxrows", type="number", value=500,
                                  min=10, max=5000, step=100,
                                  className="form-control"),
                    ], md=4),
                ], className="mb-3"),

                html.Label("SQL Query"),
                dcc.Textarea(
                    id="sql-editor",
                    value="SELECT * FROM samples.tpch.orders LIMIT 20",
                    style={"width": "100%", "height": "160px", "fontFamily": "monospace",
                           "fontSize": "0.9em", "borderRadius": "6px", "padding": "10px"},
                ),
                dbc.Button("▶️ Run Query", id="sql-run", color="danger",
                           className="mt-2", n_clicks=0),
            ]), className="mb-4 shadow-sm"),

            dcc.Loading(html.Div(id="sql-results")),

            dcc.Store(id="sql-data-store"),
        ], fluid=True),
    ])


# Populate editor from starter dropdown
@callback(
    Output("sql-editor", "value"),
    Input("sql-starter", "value"),
    prevent_initial_call=True,
)
def populate_editor(starter):
    return STARTER_QUERIES.get(starter, "") or dash.no_update


# Run query
@callback(
    Output("sql-results", "children"),
    Output("sql-data-store", "data"),
    Input("sql-run", "n_clicks"),
    State("sql-editor", "value"),
    State("sql-maxrows", "value"),
    prevent_initial_call=True,
)
def run_sql(_, query, max_rows):
    if not query or not query.strip():
        return dbc.Alert("Please enter a SQL query.", color="warning"), None

    safe = query.strip().rstrip(";")
    if "limit" not in safe.lower():
        safe = f"SELECT * FROM ({safe}) _q LIMIT {max_rows or 500}"

    try:
        df = run_query(safe)
    except Exception as e:
        return error_alert(str(e)), None

    # DataTable
    table = dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df.columns],
        page_size=20,
        sort_action="native",
        filter_action="native",
        style_table={"overflowX": "auto"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f5f5f5"},
        style_cell={"fontSize": "0.85em", "padding": "6px"},
    )

    # CSV download link (data URI — no automatic browser download)
    csv_b64 = base64.b64encode(df.to_csv(index=False).encode()).decode()
    dl_link = html.A(
        "⬇️ Download CSV",
        href=f"data:text/csv;base64,{csv_b64}",
        download="query_results.csv",
        className="btn btn-outline-secondary btn-sm mt-2 d-inline-block",
    )

    # Auto-viz controls
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    all_cols = df.columns.tolist()

    viz_section = html.Div()
    if numeric_cols and len(all_cols) >= 2:
        viz_section = dbc.Card(dbc.CardBody([
            html.H6("📈 Auto Visualization"),
            dbc.Row([
                dbc.Col([html.Label("X axis"),
                         dcc.Dropdown(id="viz-x", options=all_cols,
                                      value=all_cols[0], clearable=False)], md=4),
                dbc.Col([html.Label("Y axis"),
                         dcc.Dropdown(id="viz-y", options=numeric_cols,
                                      value=numeric_cols[0], clearable=False)], md=4),
                dbc.Col([html.Label("Chart type"),
                         dcc.Dropdown(id="viz-type",
                                      options=["Bar", "Line",
                                               "Scatter", "Area"],
                                      value="Bar", clearable=False)], md=4),
            ], className="mb-3"),
            html.Div(id="viz-chart"),
        ]), className="mt-3 shadow-sm")

    content = [
        dbc.Alert(f"✅ {len(df):,} rows returned", color="success"),
        table,
        dl_link,
        viz_section,
    ]

    return content, df.to_json(date_format="iso", orient="split")


# Auto-viz chart
@callback(
    Output("viz-chart", "children"),
    Input("viz-x", "value"),
    Input("viz-y", "value"),
    Input("viz-type", "value"),
    State("sql-data-store", "data"),
    prevent_initial_call=True,
)
def update_viz(x, y, chart_type, data_json):
    if not data_json:
        return None
    df = pd.read_json(io.StringIO(data_json), orient="split")
    try:
        if chart_type == "Bar":
            fig = px.bar(df, x=x, y=y)
        elif chart_type == "Line":
            fig = px.line(df, x=x, y=y, markers=True)
        elif chart_type == "Scatter":
            fig = px.scatter(df, x=x, y=y, opacity=0.6)
        else:
            fig = px.area(df, x=x, y=y)
        fig.update_layout(margin=dict(t=30))
        return dcc.Graph(figure=fig)
    except Exception as e:
        return error_alert(str(e))
