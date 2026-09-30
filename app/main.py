from fastapi import FastAPI

app = FastAPI(title="Job Application Tracker API")


@app.get("/health")
def health_check():
    return { "status": "ok"}

