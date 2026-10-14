from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Use a throwaway in-memory database so tests never touch job_tracker.db
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_function():
    # Fresh empty tables before every test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def make_application(**overrides):
    data = {"company": "Acme", "role": "Backend Intern"}
    data.update(overrides)
    return client.post("/applications", json=data)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_create_uses_default_status():
    response = make_application()
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "saved"
    assert body["id"] == 1


def test_create_rejects_empty_company():
    assert make_application(company="").status_code == 422


def test_create_rejects_unknown_status():
    assert make_application(status="banana").status_code == 422


def test_list_and_filter_by_status():
    make_application(status="applied")
    make_application(company="Other")
    assert len(client.get("/applications").json()) == 2
    applied = client.get("/applications", params={"status": "applied"}).json()
    assert len(applied) == 1
    assert applied[0]["status"] == "applied"


def test_get_missing_returns_404():
    assert client.get("/applications/999").status_code == 404


def test_patch_changes_only_sent_fields():
    make_application()
    response = client.patch("/applications/1", json={"status": "interview"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "interview"
    assert body["company"] == "Acme"


def test_delete_then_404():
    make_application()
    assert client.delete("/applications/1").status_code == 204
    assert client.get("/applications/1").status_code == 404
