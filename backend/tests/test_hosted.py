import pytest
from fastapi.testclient import TestClient
from app.hosted import create_app


@pytest.fixture
def hosted(monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text("<h1>ShelterStock</h1>")
    monkeypatch.setenv("STATIC_DIR", str(tmp_path))
    monkeypatch.setenv("DEMO_PASSWORD", "test-only-password-123")
    monkeypatch.setenv("DEMO_USERNAME", "demo")
    return TestClient(create_app())


def test_demo_requires_credentials_for_pages_and_api(hosted):
    for path in ["/", "/api/items", "/api/docs"]:
        assert hosted.get(path).status_code == 401
    assert hosted.get("/api/items", auth=("demo", "wrong")).status_code == 401
    assert hosted.get("/", headers={"Authorization": "Basic invalid!"}).status_code == 401


def test_demo_serves_real_api_and_frontend(hosted):
    auth = ("demo", "test-only-password-123")
    assert "ShelterStock" in hosted.get("/", auth=auth).text
    response = hosted.get("/api/items", auth=auth)
    assert response.status_code == 200 and len(response.json()) == 3
    assert response.headers["cache-control"] == "no-store"
    assert hosted.get("/health").status_code == 200


def test_demo_rejects_cross_origin_mutation(hosted):
    response = hosted.post("/api/pickups/00000000-0000-0000-0000-000000000001/fulfill",
                           auth=("demo", "test-only-password-123"),
                           headers={"Origin": "https://unrelated.example"})
    assert response.status_code == 403


def test_demo_fails_closed_without_password(monkeypatch):
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="DEMO_PASSWORD"):
        create_app()
