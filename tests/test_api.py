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
from sqlalchemy import select

from agent import actions
from agent.agent import AgentAnswer, ToolCallRecord
from api.app import app
from api.deps import get_agent, get_db
from database import repository
from database.models import TrackedObject
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


# --- GET /cameras ---


def test_list_cameras_success(client, db_session):
    repository.get_or_create_camera(db_session, "cam_list_a")
    repository.get_or_create_camera(db_session, "cam_list_b")
    db_session.flush()

    response = client.get("/cameras")
    assert response.status_code == 200
    camera_ids = {c["camera_id"] for c in response.json()}
    assert {"cam_list_a", "cam_list_b"} <= camera_ids


def test_list_cameras_empty_is_still_200(client):
    response = client.get("/cameras")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# --- GET /cameras/{camera_id}/zones, GET /cameras/{camera_id}/lines ---


def test_list_camera_zones_and_lines(client, db_session):
    camera = repository.get_or_create_camera(db_session, "cam_geo")
    repository.get_or_create_zone(db_session, camera, "z1", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)])
    repository.get_or_create_line(db_session, camera, "l1", (0.0, 5.0), (10.0, 5.0))
    db_session.flush()

    zones_response = client.get("/cameras/cam_geo/zones")
    assert zones_response.status_code == 200
    assert zones_response.json()[0]["zone_id"] == "z1"

    lines_response = client.get("/cameras/cam_geo/lines")
    assert lines_response.status_code == 200
    assert lines_response.json()[0] == {"id": lines_response.json()[0]["id"], "line_id": "l1", "start": [0.0, 5.0], "end": [10.0, 5.0]}


def test_list_camera_zones_unknown_camera_returns_404(client):
    assert client.get("/cameras/nonexistent/zones").status_code == 404


def test_list_camera_lines_unknown_camera_returns_404(client):
    assert client.get("/cameras/nonexistent/lines").status_code == 404


# --- GET /cameras/{camera_id}/objects ---


def test_list_camera_objects_success(client, db_session):
    camera = repository.get_or_create_camera(db_session, "cam_objs")
    repository.get_or_create_object(db_session, camera, object_id=1, class_name="person", timestamp=0.0)
    repository.get_or_create_object(db_session, camera, object_id=2, class_name="car", timestamp=1.0)
    db_session.flush()

    response = client.get("/cameras/cam_objs/objects")
    assert response.status_code == 200
    class_names = {o["class_name"] for o in response.json()}
    assert class_names == {"person", "car"}


def test_list_camera_objects_unknown_camera_returns_404(client):
    response = client.get("/cameras/nonexistent/objects")
    assert response.status_code == 404


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


# --- GET /videos, GET /videos/{id}, GET /videos/{id}/stream ---


def test_list_videos_filters_by_camera(client, db_session):
    camera_a = repository.get_or_create_camera(db_session, "cam_vid_a")
    camera_b = repository.get_or_create_camera(db_session, "cam_vid_b")
    repository.create_video(db_session, camera_a, "/data/a.mp4")
    repository.create_video(db_session, camera_b, "/data/b.mp4")
    db_session.flush()

    response = client.get("/videos", params={"camera_id": "cam_vid_a"})
    assert response.status_code == 200
    paths = [v["path"] for v in response.json()]
    assert paths == ["/data/a.mp4"]


def test_get_video_success(client, db_session):
    camera = repository.get_or_create_camera(db_session, "cam_vid_c")
    video = repository.create_video(db_session, camera, "/data/c.mp4")
    db_session.flush()

    response = client.get(f"/videos/{video.id}")
    assert response.status_code == 200
    assert response.json()["path"] == "/data/c.mp4"


def test_get_video_unknown_id_returns_404(client):
    response = client.get("/videos/999999")
    assert response.status_code == 404


def test_stream_video_success(client, db_session, tmp_path):
    real_file = tmp_path / "clip.mp4"
    real_file.write_bytes(b"fake mp4 bytes for streaming test")
    camera = repository.get_or_create_camera(db_session, "cam_vid_stream")
    video = repository.create_video(db_session, camera, str(real_file))
    db_session.flush()

    response = client.get(f"/videos/{video.id}/stream")
    assert response.status_code == 200
    assert response.content == b"fake mp4 bytes for streaming test"
    assert response.headers["content-type"] == "video/mp4"


