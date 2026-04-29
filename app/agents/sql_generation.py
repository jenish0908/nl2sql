import re
from groq import Groq
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.schemas import QueryIntent, GeneratedSQL, AgentUsage
from app.services.schema_inspector import inspect_schema, schema_to_text
from app.services.sql_executor import execute_sql, validate_sql_safe

SQL_SYSTEM_PROMPT = """You are an expert PostgreSQL developer. Your job is to convert structured query intents into safe, optimized SQL queries.

RULES — CRITICAL:
1. Only generate SELECT statements. Never use DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, TRUNCATE.
2. Always use table aliases for clarity in JOINs.
3. Use proper PostgreSQL date functions (NOW(), INTERVAL, DATE_TRUNC, etc.).
4. Include a LIMIT clause when returning multiple rows.
5. Never use SELECT * — always name specific columns.

REASONING PROCESS — follow this exact format:

**Step 1 - Relevant Tables:** [list the tables needed and why]
**Step 2 - Joins Required:** [describe the JOIN logic needed]
**Step 3 - SQL Query:**
```sql
SELECT ...
```
**Step 4 - Self-Review:** [verify correctness, confirm SELECT-only, no injection risks]
**Explanation:** [one paragraph plain-English explanation of what this SQL does]
**Tables Used:** [comma-separated list of tables used]
**Complexity:** [simple | moderate | complex]"""

SQL_CODE_BLOCK = re.compile(r"```sql\s*(.*?)```", re.DOTALL | re.IGNORECASE)
TABLES_USED_PATTERN = re.compile(r"\*\*Tables Used:\*\*\s*(.+)", re.IGNORECASE)
COMPLEXITY_PATTERN = re.compile(r"\*\*Complexity:\*\*\s*(\w+)", re.IGNORECASE)
EXPLANATION_PATTERN = re.compile(r"\*\*Explanation:\*\*\s*(.+?)(?=\*\*|\Z)", re.DOTALL | re.IGNORECASE)

_client = Groq(api_key=settings.groq_api_key)


def _extract_sql(text: str) -> str | None:
    match = SQL_CODE_BLOCK.search(text)
    if match:
        return match.group(1).strip()
    return None


def _extract_field(pattern: re.Pattern, text: str, default: str = "") -> str:
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    return default


def _build_user_message(intent: QueryIntent, schema_text: str) -> str:
    return f"""Database Schema:
{schema_text}

Query Intent:
- Type: {intent.intent_type.value}
- Entities referenced: {', '.join(intent.entities) if intent.entities else 'not specified'}
- Time range: {intent.time_range or 'none'}

Generate the SQL query following the step-by-step reasoning process."""


async def generate_sql(
    intent: QueryIntent,
    session: AsyncSession,
) -> tuple[GeneratedSQL, AgentUsage, int]:
    schema = await inspect_schema(session)
    schema_text = schema_to_text(schema)

    total_input_tokens = 0
    total_output_tokens = 0
    self_corrections = 0
    last_error: str | None = None

    user_message = _build_user_message(intent, schema_text)

    for attempt in range(settings.max_self_corrections + 1):
        if attempt > 0 and last_error:
            self_corrections += 1
            current_message = (
                f"{user_message}\n\n"
                f"The SQL you generated produced this error: {last_error}\n"
                f"Fix the SQL and return only the corrected query following the same step-by-step format."
            )
        else:
            current_message = user_message

        response = _client.chat.completions.create(
            model=settings.groq_model,
            max_tokens=2048,
            temperature=0,
            messages=[
                {"role": "system", "content": SQL_SYSTEM_PROMPT},
                {"role": "user", "content": current_message},
            ],
        )

        total_input_tokens += response.usage.prompt_tokens
        total_output_tokens += response.usage.completion_tokens

        raw_response = response.choices[0].message.content

        sql = _extract_sql(raw_response)
        if not sql:
            last_error = "No SQL code block found in response."
            continue

        is_safe, safety_error = validate_sql_safe(sql)
        if not is_safe:
            last_error = safety_error
            continue

        try:
            rows, row_count = await execute_sql(session, sql)
            explanation = _extract_field(
                EXPLANATION_PATTERN, raw_response, "SQL query generated successfully."
            )
            tables_raw = _extract_field(TABLES_USED_PATTERN, raw_response, "")
            tables_used = [t.strip() for t in tables_raw.split(",") if t.strip()] if tables_raw else []
            complexity = _extract_field(COMPLEXITY_PATTERN, raw_response, "moderate")

            usage = AgentUsage(
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                total_tokens=total_input_tokens + total_output_tokens,
                cost_usd=0.0,
            )

            generated = GeneratedSQL(
                sql=sql,
                explanation=explanation.strip(),
                tables_used=tables_used,
                estimated_complexity=complexity.lower(),
            )
            return generated, usage, self_corrections

        except Exception as exc:
            last_error = str(exc)

    raise RuntimeError(
        f"SQL generation failed after {settings.max_self_corrections} retries. "
        f"Last error: {last_error}"
    )
