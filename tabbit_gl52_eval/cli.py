
#!/usr/bin/env python3
"""
Tabbit GLM-5.2 Free Provider — CLI

Provides free access to GLM-5.2 via Tabbit browser's AI Panel.
No API key, no payment, no daily quota.

Usage:
    tabbit-gl52 setup         Detect platform and show Tabbit install instructions
    tabbit-gl52 send PROMPT   Send a single prompt and print the response
    tabbit-gl52 chat          Interactive chat session (send prompts, read responses)
    tabbit-gl52 info          Show platform and connection status
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
from tabbit_gl52_eval.cdp_client import (
    TabbitCDPClient,
    TabbitCDPError,
    TabbitTargetNotFoundError,
)


def cmd_setup() -> None:
    """Detect platform and show Tabbit installation instructions."""
    info = detect_platform()
    label = get_platform_label(info)
    url = get_download_url(info)

    print("=" * 60)
    print("  Tabbit GLM-5.2 Free Provider — Setup")
    print("=" * 60)
    print(f"\n  Platform: {label}")
    print(f"  OS:       {info.raw_os}")
    print(f"  Arch:     {info.raw_arch}")

    if url:
        print(f"\n  ✅ Download Tabbit:")
        print(f"     {url}")
        print(f"\n  Steps to use GLM-5.2 for free:")
        print(f"   1. Download & install Tabbit from the URL above")
        if info.is_macos:
            print(f"   2. Launch with CDP: open -a Tabbit --args --remote-debugging-port=9222")
        elif info.is_linux:
            print(f"   2. Launch with CDP: tabbit --remote-debugging-port=9222")
        elif info.is_windows:
            print(f"   2. Launch with CDP: Tabbit.exe --remote-debugging-port=9222")
        print(f"   3. Log into your Tabbit account (free to create)")
        print(f"   4. Open AI Panel (click Tabbit AI icon in sidebar)")
        print(f"   5. Select GLM-5.2 from the model picker")
        print(f"   6. Test: tabbit-gl52 send 'Hello, what model are you?'")
    else:
        print(f"\n  ❌ No official Tabbit build for this platform.")
        _raise_unsupported(info)

    # Architecture-specific recovery instructions
    if info.is_macos and info.is_arm64:
        print(f"\n  ⚠️  APPLE SILICON NOTE:")
        print(f"     If you accidentally installed the Intel (x86_64) version:")
        print(f"     → Delete: rm -rf /Applications/Tabbit.app")
        print(f"     → Re-download the arm64 version from the URL above")
    elif info.is_macos and info.is_x86_64:
        print(f"\n  ⚠️  INTEL MAC NOTE:")
        print(f"     If you accidentally installed the Apple Silicon (arm64) version:")
        print(f"     → Delete: rm -rf /Applications/Tabbit.app")
        print(f"     → Re-download the x86_64 version from the URL above")


def cmd_send(prompt: str, cdp_port: int = 9222) -> None:
    """Send a single prompt to GLM-5.2 and print the response."""
    try:
        response = asyncio.run(_send_and_read(prompt, cdp_port))
        print(response)
    except TabbitTargetNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except TabbitCDPError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


async def _send_and_read(prompt: str, cdp_port: int) -> str:
    """Send one prompt and return the response."""
    async with TabbitCDPClient(debug_port=cdp_port) as client:
        return await client.send_and_read(prompt)


def cmd_chat(cdp_port: int = 9222) -> None:
    """Interactive chat session with GLM-5.2."""
    print("=" * 60)
    print("  Tabbit GLM-5.2 — Interactive Chat")
    print("  Type /quit to exit, /clear to reset tracking")
    print("=" * 60)

    async def chat_loop():
        async with TabbitCDPClient(debug_port=cdp_port) as client:
            print(f"\n  Connected! Send your first prompt.\n")
            while True:
                try:
                    prompt = input("  You> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n  Goodbye!")
                    break

                if not prompt:
                    continue
                if prompt == "/quit":
                    print("  Goodbye!")
                    break
                if prompt == "/clear":
                    client._body_len_before = await client._get_body_length()
                    print("  [Tracking reset]")
                    continue

                print("  GLM-5.2> ", end="", flush=True)
                try:
                    response = await client.send_and_read(prompt)
                    print(response)
                    print()
                except TabbitCDPError as e:
                    print(f"\n  ❌ Error: {e}")
                    print()

    try:
        asyncio.run(chat_loop())
    except TabbitTargetNotFoundError as e:
        print(f"\n❌ {e}", file=sys.stderr)
        sys.exit(1)
    except TabbitCDPError as e:
        print(f"\n❌ {e}", file=sys.stderr)
        sys.exit(1)


def cmd_info() -> None:
    """Show platform and connection status."""
    info = detect_platform()
    url = get_download_url(info)

    print(f"Platform:      {get_platform_label(info)}")
    print(f"OS detail:     {info.raw_os}")
    print(f"Arch detail:   {info.raw_arch}")
    print(f"Tabbit URL:    {url or 'NOT AVAILABLE'}")
    print(f"Python:        {sys.version}")

    # Check if Tabbit CDP is reachable
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:9222/json", timeout=3) as resp:
            import json
            targets = json.loads(resp.read())
            panel = [t for t in targets if "panel" in t.get("url", "")]
            if panel:
                print(f"CDP:           ✅ Connected ({len(panel)} panel target(s))")
            else:
                print(f"CDP:           ⚠️  Tabbit running but AI Panel not open")
    except Exception:
        print(f"CDP:           ❌ Not reachable (launch Tabbit with --remote-debugging-port=9222)")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tabbit-gl52",
        description="Free GLM-5.2 access via Tabbit browser — no API key required",
    )
    sub = parser.add_subparsers(dest="command", help="Command")

    sub.add_parser("setup", help="Detect platform and show install instructions")
    sub.add_parser("chat", help="Interactive chat with GLM-5.2")
    sub.add_parser("info", help="Show platform and connection status")

    send_parser = sub.add_parser("send", help="Send a single prompt to GLM-5.2")
    send_parser.add_argument("prompt", nargs="+", help="Prompt text")

    parser.add_argument(
        "--cdp-port",
        type=int,
        default=9222,
        help="Chrome DevTools Protocol port (default: 9222)",
    )

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup()
    elif args.command == "send":
        cmd_send(" ".join(args.prompt), cdp_port=args.cdp_port)
    elif args.command == "chat":
        cmd_chat(cdp_port=args.cdp_port)
    elif args.command == "info":
        cmd_info()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
