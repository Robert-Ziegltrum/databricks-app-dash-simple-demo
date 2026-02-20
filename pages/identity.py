import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
from flask import request
from databricks.sdk import WorkspaceClient
from utils.components import navbar, kpi_card, error_alert, RED

dash.register_page(__name__, path="/identity", title="Identity & Access")


def layout():
    return html.Div([
        navbar("/identity"),
        dbc.Container([
            html.H2("👤 My Identity & Access"),
            html.P("Your identity as seen by this Databricks App, from HTTP headers and the Databricks SDK.",
                   className="text-muted"),
            html.Div(id="identity-content"),
            dcc.Interval(id="identity-trigger", interval=1, max_intervals=1),
        ], fluid=True),
    ])


@callback(Output("identity-content", "children"), Input("identity-trigger", "n_intervals"))
def load_identity(_):
    try:
        headers = request.headers
        email    = headers.get("X-Forwarded-Email", "")
        username = headers.get("X-Forwarded-Preferred-Username", "")
        user_id  = headers.get("X-Forwarded-User", "")
        ip       = headers.get("X-Real-Ip", "")
        token    = headers.get("X-Forwarded-Access-Token", "")
    except RuntimeError:
        # Outside request context (e.g. local dev without headers)
        email = username = user_id = ip = token = ""

    sections = [
        dbc.Row([
            dbc.Col(kpi_card("Email",    email    or "n/a"), md=4, className="mb-3"),
            dbc.Col(kpi_card("Username", username or "n/a"), md=4, className="mb-3"),
            dbc.Col(kpi_card("IP",       ip       or "n/a"), md=4, className="mb-3"),
        ]),
        html.Hr(),
    ]

    if token:
        try:
            w = WorkspaceClient(token=token, auth_type="pat")
            me = w.current_user.me()

            detail_rows = [
                dbc.Row([
                    dbc.Col([html.Strong("User ID: "), html.Code(str(me.id))],  md=4),
                    dbc.Col([html.Strong("Display Name: "), me.display_name],    md=4),
                    dbc.Col([html.Strong("Active: "), "✅ Yes" if me.active else "❌ No"], md=4),
                ], className="mb-2"),
            ]

            if me.name:
                detail_rows.append(dbc.Row([
                    dbc.Col([html.Strong("Given Name: "), me.name.given_name or "n/a"], md=4),
                    dbc.Col([html.Strong("Family Name: "), me.name.family_name or "n/a"], md=4),
                ], className="mb-2"))

            sections.append(html.H5("📋 Account Details", className="mt-2 mb-3"))
            sections.extend(detail_rows)

            # Groups
            sections.append(html.H5("👥 Group Memberships", className="mt-4 mb-3"))
            if me.groups:
                group_names = [g.display for g in me.groups if g.display]
                badges = [
                    dbc.Badge(g, color="primary", className="me-2 mb-2", pill=True)
                    for g in group_names
                ]
                sections.append(html.Div(badges))
            else:
                sections.append(dbc.Alert("No group memberships returned.", color="info"))

            # Workspace
            sections.append(html.H5("🏢 Workspace", className="mt-4 mb-2"))
            try:
                ws_id = w.get_workspace_id()
                sections.append(html.P([html.Strong("Workspace ID: "), html.Code(str(ws_id))]))
            except Exception:
                pass
            try:
                from databricks.sdk.core import Config
                cfg = Config(token=token)
                sections.append(html.P([html.Strong("Host: "), html.Code(cfg.host)]))
            except Exception:
                pass

        except Exception as e:
            sections.append(error_alert(f"Could not fetch detailed user info: {e}"))
    else:
        sections.append(dbc.Alert(
            [
                html.Strong("Basic info only. "),
                "Enable On-behalf-of-user authentication in app Settings → Authorization "
                "to see full account details and group memberships.",
            ],
            color="warning",
        ))

    # Raw headers (safe subset)
    try:
        safe = {k: v for k, v in request.headers if "token" not in k.lower() and "secret" not in k.lower()}
    except RuntimeError:
        safe = {}

    sections.append(html.Hr())
    sections.append(html.Details([
        html.Summary("🔎 Raw HTTP Headers", style={"cursor": "pointer", "fontWeight": "bold"}),
        html.Pre(
            "\n".join(f"{k}: {v}" for k, v in sorted(safe.items())),
            style={"background": "#f5f5f5", "padding": "12px", "borderRadius": "6px",
                   "fontSize": "0.8em", "maxHeight": "300px", "overflow": "auto"},
        ),
    ], className="mt-3"))

    return sections
