import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from utils.components import navbar, kpi_card, error_alert, RED, NAVY
from utils.sql_client import run_query, get_warehouse_http_path

dash.register_page(__name__, path="/sales", title="Sales Analytics")

YEARS = list(range(1992, 1999))
STATUS_OPTIONS = [
    {"label": "All",         "value": "ALL"},
    {"label": "Open",        "value": "O"},
    {"label": "Fulfilled",   "value": "F"},
    {"label": "Pending",     "value": "P"},
]


def layout():
    if not get_warehouse_http_path():
        return html.Div([navbar("/sales"), dbc.Container(
            error_alert(
                "No SQL Warehouse found. Set DATABRICKS_WAREHOUSE_ID in app.yaml."),
        )])

    return html.Div([
        navbar("/sales"),
        dbc.Container([
            html.H2("💰 Sales Analytics"),
            html.P("Interactive analytics on the TPC-H benchmark dataset from samples.tpch.",
                   className="text-muted"),

            # ── Filters ───────────────────────────────────────────────────────
            dbc.Card(dbc.CardBody(dbc.Row([
                dbc.Col([
                    html.Label("Year Range"),
                    dcc.RangeSlider(id="sales-years", min=1992, max=1998, step=1,
                                    value=[1994, 1997],
                                    marks={y: str(y) for y in YEARS}),
                ], md=5),
                dbc.Col([
                    html.Label("Order Status"),
                    dcc.Dropdown(id="sales-status", options=STATUS_OPTIONS,
                                 value="ALL", clearable=False),
                ], md=3),
                dbc.Col([
                    html.Label("Top N Customers"),
                    dcc.Slider(id="sales-topn", min=5, max=25, step=5, value=10,
                               marks={v: str(v) for v in [5, 10, 15, 20, 25]}),
                ], md=4),
            ])), className="mb-4 shadow-sm"),

            # fires once on mount so all tab content loads immediately
            dcc.Interval(id="sales-init", interval=500, max_intervals=1),

            # ── KPI Row ───────────────────────────────────────────────────────
            html.Div(id="sales-kpis", className="mb-4"),

            # ── Tabs ──────────────────────────────────────────────────────────
            dbc.Tabs([
                dbc.Tab(dcc.Loading(html.Div(id="sales-trend")),
                        label="📈 Revenue Trend"),
                dbc.Tab(dcc.Loading(html.Div(id="sales-region")),
                        label="🌍 Revenue by Region"),
                dbc.Tab(dcc.Loading(html.Div(id="sales-customers")),
                        label="🏆 Top Customers"),
            ]),
        ], fluid=True),
    ])


def _status_filter(status: str) -> str:
    if status == "ALL":
        return ""
    return f"AND o.o_orderstatus = '{status}'"


@callback(
    Output("sales-kpis", "children"),
    Input("sales-years", "value"),
    Input("sales-status", "value"),
    Input("sales-init", "n_intervals"),
)
def update_kpis(years, status, _init):
    try:
        sf = _status_filter(status)
        df = run_query(f"""
            SELECT
                COUNT(DISTINCT o.o_orderkey)  AS total_orders,
                COUNT(DISTINCT o.o_custkey)   AS unique_customers,
                ROUND(SUM(o.o_totalprice), 0) AS total_revenue,
                ROUND(AVG(o.o_totalprice), 2) AS avg_order_value
            FROM samples.tpch.orders o
            WHERE YEAR(o.o_orderdate) BETWEEN {years[0]} AND {years[1]}
            {sf}
        """)
        k = df.iloc[0]
        return dbc.Row([
            dbc.Col(kpi_card("Total Orders",
                    f"{int(k.total_orders):,}"),      md=3, className="mb-3"),
            dbc.Col(kpi_card("Unique Customers",
                    f"{int(k.unique_customers):,}"),  md=3, className="mb-3"),
            dbc.Col(kpi_card("Total Revenue",
                    f"${float(k.total_revenue):,.0f}"), md=3, className="mb-3"),
            dbc.Col(kpi_card("Avg Order Value",
                    f"${float(k.avg_order_value):,.2f}"), md=3, className="mb-3"),
        ])
    except Exception as e:
        return error_alert(str(e))


