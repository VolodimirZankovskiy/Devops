import mongomock
import pytest

from app import create_app


@pytest.fixture
def client_and_collection():
    mongo_client = mongomock.MongoClient()
    app = create_app(mongo_client=mongo_client)
    app.testing = True
    collection = mongo_client["taskmanager"]["tasks"]
    return app.test_client(), collection


def test_health(client_and_collection):
    client, _ = client_and_collection
    resp = client.get("/health")
    assert resp.status_code == 200


def test_stats_with_no_tasks(client_and_collection):
    client, _ = client_and_collection
    resp = client.get("/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 0
    assert data["by_status"] == {}


def test_stats_groups_by_status(client_and_collection):
    client, collection = client_and_collection
    collection.insert_many(
        [
            {"title": "A", "status": "pending"},
            {"title": "B", "status": "pending"},
            {"title": "C", "status": "done"},
        ]
    )

    resp = client.get("/stats")
    data = resp.get_json()
    assert data["total"] == 3
    assert data["by_status"]["pending"] == 2
    assert data["by_status"]["done"] == 1
