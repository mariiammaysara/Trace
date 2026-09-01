"""End-to-end tests for the Vision Agent's orchestration loop (Section 12):
a real seeded Postgres database, real tool execution (src/agent/tools.py),
real VisionAgent.answer() orchestration (src/agent/agent.py) -- with only
the LLM boundary itself replaced by GroundedFakeLLMSession below.

Why a fake LLM at all: this environment has no configured LLM API key (see
src/agent/llm.py's module docstring), so a real model call cannot be made
here. GroundedFakeLLMSession is NOT a simulation of LLM reasoning -- it
deterministically parses each test's question with a regex (a real model
would do this by genuine language understanding) to decide which real tool
to call, and composes its final answer strictly FROM WHATEVER THAT TOOL
ACTUALLY RETURNED, not from a value hardcoded per test. That's what lets
these tests assert against seeded ground truth: the answer is only correct
if the real tool, querying the real database, returned the right data AND
the real orchestration loop in agent.py wired it through correctly. It
implements the exact same LLMClient/LLMSession protocol
(src/agent/llm.py) as the real AnthropicLLMClient, so agent.py's loop code
is unmodified between a real run and these tests.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from agent.agent import VisionAgent
from agent.llm import ModelTurn, ToolCallRequest, ToolResult
from database import repository
from events.event import Event as PipelineEvent


class GroundedFakeLLMSession:
    def __init__(self) -> None:
        self._intent: Optional[Tuple[str, ...]] = None

    def start(self, question: str) -> ModelTurn:
        speed_match = re.search(r"exceed\s+(\d+(?:\.\d+)?)\s*km/h", question, re.IGNORECASE)
        camera_match = re.search(r"camera '([\w.-]+)'", question)
        zone_match = re.search(r"zone '([\w.-]+)' on camera '([\w.-]+)'", question)
        event_match = re.search(r"event #(\d+)", question)

        if speed_match and camera_match:
            threshold_kmh = float(speed_match.group(1))
            self._intent = ("overspeed", str(threshold_kmh))
            return ModelTurn(
                tool_calls=[
                    ToolCallRequest(
                        id="call_1",
                        name="get_camera_events",
                        arguments={"camera_id": camera_match.group(1), "event_type": "OVERSPEED"},
                    )
                ]
            )
        if zone_match:
            self._intent = ("zone",)
            return ModelTurn(
                tool_calls=[
                    ToolCallRequest(
                        id="call_1",
                        name="get_zone_events",
                        arguments={"camera_id": zone_match.group(2), "zone_id": zone_match.group(1)},
                    )
                ]
            )
        if event_match:
            self._intent = ("event",)
            return ModelTurn(
                tool_calls=[ToolCallRequest(id="call_1", name="get_event", arguments={"event_id": int(event_match.group(1))})]
            )
        raise AssertionError(f"GroundedFakeLLMSession doesn't know how to parse: {question!r}")

    def submit_tool_results(self, results: List[ToolResult]) -> ModelTurn:
        assert self._intent is not None
        result = results[0].output
        kind = self._intent[0]

        if kind == "overspeed":
            threshold_kmh = float(self._intent[1])
            events = result.get("events", [])
            over_threshold = [e for e in events if e["metadata"].get("estimated_speed", 0.0) * 3.6 > threshold_kmh]
            if not over_threshold:
                return ModelTurn(text=f"No, I found no events where a vehicle exceeded {threshold_kmh:g} km/h.")
            fastest = max(over_threshold, key=lambda e: e["metadata"]["estimated_speed"])
            kmh = fastest["metadata"]["estimated_speed"] * 3.6
            return ModelTurn(
                text=(
                    f"Yes -- object #{fastest['object_id']} ({fastest['class_name']}) reached an estimated "
                    f"{kmh:.1f} km/h on camera '{fastest['camera_id']}', exceeding {threshold_kmh:g} km/h."
                )
            )

        if kind == "zone":
            events = result.get("events", [])
            if not events:
                return ModelTurn(text="No zone events were found for that zone.")
            summary = ", ".join(f"{e['event_type']} by object #{e['object_id']} at {e['timestamp']:.1f}s" for e in events)
            return ModelTurn(text=f"{len(events)} zone event(s) found: {summary}.")

        if kind == "event":
            if "error" in result:
                return ModelTurn(text=f"I couldn't find that event: {result['error']}.")
            return ModelTurn(
                text=(
                    f"Event #{result['id']} was a {result['event_type']} by object #{result['object_id']} "
                    f"({result['class_name']}) at {result['timestamp']:.1f}s on camera '{result['camera_id']}'."
                )
            )

        raise AssertionError(f"unexpected intent {self._intent!r}")


class GroundedFakeLLMClient:
    def new_session(self) -> GroundedFakeLLMSession:
        return GroundedFakeLLMSession()


def _seed_camera_and_object(db_session, *, camera_id, class_name, object_id=1, timestamp=10.0):
    camera = repository.get_or_create_camera(db_session, camera_id)
    obj = repository.get_or_create_object(db_session, camera, object_id, class_name, timestamp)
    return camera, obj


def _seed_overspeed_event(db_session, *, camera, obj, estimated_speed, limit=20.0, timestamp=10.0):
    pipeline_event = PipelineEvent(
        event_type="OVERSPEED",
        object_id=obj.object_id,
        class_name=obj.class_name,
        timestamp=timestamp,
        camera_id=camera.camera_id,
        confidence=0.9,
        metadata={"estimated_speed": estimated_speed, "smoothed_estimated_speed": estimated_speed, "limit": limit},
    )
    event = repository.add_event(db_session, camera, obj, pipeline_event)
    db_session.commit()
    return event


# --- "did any vehicle exceed 80 km/h today?" -- known-answer scenario ---


def test_agent_answers_yes_when_a_seeded_overspeed_event_exceeds_the_threshold(db_session):
    camera, obj = _seed_camera_and_object(db_session, camera_id="agent-speed-yes", class_name="car")
    # 25.0 m/s * 3.6 = 90.0 km/h -- a known, hand-computed value above 80 km/h.
    _seed_overspeed_event(db_session, camera=camera, obj=obj, estimated_speed=25.0)

    agent = VisionAgent(GroundedFakeLLMClient())
    result = agent.answer(db_session, "Did any vehicle on camera 'agent-speed-yes' exceed 80 km/h today?")

    assert "Yes" in result.text
    assert "90.0 km/h" in result.text
    # event.object_id (as returned by the tool) is the TrackedObject's
    # internal database id (obj.id) -- add_event() stores tracked_object.id,
    # not the Tracker's own per-camera object_id (Section 9's documented
    # distinction, same one GET /objects/{id}/trajectory relies on).
    assert f"object #{obj.id}" in result.text
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "get_camera_events"
    assert result.tool_calls[0].arguments == {"camera_id": "agent-speed-yes", "event_type": "OVERSPEED"}


def test_agent_answers_no_when_a_seeded_overspeed_event_is_under_the_threshold(db_session):
    camera, obj = _seed_camera_and_object(db_session, camera_id="agent-speed-under", class_name="car")
    # 15.0 m/s * 3.6 = 54.0 km/h -- a real OVERSPEED event (over its own configured
    # limit) that still does NOT exceed the 80 km/h asked about.
    _seed_overspeed_event(db_session, camera=camera, obj=obj, estimated_speed=15.0, limit=10.0)

    agent = VisionAgent(GroundedFakeLLMClient())
    result = agent.answer(db_session, "Did any vehicle on camera 'agent-speed-under' exceed 80 km/h today?")

    assert "No" in result.text
    assert "80 km/h" in result.text


# --- no matching events at all -- must say so, never fabricate one ---


def test_agent_reports_no_matching_events_rather_than_fabricating_one(db_session):
    repository.get_or_create_camera(db_session, "agent-speed-empty")
    db_session.commit()

    agent = VisionAgent(GroundedFakeLLMClient())
    result = agent.answer(db_session, "Did any vehicle on camera 'agent-speed-empty' exceed 80 km/h today?")

    assert "No" in result.text
    assert "exceeded" in result.text
    assert result.tool_calls[0].result["events"] == []


# --- a couple more real question/answer pairs (used verbatim in the study guide) ---


def test_agent_answers_zone_events_question_from_real_seeded_events(db_session):
    camera = repository.get_or_create_camera(db_session, "agent-zone-demo")
    zone = repository.get_or_create_zone(db_session, camera, "restricted", [(0, 0), (10, 0), (10, 10), (0, 10)])
    obj = repository.get_or_create_object(db_session, camera, 1, "person", 5.0)
    entered = PipelineEvent(
        event_type="ZONE_ENTERED", object_id=1, class_name="person", timestamp=5.0, camera_id="agent-zone-demo", confidence=0.95
    )
    repository.add_event(db_session, camera, obj, entered, zone=zone)
    db_session.commit()

    agent = VisionAgent(GroundedFakeLLMClient())
    result = agent.answer(db_session, "What zone events happened in zone 'restricted' on camera 'agent-zone-demo'?")

    assert "1 zone event(s) found" in result.text
    assert f"ZONE_ENTERED by object #{obj.id} at 5.0s" in result.text


def test_agent_answers_specific_event_lookup_question(db_session):
    camera, obj = _seed_camera_and_object(db_session, camera_id="agent-event-lookup", class_name="person", timestamp=3.0)
    pipeline_event = PipelineEvent(
        event_type="LOITERING", object_id=obj.object_id, class_name="person", timestamp=42.0, camera_id="agent-event-lookup",
        confidence=0.8,
    )
    event = repository.add_event(db_session, camera, obj, pipeline_event)
    db_session.commit()

    agent = VisionAgent(GroundedFakeLLMClient())
    result = agent.answer(db_session, f"What happened in event #{event.id}?")

    assert "LOITERING" in result.text
    assert "42.0s" in result.text
    assert "agent-event-lookup" in result.text
