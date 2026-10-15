import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Imported so Base knows the Application table exists
from app import models  # noqa: F401
from app.database import Base, engine
from app.routes import router

# Create the tables in the database if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Application Tracker API")

# CORS: lets a browser app (like a React front end) on another address call this API.
# Defaults to the local Vite dev server. For a deployed front end, set the
# CORS_ORIGINS environment variable to a comma-separated list of allowed origins.
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

# Add all the /applications endpoints to the app
app.include_router(router)


# Simple check that the service is running
@app.get("/health")
def health_check():
    return {"status": "ok"}
