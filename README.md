## Suitability by Agent Workflow

The following analysis evaluates Tabbit→GLM-5.2 as a **real provider** for
autonomous agents (Hermes Agent, Claude Code, Codex CLI) — not just as a
standalone Chat interface. Each workflow is assessed against three constraints:

1. **Latency budget** — 15–25s per LLM turn. A 10-turn agent session = 3–5 minutes of pure inference time.
2. **Serial dispatch** — One prompt at a time. No parallel tool execution, no speculative branching.
3. **Reliability profile** — CDP-dependent (browser must be running). Glic bridge recovery adds ~10s MTTR.

### ✅ Optimal — Where This Provider Excels

These workflows are **reasoning-bound, not tool-call-bound**. The model's
744B-MoE architecture delivers high-quality analysis, and the per-turn latency
is amortized over deep thinking that would take similar time on any provider.

#### Research & Discovery

| Workflow | Why it fits | Expected turns | Est. wall time |
|----------|-------------|----------------|----------------|
| **Codebase exploration** | Read-heavy (search_files, read_file, grep). 1 LLM call per 3–5 tool calls while reading. | 4–8 turns | 2–4 min |
| **Dependency analysis** | Traces import graphs, checks versions, reads changelogs. Tool-heavy reads, light writes. | 3–6 turns | 1.5–3 min |
| **Security audit** | Reads files, identifies patterns, composes report. Single output artifact. | 5–10 turns | 2.5–5 min |
| **API documentation synthesis** | Reads source → reasons about behavior → writes docs. High reasoning, low iteration. | 2–4 turns | 1–2 min |

**Concrete example — codebase exploration:**
```
Turn 1 (20s): "Explore this repo structure" → reads 10 files, builds mental map
Turn 2 (20s): "Trace the auth flow" → reads 5 more files, follows call chain
Turn 3 (20s): "Summarize architecture" → produces structured output
Total: 60s inference, ~3 min wall time. High-quality analysis, $0 cost.
```

#### Deep Reasoning

| Workflow | Why it fits | Expected turns | Est. wall time |
|----------|-------------|----------------|----------------|
| **Architecture decision records** | Compares trade-offs, produces structured doc. Single output, deep thinking between turns. | 1–3 turns | 30s–1.5 min |
| **Root-cause analysis** | Given a stack trace + logs, reasons through causality. Minimal tool calls outside reading. | 2–5 turns | 1–2.5 min |
| **Refactoring strategy** | Analyzes coupling, proposes migration path. Reasoning-heavy, code-generation-light. | 3–6 turns | 1.5–3 min |
| **Test strategy planning** | Reads coverage gaps → reasons about test cases → writes plan. Not writing tests, just planning them. | 2–4 turns | 1–2 min |

#### High-Value Single-Shot Tasks

| Workflow | Why it fits | Expected turns | Est. wall time |
|----------|-------------|----------------|----------------|
| **PR review (single PR)** | Reads diff, produces inline comments. 1–2 LLM calls. | 1–2 turns | 20–40s |
| **Commit message generation** | Reads diff, writes conventional commit. 1 call. | 1 turn | 20s |
| **Error message explanation** | Given error + code context, explains root cause. 1 call. | 1 turn | 20s |
| **SQL query optimization** | Reads schema + slow query → suggests rewrite. 1–2 calls. | 1–2 turns | 20–40s |

### ⚠️ Feasible — Works but Suboptimal

These workflows **can work** but the serial-latency constraint makes them
noticeably slower than a native API provider. Use when cost savings ($0 vs
~$1+/session) outweigh the time penalty.

| Workflow | Why it's slower | Expected turns | Est. wall time | vs API provider |
|----------|----------------|----------------|----------------|----------------|
| **Single-file feature** | Write → test → fix → retest. Each fix cycle adds 20s. | 5–12 turns | 2.5–6 min | 2–3× slower |
| **Bug fix with test** | Red-green-refactor loop. Each iteration adds latency. | 8–20 turns | 4–10 min | 3–4× slower |
| **Documentation generation** | Read files → write docs → verify formatting. Moderate tool density. | 4–8 turns | 2–4 min | 1.5–2× slower |
| **Config/dependency updates** | Read manifests → update → verify build. Each verification adds 20s. | 3–8 turns | 1.5–4 min | 2× slower |

