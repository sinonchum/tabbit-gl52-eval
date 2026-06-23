# tabbit-gl52 — Free GLM-5.2 Provider via Tabbit

> **Access GLM-5.2 (744B MoE, 1M context) for FREE through Tabbit browser's AI Panel. No API key. No payment. No daily quota.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

## What is this?

A lightweight Python tool that lets your AI agent (Hermes, Claude Code, custom scripts) use **GLM-5.2 as a free provider** through the Tabbit browser. It handles:

- **Auto-detection** of your OS and CPU architecture (no wrong downloads)
- **CDP automation** — sends prompts and reads responses via Chrome DevTools Protocol
- **Multi-format parsing** — extracts clean text from Tabbit's proprietary UI format

### Why Tabbit?

Tabbit's [FAQ](https://www.tabbit.ai) states: *"The browser and all integrated models are free, with no daily quota. There's no upsell tier hidden behind a paywall."*

GLM-5.2 is one of the models available in the free tier. Normally it costs **$1.40/$4.40 per million tokens** via Z.AI's API. Through Tabbit, it's **completely free**.

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/sinonchum/tabbit-gl52-eval.git
cd tabbit-gl52-eval
pip install -e .
```

### 2. Detect your platform

```bash
tabbit-gl52 setup
```

This auto-detects your OS and CPU architecture and shows the **correct Tabbit download URL** for your machine. It also warns you about common architecture mismatch mistakes.

### 3. Install and launch Tabbit

Download Tabbit from the URL shown by `setup`, install it, then launch with CDP enabled:

**macOS:**
```bash
open -a Tabbit --args --remote-debugging-port=9222
```

**Linux:**
```bash
tabbit --remote-debugging-port=9222
```

**Windows:**
```cmd
Tabbit.exe --remote-debugging-port=9222
```

### 4. Log in and open the AI Panel

1. Log into your Tabbit account (or create a free one)
2. Click the **Tabbit AI icon** in the browser sidebar
3. Select **GLM-5.2** from the model picker

### 5. Start using GLM-5.2

```bash
# Single prompt
tabbit-gl52 send "Write a Python function to reverse a linked list"

# Interactive chat
tabbit-gl52 chat

# Check connection status
tabbit-gl52 info
```

---

## Usage Modes

### CLI — one-shot prompt

```bash
tabbit-gl52 send "Explain the difference between asyncio.gather and asyncio.wait"
```

Outputs the model's response to stdout. Use in pipes and scripts.

### CLI — interactive chat

```bash
tabbit-gl52 chat
```

```
  You> What is 2+2?
  GLM-5.2> 2+2 = 4

  You> /quit
  Goodbye!
```

Commands: `/quit` to exit, `/clear` to reset response tracking.

### Python API — programmatic access

```python
import asyncio
from tabbit_gl52_eval.cdp_client import TabbitCDPClient

async def ask_glm52(prompt: str) -> str:
    async with TabbitCDPClient() as client:
        return await client.send_and_read(prompt)

response = asyncio.run(ask_glm52("Write a haiku about coding"))
print(response)
```

### Hermes Agent — as a skill

Load the `tabbit-glm52-eval` skill in Hermes and the agent can call GLM-5.2 directly:

```
/skill tabbit-glm52-eval
```

---

## Architecture

```
┌─────────────┐     CDP WebSocket     ┌──────────────────┐
│  Tabbit      │◄────────────────────►│  cdp_client.py   │
│  Browser     │   DOM manipulation   │                  │
│  (GLM-5.2)   │   + page reading     │  send_prompt()   │
└─────────────┘                       │  read_response() │
                                      └────────┬─────────┘
                                               │ raw text
                                      ┌────────▼─────────┐
                                      │  code_extractor   │
                                      │  .py (optional)   │
                                      │                   │
                                      │  Clean text from  │
                                      │  Tabbit UI chrome │
                                      └────────┬─────────┘
                                               │ clean text
                                      ┌────────▼─────────┐
                                      │  Your Agent       │
                                      │                   │
                                      │  Consume GLM-5.2  │
                                      │  responses        │
                                      └──────────────────┘
