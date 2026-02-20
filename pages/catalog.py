import dash
from dash import html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import pandas as pd
from functools import lru_cache
from databricks.sdk import WorkspaceClient
from utils.components import navbar, error_alert, NAVY

dash.register_page(__name__, path="/catalog", title="Catalog Browser")


@lru_cache(maxsize=1)
def _client():
    return WorkspaceClient()


def layout():
    return html.Div([
        navbar("/catalog"),
        dbc.Container([
            html.H2("📂 Catalog Browser"),
            html.P("Explore your Unity Catalog hierarchy — catalogs, schemas, tables, and columns.",
                   className="text-muted"),

            dbc.Row([
                # Catalog column
                dbc.Col([
                    html.H6("🗄️ Catalogs"),
                    dcc.Loading(html.Div(id="cat-list")),
                    dcc.Interval(id="cat-trigger", interval=1, max_intervals=1),
                ], md=3, style={"borderRight": "1px solid #eee"}),

                # Schema column
                dbc.Col([
                    html.H6("📁 Schemas"),
                    dcc.Loading(html.Div(id="schema-list")),
                ], md=3, style={"borderRight": "1px solid #eee"}),

                # Table column
                dbc.Col([
                    html.H6("📋 Tables"),
                    dcc.Loading(html.Div(id="table-list")),
                ], md=3, style={"borderRight": "1px solid #eee"}),

                # Detail column
                dbc.Col([
                    html.H6("🔎 Details"),
                    dcc.Loading(html.Div(id="table-detail")),
                ], md=3),
            ]),

            # Hidden stores
            dcc.Store(id="store-catalog"),
            dcc.Store(id="store-schema"),
            dcc.Store(id="store-table"),
        ], fluid=True),
    ])


# ── Load catalogs ─────────────────────────────────────────────────────────────
@callback(Output("cat-list", "children"), Input("cat-trigger", "n_intervals"))
def load_catalogs(_):
    try:
        w = _client()
        catalogs = [c.name for c in w.catalogs.list() if c.name]
        # Surface samples first
        if "samples" in catalogs:
            catalogs = ["samples"] + [c for c in catalogs if c != "samples"]
        return dbc.ListGroup([
            dbc.ListGroupItem(c, id={"type": "cat-item", "index": c},
                              action=True, style={"fontSize": "0.9em", "cursor": "pointer"})
            for c in catalogs
        ], flush=True)
    except Exception as e:
        return error_alert(str(e))


# ── Catalog click → load schemas ──────────────────────────────────────────────
@callback(
    Output("schema-list", "children"),
    Output("store-catalog", "data"),
    Input({"type": "cat-item", "index": dash.ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def load_schemas(n_clicks):
    ctx = dash.callback_context
    if not ctx.triggered or not any(n_clicks):
        return dash.no_update, dash.no_update
    cat = ctx.triggered_id["index"]
    try:
        w = _client()
        schemas = [s.name for s in w.schemas.list(catalog_name=cat) if s.name]
        return (
            dbc.ListGroup([
                dbc.ListGroupItem(s, id={"type": "schema-item", "index": s},
                                  action=True, style={"fontSize": "0.9em", "cursor": "pointer"})
                for s in schemas
            ], flush=True),
            cat,
        )
    except Exception as e:
        return error_alert(str(e)), dash.no_update


# ── Schema click → load tables ────────────────────────────────────────────────
@callback(
    Output("table-list", "children"),
    Output("store-schema", "data"),
    Input({"type": "schema-item", "index": dash.ALL}, "n_clicks"),
    Input("store-catalog", "data"),
    prevent_initial_call=True,
)
def load_tables(n_clicks, catalog):
    ctx = dash.callback_context
    if not ctx.triggered or not catalog:
        return dash.no_update, dash.no_update
    triggered = ctx.triggered_id
    if not isinstance(triggered, dict) or triggered.get("type") != "schema-item":
        return dash.no_update, dash.no_update
    schema = triggered["index"]
    try:
        w = _client()
        tables = [t.name for t in w.tables.list(catalog_name=catalog, schema_name=schema) if t.name]
        return (
            dbc.ListGroup([
                dbc.ListGroupItem(t, id={"type": "table-item", "index": t},
                                  action=True, style={"fontSize": "0.9em", "cursor": "pointer"})
                for t in tables
            ], flush=True),
            schema,
        )
    except Exception as e:
        return error_alert(str(e)), dash.no_update


# ── Table click → show details ────────────────────────────────────────────────
@callback(
    Output("table-detail", "children"),
    Input({"type": "table-item", "index": dash.ALL}, "n_clicks"),
    Input("store-catalog", "data"),
    Input("store-schema", "data"),
    prevent_initial_call=True,
)
def show_detail(n_clicks, catalog, schema):
    ctx = dash.callback_context
    if not ctx.triggered or not catalog or not schema:
        return dash.no_update
    triggered = ctx.triggered_id
    if not isinstance(triggered, dict) or triggered.get("type") != "table-item":
        return dash.no_update
    table = triggered["index"]
    try:
        w = _client()
        t = w.tables.get(full_name=f"{catalog}.{schema}.{table}")

        meta = [
            html.P([html.Strong("Type: "), html.Code(t.table_type.value if t.table_type else "n/a")]),
            html.P([html.Strong("Owner: "), t.owner or "n/a"]),
            html.P([html.Strong("Format: "), html.Code(
                t.data_source_format.value if t.data_source_format else "n/a")]),
        ]
        if t.comment:
            meta.append(dbc.Alert(t.comment, color="info", className="py-2"))

        cols_section = html.Div()
        if t.columns:
            col_df = pd.DataFrame([{
                "Column": c.name,
                "Type": c.type_text or str(c.type_name),
                "Nullable": "✅" if c.nullable else "❌",
            } for c in t.columns])
            cols_section = html.Div([
                html.Strong("Schema", className="d-block mt-2 mb-1"),
                dbc.Table.from_dataframe(col_df, striped=True, bordered=False,
                                         hover=True, size="sm", responsive=True),
            ])

        col_names = ", ".join([c.name for c in t.columns]) if t.columns else "*"
        sql_ref = html.Div([
            html.Strong("SQL Reference", className="d-block mt-2 mb-1"),
            html.Pre(
                f"SELECT {col_names}\nFROM {catalog}.{schema}.{table}\nLIMIT 100",
                style={"background": "#f5f5f5", "padding": "10px",
                       "borderRadius": "6px", "fontSize": "0.8em",
                       "overflowX": "auto"},
            ),
        ])

        return html.Div(meta + [cols_section, sql_ref])
    except Exception as e:
        return error_alert(str(e))
