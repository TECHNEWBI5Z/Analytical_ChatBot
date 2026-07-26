"""Database access and schema discovery."""
import os
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, inspect, text

load_dotenv()


@lru_cache(maxsize=1)
def get_engine():
    """Return an engine configured from .env (no connection is made yet)."""
    required = ["MYSQL_HOST", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing environment settings: {', '.join(missing)}")

    url = URL.create(
        "mysql+pymysql",
        username=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        host=os.environ["MYSQL_HOST"],
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.environ["MYSQL_DATABASE"],
    )
    return create_engine(url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_schema() -> str:
    """Create a compact schema description for the model; no row data is shared."""
    inspector = inspect(get_engine())
    parts = []
    for table in inspector.get_table_names():
        columns = inspector.get_columns(table)
        definitions = ", ".join(f"{c['name']} ({c['type']})" for c in columns)
        parts.append(f"{table}: {definitions}")
    return "\n".join(parts) or "No tables found."


def run_read_query(sql: str):
    """Execute already-validated SQL and return data rows as a dataframe."""
    import pandas as pd

    with get_engine().connect() as connection:
        return pd.read_sql(text(sql), connection)
