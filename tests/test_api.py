"""API tests via FastAPI's TestClient: at least one success and one failure
case per endpoint, plus the global 500 handler.

Uses the same db_session fixture (tests/conftest.py) as the repository/
analytics tests -- everything happens inside a rolled-back transaction, so
these tests never leave data behind. get_db is overridden via
app.dependency_overrides to hand back that same session.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.deps import get_db
from database import repository
from events.event import Event as PipelineEvent


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # raise_server_exceptions=False: Starlette's TestClient re-raises the
    # original exception for debuggability by default, even when a
    # registered exception handler already turned it into a real response --
    # we need the actual HTTP response here, not the raw exception.
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# --- POST /cameras ---


def test_create_camera_success(client):
    response = client.post("/cameras", json={"camera_id": "cam_1", "name": "Front Gate"})
    assert response.status_code == 201
    body = response.json()
    assert body["camera_id"] == "cam_1"
    assert body["name"] == "Front Gate"
    assert "id" in body


def test_create_camera_missing_required_field_fails_validation(client):
    response = client.post("/cameras", json={"name": "no camera_id given"})
    assert response.status_code == 422


# --- GET /cameras/{camera_id}/events ---


def test_list_camera_events_success(client, db_session):
    camera = repository.get_or_create_camera(db_session, "cam_2")
    repository.get_or_create_object(db_session, camera, object_id=1, class_name="person", timestamp=0.0)
    event = PipelineEvent(
        event_type="OBJECT_APPEARED", object_id=1, class_name="person",
        timestamp=0.0, camera_id="cam_2", confidence=0.9, metadata={},
    )
    repository.add_event_from_pipeline(db_session, camera, event)
    db_session.flush()

    response = client.get("/cameras/cam_2/events")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["event_type"] == "OBJECT_APPEARED"
    assert body[0]["class_name"] == "person"


def test_list_camera_events_unknown_camera_returns_404(client):
    response = client.get("/cameras/nonexistent/events")
    assert response.status_code == 404


# --- POST /videos ---


def test_create_video_success(client):
    client.post("/cameras", json={"camera_id": "cam_3"})
    response = client.post("/videos", json={"camera_id": "cam_3", "path": "/data/clip.mp4"})
    assert response.status_code == 201
    assert response.json()["path"] == "/data/clip.mp4"


def test_create_video_unknown_camera_returns_404(client):
    response = client.post("/videos", json={"camera_id": "nonexistent", "path": "/data/clip.mp4"})
    assert response.status_code == 404


# --- GET /objects/{id}/trajectory ---


def test_get_object_trajectory_success(client, db_session):
    camera = repository.get_or_create_camera(db_session, "cam_4")
    obj = repository.get_or_create_object(db_session, camera, object_id=1, class_name="car", timestamp=0.0)
    repository.add_track_point(db_session, obj, frame_id=0, timestamp=0.0, x=1.0, y=2.0)
    repository.add_track_point(db_session, obj, frame_id=1, timestamp=0.1, x=3.0, y=4.0)
    db_session.flush()

    response = client.get(f"/objects/{obj.id}/trajectory")
    assert response.status_code == 200
    body = response.json()
    assert body["camera_id"] == "cam_4"
    assert body["class_name"] == "car"
    assert len(body["points"]) == 2
    assert body["points"][0] == {"frame_id": 0, "timestamp": 0.0, "x": 1.0, "y": 2.0}


def test_get_object_trajectory_unknown_id_returns_404(client):
    response = client.get("/objects/999999/trajectory")
    assert response.status_code == 404


# --- POST /zones ---


def test_create_zone_success(client):
    client.post("/cameras", json={"camera_id": "cam_5"})
    response = client.post(
        "/zones", json={"camera_id": "cam_5", "zone_id": "restricted", "polygon": [[0, 0], [10, 0], [10, 10]]}
    )
    assert response.status_code == 201
    assert response.json()["zone_id"] == "restricted"


def test_create_zone_with_fewer_than_three_points_fails_validation(client):
    client.post("/cameras", json={"camera_id": "cam_6"})
    response = client.post("/zones", json={"camera_id": "cam_6", "zone_id": "bad", "polygon": [[0, 0], [10, 0]]})
    assert response.status_code == 422


# --- POST /lines ---


def test_create_line_success(client):
    client.post("/cameras", json={"camera_id": "cam_7"})
    response = client.post(
        "/lines", json={"camera_id": "cam_7", "line_id": "entrance", "start": [0, 50], "end": [100, 50]}
    )
    assert response.status_code == 201
    assert response.json()["line_id"] == "entrance"


def test_create_line_with_identical_start_and_end_fails_validation(client):
    client.post("/cameras", json={"camera_id": "cam_8"})
    response = client.post(
        "/lines", json={"camera_id": "cam_8", "line_id": "bad", "start": [10, 10], "end": [10, 10]}
    )
    assert response.status_code == 422


# --- GET /analytics ---


def test_get_analytics_success(client, db_session):
    camera = repository.get_or_create_camera(db_session, "cam_9")
    repository.get_or_create_object(db_session, camera, object_id=1, class_name="person", timestamp=0.0)
    event = PipelineEvent(
        event_type="OBJECT_APPEARED", object_id=1, class_name="person",
        timestamp=0.0, camera_id="cam_9", confidence=0.9, metadata={},
    )
    repository.add_event_from_pipeline(db_session, camera, event)
    db_session.flush()

    response = client.get("/analytics", params={"camera_id": "cam_9"})
    assert response.status_code == 200
    body = response.json()
    assert body["object_count"] == 1
    assert body["event_frequency"] == {"OBJECT_APPEARED": 1}


def test_get_analytics_invalid_query_param_type_fails_validation(client):
    response = client.get("/analytics", params={"start_time": "not-a-number"})
    assert response.status_code == 422


# --- 500 handling ---


def test_unexpected_error_returns_clean_500_not_a_stack_trace(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("simulated unexpected failure")

    monkeypatch.setattr("database.repository.get_camera", boom)

    response = client.get("/cameras/anything/events")
    assert response.status_code == 500
    assert response.json() == {"detail": "internal server error"}
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text