def test_stream_video_missing_file_on_disk_returns_404(client, db_session):
    camera = repository.get_or_create_camera(db_session, "cam_vid_missing")
    video = repository.create_video(db_session, camera, "/nonexistent/path/does-not-exist.mp4")
    db_session.flush()

    response = client.get(f"/videos/{video.id}/stream")
    assert response.status_code == 404


def test_stream_video_unknown_id_returns_404(client):
    response = client.get("/videos/999999/stream")
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
    assert body["points"][0] == {
        "frame_id": 0, "timestamp": 0.0, "x": 1.0, "y": 2.0,
        "x_min": None, "y_min": None, "x_max": None, "y_max": None,
    }


def test_get_object_trajectory_includes_bbox_when_provided(client, db_session):
    camera = repository.get_or_create_camera(db_session, "cam_4b")
    obj = repository.get_or_create_object(db_session, camera, object_id=1, class_name="car", timestamp=0.0)
    repository.add_track_point(db_session, obj, frame_id=0, timestamp=0.0, x=5.0, y=5.0, bbox=(0.0, 1.0, 10.0, 11.0))
    db_session.flush()

    response = client.get(f"/objects/{obj.id}/trajectory")
    point = response.json()["points"][0]
    assert (point["x_min"], point["y_min"], point["x_max"], point["y_max"]) == (0.0, 1.0, 10.0, 11.0)


def test_get_object_trajectory_unknown_id_returns_404(client):
    response = client.get("/objects/999999/trajectory")
    assert response.status_code == 404


# --- GET /objects/{id}, GET /objects/{id}/events ---


def _seed_object_with_lifecycle(db_session):
    """One object with two completed zone visits, one non-zone event, and a
    known first/last seen -- lets tests assert exact aggregation numbers
    (15.0 + 12.0 = 27.0 dwell seconds, 5 total events) instead of just
    checking the endpoint renders something."""
    camera = repository.get_or_create_camera(db_session, "cam_profile", name="Profile Camera")
    repository.get_or_create_zone(db_session, camera, "z1", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)])
    repository.get_or_create_object(db_session, camera, object_id=1, class_name="person", timestamp=0.0)
    repository.get_or_create_object(db_session, camera, object_id=1, class_name="person", timestamp=60.0)

    def _add(event_type, timestamp, metadata=None):
        repository.add_event_from_pipeline(
            db_session, camera,
            PipelineEvent(
                event_type=event_type, object_id=1, class_name="person",
                timestamp=timestamp, camera_id="cam_profile", confidence=0.9, metadata=metadata or {},
            ),
        )

    _add("OBJECT_APPEARED", 0.0)
    _add("ZONE_ENTERED", 10.0, {"zone_id": "z1"})
    _add("ZONE_EXITED", 25.0, {"zone_id": "z1"})  # visit 1: 15.0s
    _add("ZONE_ENTERED", 40.0, {"zone_id": "z1"})
    _add("ZONE_EXITED", 52.0, {"zone_id": "z1"})  # visit 2: 12.0s
    db_session.flush()

    obj = db_session.execute(
        select(TrackedObject).where(TrackedObject.camera_id == camera.id, TrackedObject.object_id == 1)
    ).scalar_one()
    return camera, obj


