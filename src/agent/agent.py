"""The Vision Agent's orchestration loop (Section 12): user question -> LLM
selects tool(s) -> tools query the real database -> LLM composes an answer
grounded strictly in what the tools returned.

This loop is provider-agnostic: it only depends on the LLMClient/LLMSession
protocol (agent.llm), never on Anthropic (or any provider) directly, so the
exact same code here is exercised whether the session behind it is a real
AnthropicLLMClient or a test double.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from agent.llm import LLMClient, ToolResult
from agent.tools import execute_tool

DEFAULT_MAX_ITERATIONS = 6


@dataclass(frozen=True)
class ToolCallRecord:
    """One executed tool call, kept on the answer for transparency/debugging
    -- lets a caller (or a test) see exactly what grounded the answer."""

    name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]


@dataclass(frozen=True)
class AgentAnswer:
    text: str
    tool_calls: List[ToolCallRecord] = field(default_factory=list)


class VisionAgent:
    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    def answer(self, session: Session, question: str, *, max_iterations: int = DEFAULT_MAX_ITERATIONS) -> AgentAnswer:
        llm_session = self._llm_client.new_session()
        turn = llm_session.start(question)
        tool_calls_made: List[ToolCallRecord] = []

        for _ in range(max_iterations):
            if turn.text is not None:
                return AgentAnswer(text=turn.text, tool_calls=tool_calls_made)

            results: List[ToolResult] = []
            for call in turn.tool_calls:
                output = execute_tool(session, call.name, call.arguments)
                tool_calls_made.append(ToolCallRecord(name=call.name, arguments=call.arguments, result=output))
                results.append(ToolResult(call_id=call.id, output=output))

            turn = llm_session.submit_tool_results(results)

        return AgentAnswer(
            text="I couldn't reach a final answer within the allowed number of tool calls -- please rephrase or narrow the question.",
            tool_calls=tool_calls_made,
        )