**Concrete example — single-file feature (TDD):**
```
Turn 1 (20s): Write failing test
Turn 2 (20s): Implement minimal code
Turn 3 (20s): Run test → FAIL (edge case)
Turn 4 (20s): Fix edge case
Turn 5 (20s): Run test → FAIL (another edge case)
Turn 6 (20s): Fix
Turn 7 (20s): Run test → PASS
Turn 8 (20s): Refactor
Total: 160s inference + tool execution overhead. ~4–5 min wall time.
Same task via API (streaming, ~3s/turn): ~40s inference. 4× faster.
```

### ❌ Unsuitable — Will Cause Active Frustration

These workflows are **tool-call-bound** — the model spends more time waiting for
tool results than reasoning. The 15–25s per-turn latency compounds, turning
2-minute tasks into 15-minute ordeals. The Glic bridge may also disconnect
mid-session, forcing a restart.

| Workflow | Failure mode | Typical disaster scenario |
|----------|-------------|--------------------------|
| **Multi-file refactoring** | Each file = 1+ turns to write + verify. 10 files = 50+ turns = 15+ minutes. Bridge disconnect mid-way loses context. | "Why is this still running after 20 minutes?" |
| **TDD (red-green-refactor)** | 3 iterations per function × 5 functions = 15 test-fix cycles = 5+ minutes of pure latency. Developer loses flow state. | Faster to write the code yourself. |
| **CI/CD pipeline debugging** | Read logs → hypothesize → change config → push → read logs → repeat. Each cycle 1–2 turns. 5 cycles = 5–10 min. | Pipeline takes 2 min to run, debugging takes 10 min. |
| **Real-time pair programming** | Human types → agent responds. 20s latency between every exchange breaks conversational flow entirely. | "Hello?" ... (20 seconds) ... "Oh, right, here's the code." |
| **Large-scale code generation** | Generate boilerplate for 20 files. Even 1 turn each = 7 minutes. An API provider does it in 30 seconds. | "I asked for CRUD scaffolding 10 minutes ago..." |
| **Emergency hotfix** | Production is down. Each diagnostic turn costs 20s. 5 turns = 2 min before first fix attempt. Unacceptable for SLO-bound incidents. | MTTR goes from 3 min to 10 min. That's a pageable event. |

### Decision Framework

```
Is the task REASONING-BOUND or TOOL-CALL-BOUND?

Reasoning-bound (✅ use Tabbit→GLM-5.2):
  - Deep analysis, few tool calls
  - Single output artifact
  - High-quality thinking > speed
  - Examples: architecture review, root-cause analysis, PR review

Tool-call-bound (❌ use a different provider):
  - Many test-fix-verify cycles
  - Multi-file writes with validation
  - Fast iteration > per-turn quality
  - Examples: TDD, large refactors, CI debugging
```

### Recommended Provider Strategy

Pair Tabbit→GLM-5.2 with a fast/cheap API model as a **tiered routing setup**:

```yaml
# Hermes Agent config.yaml
model:
  default: GLM-5.2 via Tabbit  # Deep reasoning, architecture, code review

fallback_providers:
  - provider: openrouter
    model: google/gemini-2.0-flash-001   # Fast iteration, TDD loops
  - provider: openrouter
    model: deepseek/deepseek-chat        # Bulk generation, boilerplate
```

**Routing heuristic:**
- Prompt contains "review" / "analyze" / "architecture" / "why" → GLM-5.2
- Prompt contains "fix" / "add test" / "refactor all" / "generate" → fast fallback
- Single-turn queries → GLM-5.2 (20s is acceptable for one shot)
- Multi-turn agent loops → fast fallback (latency compounds)

This gives you **frontier-model reasoning for free** where it matters most,
without paying the latency penalty on every turn.