def test_get_object_profile_aggregates_dwell_time_and_event_count_correctly(client, db_session):
    camera, obj = _seed_object_with_lifecycle(db_session)

    response = client.get(f"/objects/{obj.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["class_name"] == "person"
    assert body["first_seen"] == 0.0
    assert body["last_seen"] == 60.0
    assert body["camera_id"] == "cam_profile"
    assert body["camera_name"] == "Profile Camera"
    # Real aggregation math, not just "some number": two completed zone
    # visits (15.0s + 12.0s), five stored events total.
    assert body["total_dwell_seconds"] == 27.0
    assert body["event_count"] == 5


def test_get_object_profile_counts_a_still_open_zone_visit_through_last_seen(client, db_session):
    camera = repository.get_or_create_camera(db_session, "cam_open_visit")
    repository.get_or_create_zone(db_session, camera, "z1", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)])
    repository.get_or_create_object(db_session, camera, object_id=1, class_name="person", timestamp=0.0)
    repository.get_or_create_object(db_session, camera, object_id=1, class_name="person", timestamp=30.0)
    repository.add_event_from_pipeline(
        db_session, camera,
        PipelineEvent(
            event_type="ZONE_ENTERED", object_id=1, class_name="person",
            timestamp=20.0, camera_id="cam_open_visit", confidence=0.9, metadata={"zone_id": "z1"},
        ),
    )
    db_session.flush()

    obj = db_session.execute(
        select(TrackedObject).where(TrackedObject.camera_id == camera.id, TrackedObject.object_id == 1)
    ).scalar_one()

    response = client.get(f"/objects/{obj.id}")
    # No ZONE_EXITED was ever recorded -- the visit counts through last_seen
    # (30.0 - 20.0 = 10.0), matching DwellTracker's live "duration so far".
    assert response.json()["total_dwell_seconds"] == 10.0


def test_get_object_profile_unknown_id_returns_404(client):
    response = client.get("/objects/999999")
    assert response.status_code == 404


def test_get_object_events_success(client, db_session):
    camera, obj = _seed_object_with_lifecycle(db_session)

    response = client.get(f"/objects/{obj.id}/events")
    assert response.status_code == 200
    body = response.json()
    assert [e["event_type"] for e in body] == ["OBJECT_APPEARED", "ZONE_ENTERED", "ZONE_EXITED", "ZONE_ENTERED", "ZONE_EXITED"]
    assert all(e["object_id"] == obj.id for e in body)


def test_get_object_events_unknown_id_returns_404(client):
    response = client.get("/objects/999999/events")
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


# --- POST /agent/query ---


def test_query_agent_success(client):
    class FakeAgent:
        def answer(self, session, question, **kwargs):
            return AgentAnswer(
                text="2 objects were tracked on camera 'demo'.",
                tool_calls=[ToolCallRecord(name="get_camera_events", arguments={"camera_id": "demo"}, result={"count": 2})],
            )

    app.dependency_overrides[get_agent] = lambda: FakeAgent()
    try:
        response = client.post("/agent/query", json={"question": "How many objects were tracked on camera demo?"})
    finally:
        del app.dependency_overrides[get_agent]

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "2 objects were tracked on camera 'demo'."
    assert body["tool_calls"] == [{"name": "get_camera_events", "arguments": {"camera_id": "demo"}, "result": {"count": 2}}]


def test_query_agent_missing_question_fails_validation(client):
    # Overriding get_agent here too: FastAPI can resolve a route's
    # dependencies (get_agent, which fails with 503 when no LLM is
    # configured) before/independent of body validation, so this test would
    # otherwise incorrectly depend on ambient ANTHROPIC_API_KEY state to
    # observe the 422 it's actually testing for.
    class FakeAgent:
        def answer(self, session, question, **kwargs):
            raise AssertionError("should never be called -- request body is invalid")

    app.dependency_overrides[get_agent] = lambda: FakeAgent()
    try:
        response = client.post("/agent/query", json={})
    finally:
        del app.dependency_overrides[get_agent]

    assert response.status_code == 422


def test_query_agent_without_configured_llm_returns_503(client, monkeypatch):
    # No dependency override here -- get_agent() runs for real, which calls
    # build_default_llm_client(); this asserts the "no LLM configured" case
    # is a clear 503, not a generic 500 or a silent fake answer.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    response = client.post("/agent/query", json={"question": "anything"})

    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


# --- POST /alerts, GET /cameras/{id}/alerts ---


