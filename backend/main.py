"""
main.py
-------
Yeh hamari FastAPI application ka entrypoint hai.
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.api import admin, auth, chat, conversations, documents, notices
from backend.config import settings
from backend.database.connection import get_db, init_db

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App start par database tables ensure karo."""
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Language-Agnostic Institutional Chatbot backend (SIH25104)",
    lifespan=lifespan,
)

# ---------------------------------------------------------
# CORS setup
# ---------------------------------------------------------
# Humara frontend ek alag "origin" se serve ho raha hai
# (seedha file:// se, ya baad mein kisi doosre port se).
# Bina CORS ke, browser security ke wajah se fetch() calls
# block kar dega. Development ke liye hum sab origins allow
# kar rahe hain — Phase 15 (Security) mein isko restrict
# karenge sirf apne actual frontend URL tak.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend ka path current working directory par depend nahi hona chahiye.
frontend_path = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")

# Register API routers
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(auth.router)
app.include_router(notices.router)
app.include_router(admin.router)
app.include_router(documents.router)


@app.get("/")
def root():
    return {
        "message": "SIH25104 Chatbot backend is running.",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def database_health_check(db: Session = Depends(get_db)):
    """Database connection ko simple SELECT 1 se check karo."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable")
