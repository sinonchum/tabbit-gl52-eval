
#!/usr/bin/env python3
"""
Tabbit GLM-5.2 Feiyue Evaluator — CLI

Usage:
    tabbit-gl52-eval setup     Detect platform and show Tabbit install instructions
    tabbit-gl52-eval eval      Run the full GLM-5.2 capability evaluation
    tabbit-gl52-eval quick     Run a single test task to verify the pipeline
    tabbit-gl52-eval info      Show platform and configuration information
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from tabbit_gl52_eval.platform_detect import (
    detect_platform,
    get_download_url,
    get_platform_label,
    _raise_unsupported,
)
from tabbit_gl52_eval.benchmarks import DEFAULT_BENCHMARKS, BenchmarkTask
from tabbit_gl52_eval.runner import run_benchmarks, RunnerError


def cmd_setup() -> None:
    """Detect platform and show Tabbit installation instructions."""
    info = detect_platform()
    label = get_platform_label(info)
    url = get_download_url(info)

    print("=" * 60)
    print("  Tabbit GLM-5.2 Feiyue Evaluator — Setup")
    print("=" * 60)
    print(f"\n  Platform: {label}")
    print(f"  OS:       {info.raw_os}")
    print(f"  Arch:     {info.raw_arch}")

    if url:
        print(f"\n  ✅ Download URL:")
        print(f"     {url}")
        print(f"\n  Steps:")
        print(f"   1. Download Tabbit from the URL above")
        if info.is_macos:
            print(f"   2. Open the .dmg file and drag Tabbit to /Applications")
            print(f"   3. Launch Tabbit with CDP enabled:")
            print(f"      open -a Tabbit --args --remote-debugging-port=9222")
        elif info.is_linux:
            print(f"   2. Install: sudo dpkg -i Tabbit-*.deb")
            print(f"   3. Launch: tabbit --remote-debugging-port=9222")
        elif info.is_windows:
            print(f"   2. Run the installer")
            print(f"   3. Launch: Tabbit.exe --remote-debugging-port=9222")
        print(f"   4. Log into your Tabbit account")
        print(f"   5. Open the AI Panel (click Tabbit AI icon in sidebar)")
        print(f"   6. Select GLM-5.2 from the model picker")
        print(f"   7. Run: tabbit-gl52-eval eval")
    else:
        print(f"\n  ❌ No official Tabbit build for this platform.")
        _raise_unsupported(info)

    # Architecture-specific warnings
    if info.is_macos and info.is_arm64:
        print(f"\n  ⚠️  ARCHITECTURE NOTE (Apple Silicon):")
        print(f"     If you accidentally download the Intel (x86_64) version:")
        print(f"     - It will fail with 'App is damaged' on Apple Silicon")
        print(f"     - Fix: Delete Tabbit from /Applications")
        print(f"     - Re-download the arm64 version from the URL above")
    elif info.is_macos and info.is_x86_64:
        print(f"\n  ⚠️  ARCHITECTURE NOTE (Intel Mac):")
        print(f"     If you accidentally download the Apple Silicon (arm64) version:")
        print(f"     - It will not launch on Intel Macs")
        print(f"     - Fix: Delete Tabbit from /Applications")
        print(f"     - Re-download the x86_64 version from the URL above")


def cmd_eval(cdp_port: int = 9222) -> None:
    """Run the full evaluation suite."""
    print("=" * 60)
    print("  Tabbit GLM-5.2 Feiyue Capability Evaluation")
    print("=" * 60)
    print(f"\n  CDP Port: {cdp_port}")
    print(f"  Tasks:    {len(DEFAULT_BENCHMARKS)}")
    print(f"  Model:    GLM-5.2 (via Tabbit free tier)")
    print(f"\n  Connecting to Tabbit...")
    print(f"  (Make sure Tabbit is running with --remote-debugging-port={cdp_port})")
    print(f"  (Make sure the AI Panel is open and GLM-5.2 is selected)")
    print()

    try:
        records, recommendation = asyncio.run(
            run_benchmarks(
                tasks=DEFAULT_BENCHMARKS,
                model_id="GLM-5.2",
                cdp_port=cdp_port,
            )
        )
    except RunnerError as e:
        print(f"\n  ❌ ERROR: {e}")
        sys.exit(1)

    # ── Print detailed results ──────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print(f"  Results")
    print(f"{'─' * 60}")
    print(f"  {'Task':<20} {'Level':<30} {'Result':<10} P/F")
    print(f"  {'─' * 60}")
    for r in records:
        pf = f"{r.pytest_passed}/{r.pytest_failed}" if r.pytest_passed + r.pytest_failed > 0 else "-"
        print(f"  {r.task_id:<20} {r.capability_level:<30} {r.result.value:<10} {pf}")

    # ── Print classification ────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print(f"  Classification: {recommendation.action.value.upper()}")
    print(f"{'═' * 60}")
    print(f"  Passed:  {recommendation.passed_count}")
    print(f"  Failed:  {recommendation.failed_count}")
    print(f"  Blocked: {recommendation.blocked_count}")

    if recommendation.mistake_counts:
        print(f"  Mistakes:")
        for cat, count in sorted(recommendation.mistake_counts.items()):
            print(f"    {cat}: {count}")

    print(f"\n  Verdict: ", end="")
    if recommendation.is_strong:
        print("STRONG ✅ — model qualifies for promotion")
    elif recommendation.is_weak:
        print("WEAK ⚠️ — model should be demoted")
    else:
        print("MID — model stays at current level")

    print(f"\n  Rationale: {recommendation.rationale}")


def cmd_quick(cdp_port: int = 9222) -> None:
    """Run a single quick test to verify the pipeline."""
    test_task = BenchmarkTask(
        task_id="quick.test",
        capability_level="documentation_boilerplate",
        category="test",
        setup_files={
            "hello.py": "def greet():\n    pass\n",
            "test_hello.py": (
                "from hello import greet\n\n"
                "def test_greet():\n"
                "    # This will only pass after the model implements greet()\n"
                "    # For now it just checks the file is importable\n"
                "    assert callable(greet)\n"
            ),
        },
        prompt=(
            "Implement the greet() function in hello.py. "
            "It should return the string 'Hello, Feiyue!'. "
            "Output ONLY the completed hello.py file."
        ),
        verifier_command=["pytest", "test_hello.py", "-v", "--tb=short"],
        target_file="hello.py",
    )

    print("Running quick pipeline test...")
    print("(This sends one prompt to GLM-5.2 and verifies the response.)\n")

    try:
        records, rec = asyncio.run(
            run_benchmarks(
                tasks=[test_task],
                model_id="GLM-5.2",
                cdp_port=cdp_port,
            )
        )
        r = records[0]
        icon = "✅" if r.result.value == "passed" else "❌"
        print(f"\n  {icon} {r.result.value.upper()}")
        print(f"  Verifier: {r.verifier_result[:300]}")
        if r.result.value == "passed":
            print(f"\n  Pipeline is working! Run 'tabbit-gl52-eval eval' for full evaluation.")
    except RunnerError as e:
        print(f"\n  ❌ Pipeline test failed: {e}")
        print(f"  Check that Tabbit is running and the AI Panel is open.")
        sys.exit(1)


def cmd_info() -> None:
    """Show platform and configuration information."""
    info = detect_platform()
    url = get_download_url(info)

    print(f"Platform:      {get_platform_label(info)}")
    print(f"OS detail:     {info.raw_os}")
    print(f"Arch detail:   {info.raw_arch}")
    print(f"Tabbit URL:    {url or 'NOT AVAILABLE'}")
    print(f"Python:        {sys.version}")
    print(f"Benchmarks:    {len(DEFAULT_BENCHMARKS)} tasks")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tabbit-gl52-eval",
        description="Evaluate GLM-5.2 capability via Tabbit using Feiyue methodology",
    )
    sub = parser.add_subparsers(dest="command", help="Command")

    sub.add_parser("setup", help="Detect platform and show install instructions")
    sub.add_parser("eval", help="Run full GLM-5.2 capability evaluation")
    sub.add_parser("quick", help="Run a single pipeline test")
    sub.add_parser("info", help="Show platform and config info")

    parser.add_argument(
        "--cdp-port",
        type=int,
        default=9222,
        help="Chrome DevTools Protocol port (default: 9222)",
    )

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup()
    elif args.command == "eval":
        cmd_eval(cdp_port=args.cdp_port)
    elif args.command == "quick":
        cmd_quick(cdp_port=args.cdp_port)
    elif args.command == "info":
        cmd_info()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
