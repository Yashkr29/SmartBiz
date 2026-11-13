import os, sys, tempfile, pathlib
# Tests always run on a throwaway SQLite file with the AI switched off, whatever backend/.env says.
_tmp = tempfile.mkdtemp(prefix="smartbiz-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{pathlib.Path(_tmp, 'test.db').as_posix()}"
os.environ["GOOGLE_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ.pop("AI_DATABASE_URL", None)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import itertools, pytest
from fastapi.testclient import TestClient
from app.main import app

_n = itertools.count()

@pytest.fixture
def client():
    return TestClient(app)

def signup(client, name="Owner"):
    i = next(_n)
    r = client.post("/api/auth/register", json={"name": f"{name} {i}", "email": f"user{i}@test.com", "password": "secret123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

def owner_id(client, headers):
    return client.get("/api/auth/me", headers=headers).json()["id"]

@pytest.fixture
def user(client):
    return signup(client, "A")

@pytest.fixture
def other(client):
    return signup(client, "B")
