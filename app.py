import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Databricks Demo App",
)
server = app.server  # expose Flask server for Databricks Apps

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dash.page_container,
])

if __name__ == "__main__":
    import os
    port = int(os.getenv("DATABRICKS_APP_PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
