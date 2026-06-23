# Tabbit GLM-5.2 Feiyue Evaluator

> **Evaluate GLM-5.2's programming capability for FREE using Tabbit's international edition — with real pytest verification and Feiyue capability classification.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

## What is this?

This tool evaluates **GLM-5.2** (a 744B MoE model by Zhipu AI) by running real programming tasks through **Tabbit International Edition's free Chat**. It:

1. **Auto-detects your OS and chip architecture** — never download the wrong Tabbit binary again
2. **Sends benchmark prompts** to GLM-5.2 via Chrome DevTools Protocol (CDP)
3. **Extracts code** from model responses with multi-format parsing
4. **Runs pytest verifiers** on the extracted code — not keyword matching, real execution
5. **Classifies the model** as `weak` / `mid` / `strong` using the Feiyue capability ladder

### Why Tabbit?

Tabbit's international edition offers **GLM-5.2 for free with no daily quota**. No API key, no credit card, no rate limits. You just need the Tabbit browser installed and logged in.

### Methodology

This project implements the **Feiyue capability evaluation framework** (`feiyue_core/capability/rules.py`):

| Rule | Threshold | Action |
|------|-----------|--------|
| Independent successes | ≥ 3 | **Promote** → `strong` |
| Same mistake repeated | ≥ 2 | **Demote** → `weak` |
| Everything else | — | **Keep** → `mid` |

Each benchmark task runs through: **Prompt → Code Extraction → Syntax Check → pytest → Classification**.

---

## Quick Start

### 1. Install this tool

```bash
git clone https://github.com/sinonchum/tabbit-gl52-eval.git
cd tabbit-gl52-eval
pip install -e .
```

### 2. Detect your platform

```bash
tabbit-gl52-eval setup
```

This auto-detects your OS and CPU (Apple Silicon vs Intel, Linux x86_64, etc.) and shows the **correct download URL** for your architecture.

Output example:
```
Platform: macOS (Apple Silicon — M1/M2/M3/M4)
OS:       darwin
Arch:     arm64

✅ Download URL:
   https://www.tabbit.ai/download/Tabbit-1.1.2-arm64.dmg

⚠️  ARCHITECTURE NOTE (Apple Silicon):
   If you accidentally download the Intel (x86_64) version:
   - It will fail with 'App is damaged' on Apple Silicon
   - Fix: Delete Tabbit from /Applications
   - Re-download the arm64 version from the URL above
```

### 3. Install Tabbit

Download from the URL shown by `setup`, then:

**macOS:**
```bash
# Launch with CDP enabled
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

### 4. Log in and open AI Panel

1. Log into your Tabbit account (or create a free one)
2. Click the **Tabbit AI icon** in the browser sidebar
3. Select **GLM-5.2** from the model picker

### 5. Run the evaluation

```bash
# Quick test — verify the pipeline works
tabbit-gl52-eval quick

# Full evaluation — 6 tasks, L1–L6
tabbit-gl52-eval eval
```

### 6. Interpret results

```
══════════════════════════════════════════════════════
  Classification: PROMOTE
══════════════════════════════════════════════════════
  Passed:  6
  Failed:  0
  Blocked: 0

  Verdict: STRONG ✅ — model qualifies for promotion
  Rationale: 6 independent successes (threshold: 3), teacher call rate 0.00.
```

---

## Architecture

```
tabbit-gl52-eval/
├── tabbit_gl52_eval/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point (setup/eval/quick/info)
│   ├── platform_detect.py  # OS + architecture auto-detection
│   ├── cdp_client.py       # Chrome DevTools Protocol WebSocket client
│   ├── code_extractor.py   # Multi-format code parsing from responses
│   ├── evaluator.py        # Feiyue rules.py classification engine
│   ├── benchmarks.py       # Benchmark task definitions (L1–L6)
│   └── runner.py           # Orchestration: prompt → code → pytest → classify
├── pyproject.toml
└── README.md
```

### How it works

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
                                      │  .py              │
                                      │                   │
                                      │  Extract clean    │
                                      │  Python from      │
                                      │  response text    │
                                      └────────┬─────────┘
                                               │ code string
                                      ┌────────▼─────────┐
                                      │  runner.py        │
                                      │                   │
                                      │  Write to file    │
                                      │  Syntax check     │
                                      │  Run pytest       │
                                      └────────┬─────────┘
                                               │ pass/fail
                                      ┌────────▼─────────┐
                                      │  evaluator.py     │
                                      │                   │
                                      │  Feiyue rules.py  │
                                      │  → PROMOTE/KEEP/  │
                                      │    DEMOTE         │
                                      └──────────────────┘
```

