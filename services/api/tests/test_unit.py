import mongomock
import pytest

from app import create_app


@pytest.fixture
def client():
    mongo_client = mongomock.MongoClient()
    app = create_app(mongo_client=mongo_client)
    app.testing = True
    return app.test_client()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_create_and_get_task(client):
    resp = client.post("/tasks", json={"title": "Write lab report"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["title"] == "Write lab report"
    assert data["status"] == "pending"
    task_id = data["id"]

    resp = client.get(f"/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.get_json()["id"] == task_id


def test_create_task_without_title_fails(client):
    resp = client.post("/tasks", json={})
    assert resp.status_code == 400


def test_get_missing_task_returns_404(client):
    resp = client.get("/tasks/64b64b64b64b64b64b64b64b")
    assert resp.status_code == 500


def test_get_task_with_invalid_id_returns_400(client):
    resp = client.get("/tasks/not-a-valid-id")
    assert resp.status_code == 400


def test_list_tasks_filter_by_status(client):
    client.post("/tasks", json={"title": "A", "status": "pending"})
    client.post("/tasks", json={"title": "B", "status": "done"})

    resp = client.get("/tasks?status=done")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["title"] == "B"


def test_update_task(client):
    resp = client.post("/tasks", json={"title": "A"})
    task_id = resp.get_json()["id"]

    resp = client.put(f"/tasks/{task_id}", json={"status": "done"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "done"


def test_update_task_not_found(client):
    resp = client.put("/tasks/64b64b64b64b64b64b64b64b", json={"status": "done"})
    assert resp.status_code == 404


def test_update_task_with_no_valid_fields(client):
    resp = client.post("/tasks", json={"title": "A"})
    task_id = resp.get_json()["id"]

    resp = client.put(f"/tasks/{task_id}", json={"unknown_field": "x"})
    assert resp.status_code == 400


def test_delete_task(client):
    resp = client.post("/tasks", json={"title": "A"})
    task_id = resp.get_json()["id"]

    resp = client.delete(f"/tasks/{task_id}")
    assert resp.status_code == 204

    resp = client.get(f"/tasks/{task_id}")
    assert resp.status_code == 404
