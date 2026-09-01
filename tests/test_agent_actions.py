"""Section 13's real approval gate, tested against a real (rolled-back)
Postgres transaction -- db_session, same fixture tests/test_repository.py
and tests/test_agent.py already use.

Core property under test throughout: propose_*() never mutates
cameras/zones/lines/alerts, no matter what; execute_pending_action() is the
only thing that does, and only once per pending action.
"""

from __future__ import annotations

from agent import actions
from database import repository
from events.event import Event as PipelineEvent


def _seed_camera(db_session, camera_id="agent-actions-demo"):
    return repository.get_or_create_camera(db_session, camera_id)


# --- create_alert ---


def test_propose_create_alert_does_not_create_an_alert(db_session):
    camera = _seed_camera(db_session)

    result = actions.propose_create_alert(db_session, camera.camera_id, "OVERSPEED", "test message")

    assert result["status"] == "pending_approval"
    assert "action_id" in result
    assert repository.list_alerts_for_camera(db_session, camera) == []


def test_create_alert_is_created_only_after_approval(db_session):
    camera = _seed_camera(db_session)
    proposal = actions.propose_create_alert(db_session, camera.camera_id, "OVERSPEED", "test message")

    result = actions.execute_pending_action(db_session, proposal["action_id"])

    assert "alert_id" in result
    alerts = repository.list_alerts_for_camera(db_session, camera)
    assert len(alerts) == 1
    assert alerts[0].message == "test message"
    assert alerts[0].event_type == "OVERSPEED"


def test_propose_create_alert_rejects_unknown_event_type(db_session):
    camera = _seed_camera(db_session)
    result = actions.propose_create_alert(db_session, camera.camera_id, "NOT_A_REAL_EVENT_TYPE", "message")
    assert "error" in result


def test_propose_create_alert_rejects_unknown_camera(db_session):
    result = actions.propose_create_alert(db_session, "no-such-camera", "OVERSPEED", "message")
    assert "error" in result


# --- configure_zone ---


def test_propose_configure_zone_does_not_create_a_zone(db_session):
    camera = _seed_camera(db_session)
    polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]

    result = actions.propose_configure_zone(db_session, camera.camera_id, "restricted", polygon)

    assert result["status"] == "pending_approval"
    assert repository.get_zone(db_session, camera, "restricted") is None


def test_configure_zone_is_created_only_after_approval(db_session):
    camera = _seed_camera(db_session)
    polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]
    proposal = actions.propose_configure_zone(db_session, camera.camera_id, "restricted", polygon)

    assert repository.get_zone(db_session, camera, "restricted") is None  # still nothing before approval

    result = actions.execute_pending_action(db_session, proposal["action_id"])

    assert result["zone_id"] == "restricted"
    zone = repository.get_zone(db_session, camera, "restricted")
    assert zone is not None
    assert [tuple(p) for p in zone.polygon] == polygon


def test_propose_configure_zone_rejects_fewer_than_three_points(db_session):
    camera = _seed_camera(db_session)
    result = actions.propose_configure_zone(db_session, camera.camera_id, "bad", [(0, 0), (1, 1)])
    assert "error" in result


# --- configure_line ---


def test_configure_line_is_created_only_after_approval(db_session):
    camera = _seed_camera(db_session)
    proposal = actions.propose_configure_line(db_session, camera.camera_id, "gate", (0, 0), (10, 10))

    assert repository.get_line(db_session, camera, "gate") is None

    result = actions.execute_pending_action(db_session, proposal["action_id"])

    assert result["line_id"] == "gate"
    assert repository.get_line(db_session, camera, "gate") is not None


def test_propose_configure_line_rejects_identical_start_and_end(db_session):
    camera = _seed_camera(db_session)
    result = actions.propose_configure_line(db_session, camera.camera_id, "bad", (1, 1), (1, 1))
    assert "error" in result


# --- generate_report ---


def test_generate_report_executes_only_after_approval_and_reuses_real_analytics(db_session):
    camera = _seed_camera(db_session)
    obj = repository.get_or_create_object(db_session, camera, 1, "person", 0.0)
    repository.add_event_from_pipeline(
        db_session,
        camera,
        PipelineEvent(
            event_type="OBJECT_APPEARED", object_id=1, class_name="person", timestamp=0.0,
            camera_id=camera.camera_id, confidence=0.9,
        ),
    )
    db_session.commit()

    proposal = actions.propose_generate_report(db_session, camera.camera_id)
    result = actions.execute_pending_action(db_session, proposal["action_id"])

    assert result["object_count"] == 1
    assert result["event_frequency"] == {"OBJECT_APPEARED": 1}


# --- send_notification ---


def test_send_notification_creates_an_alert_only_after_approval(db_session):
    camera = _seed_camera(db_session)
    proposal = actions.propose_send_notification(db_session, camera.camera_id, "heads up", channel="dashboard")

    assert repository.list_alerts_for_camera(db_session, camera) == []

    result = actions.execute_pending_action(db_session, proposal["action_id"])

    assert result["delivered_via"] == "dashboard"
    alerts = repository.list_alerts_for_camera(db_session, camera)
    assert len(alerts) == 1
    assert alerts[0].message == "heads up"


# --- execute_pending_action safety properties ---


def test_execute_pending_action_unknown_id_returns_error(db_session):
    result = actions.execute_pending_action(db_session, 999999)
    assert "error" in result


def test_execute_pending_action_cannot_run_twice(db_session):
    camera = _seed_camera(db_session)
    proposal = actions.propose_create_alert(db_session, camera.camera_id, "OVERSPEED", "once only")

    first = actions.execute_pending_action(db_session, proposal["action_id"])
    second = actions.execute_pending_action(db_session, proposal["action_id"])

    assert "alert_id" in first
    assert "error" in second
    # exactly one alert was created, not two
    assert len(repository.list_alerts_for_camera(db_session, camera)) == 1


# --- real-time alert triggering from the event engine (Section 13) ---


def test_overspeed_event_produces_an_alert_record_end_to_end(db_session):
    camera = _seed_camera(db_session, "agent-actions-overspeed")
    repository.get_or_create_object(db_session, camera, 1, "car", 5.0)

    event = PipelineEvent(
        event_type="OVERSPEED", object_id=1, class_name="car", timestamp=5.0,
        camera_id=camera.camera_id, confidence=0.9,
        metadata={"estimated_speed": 30.0, "smoothed_estimated_speed": 30.0, "limit": 20.0},
    )
    repository.add_event_from_pipeline(db_session, camera, event)
    db_session.commit()

    alerts = repository.list_alerts_for_camera(db_session, camera)
    assert len(alerts) == 1
    assert alerts[0].event_type == "OVERSPEED"
    assert alerts[0].channel == "dashboard"
    assert alerts[0].event is not None
    assert alerts[0].event.event_type == "OVERSPEED"


def test_non_triggering_event_type_does_not_produce_an_alert(db_session):
    camera = _seed_camera(db_session, "agent-actions-no-alert")
    repository.get_or_create_object(db_session, camera, 1, "person", 5.0)

    event = PipelineEvent(
        event_type="OBJECT_APPEARED", object_id=1, class_name="person", timestamp=5.0,
        camera_id=camera.camera_id, confidence=0.9,
    )
    repository.add_event_from_pipeline(db_session, camera, event)
    db_session.commit()

    assert repository.list_alerts_for_camera(db_session, camera) == []
