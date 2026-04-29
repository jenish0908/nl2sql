import re
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException

DANGEROUS_PATTERN = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|UPDATE|INSERT|ALTER|CREATE|EXEC|EXECUTE|XP_|SP_)\b",
    re.IGNORECASE,
)

COMMENT_PATTERN = re.compile(r"(--[^\n]*|/\*.*?\*/)", re.DOTALL)

LIMIT_PATTERN = re.compile(r"\bLIMIT\s+\d+", re.IGNORECASE)

MAX_ROWS = 100


def _strip_comments(sql: str) -> str:
    return COMMENT_PATTERN.sub(" ", sql).strip()


def _check_safe(sql: str) -> None:
    stripped = _strip_comments(sql)
    if not stripped.upper().startswith("SELECT"):
        raise ValueError("Only SELECT statements are permitted.")
    match = DANGEROUS_PATTERN.search(stripped)
    if match:
        raise ValueError(
            f"Dangerous SQL keyword detected: '{match.group()}'. Only SELECT queries are allowed."
        )


def _inject_limit(sql: str, max_rows: int = MAX_ROWS) -> str:
    if not LIMIT_PATTERN.search(sql):
        sql = sql.rstrip().rstrip(";")
        sql = f"{sql}\nLIMIT {max_rows}"
    return sql


def _serialize_row(row: dict) -> dict:
    result = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            result[key] = float(value)
        elif isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


async def execute_sql(session: AsyncSession, sql: str) -> tuple[list[dict], int]:
    try:
        _check_safe(sql)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    clean_sql = _strip_comments(sql)
    limited_sql = _inject_limit(clean_sql)

    result = await session.execute(text(limited_sql))
    columns = list(result.keys())
    rows = [_serialize_row(dict(zip(columns, row))) for row in result.fetchall()]
    return rows, len(rows)


def validate_sql_safe(sql: str) -> tuple[bool, str]:
    try:
        _check_safe(sql)
        return True, ""
    except ValueError as exc:
        return False, str(exc)
