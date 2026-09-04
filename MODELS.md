# Models Used by the TRACE API

This file lists every ML/AI model the API can load, where it's configured, and how to switch it. See `TRACE_STUDY_GUIDE.md` (Sections 2 and 12) for the full reasoning behind these choices.

## 1. Object Detector (YOLO)

Backs every detection/tracking endpoint and the agent's vision tools. Implementation: `src/detection/yolo_detector.py` (`YoloDetector`), interface: `src/detection/detector.py`.

| | |
|---|---|
| Engine | Ultralytics YOLO (`ultralytics>=8.1`) |
| Default weights | `yolov8n.pt` (pretrained COCO baseline, auto-downloaded by Ultralytics on first use if not cached) |
| Env override | `TRACE_DETECTOR_WEIGHTS` |
| Default confidence threshold | `0.25` (env: `TRACE_DETECTOR_CONFIDENCE`) |
| Class allowlist | `person`, `car`, `motorcycle`, `bus`, `truck`, `bicycle` |

### Fine-tuned variants (in `models/`)

Produced by the offline pipeline in `training/`, **not used by default**:

- `yolov8n_trace_stage1.pt` — yolov8n narrowed to TRACE's 6 classes on a COCO128 subset. Rejected: precision cratered (~0.003–0.005), 5/6 classes hit 0 mAP on held-out data.
- `yolov8n_trace_stage2.pt` — Stage 1 further adapted on real footage. Partially recovered localization on the one scene it adapted to, but inherited Stage 1's precision collapse.
- `yolov8n.onnx` — ONNX export of the pretrained baseline.

The plain pretrained `yolov8n.pt` baseline outperformed both fine-tuned stages on every held-out set tested, so it stays the default. Point `TRACE_DETECTOR_WEIGHTS` at either stage file to try them anyway.

## 2. Vision Agent LLM

Backs `POST /agent/query` (and the approval-gated tool loop behind it). Implementation: `src/agent/llm.py`. Provider is pluggable behind a shared `LLMClient`/`LLMSession` protocol so `agent.py` never branches on which one is active.

| Provider | Default model | Required env | SDK |
|---|---|---|---|
| `anthropic` (default) | `claude-sonnet-4-5` | `ANTHROPIC_API_KEY` | `anthropic>=0.40` |
| `openrouter` | `openrouter/free` | `OPENROUTER_API_KEY` | `openai>=1.0` (OpenAI-compatible chat-completions, pointed at `https://openrouter.ai/api/v1`) |

- Select provider: `TRACE_LLM_PROVIDER` (`anthropic` or `openrouter`).
- Override the active provider's model: `TRACE_LLM_MODEL`.
- No key set → `POST /agent/query` returns a clean `503` (`LLMNotConfiguredError`), not a crash.
- `AnthropicLLMClient` is implemented against the real Messages API tool-use protocol but has no live test coverage in this environment (no `ANTHROPIC_API_KEY` configured at build time); `OpenRouterLLMClient` has been verified with live end-to-end queries. Test coverage for the agent loop itself runs against `ScriptedLLMClient`/`FakeLLMClient` (same protocol, canned responses) so the orchestration code is under test independent of any real model call.

> Note: `claude-sonnet-4-5` predates the current Claude model lineup (Claude 5 family: `claude-opus-5`, `claude-sonnet-5`, `claude-fable-5-1`, plus `claude-haiku-4-5-20251001`). Worth confirming the pinned model id is still the intended one before relying on it in production.

## Quick reference: env vars

| Var | Default | Controls |
|---|---|---|
| `TRACE_DETECTOR_WEIGHTS` | `yolov8n.pt` | Detector weights path |
| `TRACE_DETECTOR_CONFIDENCE` | `0.25` | Detector confidence threshold |
| `TRACE_LLM_PROVIDER` | `anthropic` | Agent LLM provider |
| `ANTHROPIC_API_KEY` | (unset) | Anthropic key |
| `OPENROUTER_API_KEY` | (unset) | OpenRouter key |
| `TRACE_LLM_MODEL` | provider default | Override active provider's model |
