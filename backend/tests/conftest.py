import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="yhg-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["CHECKPOINT_DB"] = f"{_tmp}/checkpoints.db"
os.environ["OPENAI_API_KEY"] = ""  # force demo mode (no network)
os.environ["STATIC_DIR"] = f"{_tmp}/no-static"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import DEMO_PATIENT_EMAIL, DEMO_PATIENT_PASSWORD  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def patient_headers(client):
    return _login(client, DEMO_PATIENT_EMAIL, DEMO_PATIENT_PASSWORD)


@pytest.fixture
def login():
    return _login
