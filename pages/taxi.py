import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.express as px
from utils.components import navbar, kpi_card, error_alert, RED, NAVY
from utils.sql_client import run_query, get_warehouse_http_path

dash.register_page(__name__, path="/taxi", title="NYC Taxi Analytics")

SAMPLE_SIZES = [10_000, 50_000, 100_000]


def layout():
    if not get_warehouse_http_path():
        return html.Div([navbar("/taxi"), dbc.Container(
            error_alert("No SQL Warehouse found. Set DATABRICKS_WAREHOUSE_ID in app.yaml.")
        )])

    return html.Div([
        navbar("/taxi"),
        dbc.Container([
            html.H2("🚕 NYC Taxi Analytics"),
            html.P("Interactive exploration of NYC taxi trips from samples.nyctaxi.trips.",
                   className="text-muted"),

            # ── Filters ───────────────────────────────────────────────────────
            dbc.Card(dbc.CardBody(dbc.Row([
                dbc.Col([
                    html.Label("Fare Range ($)"),
                    dcc.RangeSlider(id="taxi-fare", min=0, max=200, step=5,
                                    value=[0, 100],
                                    marks={v: f"${v}" for v in [0, 50, 100, 150, 200]}),
                ], md=4),
                dbc.Col([
                    html.Label("Distance Range (miles)"),
                    dcc.RangeSlider(id="taxi-dist", min=0, max=50, step=1,
                                    value=[0, 20],
                                    marks={v: str(v) for v in [0, 10, 20, 30, 40, 50]}),
                ], md=4),
                dbc.Col([
                    html.Label("Sample Size"),
                    dcc.Dropdown(id="taxi-sample",
                                 options=[{"label": f"{v:,} rows", "value": v} for v in SAMPLE_SIZES],
                                 value=10_000, clearable=False),
                ], md=4),
            ])), className="mb-4 shadow-sm"),

            html.Div(id="taxi-kpis", className="mb-4"),

            dbc.Tabs([
                dbc.Tab(dcc.Loading(html.Div(id="taxi-dist-tab")),   label="📊 Distributions"),
                dbc.Tab(dcc.Loading(html.Div(id="taxi-hourly-tab")), label="📅 Hourly Patterns"),
                dbc.Tab(dcc.Loading(html.Div(id="taxi-scatter-tab")), label="🗺️ Fare vs Distance"),
            ]),
        ], fluid=True),
    ])


def _where(fare, dist):
    return (f"WHERE fare_amount BETWEEN {fare[0]} AND {fare[1]}"
            f"  AND trip_distance BETWEEN {dist[0]} AND {dist[1]}"
            f"  AND trip_distance > 0 AND fare_amount > 0")


@callback(
    Output("taxi-kpis", "children"),
    Input("taxi-fare", "value"),
    Input("taxi-dist", "value"),
)
def update_kpis(fare, dist):
    try:
        w = _where(fare, dist)
        df = run_query(f"""
            SELECT COUNT(*) AS total_trips,
                   ROUND(AVG(fare_amount), 2)  AS avg_fare,
                   ROUND(AVG(trip_distance), 2) AS avg_distance,
                   ROUND(AVG(fare_amount / NULLIF(trip_distance, 0)), 2) AS avg_fare_per_mile
            FROM samples.nyctaxi.trips {w}
        """)
        k = df.iloc[0]
        return dbc.Row([
            dbc.Col(kpi_card("Total Trips",      f"{int(k.total_trips):,}"),              md=3, className="mb-3"),
            dbc.Col(kpi_card("Avg Fare",         f"${float(k.avg_fare):.2f}"),            md=3, className="mb-3"),
            dbc.Col(kpi_card("Avg Distance",     f"{float(k.avg_distance):.1f} mi"),      md=3, className="mb-3"),
            dbc.Col(kpi_card("Avg Fare / Mile",  f"${float(k.avg_fare_per_mile):.2f}"),   md=3, className="mb-3"),
        ])
    except Exception as e:
        return error_alert(str(e))


@callback(
    Output("taxi-dist-tab", "children"),
    Input("taxi-fare", "value"),
    Input("taxi-dist", "value"),
    Input("taxi-sample", "value"),
)
def update_distributions(fare, dist, sample):
    try:
        w = _where(fare, dist)
        df = run_query(f"SELECT fare_amount, trip_distance FROM samples.nyctaxi.trips {w} LIMIT {sample}")
        fig1 = px.histogram(df, x="fare_amount", nbins=50, title="Fare Amount Distribution",
                            labels={"fare_amount": "Fare ($)"}, color_discrete_sequence=[RED])
        fig2 = px.histogram(df, x="trip_distance", nbins=50, title="Trip Distance Distribution",
                            labels={"trip_distance": "Distance (miles)"}, color_discrete_sequence=[NAVY])
        return dbc.Row([
            dbc.Col(dcc.Graph(figure=fig1), md=6),
            dbc.Col(dcc.Graph(figure=fig2), md=6),
        ])
    except Exception as e:
        return error_alert(str(e))


@callback(
    Output("taxi-hourly-tab", "children"),
    Input("taxi-fare", "value"),
    Input("taxi-dist", "value"),
)
def update_hourly(fare, dist):
    try:
        w = _where(fare, dist)
        df = run_query(f"""
            SELECT HOUR(tpep_pickup_datetime)      AS hour_of_day,
                   COUNT(*)                        AS trips,
                   ROUND(AVG(fare_amount), 2)      AS avg_fare
            FROM samples.nyctaxi.trips {w}
            GROUP BY 1 ORDER BY 1
        """)
        fig1 = px.bar(df, x="hour_of_day", y="trips", title="Trips by Hour of Day",
                      labels={"hour_of_day": "Hour (24h)", "trips": "Trip Count"},
                      color_discrete_sequence=[RED])
        fig2 = px.line(df, x="hour_of_day", y="avg_fare", markers=True,
                       title="Average Fare by Hour",
                       labels={"hour_of_day": "Hour (24h)", "avg_fare": "Avg Fare ($)"},
                       color_discrete_sequence=[NAVY])
        return dbc.Row([
            dbc.Col(dcc.Graph(figure=fig1), md=6),
            dbc.Col(dcc.Graph(figure=fig2), md=6),
        ])
    except Exception as e:
        return error_alert(str(e))


@callback(
    Output("taxi-scatter-tab", "children"),
    Input("taxi-fare", "value"),
    Input("taxi-dist", "value"),
    Input("taxi-sample", "value"),
)
def update_scatter(fare, dist, sample):
    try:
        w = _where(fare, dist)
        df = run_query(f"""
            SELECT fare_amount, trip_distance
            FROM samples.nyctaxi.trips {w}
            ORDER BY RAND() LIMIT {min(sample, 5000)}
        """)
        fig = px.scatter(df, x="trip_distance", y="fare_amount", opacity=0.4,
                         title="Fare vs Distance (random sample)",
                         labels={"trip_distance": "Distance (miles)", "fare_amount": "Fare ($)"},
                         color_discrete_sequence=[RED])
        return dcc.Graph(figure=fig)
    except Exception as e:
        return error_alert(str(e))
