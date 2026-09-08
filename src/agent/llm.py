"""The boundary between the Vision Agent's orchestration loop (agent.py) and
whatever actually does the reasoning. Kept as a small protocol so the loop
itself never depends on a specific provider's message format -- only on
"give me the next turn" / "here are the tool results, give me the next turn."

Two real implementations exist, both built against this same LLMClient /
LLMSession protocol so agent.py never imports or branches on a concrete
provider class: AnthropicLLMClient (the Messages API's tool-use feature) and
OpenRouterLLMClient (OpenRouter's OpenAI-compatible chat-completions tool
calling, so a free-tier model can be used instead of a paid Anthropic key).
build_llm_client() is the one place that picks between them, via
TRACE_LLM_PROVIDER (env or explicit argument).

AnthropicLLMClient is NOT exercised by this codebase's test suite: this
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
OpenRouterLLMClient was verified with real, live end-to-end queries against
seeded data (see the docstring above build_llm_client() and Section 12).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOL_SPECS, ToolSpec

# Config constants -- never hardcoded inline inside a client class.
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"
DEFAULT_OPENROUTER_MODEL = "openrouter/free"


def _env_or_default(name: str, default: str) -> str:
    """Same intent as os.environ.get(name, default), except a present-but-
    empty value (docker-compose's `VAR: ${VAR:-}` pattern -- see
    docker-compose.yml's api/worker services -- sets the env var to "" for
    every var it lists, even when .env leaves it blank/commented out; that
    is NOT the same thing as the var being absent) is also treated as "use
    the default". Without this, TRACE_LLM_MODEL left blank in .env silently
    sends an empty model string to the provider instead of DEFAULT_*_MODEL
    -- OpenRouter's real failure mode for that is a 400 "No models
    provided", not a clean fallback."""
    return os.environ.get(name) or default


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


class LLMProviderError(RuntimeError):
    """Raised by an LLMSession when the underlying provider SDK call fails,
    wrapping whatever provider-specific exception occurred (anthropic.APIError,
    openai.OpenAIError, ...). Calling code (agent.py, API routes) only ever
    needs to handle this one type -- never a provider-specific exception --
    to react correctly regardless of which provider is active."""


class AnthropicLLMClient:
    """Real implementation, backed by the `anthropic` Python SDK's tool-use
    protocol. See this module's docstring for why it's untested by live call
    in this environment."""

    def __init__(self, api_key: str, model: str = DEFAULT_ANTHROPIC_MODEL) -> None:
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
        import anthropic

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=self._messages,
                tools=self._tools,
            )
        except anthropic.APIError as exc:
            raise LLMProviderError(f"Anthropic API call failed: {exc}") from exc

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


class OpenRouterLLMClient:
    """Second real implementation of LLMClient, backed by the `openai` SDK
    pointed at OpenRouter's OpenAI-compatible chat-completions endpoint
    (OPENROUTER_BASE_URL). Lets the Vision Agent run against any OpenRouter
    model -- including its free tier -- via the exact same LLMClient /
    LLMSession protocol AnthropicLLMClient implements, so agent.py and every
    caller above it are unaware which provider is active."""

    def __init__(
        self, api_key: str, model: str = DEFAULT_OPENROUTER_MODEL, base_url: str = OPENROUTER_BASE_URL
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    def new_session(self) -> "_OpenRouterLLMSession":
        import openai  # lazy import: only needed on the real-LLM path

        client = openai.OpenAI(api_key=self._api_key, base_url=self._base_url)
        return _OpenRouterLLMSession(client, self._model)


def _tool_specs_to_openai(specs: List[ToolSpec]) -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {"name": s.name, "description": s.description, "parameters": s.input_schema},
        }
        for s in specs
    ]


class _OpenRouterLLMSession:
    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model
        self._messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._tools = _tool_specs_to_openai(TOOL_SPECS)

    def start(self, question: str) -> ModelTurn:
        self._messages.append({"role": "user", "content": question})
        return self._step()

    def submit_tool_results(self, results: List[ToolResult]) -> ModelTurn:
        for r in results:
            self._messages.append({"role": "tool", "tool_call_id": r.call_id, "content": json.dumps(r.output)})
        return self._step()

    def _step(self) -> ModelTurn:
        import openai

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=self._messages,
                tools=self._tools,
            )
        except openai.OpenAIError as exc:
            raise LLMProviderError(f"OpenRouter API call failed: {exc}") from exc

        message = response.choices[0].message
        self._messages.append(message.model_dump(exclude_none=True))

        if message.tool_calls:
            tool_calls = [
                ToolCallRequest(id=call.id, name=call.function.name, arguments=json.loads(call.function.arguments))
                for call in message.tool_calls
            ]
            return ModelTurn(tool_calls=tool_calls)

        return ModelTurn(text=message.content or "")


class LLMNotConfiguredError(RuntimeError):
    """Raised by build_llm_client() when no real LLM API key is available for
    the selected provider -- a route/caller should turn this into a clear
    error to the user, never silently fall back to a scripted/fake answer
    over a real API (that would misrepresent canned output as a real
    model's reasoning)."""


def build_llm_client(provider: Optional[str] = None) -> LLMClient:
    """The single factory/branch point for provider selection (Open/Closed:
    adding a provider means one new class + one branch here, nothing else).
    `provider` overrides the TRACE_LLM_PROVIDER env var (default
    "anthropic") -- passing it explicitly, e.g. from a test, swaps providers
    via a plain argument, no global state or monkeypatching required.
    """
    resolved = (provider if provider is not None else os.environ.get("TRACE_LLM_PROVIDER", "anthropic")).strip().lower()

    if resolved == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMNotConfiguredError(
                "ANTHROPIC_API_KEY is not set -- the Vision Agent has no LLM to call. "
                "Set a real Anthropic API key to use POST /agent/query."
            )
        model = _env_or_default("TRACE_LLM_MODEL", DEFAULT_ANTHROPIC_MODEL)
        return AnthropicLLMClient(api_key=api_key, model=model)

    if resolved == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise LLMNotConfiguredError(
                "OPENROUTER_API_KEY is not set -- the Vision Agent has no LLM to call. "
                "Set a real OpenRouter API key (from openrouter.ai/keys) to use POST /agent/query "
                "with TRACE_LLM_PROVIDER=openrouter."
            )
        model = _env_or_default("TRACE_LLM_MODEL", DEFAULT_OPENROUTER_MODEL)
        return OpenRouterLLMClient(api_key=api_key, model=model)

    raise LLMNotConfiguredError(f"Unknown TRACE_LLM_PROVIDER {resolved!r} -- expected 'anthropic' or 'openrouter'.")
