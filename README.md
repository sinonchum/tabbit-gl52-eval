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

## Rate Limits

**There are no rate limits.** Tabbit's FAQ states all models are free with no daily quota.

However, there are practical constraints:
- Each request takes **~15-25 seconds** (model inference + CDP overhead)
- **Sequential only** — one prompt at a time through the Chat UI
- The Glic bridge may disconnect after extended idle periods (just reopen the AI Panel)

For comparison, Z.AI's paid API pricing: **$1.40/1M input tokens, $4.40/1M output tokens**. Through Tabbit, you get the same model for free.

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
