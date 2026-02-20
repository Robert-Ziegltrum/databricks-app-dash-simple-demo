"""Shared layout helpers and theme for the Databricks Demo Dash App."""
import dash_bootstrap_components as dbc
from dash import html

# ── Databricks brand colours ──────────────────────────────────────────────────
RED = "#FF3621"
NAVY = "#1B3A8C"
GREEN = "#00A972"
DARK = "#1A1A1A"
LIGHT = "#F5F5F5"


def navbar(active: str = "") -> dbc.NavbarSimple:
    pages = [
        ("🏠 Home",            "/"),
        ("👤 Identity",        "/identity"),
        ("💰 Sales Analytics", "/sales"),
        ("🚕 NYC Taxi",        "/taxi"),
        ("🔍 SQL Explorer",    "/sql"),
        ("📂 Catalog Browser", "/catalog"),
    ]
    return dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink(label, href=href, active=(href == active)))
            for label, href in pages
        ],
        brand="🧱 Databricks Demo",
        brand_href="/",
        color=DARK,
        dark=True,
        fluid=True,
        className="mb-4",
    )


def kpi_card(title: str, value: str, color: str = RED) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody([
            html.P(title, className="text-muted small mb-1"),
            html.H4(value, style={"color": color, "fontWeight": "bold"}),
        ]),
        className="shadow-sm",
    )


def error_alert(msg: str) -> dbc.Alert:
    return dbc.Alert(f"⚠️ {msg}", color="danger", className="mt-3")


def spinner_overlay() -> html.Div:
    return html.Div(
        dbc.Spinner(color="danger", size="lg"),
        style={"textAlign": "center", "padding": "60px"},
    )
