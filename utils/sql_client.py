"""
Shared SQL connection utility.
Uses DATABRICKS_WAREHOUSE_ID env var (set in app.yaml) or auto-discovers
the first available warehouse via the SDK.
"""
import os
from functools import lru_cache
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks import sql


@lru_cache(maxsize=1)
def get_warehouse_http_path() -> str | None:
    try:
        w = WorkspaceClient()
        warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        if warehouse_id:
            return f"/sql/1.0/warehouses/{warehouse_id}"

        warehouses = list(w.warehouses.list())
        serverless = [wh for wh in warehouses if getattr(wh, "enable_serverless_compute", False)]
        if serverless:
            return f"/sql/1.0/warehouses/{serverless[0].id}"
        running = [wh for wh in warehouses if wh.state and wh.state.value == "RUNNING"]
        if running:
            return f"/sql/1.0/warehouses/{running[0].id}"
        if warehouses:
            return f"/sql/1.0/warehouses/{warehouses[0].id}"
    except Exception:
        pass
    return None


@lru_cache(maxsize=1)
def get_connection(http_path: str):
    cfg = Config()
    return sql.connect(
        server_hostname=cfg.host,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate,
    )


def run_query(query: str) -> "pd.DataFrame":
    import pandas as pd
    http_path = get_warehouse_http_path()
    if not http_path:
        raise RuntimeError("No SQL warehouse available.")
    conn = get_connection(http_path)
    with conn.cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall_arrow().to_pandas()