```

### How CDP communication works

**Sending prompts:**
1. Find the Chat input: `document.querySelector('[role="textbox"]')`
2. Set content: `el.innerText = prompt`
3. Trigger React: `el.dispatchEvent(new Event('input', {bubbles: true}))`
4. Press Enter: `el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', ...}))`

**Reading responses:**
1. Use body-length diffing to detect new content
2. Strip "Thinking Process" preamble
3. Strip Tabbit UI chrome markers

No accessibility permissions needed — pure DOM manipulation over CDP.

---

## Platform Support

| OS | Architecture | Supported | Binary Format |
|----|-------------|-----------|---------------|
| macOS | Apple Silicon (M1–M4) | ✅ | `Tabbit-*-arm64.dmg` |
| macOS | Intel (x86_64) | ✅ | `Tabbit-*-x86_64.dmg` |
| Linux | x86_64 / amd64 | ✅ | `Tabbit-*-amd64.deb` |
| Windows | x86_64 | ✅ | `Tabbit-*-x64.exe` |
| Linux | ARM64 (aarch64) | ⚠️ | Check tabbit.ai |
| Windows | ARM64 (Snapdragon) | ⚠️ | Check tabbit.ai |

---

## Troubleshooting

### "App is damaged" / won't launch on macOS

You downloaded the **wrong architecture** version.

```bash
# Check what you installed:
file /Applications/Tabbit.app/Contents/MacOS/Tabbit

# If "arm64" on Intel Mac → delete and re-download x86_64:
rm -rf /Applications/Tabbit.app
tabbit-gl52 setup  # shows correct URL

# If "x86_64" on Apple Silicon → delete and re-download arm64:
rm -rf /Applications/Tabbit.app
tabbit-gl52 setup  # shows correct URL
```

### "Cannot reach CDP endpoint"

Tabbit must be launched with CDP enabled:

```bash
# macOS — make sure to use the --args flag
open -a Tabbit --args --remote-debugging-port=9222

# Verify:
curl -s http://localhost:9222/json
```

### "No Tabbit AI Panel target found"

Click the **Tabbit AI icon** in the sidebar to open the AI Panel. The webview must be open for CDP to discover it.

### "Connecting to AI Panel runtime... Retry"

The Glic bridge disconnected. Close and reopen the AI Panel (click Tabbit AI icon).

### Model not responding

Make sure GLM-5.2 is selected in the model picker. You can verify by running `tabbit-gl52 info` and checking the connection.

---

## Service-Level Characteristics

### Throughput Model

Tabbit provides **uncapped, zero-cost access** to GLM-5.2 and all other
integrated models. The official FAQ states:

