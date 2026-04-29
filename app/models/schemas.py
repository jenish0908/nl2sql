from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class IntentType(str, Enum):
    aggregation = "aggregation"
    filter = "filter"
    join = "join"
    trend = "trend"
    comparison = "comparison"


class QueryIntent(BaseModel):
    intent_type: IntentType
    entities: List[str]
    time_range: Optional[str] = None
    ambiguity_flags: List[str] = []


class ClarificationRequest(BaseModel):
    original_question: str
    clarification_needed: str
    ambiguity_flags: List[str]


class GeneratedSQL(BaseModel):
    sql: str
    explanation: str
    tables_used: List[str]
    estimated_complexity: str


class AgentUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float


class QueryRequest(BaseModel):
    question: str


class ClarifyRequest(BaseModel):
    question: str
    clarification: str


class QueryResponse(BaseModel):
    query_id: int
    sql: Optional[str] = None
    explanation: Optional[str] = None
    results: List[dict] = []
    row_count: int = 0
    intent: Optional[dict] = None
    latency_ms: float
    tokens_used: int
    cost_usd: float
    self_corrections: int = 0
    clarification_needed: Optional[ClarificationRequest] = None
    error: Optional[str] = None


class FeedbackRequest(BaseModel):
    sql_correct: bool
    result_correct: bool
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class EvaluationSummary(BaseModel):
    total_queries: int
    avg_latency_ms: float
    avg_cost_usd: float
    self_correction_rate: float
    clarification_rate: float
    error_rate: float


class HistoryItem(BaseModel):
    id: int
    question: str
    sql: Optional[str] = None
    explanation: Optional[str] = None
    row_count: Optional[int] = None
    latency_ms: Optional[float] = None
    cost_usd: Optional[float] = None
    tokens_used: Optional[int] = None
    self_corrections: Optional[int] = None
    clarification_requested: Optional[bool] = None
    execution_error: Optional[bool] = None
    created_at: datetime


class SchemaColumn(BaseModel):
    name: str
    type: str
    nullable: bool
    primary_key: bool = False


class SchemaForeignKey(BaseModel):
    column: str
    references_table: str
    references_column: str


class SchemaTable(BaseModel):
    name: str
    columns: List[SchemaColumn]
    foreign_keys: List[SchemaForeignKey] = []


class DatabaseSchema(BaseModel):
    tables: List[SchemaTable]
