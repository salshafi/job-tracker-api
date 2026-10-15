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


# ---------- Input clean-up and validation ----------


def test_create_rejects_whitespace_only_company_and_role():
    assert make_application(company="   ").status_code == 422
    assert make_application(role="\t \n").status_code == 422


def test_create_trims_company_and_role():
    body = make_application(company="  Acme  ", role=" Backend Intern ").json()
    assert body["company"] == "Acme"
    assert body["role"] == "Backend Intern"


def test_blank_notes_and_job_url_are_stored_as_none():
    body = make_application(notes="   ", job_url="").json()
    assert body["notes"] is None
    assert body["job_url"] is None


def test_valid_job_url_is_accepted_and_trimmed():
    response = make_application(job_url="  https://example.com/jobs/123  ")
    assert response.status_code == 201
    assert response.json()["job_url"] == "https://example.com/jobs/123"


def test_invalid_job_urls_are_rejected():
    for bad in ["not a url", "ftp://example.com/job", "javascript:alert(1)", "https://"]:
        assert make_application(job_url=bad).status_code == 422, bad


def test_too_long_job_url_is_rejected():
    long_url = "https://example.com/" + "a" * 500
    assert make_application(job_url=long_url).status_code == 422


def test_patch_rejects_blank_company_and_bad_url():
    make_application()
    assert client.patch("/applications/1", json={"company": "  "}).status_code == 422
    assert client.patch("/applications/1", json={"job_url": "nope"}).status_code == 422
    # the record is unchanged after the rejected updates
    assert client.get("/applications/1").json()["company"] == "Acme"


def test_patch_can_clear_job_url():
    make_application(job_url="https://example.com/jobs/1")
    response = client.patch("/applications/1", json={"job_url": ""})
    assert response.status_code == 200
    assert response.json()["job_url"] is None


# ---------- CORS (lets the React front end call the API) ----------


def preflight(origin):
    return client.options(
        "/applications",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


def test_cors_allows_the_local_react_dev_server():
    response = preflight("http://localhost:5173")
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_blocks_unknown_origins():
    response = preflight("https://evil.example.com")
    assert "access-control-allow-origin" not in response.headers