---

## Platform Support

| OS | Architecture | Supported | Notes |
|----|-------------|-----------|-------|
| macOS | Apple Silicon (M1–M4) | ✅ | arm64 .dmg |
| macOS | Intel (x86_64) | ✅ | x86_64 .dmg |
| Linux | x86_64 / amd64 | ✅ | .deb package |
| Windows | x86_64 | ✅ | .exe installer |
| Linux | ARM64 (aarch64) | ⚠️ | Check tabbit.ai for builds |
| Windows | ARM64 (Snapdragon) | ⚠️ | Check tabbit.ai for builds |

---

## Troubleshooting

### "App is damaged" on macOS

You downloaded the wrong architecture version.

```bash
# Check which version you have:
file /Applications/Tabbit.app/Contents/MacOS/Tabbit

# If it shows "arm64" but you're on Intel:
rm -rf /Applications/Tabbit.app
# Re-download the x86_64 version (run: tabbit-gl52-eval setup)

# If it shows "x86_64" but you're on Apple Silicon:
rm -rf /Applications/Tabbit.app
# Re-download the arm64 version (run: tabbit-gl52-eval setup)
```

### "Cannot reach CDP endpoint"

Tabbit must be launched with `--remote-debugging-port=9222`:

```bash
# macOS
open -a Tabbit --args --remote-debugging-port=9222

# Verify it's listening:
curl -s http://localhost:9222/json | head -20
```

### "No Tabbit AI Panel target found"

Click the **Tabbit AI icon** in the browser sidebar to open the AI Panel. The panel must be open for CDP to discover it.

### "Chat textbox not found"

The AI Panel is still loading. Wait 5–10 seconds and retry. If persistent, the Glic bridge may have disconnected — close and reopen the AI Panel.

### "No code block found in response"

GLM-5.2 responded but the code extractor couldn't parse the format. This is rare — the extractor handles markdown code blocks, Tabbit's proprietary format, and heuristic plain-text extraction. If it happens, check the actual response via `tabbit-gl52-eval quick` to debug.

---

## Benchmark Tasks

| Task | Feiyue Level | Description | Tests |
|------|-------------|-------------|-------|
| L1.slugify | Documentation/Simple Code | Implement URL slug function | 5 |
| L2.bsearch | Single-File Change | Fix binary search off-by-one | 6 |
| L2.average | Single-File Change | Fix zero-division on empty list | 4 |
| L4.palindrome | Bounded Debug | Implement case-insensitive palindrome | 6 |
| L5.ratelimiter | Module Feature Slice | Thread-safe sliding window rate limiter | 3 |
| L6.async_fetch | Complex Refactor | Convert sync HTTP to async/await + aiohttp | 5 |

All tasks are self-contained — no network access or external packages needed.

---

## Contributing

### Adding new benchmark tasks

1. Add a `BenchmarkTask` to `tabbit_gl52_eval/benchmarks.py`
2. Include the code skeleton, test file, prompt, and verifier command
3. Add it to `DEFAULT_BENCHMARKS`
4. Run `tabbit-gl52-eval quick` to verify

### Adding support for other models

The CDP client is model-agnostic. To evaluate a different model in Tabbit:
- Switch the model in Tabbit's UI
- Pass `model_id` to `run_benchmarks()`

### Installing as a Hermes skill

```bash
# Create skill from this repo
hermes skills tap add https://github.com/YOUR_USERNAME/tabbit-gl52-eval
hermes skills install tabbit-gl52-eval
```

---

## Related Projects

- [Feiyue](https://github.com/sinonchum/Feiyue) — AI capability evaluation framework
- [Tabbit](https://www.tabbit.ai) — Free multi-model AI browser
- [GPT4Free](https://github.com/xtekky/gpt4free) — Free LLM access via provider adapters
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — Autonomous AI agent framework

---

## License

MIT — see [LICENSE](LICENSE) for details.
