from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.db import get_db
from app.services.schema_inspector import inspect_schema
from app.models.schemas import DatabaseSchema

router = APIRouter()


@router.get("/schema", response_model=DatabaseSchema)
async def get_schema(session: AsyncSession = Depends(get_db)):
    return await inspect_schema(session)
