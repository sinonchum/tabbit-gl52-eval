#!/usr/bin/env python3
"""
Standalone trajectory generation runner.

This is the EXACT script used for 100% successful 2-batch trajectory
generation (21 total, 0 failures). No pip dependencies beyond the stdlib
+ websockets. No tabbit-gl52 package needed.

Usage:
    1. Set CDP_WS to the active panel URL (from http://localhost:9222/json)
       - panel/<uuid>  ←  active chat (preferred)
       - panel?mode=mi ←  dead launch screen (don't use)

    2. Prepare remaining_contracts.json:
       [{
         "task_id": "new-feature-001",
         "description": "Add user authentication...",
         "expected_tools": ["file_read", "apply_patch"],
         "allowed_files": ["src/auth.py", "src/models.py"]
       }, ...]

    3. Run:
       python3 trajectory_batch.py

    4. Output: trajectories_glm52.jsonl (append-only, safe to resume)

Performance (GLM-5.2 + Deep Think active):
    - 5,206–25,005 chars per trajectory
    - 2–4 min per item (median ~3 min)
    - 21 items in ~40 min across 2 sessions
    - 100% success rate (0 stuck, 0 timeout)

Key insights:
    - Stability: 4 consecutive same-length polls (was 3 — Deep Think needs more)
    - Poll interval: 3s (5s was indistinguishable, 3s gives finer granularity)
    - Baseline reset: re-read body length BEFORE each send (body grows across items)
    - UI markers: "Thinking Process" + "Deep Think" appear as UI chrome, not bot text
    - CDP page ID: must use the active panel/<uuid>, not panel?mode=mi
