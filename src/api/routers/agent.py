"""POST /agent/query -- Section 12's Vision Agent. POST /agent/actions/{id}/approve
and GET /agent/actions/{id} -- Section 13's real-time approval gate for the
agent's state-changing tools: this approve endpoint is the ONLY place in
this codebase that calls execute_pending_action(). There is no agent tool
that can approve a pending action -- see agent/actions.py's module docstring
for why that's deliberate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agent import VisionAgent, execute_pending_action
from api.deps import get_agent, get_db
from api.schemas import AgentQueryRequest, AgentQueryResponse, AgentToolCallRead, PendingActionRead
from database import repository

router = APIRouter(tags=["agent"])


@router.post("/agent/query", response_model=AgentQueryResponse)
def query_agent(
    payload: AgentQueryRequest,
    session: Session = Depends(get_db),
    agent: VisionAgent = Depends(get_agent),
) -> AgentQueryResponse:
    result = agent.answer(session, payload.question)
    return AgentQueryResponse(
        answer=result.text,
        tool_calls=[
            AgentToolCallRead(name=call.name, arguments=call.arguments, result=call.result) for call in result.tool_calls
        ],
    )


def _get_pending_action_or_404(session: Session, action_id: int):
    action = repository.get_pending_action(session, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"no pending action with id={action_id}")
    return action


@router.get("/agent/actions/{action_id}", response_model=PendingActionRead)
def get_agent_action(action_id: int, session: Session = Depends(get_db)) -> PendingActionRead:
    return PendingActionRead.model_validate(_get_pending_action_or_404(session, action_id))


@router.post("/agent/actions/{action_id}/approve", response_model=PendingActionRead)
def approve_agent_action(action_id: int, session: Session = Depends(get_db)) -> PendingActionRead:
    action = _get_pending_action_or_404(session, action_id)
    if action.status != "pending":
        raise HTTPException(status_code=409, detail=f"action {action_id} is not pending (status={action.status!r})")

    execute_pending_action(session, action_id)
    session.refresh(action)
    return PendingActionRead.model_validate(action)
