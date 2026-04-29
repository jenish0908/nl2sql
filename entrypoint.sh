#!/bin/sh
set -e

echo "Creating database tables..."
python -c "
from sqlalchemy import create_engine
from app.models.database import Base
from app.config import settings
engine = create_engine(settings.sync_database_url)
Base.metadata.create_all(engine)
engine.dispose()
print('Tables created.')
"

echo "Seeding demo data..."
python scripts/seed_demo_data.py

echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
