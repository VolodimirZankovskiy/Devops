import os

import pytest
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from app import create_app

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
TEST_DB_NAME = "taskmanager_integration_test"


def _mongo_available():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=500)
        client.admin.command("ping")
        return True
    except ServerSelectionTimeoutError:
        return False


pytestmark = pytest.mark.skipif(
    not _mongo_available(),
    reason="MongoDB is not reachable at MONGO_URI, skipping integration tests",
)


@pytest.fixture
def client():
    mongo_client = MongoClient(MONGO_URI)
    mongo_client.drop_database(TEST_DB_NAME)
    os.environ["MONGO_DB"] = TEST_DB_NAME

    app = create_app(mongo_client=mongo_client)
    app.testing = True
    yield app.test_client()

    mongo_client.drop_database(TEST_DB_NAME)


def test_full_task_lifecycle_against_real_mongo(client):
    resp = client.post("/tasks", json={"title": "Integration test task"})
    assert resp.status_code == 201
    task_id = resp.get_json()["id"]

    resp = client.get("/tasks")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1

    resp = client.put(f"/tasks/{task_id}", json={"status": "done"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "done"

    resp = client.delete(f"/tasks/{task_id}")
    assert resp.status_code == 204

    resp = client.get(f"/tasks/{task_id}")
    assert resp.status_code == 404
