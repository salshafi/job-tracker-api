from fastapi import FastAPI

# Imported so Base knows the Application table exists
from app import models  # noqa: F401
from app.database import Base, engine
from app.routes import router

# Create the tables in the database if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Application Tracker API")

# Add all the /applications endpoints to the app
app.include_router(router)


# Simple check that the service is running
@app.get("/health")
def health_check():
    return {"status": "ok"}