def test_create_alert_success(client, db_session):
    repository.get_or_create_camera(db_session, "cam_alert")
    db_session.commit()

    response = client.post(
        "/alerts", json={"camera_id": "cam_alert", "event_type": "OVERSPEED", "message": "too fast", "channel": "dashboard"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["camera_id"] == "cam_alert"
    assert body["event_type"] == "OVERSPEED"
    assert body["message"] == "too fast"


def test_create_alert_unknown_camera_returns_404(client):
    response = client.post("/alerts", json={"camera_id": "no-such-camera", "event_type": "OVERSPEED", "message": "x"})
    assert response.status_code == 404


def test_list_camera_alerts_success(client, db_session):
    camera = repository.get_or_create_camera(db_session, "cam_alert_list")
    repository.create_alert(db_session, camera, event_type="OVERSPEED", message="hello", channel="dashboard")
    db_session.commit()

    response = client.get("/cameras/cam_alert_list/alerts")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["message"] == "hello"


def test_list_camera_alerts_unknown_camera_returns_404(client):
    response = client.get("/cameras/no-such-camera/alerts")
    assert response.status_code == 404


# --- POST /agent/actions/{id}/approve, GET /agent/actions/{id} ---


def test_approve_agent_action_executes_it(client, db_session):
    camera = repository.get_or_create_camera(db_session, "cam_action")
    db_session.commit()

    proposal = actions.propose_create_alert(db_session, "cam_action", "OVERSPEED", "pending message")
    db_session.commit()

    response = client.post(f"/agent/actions/{proposal['action_id']}/approve")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "executed"
    assert body["result"]["alert_id"] is not None
    assert len(repository.list_alerts_for_camera(db_session, camera)) == 1


def test_approve_agent_action_unknown_id_returns_404(client):
    response = client.post("/agent/actions/999999/approve")
    assert response.status_code == 404


def test_approve_agent_action_already_executed_returns_409(client, db_session):
    repository.get_or_create_camera(db_session, "cam_action_twice")
    db_session.commit()

    proposal = actions.propose_create_alert(db_session, "cam_action_twice", "OVERSPEED", "once")
    db_session.commit()

    first = client.post(f"/agent/actions/{proposal['action_id']}/approve")
    second = client.post(f"/agent/actions/{proposal['action_id']}/approve")

    assert first.status_code == 200
    assert second.status_code == 409


def test_get_agent_action_success(client, db_session):
    repository.get_or_create_camera(db_session, "cam_action_get")
    db_session.commit()

    proposal = actions.propose_create_alert(db_session, "cam_action_get", "OVERSPEED", "look at me")
    db_session.commit()

    response = client.get(f"/agent/actions/{proposal['action_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["action_type"] == "create_alert"


def test_get_agent_action_unknown_id_returns_404(client):
    response = client.get("/agent/actions/999999")
    assert response.status_code == 404


# --- GET /evaluation ---


def test_get_evaluation_matches_the_checked_in_evaluation_files_exactly(client):
    """The endpoint must be a real passthrough of Phase 14's evaluation-harness
    output, not a hand-maintained copy that could silently drift from it."""
    import json

    from api.routers.evaluation import DETECTION_RESULTS_PATH, TRACKING_RESULTS_PATH

    response = client.get("/evaluation")
    assert response.status_code == 200
    body = response.json()

    with DETECTION_RESULTS_PATH.open(encoding="utf-8") as f:
        assert body["detection"] == json.load(f)
    with TRACKING_RESULTS_PATH.open(encoding="utf-8") as f:
        assert body["tracking"] == json.load(f)


def test_get_evaluation_includes_the_real_stage1_collapse_not_filtered_out(client):
    """Stage 1's real result is a collapse on 5/6 COCO classes and a flat
    0.0 MOTA/IDF1 on real footage -- this endpoint must return those exact
    zero/near-zero values, not silently omit or clamp them."""
    response = client.get("/evaluation")
    body = response.json()

    car_stage1 = body["detection"]["coco_holdout"]["per_class"]["car"]["stage1"]
    assert car_stage1["mAP50"] == 0.0
    assert car_stage1["Box-P"] == 0.0

    tracking_stage1 = body["tracking"]["real_footage"]["results"]["stage1"]
    assert tracking_stage1["mota"] == 0.0
    assert tracking_stage1["idf1"] == 0.0
    assert tracking_stage1["num_misses"] == 244.0

    tracking_pretrained = body["tracking"]["real_footage"]["results"]["pretrained"]
    assert tracking_pretrained["mota"] == 1.0


def test_get_evaluation_returns_503_with_reason_when_results_file_missing(client, monkeypatch, tmp_path):
    from api.routers import evaluation

    monkeypatch.setattr(evaluation, "DETECTION_RESULTS_PATH", tmp_path / "does_not_exist.json")

    response = client.get("/evaluation")
    assert response.status_code == 503
    assert "evaluation" in response.json()["detail"].lower()


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