@callback(
    Output("sales-trend", "children"),
    Input("sales-years", "value"),
    Input("sales-status", "value"),
    Input("sales-init", "n_intervals"),
)
def update_trend(years, status, _init):
    try:
        sf = _status_filter(status)
        df = run_query(f"""
            SELECT DATE_TRUNC('month', o.o_orderdate) AS month,
                   ROUND(SUM(o.o_totalprice), 0)      AS revenue
            FROM samples.tpch.orders o
            WHERE YEAR(o.o_orderdate) BETWEEN {years[0]} AND {years[1]}
            {sf}
            GROUP BY 1 ORDER BY 1
        """)
        df["month"] = df["month"].astype(str)
        fig = px.area(df, x="month", y="revenue", title="Monthly Revenue",
                      labels={"month": "Month", "revenue": "Revenue ($)"},
                      color_discrete_sequence=[RED])
        fig.update_layout(hovermode="x unified",
                          xaxis_tickangle=-30, margin=dict(t=40))
        return dcc.Graph(figure=fig)
    except Exception as e:
        return error_alert(str(e))


@callback(
    Output("sales-region", "children"),
    Input("sales-years", "value"),
    Input("sales-status", "value"),
    Input("sales-init", "n_intervals"),
)
def update_region(years, status, _init):
    try:
        sf = _status_filter(status)
        df = run_query(f"""
            SELECT r.r_name AS region, n.n_name AS nation,
                   ROUND(SUM(o.o_totalprice), 0) AS revenue
            FROM samples.tpch.orders o
            JOIN samples.tpch.customer c ON o.o_custkey   = c.c_custkey
            JOIN samples.tpch.nation   n ON c.c_nationkey = n.n_nationkey
            JOIN samples.tpch.region   r ON n.n_regionkey = r.r_regionkey
            WHERE YEAR(o.o_orderdate) BETWEEN {years[0]} AND {years[1]}
            {sf}
            GROUP BY 1, 2 ORDER BY 1, 3 DESC
        """)
        region_sum = df.groupby("region")["revenue"].sum().reset_index()
        fig_pie = px.pie(region_sum, names="region", values="revenue",
                         title="Revenue by Region", hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Bold)
        fig_bar = px.bar(df.sort_values("revenue", ascending=False).head(15),
                         x="revenue", y="nation", orientation="h", color="region",
                         title="Top Nations by Revenue",
                         labels={"revenue": "Revenue ($)", "nation": "Nation"})
        fig_bar.update_layout(
            yaxis={"categoryorder": "total ascending"}, margin=dict(t=40))
        return dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_pie), md=5),
            dbc.Col(dcc.Graph(figure=fig_bar), md=7),
        ])
    except Exception as e:
        return error_alert(str(e))


@callback(
    Output("sales-customers", "children"),
    Input("sales-years", "value"),
    Input("sales-status", "value"),
    Input("sales-topn", "value"),
    Input("sales-init", "n_intervals"),
)
def update_customers(years, status, topn, _init):
    try:
        sf = _status_filter(status)
        df = run_query(f"""
            SELECT c.c_name        AS customer,
                   c.c_mktsegment  AS segment,
                   COUNT(o.o_orderkey)           AS orders,
                   ROUND(SUM(o.o_totalprice), 0) AS revenue,
                   ROUND(AVG(o.o_totalprice), 2) AS avg_order
            FROM samples.tpch.orders o
            JOIN samples.tpch.customer c ON o.o_custkey = c.c_custkey
            WHERE YEAR(o.o_orderdate) BETWEEN {years[0]} AND {years[1]}
            {sf}
            GROUP BY 1, 2 ORDER BY 4 DESC LIMIT {topn}
        """)
        fig = px.bar(df, x="revenue", y="customer", orientation="h", color="segment",
                     title=f"Top {topn} Customers by Revenue",
                     labels={"revenue": "Revenue ($)", "customer": "Customer"},
                     hover_data={"orders": True, "avg_order": ":.2f"})
        fig.update_layout(yaxis={"categoryorder": "total ascending"},
                          height=max(400, topn * 35), margin=dict(t=40))

        table_df = df.copy()
        table_df["revenue"] = table_df["revenue"].apply(lambda x: f"${x:,.0f}")
        table_df["avg_order"] = table_df["avg_order"].apply(
            lambda x: f"${x:,.2f}")

        return html.Div([
            dcc.Graph(figure=fig),
            html.H6("Detail Table", className="mt-3"),
            dbc.Table.from_dataframe(table_df, striped=True, bordered=False,
                                     hover=True, responsive=True, size="sm"),
        ])
    except Exception as e:
        return error_alert(str(e))
