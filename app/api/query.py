import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.db import get_db
from app.services.sql_executor import execute_sql
from app.agents.intent_extraction import extract_intent
from app.agents.clarification import refine_with_clarification
from app.agents.sql_generation import generate_sql
from app.models.schemas import (
    QueryRequest,
    ClarifyRequest,
    QueryResponse,
    ClarificationRequest,
)
from app.models.database import QueryLog

router = APIRouter()


async def _run_pipeline(
    question: str,
    session: AsyncSession,
) -> QueryResponse:
    start = time.monotonic()
    total_tokens = 0
    total_cost = 0.0

    intent_result, intent_usage = extract_intent(question)
    total_tokens += intent_usage.total_tokens
    total_cost += intent_usage.cost_usd

    latency_ms = (time.monotonic() - start) * 1000

    if isinstance(intent_result, ClarificationRequest):
        log = QueryLog(
            question=question,
            latency_ms=latency_ms,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            clarification_requested=True,
            execution_error=False,
            self_corrections=0,
        )
        session.add(log)
        await session.flush()
        await session.refresh(log)

        return QueryResponse(
            query_id=log.id,
            latency_ms=round(latency_ms, 2),
            tokens_used=total_tokens,
            cost_usd=round(total_cost, 6),
            clarification_needed=intent_result,
        )

    try:
        generated, sql_usage, self_corrections = await generate_sql(intent_result, session)
        total_tokens += sql_usage.total_tokens
        total_cost += sql_usage.cost_usd

        rows, row_count = await execute_sql(session, generated.sql)
        latency_ms = (time.monotonic() - start) * 1000

        log = QueryLog(
            question=question,
            sql=generated.sql,
            explanation=generated.explanation,
            row_count=row_count,
            intent_type=intent_result.intent_type.value,
            tables_used=",".join(generated.tables_used),
            latency_ms=round(latency_ms, 2),
            tokens_used=total_tokens,
            cost_usd=round(total_cost, 6),
            self_corrections=self_corrections,
            clarification_requested=False,
            execution_error=False,
        )
        session.add(log)
        await session.flush()
        await session.refresh(log)

        return QueryResponse(
            query_id=log.id,
            sql=generated.sql,
            explanation=generated.explanation,
            results=rows,
            row_count=row_count,
            intent=intent_result.model_dump(),
            latency_ms=round(latency_ms, 2),
            tokens_used=total_tokens,
            cost_usd=round(total_cost, 6),
            self_corrections=self_corrections,
        )

    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        log = QueryLog(
            question=question,
            latency_ms=round(latency_ms, 2),
            tokens_used=total_tokens,
            cost_usd=round(total_cost, 6),
            execution_error=True,
            error_message=str(exc),
            self_corrections=0,
        )
        session.add(log)
        await session.flush()
        await session.refresh(log)

        return QueryResponse(
            query_id=log.id,
            latency_ms=round(latency_ms, 2),
            tokens_used=total_tokens,
            cost_usd=round(total_cost, 6),
            error=str(exc),
        )


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, session: AsyncSession = Depends(get_db)):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    return await _run_pipeline(request.question.strip(), session)


@router.post("/query/clarify", response_model=QueryResponse)
async def query_clarify(request: ClarifyRequest, session: AsyncSession = Depends(get_db)):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if not request.clarification.strip():
        raise HTTPException(status_code=400, detail="Clarification cannot be empty.")

    combined = f"{request.question.strip()}\n\nAdditional context: {request.clarification.strip()}"
    return await _run_pipeline(combined, session)