> *"The browser and all integrated models are free, with no daily quota.
> There's no upsell tier hidden behind a paywall."*
>
> — [tabbit.ai](https://www.tabbit.ai)

Unlike metered API gateways (OpenRouter, Z.AI, Anthropic), Tabbit does not
enforce token-based billing, rate limiting, or concurrency throttling at the
application layer. Usage is governed exclusively by the Chat UI's inherent
serialization model and the underlying inference latency of the selected model.

### Observed Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **Round-trip latency** | 15–25 seconds | Model inference + CDP transport + DOM I/O |
| **Concurrency** | 1 (serial) | Single Chat turn; no parallel prompt dispatch |
| **Context persistence** | Session-scoped | Chat history retained server-side; no explicit context window cutoff observed |
| **Idle timeout** | ~10–30 minutes | Glic bridge may tear down; reconnect by reopening AI Panel |
| **Mean time to recover (MTTR)** | < 10 seconds | Reopen AI Panel → CDP auto-rediscovers target |

### Throughput Estimation

```
Peak throughput  =  1 request / 20 seconds  =  3 requests/minute
                                             ≈ 180 requests/hour
                                             ≈ 4,320 requests/day (theoretical max)
```

In practice, agent-driven workflows typically consume **60–120 requests per
session** before context compression or task completion, well within the
sustainable envelope.

### Cost Comparison: Tabbit Free vs. Z.AI Paid API

| | Tabbit (Free) | Z.AI API (Paid) |
|---|---|---|
| **Input pricing** | $0 | $1.40 / 1M tokens |
| **Output pricing** | $0 | $4.40 / 1M tokens |
| **Cached input** | N/A | $0.26 / 1M tokens |
| **Daily quota** | None | Tier-dependent (Lite/Pro/Max) |
| **Rate limiting** | None | Per-tier token budget |
| **Concurrent requests** | 1 (Chat UI) | Configurable |
| **Context window** | Not explicitly capped | 1M tokens (glm-5.2[1m]) |
| **SLA / uptime** | Best-effort (free browser) | 99.5% (paid API) |

**Cost avoidance example:** A coding agent that consumes 500K input + 100K
output tokens per session would cost **~$1.14/session** via Z.AI's API.
Through Tabbit, the same workload is **$0.00/session**.

### Practical Constraints

#### 1. Serial Prompt Dispatch

The Chat UI accepts one prompt per turn; responses must be fully received
before the next prompt can be dispatched. This is an architectural constraint
of the Chat interface, not a rate limit. Workloads requiring parallel
speculative decoding or multi-prompt fan-out are not suitable.

**Mitigation:** Batch independent prompts sequentially; use this provider
for targeted, high-value reasoning tasks rather than bulk generation.

#### 2. Glic Bridge Stability

Tabbit's AI Panel communicates with the model backend through a **Glic bridge**
(visible as `chrome://glic/` in CDP targets). This bridge may tear down after
extended idle periods (~10–30 minutes of inactivity). When this occurs, the
panel displays *"Connecting to the AI Panel runtime... Retry"*.

**Recovery:** Close and reopen the AI Panel (click the Tabbit AI icon in the
sidebar). The CDP client automatically discovers the new webview target on
the next `connect()` call. MTTR is typically under 10 seconds.

#### 3. No Streaming

Responses are delivered as complete text blocks, not token-level streams.
This adds ~1–3 seconds of buffering latency compared to streaming API endpoints,
but eliminates the complexity of incremental parsing.

#### 4. UI Chrome in Responses

Raw responses include Tabbit UI elements (*"New Tab"*, *"Select text or
screenshot to ask"*, model selector labels). The `code_extractor` module
handles this automatically; downstream consumers receive clean text.

### Suitability by Workload

| Workload | Suitable? | Rationale |
|---|---|---|
| **Code generation** | ✅ Optimal | High-quality output, zero cost |
| **Code review / debugging** | ✅ Optimal | Strong reasoning, no token anxiety |
| **Architecture planning** | ✅ Optimal | Long-form responses, no per-token cost |
| **Batch inference (>100 prompts)** | ⚠️ Feasible | Serial only; ~33 min per 100 prompts |
| **Real-time streaming** | ❌ Unsuitable | No token-level streaming support |
| **Multi-agent fan-out** | ❌ Unsuitable | Single Chat turn; no parallel dispatch |
| **Production API endpoint** | ❌ Unsuitable | Browser-dependent; no HTTP API surface |

### Best Practices for Agent Integration

1. **Reserve for reasoning-heavy tasks.** Use cheaper/faster models for
   boilerplate generation; route complex debugging, architecture, and
   refactoring prompts to GLM-5.2 via Tabbit.

2. **Implement retry with exponential backoff.** If the CDP connection fails
   (Glic teardown, browser restart), reconnect with a `[1s, 2s, 4s]` backoff
   before surfacing the error.

3. **Cache responses.** GLM-5.2 responses are deterministic for identical
   prompts at temperature 0. Cache results locally to avoid redundant calls.

4. **Monitor body-length drift.** The CDP client tracks `document.body.innerText`
   length to detect stale reads. Reset tracking if response extraction returns
   empty content twice consecutively.

5. **Pre-warm the connection.** On agent startup, send a lightweight probe
   (`"Respond with OK"`) to verify CDP connectivity and warm the Glic bridge
   before dispatching substantive prompts.

---

## Related Projects

- [Tabbit Browser](https://www.tabbit.ai) — Free multi-model AI browser
- [GLM-5.2](https://z.ai/blog/glm-5.2) — Z.AI's flagship coding model
- [Feiyue](https://github.com/sinonchum/Feiyue) — AI capability evaluation framework
- [GPT4Free](https://github.com/xtekky/gpt4free) — Free LLM access via provider adapters
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — Autonomous AI agent framework

---

## License

MIT — see [LICENSE](LICENSE) for details.
