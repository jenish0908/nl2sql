from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.services.db import get_db
from app.models.database import QueryLog
from app.models.schemas import FeedbackRequest, EvaluationSummary, HistoryItem

router = APIRouter()


@router.get("/history", response_model=list[HistoryItem])
async def get_history(session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(QueryLog).order_by(QueryLog.created_at.desc()).limit(20)
    )
    logs = result.scalars().all()
    return [
        HistoryItem(
            id=log.id,
            question=log.question,
            sql=log.sql,
            explanation=log.explanation,
            row_count=log.row_count,
            latency_ms=log.latency_ms,
            cost_usd=log.cost_usd,
            tokens_used=log.tokens_used,
            self_corrections=log.self_corrections,
            clarification_requested=log.clarification_requested,
            execution_error=log.execution_error,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get("/evaluations/summary", response_model=EvaluationSummary)
async def get_evaluation_summary(session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(
            func.count(QueryLog.id).label("total"),
            func.avg(QueryLog.latency_ms).label("avg_latency"),
            func.avg(QueryLog.cost_usd).label("avg_cost"),
            func.avg(
                case((QueryLog.self_corrections > 0, 1.0), else_=0.0)
            ).label("correction_rate"),
            func.avg(
                case((QueryLog.clarification_requested == True, 1.0), else_=0.0)
            ).label("clarification_rate"),
            func.avg(
                case((QueryLog.execution_error == True, 1.0), else_=0.0)
            ).label("error_rate"),
        )
    )
    row = result.one()

    return EvaluationSummary(
        total_queries=row.total or 0,
        avg_latency_ms=round(float(row.avg_latency or 0), 2),
        avg_cost_usd=round(float(row.avg_cost or 0), 6),
        self_correction_rate=round(float(row.correction_rate or 0), 4),
        clarification_rate=round(float(row.clarification_rate or 0), 4),
        error_rate=round(float(row.error_rate or 0), 4),
    )


@router.post("/evaluations/{query_id}/feedback")
async def submit_feedback(
    query_id: int,
    feedback: FeedbackRequest,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(QueryLog).where(QueryLog.id == query_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail=f"Query ID {query_id} not found.")

    log.sql_correct = feedback.sql_correct
    log.result_correct = feedback.result_correct
    log.rating = feedback.rating
    log.feedback_comment = feedback.comment
    await session.flush()

    return {"message": "Feedback recorded.", "query_id": query_id}
