"""Unit coverage for src/agent/llm.py's provider-selection factory and the
OpenRouterLLMClient wire format -- no network calls, no real API key
anywhere (same constraint AnthropicLLMClient lives under, see llm.py's
module docstring). build_llm_client()'s branching is exercised here at unit
level; test_api.py's test_query_agent_*_returns_503 tests confirm the same
branching is actually reached through a real request via deps.py.

_OpenRouterLLMSession is tested against a fake object standing in for the
`openai` SDK's client -- shaped exactly like the real
openai.OpenAI().chat.completions.create(...) response (choices[0].message
with .content / .tool_calls / .model_dump()), so a wire-format bug (wrong
tool spec shape, wrong arguments parsing) would fail here before ever
reaching a live OpenRouter call.
"""

from __future__ import annotations

import json

import pytest

from agent.llm import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    AnthropicLLMClient,
    LLMNotConfiguredError,
    ModelTurn,
    OpenRouterLLMClient,
    ToolResult,
    build_llm_client,
)

# --- build_llm_client() provider selection ---


def test_build_llm_client_defaults_to_anthropic(monkeypatch):
    monkeypatch.delenv("TRACE_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    client = build_llm_client()

    assert isinstance(client, AnthropicLLMClient)
    assert client._model == DEFAULT_ANTHROPIC_MODEL


def test_build_llm_client_raises_when_anthropic_key_missing(monkeypatch):
    monkeypatch.delenv("TRACE_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(LLMNotConfiguredError, match="ANTHROPIC_API_KEY"):
        build_llm_client()


def test_build_llm_client_selects_openrouter_via_env(monkeypatch):
    monkeypatch.setenv("TRACE_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    client = build_llm_client()

    assert isinstance(client, OpenRouterLLMClient)
    assert client._model == DEFAULT_OPENROUTER_MODEL


def test_build_llm_client_selects_openrouter_via_explicit_argument(monkeypatch):
    # Explicit argument wins even if the env var says otherwise -- this is
    # what lets a caller (or a test) swap providers by passing a different
    # argument, no global state involved.
    monkeypatch.setenv("TRACE_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    client = build_llm_client(provider="openrouter")

    assert isinstance(client, OpenRouterLLMClient)


def test_build_llm_client_raises_when_openrouter_key_missing(monkeypatch):
    monkeypatch.setenv("TRACE_LLM_PROVIDER", "openrouter")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(LLMNotConfiguredError, match="OPENROUTER_API_KEY"):
        build_llm_client()


def test_build_llm_client_honors_model_override(monkeypatch):
    monkeypatch.setenv("TRACE_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("TRACE_LLM_MODEL", "some/other-model:free")

    client = build_llm_client()

    assert client._model == "some/other-model:free"


def test_build_llm_client_rejects_unknown_provider(monkeypatch):
    with pytest.raises(LLMNotConfiguredError, match="foo"):
        build_llm_client(provider="foo")


# --- OpenRouterLLMClient / _OpenRouterLLMSession wire format ---


class _FakeFunction:
    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, call_id: str, name: str, arguments: dict) -> None:
        self.id = call_id
        self.function = _FakeFunction(name, json.dumps(arguments))


class _FakeMessage:
    def __init__(self, *, content=None, tool_calls=None) -> None:
        self.content = content
        self.tool_calls = tool_calls or []

    def model_dump(self, exclude_none: bool = False) -> dict:
        data = {"role": "assistant", "content": self.content, "tool_calls": self.tool_calls}
        if exclude_none:
            data = {k: v for k, v in data.items() if v is not None}
        return data


class _FakeChoice:
    def __init__(self, message: _FakeMessage) -> None:
        self.message = message


class _FakeResponse:
    def __init__(self, message: _FakeMessage) -> None:
        self.choices = [_FakeChoice(message)]


class _FakeCompletions:
    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self.calls: list = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeOpenAIClient:
    def __init__(self, responses: list) -> None:
        self.completions = _FakeCompletions(responses)
        self.chat = _FakeChat(self.completions)


def test_openrouter_session_start_sends_system_prompt_and_tool_specs():
    fake_client = _FakeOpenAIClient([_FakeResponse(_FakeMessage(content="hello"))])
    client = OpenRouterLLMClient(api_key="sk-or-test", model="test-model")
    session = client.new_session()
    session._client = fake_client  # swap in the fake in place of a real openai.OpenAI()

    turn = session.start("What happened?")

    assert turn == ModelTurn(text="hello")
    sent = fake_client.completions.calls[0]
    assert sent["model"] == "test-model"
    assert sent["messages"][0] == {"role": "system", "content": session._messages[0]["content"]}
    assert sent["messages"][1] == {"role": "user", "content": "What happened?"}
    assert {t["function"]["name"] for t in sent["tools"]} >= {"get_camera_events", "get_line_crossings"}


def test_openrouter_session_parses_tool_calls_from_response():
    tool_call = _FakeToolCall("call_1", "get_line_crossings", {"camera_id": "demo-trafficlight", "line_id": "crosswalk_tripwire"})
    fake_client = _FakeOpenAIClient([_FakeResponse(_FakeMessage(tool_calls=[tool_call]))])
    client = OpenRouterLLMClient(api_key="sk-or-test", model="test-model")
    session = client.new_session()
    session._client = fake_client

    turn = session.start("Did any vehicle cross the tripwire?")

    assert turn.text is None
    assert len(turn.tool_calls) == 1
    assert turn.tool_calls[0].id == "call_1"
    assert turn.tool_calls[0].name == "get_line_crossings"
    assert turn.tool_calls[0].arguments == {"camera_id": "demo-trafficlight", "line_id": "crosswalk_tripwire"}


def test_openrouter_session_submits_tool_results_and_returns_final_text():
    tool_call = _FakeToolCall("call_1", "get_line_crossings", {"camera_id": "demo-trafficlight"})
    fake_client = _FakeOpenAIClient(
        [
            _FakeResponse(_FakeMessage(tool_calls=[tool_call])),
            _FakeResponse(_FakeMessage(content="Yes, object #2 crossed the line.")),
        ]
    )
    client = OpenRouterLLMClient(api_key="sk-or-test", model="test-model")
    session = client.new_session()
    session._client = fake_client

    session.start("Did any vehicle cross the tripwire?")
    turn = session.submit_tool_results([ToolResult(call_id="call_1", output={"crossings": [{"object_id": 2}]})])

    assert turn == ModelTurn(text="Yes, object #2 crossed the line.")
    second_call_messages = fake_client.completions.calls[1]["messages"]
    tool_message = next(m for m in second_call_messages if m.get("role") == "tool")
    assert tool_message["tool_call_id"] == "call_1"
    assert json.loads(tool_message["content"]) == {"crossings": [{"object_id": 2}]}
