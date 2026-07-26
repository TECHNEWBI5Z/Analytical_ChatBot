"""Translate natural language into one safe MySQL SELECT statement with Ollama."""
import json
import os
import re
from typing import Optional

import ollama

SYSTEM_PROMPT = """Use the ART (Action–Role–Task) framework below.

ACTION
Translate one natural-language analytics question into one correct, read-only MySQL query.

ROLE
You are a careful MySQL data analyst for plant-growth experiments. You prioritize correct joins,
clear aggregate aliases, and results that are easy to chart.

TASK
Return JSON only, matching exactly: {\"sql\": \"...\", \"explanation\": \"...\"}.

Requirements:
- Generate exactly one SELECT query. A WITH/CTE is allowed only when it ends in SELECT.
- Answer one user question at a time; never return more than one query.
- Use only the supplied schema's exact table and column names.
- Never invent, rename, abbreviate, or add prefixes to a table or column name. Check every identifier
  against the supplied schema before returning SQL.
- This is MySQL: use `LIMIT 10`, never `TOP 10`.
- Never write, change, or create data. Never use SELECT INTO, OUTFILE, or multiple statements.
- For computations, use COUNT, SUM, AVG, MIN, MAX, GROUP BY, HAVING, and ORDER BY when appropriate.
- For a question spanning related tables, use explicit INNER JOIN syntax and join only on columns that
  appear in both tables. For these plant datasets, GenotypeName is normally the relationship key.
- Qualify joined columns with short table aliases, for example `rf.RootLength`.
- Give aggregate expressions a descriptive alias, for example `AVG(r.RootLength) AS AverageRootLength`.
- For a request to show a table, select its columns. Include a LIMIT for detail-level results.
- If the question cannot be answered from the schema, return an empty sql and explain why.
"""


def simple_table_preview(question: str, schema: str) -> Optional[dict]:
    """Handle a frequent request without relying on a small local model."""
    match = re.match(
        r"^\s*(?:show|display|get)\s+(?:the\s+)?(?:(?:first|top)\s+)?(\d+)?\s*"
        r"(?:rows?|records?)?\s*(?:from|of)\s+`?([a-zA-Z0-9_]+)`?\s*\??\s*$",
        question,
        re.IGNORECASE,
    )
    if not match:
        return None

    table_lookup = {
        line.split(":", 1)[0].lower(): line.split(":", 1)[0]
        for line in schema.splitlines()
        if ":" in line
    }
    requested_table = table_lookup.get(match.group(2).lower())
    if not requested_table:
        return {"sql": "", "explanation": f"I cannot find a table named `{match.group(2)}` in MySQL."}

    row_count = min(int(match.group(1) or 10), 200)
    return {
        "sql": f"SELECT * FROM `{requested_table}` LIMIT {row_count}",
        "explanation": f"Showing the first {row_count} rows from `{requested_table}`.",
    }


def question_to_sql(question: str, schema: str) -> dict:
    preview = simple_table_preview(question, schema)
    if preview is not None:
        return preview

    response = ollama.chat(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
        format="json",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Schema:\n{schema}\n\nQuestion: {question}"},
        ],
        options={"temperature": 0},
    )
    try:
        answer = json.loads(response["message"]["content"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Ollama returned an invalid response. Try again.") from exc
    return {"sql": answer.get("sql", ""), "explanation": answer.get("explanation", "")}
