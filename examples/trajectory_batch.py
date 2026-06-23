#!/usr/bin/env python3
"""
Batch trajectory generation via Tabbit CDP + GLM-5.2.

Generates multi-turn AI coding assistant trajectories in ChatML format
for fine-tuning data. Reads task contracts from a JSON file, sends each
as a prompt through Tabbit's CDP bridge, and extracts GLM-5.2's response.

Usage:
    python3 trajectory_batch.py

Prerequisites:
    - Tabbit running with: open -a Tabbit --args --remote-debugging-port=9222
    - AI Panel open (click Tabbit AI icon in sidebar)
    - GLM-5.2 selected in model picker

Input:  remaining_contracts.json — list of task contracts
Output: trajectories_glm52.jsonl — generated trajectories (append-only)

Performance:
    ~3 min per trajectory (Deep Think adds ~60-90s to response time)
    21 trajectories generated in ~40 min with 100% success rate
"""

import json
import os
import asyncio

import websockets

# ── Configuration ────────────────────────────────────────────────────────
CDP_WS = "ws://localhost:9222/devtools/page/PAGE_ID"
OUTPUT = os.path.expanduser("~/Desktop/feiyue-gen-pack/trajectories_glm52.jsonl")
INPUT = os.path.expanduser("~/Desktop/feiyue-gen-pack/remaining_contracts.json")

# Prompt template for multi-turn trajectories
PROMPT_TEMPLATE = """Generate a realistic multi-turn AI coding assistant trajectory in ChatML format, 4-8 turns.

TASK: {desc}
FILES: {files}
TOOLS: {tools}

Use <|im_start|>user/assistant/environment, <think> blocks, <tool_call> blocks with real code.
End with SUMMARY: [one line]. Output ONLY the trajectory."""

# UI chrome markers to strip from extracted text
CLEANUP_MARKERS = [
    "New Tab", "https://web.tabbit.ai/newtab", "GLM-5.2",
    "Expand", "Thinking Process", "Select text", "Exchange",
    "Deep Think", "Web Search", "New Chat",
]


async def send_prompt(ws, prompt):
    """Inject prompt into Tabbit's textbox via DOM manipulation."""
    js = (
        "(()=>{"
        "const e=document.querySelector('[role=textbox]');"
        "if(!e)return'NOBOX';"
        "e.focus();e.click();"
        "e.innerText=" + json.dumps(prompt) + ";"
        "e.dispatchEvent(new Event('input',{bubbles:true,composed:true}));"
        "e.dispatchEvent(new KeyboardEvent('keydown',"
        "{key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true}));"
        "return'OK'"
        "})()"
    )
    await ws.send(json.dumps({
        "id": 1, "method": "Runtime.evaluate",
        "params": {"expression": js, "returnByValue": True},
    }))
    await ws.recv()


async def wait_for_response(ws, baseline_body_len, max_wait=120, poll_interval=3):
    """
    Poll body length until stable for 4 consecutive polls (>500 new chars).

    Stability check: 4 consecutive polls with same body length ensures
    GLM-5.2 has finished streaming (Deep Think output + final response).
    3 polls was insufficient when Deep Think is active (double latency).
    """
    last_len = baseline_body_len
    stable_count = 0

    for i in range(max_wait):
        await asyncio.sleep(poll_interval)
        req_id = 100 + i
        await ws.send(json.dumps({
            "id": req_id, "method": "Runtime.evaluate",
            "params": {
                "expression": "document.body.innerText.length",
                "returnByValue": True,
            },
        }))
        raw = await ws.recv()
        result = json.loads(raw)
        cur_len = result["result"]["result"]["value"]

        if cur_len == last_len:
            stable_count += 1
        else:
            stable_count = 0
            last_len = cur_len

        if stable_count >= 4 and cur_len > baseline_body_len + 500:
            # Extract new content
            await ws.send(json.dumps({
                "id": 999, "method": "Runtime.evaluate",
                "params": {
                    "expression": f"document.body.innerText.slice({baseline_body_len})",
                    "returnByValue": True,
                },
            }))
            raw = await ws.recv()
            text = json.loads(raw)["result"]["result"]["value"]
            return clean_response(text)

        if i % 10 == 9:
            print(f"  ...{(i + 1) * poll_interval}s", flush=True)

    return None


def clean_response(text):
    """Strip Tabbit UI chrome markers from extracted text."""
    for marker in CLEANUP_MARKERS:
        text = text.replace(marker, "")
    return text.strip()


async def main():
    with open(INPUT) as f:
        all_contracts = json.load(f)

    # Resume: skip already-completed tasks
    completed_ids = set()
    if os.path.exists(OUTPUT):
        with open(OUTPUT) as f:
            for line in f:
                if line.strip():
                    completed_ids.add(json.loads(line)["task_id"])

    pending = [c for c in all_contracts if c["task_id"] not in completed_ids]
    print(f"Pending: {len(pending)}/{len(all_contracts)}", flush=True)

    # All 21 were generated in 2 batches of 10
    batch = pending[:10]
    print(f"Batch size: {len(batch)}", flush=True)

    ws = await websockets.connect(CDP_WS, max_size=10 * 1024 * 1024)

    for i, contract in enumerate(batch):
        cid = contract["task_id"]
        tools = ", ".join(contract.get("expected_tools", ["file_read", "apply_patch"]))
        files = ", ".join(contract.get("allowed_files", ["src/main.py"]))
        prompt = PROMPT_TEMPLATE.format(
            desc=contract["description"], files=files, tools=tools
        )

        print(f"[{i + 1}/{len(batch)}] {cid}", flush=True)

        # Get current body length as baseline (includes previous trajectory text)
        await ws.send(json.dumps({
            "id": 1, "method": "Runtime.evaluate",
            "params": {
                "expression": "document.body.innerText.length",
                "returnByValue": True,
            },
        }))
        baseline = json.loads(await ws.recv())["result"]["result"]["value"]

        await send_prompt(ws, prompt)
        trajectory = await wait_for_response(ws, baseline)

        if trajectory and len(trajectory) > 200:
            with open(OUTPUT, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "task_id": cid,
                    "contract": contract,
                    "trajectory": trajectory,
                    "source": "glm-5.2-tabbit",
                }, ensure_ascii=False) + "\n")
            print(f"  OK {len(trajectory)}c", flush=True)
        else:
            print(f"  FAIL (len={len(trajectory) if trajectory else 0})", flush=True)

    await ws.close()

    total = sum(1 for _ in open(OUTPUT))
    print(f"\nDone. Total trajectories: {total}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
