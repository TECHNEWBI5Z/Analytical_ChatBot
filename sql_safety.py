"""Conservative SQL validation. The database user must still be SELECT-only."""
import re

import sqlglot
from sqlglot import exp

MAX_ROWS = 200
FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|CALL|INTO|LOAD|OUTFILE)\b",
    re.IGNORECASE,
)


def validate_and_limit(sql: str) -> str:
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise ValueError("The model did not return SQL.")
    # A small local model may occasionally use SQL Server's `TOP n` despite the
    # MySQL prompt. Convert the simple form before parsing it as MySQL.
    top_match = re.match(r"^SELECT\s+TOP\s+(\d+)\s+", cleaned, re.IGNORECASE)
    if top_match:
        row_count = top_match.group(1)
        cleaned = re.sub(r"^SELECT\s+TOP\s+\d+\s+", "SELECT ", cleaned, flags=re.IGNORECASE)
        cleaned = f"{cleaned} LIMIT {row_count}"

    if len(re.findall(r"\bSELECT\b", cleaned, re.IGNORECASE)) > 1 and not re.match(
        r"^\s*WITH\b", cleaned, re.IGNORECASE
    ):
        raise ValueError("Please ask one question at a time. I can run only one SQL query per message.")
    if ";" in cleaned or FORBIDDEN.search(cleaned):
        raise ValueError("Only a single read-only SELECT query is allowed.")

    try:
        statement = sqlglot.parse_one(cleaned, read="mysql")
    except sqlglot.errors.ParseError as exc:
        raise ValueError(f"Invalid MySQL syntax: {exc}") from exc

    if not isinstance(statement, (exp.Select, exp.Union, exp.With)):
        # CTEs are normally represented with Select/Union carrying a WITH clause.
        if not statement.find(exp.Select):
            raise ValueError("Only SELECT queries are allowed.")

    # Do not let a generated query accidentally return millions of records.
    if not statement.args.get("limit"):
        cleaned = f"{cleaned} LIMIT {MAX_ROWS}"
    return cleaned
