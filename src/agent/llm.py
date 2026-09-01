"""The boundary between the Vision Agent's orchestration loop (agent.py) and
whatever actually does the reasoning. Kept as a small protocol so the loop
itself never depends on a specific provider's message format -- only on
"give me the next turn" / "here are the tool results, give me the next turn."

AnthropicLLMClient is the real implementation, using the Messages API's
tool-use feature. It is NOT exercised by this codebase's test suite: this
environment has no configured LLM API key (checked at Phase 11 build time --
only an empty placeholder GEMINI_API_KEY exists, no ANTHROPIC_API_KEY), so
there is no way to make a real, live call here. It's implemented against the
real Anthropic Messages API tool-use protocol so it's correct and usable the
moment a real key is provided; `python-agent-e2e`-style test coverage of the
tool-execution loop instead runs against ScriptedLLMClient (tests/) or the
FakeLLMClient below, which implement the exact same LLMClient protocol so
the real orchestration code in agent.py is what's actually under test --
only the "which tool, what final wording" decision is scripted instead of
model-generated. See TRACE_STUDY_GUIDE.md Section 12 for the full caveat.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOL_SPECS, ToolSpec


@dataclass(frozen=True)
class ToolCallRequest:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    output: Dict[str, Any]


@dataclass(frozen=True)
class ModelTurn:
    """Either more tool calls to execute (`tool_calls` non-empty, `text`
    None) or a final answer (`text` set, `tool_calls` empty) -- never both."""

    tool_calls: List[ToolCallRequest] = field(default_factory=list)
    text: Optional[str] = None


class LLMSession(Protocol):
    """One question's worth of conversation state. A fresh instance per
    VisionAgent.answer() call so no state leaks between questions."""

    def start(self, question: str) -> ModelTurn: ...

    def submit_tool_results(self, results: List[ToolResult]) -> ModelTurn: ...


class LLMClient(Protocol):
    def new_session(self) -> LLMSession: ...


class AnthropicLLMClient:
    """Real implementation, backed by the `anthropic` Python SDK's tool-use
    protocol. See this module's docstring for why it's untested by live call
    in this environment."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5") -> None:
        self._api_key = api_key
        self._model = model

    def new_session(self) -> "_AnthropicLLMSession":
        import anthropic  # lazy import: only needed on the real-LLM path

        client = anthropic.Anthropic(api_key=self._api_key)
        return _AnthropicLLMSession(client, self._model)


def _tool_specs_to_anthropic(specs: List[ToolSpec]) -> List[Dict[str, Any]]:
    return [{"name": s.name, "description": s.description, "input_schema": s.input_schema} for s in specs]


class _AnthropicLLMSession:
    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model
        self._messages: List[Dict[str, Any]] = []
        self._tools = _tool_specs_to_anthropic(TOOL_SPECS)

    def start(self, question: str) -> ModelTurn:
        self._messages.append({"role": "user", "content": question})
        return self._step()

    def submit_tool_results(self, results: List[ToolResult]) -> ModelTurn:
        import json

        self._messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": r.call_id, "content": json.dumps(r.output)} for r in results
                ],
            }
        )
        return self._step()

    def _step(self) -> ModelTurn:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=self._messages,
            tools=self._tools,
        )
        self._messages.append({"role": "assistant", "content": response.content})

        tool_calls = [
            ToolCallRequest(id=block.id, name=block.name, arguments=block.input)
            for block in response.content
            if block.type == "tool_use"
        ]
        if tool_calls:
            return ModelTurn(tool_calls=tool_calls)

        text = "".join(block.text for block in response.content if block.type == "text")
        return ModelTurn(text=text)


class LLMNotConfiguredError(RuntimeError):
    """Raised by build_default_llm_client() when no real LLM API key is
    available -- a route/caller should turn this into a clear error to the
    user, never silently fall back to a scripted/fake answer over a real API
    (that would misrepresent canned output as a real model's reasoning)."""


def build_default_llm_client() -> LLMClient:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMNotConfiguredError(
            "ANTHROPIC_API_KEY is not set -- the Vision Agent has no LLM to call. "
            "Set a real Anthropic API key to use POST /agent/query."
        )
    return AnthropicLLMClient(api_key=api_key)
