from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.models.schemas import DatabaseSchema, SchemaTable, SchemaColumn, SchemaForeignKey

EXCLUDED_TABLES = {"query_log", "alembic_version"}


async def inspect_schema(session: AsyncSession) -> DatabaseSchema:
    tables_result = await session.execute(
        text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
    )
    table_names = [row[0] for row in tables_result if row[0] not in EXCLUDED_TABLES]

    pk_result = await session.execute(
        text("""
            SELECT kcu.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
        """)
    )
    primary_keys: dict[str, set[str]] = {}
    for row in pk_result:
        primary_keys.setdefault(row[0], set()).add(row[1])

    fk_result = await session.execute(
        text("""
            SELECT
                kcu.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
        """)
    )
    foreign_keys: dict[str, list[SchemaForeignKey]] = {}
    for row in fk_result:
        fk = SchemaForeignKey(
            column=row[1],
            references_table=row[2],
            references_column=row[3],
        )
        foreign_keys.setdefault(row[0], []).append(fk)

    schema_tables: list[SchemaTable] = []
    for table_name in table_names:
        cols_result = await session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                ORDER BY ordinal_position
            """),
            {"table_name": table_name},
        )
        columns = [
            SchemaColumn(
                name=row[0],
                type=row[1],
                nullable=(row[2] == "YES"),
                primary_key=(row[0] in primary_keys.get(table_name, set())),
            )
            for row in cols_result
        ]
        schema_tables.append(
            SchemaTable(
                name=table_name,
                columns=columns,
                foreign_keys=foreign_keys.get(table_name, []),
            )
        )

    return DatabaseSchema(tables=schema_tables)


def schema_to_text(schema: DatabaseSchema) -> str:
    lines: list[str] = []
    for table in schema.tables:
        lines.append(f"Table: {table.name}")
        for col in table.columns:
            pk_marker = " [PK]" if col.primary_key else ""
            null_marker = "" if col.nullable else " NOT NULL"
            lines.append(f"  - {col.name}: {col.type}{pk_marker}{null_marker}")
        for fk in table.foreign_keys:
            lines.append(
                f"  FK: {fk.column} -> {fk.references_table}.{fk.references_column}"
            )
        lines.append("")
    return "\n".join(lines)
