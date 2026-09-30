from fastapi import FastAPI

app = FastAPI(title="Job Application Tracker API")


@app.get("/health")
def health_check():
    return { "status": "ok"}

from app import models  # noqa: F401
from app.database import Base, engine

Base.metadata.create_all(bind=engine)