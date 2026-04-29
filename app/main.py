from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.db import create_tables
from app.api import query, schema, evaluations


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title="NL2SQL Agent",
    description="AI-powered natural language to SQL query agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router, tags=["Query"])
app.include_router(schema.router, tags=["Schema"])
app.include_router(evaluations.router, tags=["Evaluations"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "nl2sql-agent"}
