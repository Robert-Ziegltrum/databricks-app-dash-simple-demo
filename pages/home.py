import dash
from dash import html
import dash_bootstrap_components as dbc
from utils.components import navbar, RED, NAVY, GREEN

dash.register_page(__name__, path="/", title="Home")

cards = [
    ("👤 My Identity & Access",  "/identity", RED,
     "See who you are, your groups, and your workspace context."),
    ("💰 Sales Analytics",       "/sales",    NAVY,
     "Explore TPC-H orders, revenue trends, and top customers."),
    ("🚕 NYC Taxi Analytics",    "/taxi",     GREEN,
     "Analyse NYC taxi trips: fares, distances, and patterns."),
    ("🔍 SQL Explorer",          "/sql",      RED,
     "Write and run ad-hoc SQL against the samples catalog."),
    ("📂 Catalog Browser",       "/catalog",  NAVY,
     "Browse Unity Catalog: catalogs, schemas, tables, columns."),
]


def layout():
    return html.Div([
        navbar("/"),
        dbc.Container([
            html.H1("🧱 Databricks Demo App", className="mb-2"),
            html.P(
                "A realistic, interactive demo built with Dash and deployed directly from Git "
                "into any Databricks workspace — zero manual setup required.",
                className="lead text-muted mb-4",
            ),
            dbc.Row([
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(title, style={"color": color}),
                            html.P(desc, className="text-muted small"),
                            dbc.Button("Open →", href=href,
                                       color="dark", outline=True, size="sm"),
                        ])
                    ], className="h-100 shadow-sm"),
                    md=4, className="mb-4"
                )
                for title, href, color, desc in cards
            ]),
            html.Hr(),
            html.P([
                "Built using Databricks Apps · ",
                html.A("Cookbook", href="https://apps-cookbook.dev",
                       target="_blank"),
                " · ",
                html.A(
                    "GitHub", href="https://github.com/databricks-solutions/databricks-apps-cookbook", target="_blank"),
            ], className="text-muted small"),
        ], fluid=True),
    ])
