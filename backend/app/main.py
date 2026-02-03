from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time
from sqlalchemy.exc import OperationalError

from app.api import router
from app.db.session import engine
from app.db.models import Base

app = FastAPI(
    title="Architecture Diagram Generator",
    version="0.1.0",
)

# ✅ Middleware FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Routes AFTER middleware
app.include_router(router)


@app.on_event("startup")
def startup():
    retries = 10
    delay = 2

    for attempt in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Database connected")
            return
        except OperationalError:
            print(f"⏳ Waiting for database... ({attempt + 1}/{retries})")
            time.sleep(delay)

    raise RuntimeError("❌ Database not ready after retries")
