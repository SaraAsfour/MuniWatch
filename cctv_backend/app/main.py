from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, dashboard, live_feed, events, analytics, internal

# Auto-create tables in dev. In production, use Alembic migrations instead.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for the AI CCTV Monitoring System (auth, dashboard, live feed, evidence log, analytics).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(live_feed.router)
app.include_router(events.router)
app.include_router(analytics.router)
app.include_router(internal.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
