"""POST /agent/query -- Section 12's Vision Agent, wired to the FastAPI app."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from agent import VisionAgent
from api.deps import get_agent, get_db
from api.schemas import AgentQueryRequest, AgentQueryResponse, AgentToolCallRead

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
