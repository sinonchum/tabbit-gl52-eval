
"""
Tabbit CDP (Chrome DevTools Protocol) Client

Low-level WebSocket client for communicating with Tabbit's AI Panel webview
via the Chrome DevTools Protocol. Handles connection lifecycle, message
dispatch, response parsing, and target discovery.

Architecture:
    Tabbit browser must be launched with --remote-debugging-port=9222
    The AI Panel runs as a webview at web.tabbit.ai/panel
    Prompts are sent by manipulating the DOM [role="textbox"] element
    Responses are extracted from the page body as plain text
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────────
DEFAULT_DEBUG_PORT = 9222
DEFAULT_PANEL_URL_PATTERN = "panel"
DEFAULT_CDP_TIMEOUT = 15  # seconds
DEFAULT_RESPONSE_WAIT = 18  # seconds to wait for model response

# UI chrome markers present in Tabbit's page body that should be stripped
UI_MARKERS = [
    "New Tab",
    "Select text or screenshot",
    "GLM-5.2",
    "Exchange",
    "https://web.tabbit.ai",
    "Type \"/\" to use skills",
    "Choose the AI model",
    "Capture screenshots",
    "chrome://newtab/",
]


class TabbitCDPError(Exception):
    """Raised when CDP communication with Tabbit fails."""
    pass


class TabbitTargetNotFoundError(TabbitCDPError):
    """Raised when the AI Panel target cannot be found."""
    pass


class TabbitCDPClient:
    """WebSocket client for Tabbit's Chrome DevTools Protocol endpoint.

    Usage:
        async with TabbitCDPClient() as client:
            await client.send_prompt("Write a Python function...")
            response = await client.read_response()
    """

    def __init__(
        self,
        debug_port: int = DEFAULT_DEBUG_PORT,
        response_wait: int = DEFAULT_RESPONSE_WAIT,
        cdp_timeout: int = DEFAULT_CDP_TIMEOUT,
    ) -> None:
        self.debug_port = debug_port
        self.response_wait = response_wait
        self.cdp_timeout = cdp_timeout
        self._ws: ClientConnection | None = None
        self._target_id: str | None = None
        self._body_len_before: int = 0
        self._request_id: int = 0

    # ── Public API ──────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Discover the AI Panel target and establish a WebSocket connection.

        Raises:
            TabbitTargetNotFoundError: if the AI Panel webview is not found.
            TabbitCDPError: if the WebSocket handshake fails.
        """
        target = await self._find_panel_target()
        if target is None:
            raise TabbitTargetNotFoundError(
                f"No Tabbit AI Panel target found at "
                f"http://localhost:{self.debug_port}/json. "
                f"Make sure Tabbit is running with --remote-debugging-port={self.debug_port} "
                f"and the AI Panel is open (click the Tabbit AI icon in the sidebar)."
            )

        ws_url = target["webSocketDebuggerUrl"]
        self._target_id = target["id"]

        try:
            self._ws = await websockets.connect(ws_url, close_timeout=30)
        except Exception as e:
            raise TabbitCDPError(f"WebSocket connection failed: {e}") from e

        # Record initial body length for diff-based response extraction
        self._body_len_before = await self._get_body_length()
        logger.info(
            "Connected to Tabbit AI Panel (target=%s, body_len=%d)",
            self._target_id,
            self._body_len_before,
        )

    async def disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
            self._target_id = None

    async def send_prompt(self, prompt: str) -> None:
        """Send a prompt to the GLM-5.2 Chat input and press Enter.

        Uses DOM manipulation to set the textbox content and dispatch
        a synthetic KeyboardEvent for the Enter key.

        Args:
            prompt: The text prompt to send.

        Raises:
            TabbitCDPError: if not connected or the textbox is not found.
        """
        if self._ws is None:
            raise TabbitCDPError("Not connected. Call connect() first.")

        escaped = json.dumps(prompt)
        expr = f"""
        (() => {{
            const e = document.querySelector('[role="textbox"]');
            if (!e) return 'NOBOX';
            e.focus();
            e.click();
            e.innerText = {escaped};
            e.dispatchEvent(new Event('input', {{bubbles: true, composed: true}}));
            e.dispatchEvent(new KeyboardEvent('keydown', {{
                key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
            }}));
            return 'SENT';
        }})()
        """

        result = await self._evaluate(expr)
        if result == "NOBOX":
            raise TabbitCDPError(
                "Chat textbox not found. The AI Panel may need to finish loading. "
                "Wait a few seconds and retry, or click the textbox manually."
            )
        logger.debug("Prompt sent (%d chars): %s...", len(prompt), prompt[:80])

    async def read_response(self) -> str:
        """Wait for GLM-5.2 to respond, then return the new content.

        Uses body-length diffing to only return content added since the
        last call. Strips Thinking Process preamble and UI chrome.

        Returns:
            The model's response text (minus Thinking Process).

        Raises:
            TabbitCDPError: if not connected or read fails.
        """
        if self._ws is None:
            raise TabbitCDPError("Not connected. Call connect() first.")

        await asyncio.sleep(self.response_wait)

        full_body = await self._get_body()
        if len(full_body) <= self._body_len_before:
            logger.warning("No new content detected (body unchanged)")
            return ""

        new_content = full_body[self._body_len_before:]
        self._body_len_before = len(full_body)

        # Strip "Thinking Process" preamble
        if "Thinking Process" in new_content:
            new_content = new_content.rsplit("Thinking Process", 1)[-1]

        # Strip UI chrome markers
        for marker in UI_MARKERS:
            if marker in new_content:
                new_content = new_content.split(marker)[0]

        return new_content.strip()

    async def send_and_read(self, prompt: str) -> str:
        """Convenience: send a prompt, wait, and return the response."""
        await self.send_prompt(prompt)
        # Reset body-length baseline after the prompt was injected into the DOM,
        # so read_response only captures the model's reply (not the prompt text).
        self._body_len_before = await self._get_body_length()
        return await self.read_response()

    # ── Internal methods ────────────────────────────────────────────────

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _find_panel_target(self) -> dict[str, Any] | None:
        """Query http://localhost:<port>/json for the AI Panel webview target.

        The AI Panel URL contains 'panel'. Prefers active chat sessions
        (panel/<uuid>) over the initial panel screen (panel?mode=mi).
        Falls back to checking for a live textbox.
        """
        import urllib.request

        url = f"http://localhost:{self.debug_port}/json"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                targets = json.loads(resp.read())
        except Exception as e:
            raise TabbitCDPError(
                f"Cannot reach CDP endpoint at {url}. "
                f"Is Tabbit running with --remote-debugging-port={self.debug_port}?\n"
                f"Error: {e}"
            ) from e

        # Collect all panel targets
        panels = [
            t for t in targets
            if "panel" in t.get("url", "")
            and ("mode=mi" in t.get("url", "") or "panel/" in t.get("url", ""))
        ]

        if not panels:
            return None

        # Prefer targets with "panel/<uuid>" (active chat session) over "mode=mi" (fresh panel)
        panels.sort(key=lambda t: 0 if "panel/" in t["url"] else 1)

        return panels[0]

    async def _evaluate(self, expression: str) -> str:
        """Send Runtime.evaluate and return the result value.

        Filters out CDP events (non-response messages) automatically.
        """
        if self._ws is None:
            raise TabbitCDPError("Not connected.")

        cid = self._next_id()
        await self._ws.send(json.dumps({
            "id": cid,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "returnByValue": True,
            },
        }))

        while True:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=self.cdp_timeout)
            msg = json.loads(raw)
            if msg.get("id") == cid:
                return msg.get("result", {}).get("result", {}).get("value", "")

    async def _get_body_length(self) -> int:
        """Get the current length of document.body.innerText."""
        result = await self._evaluate(
            "document.body?.innerText?.length || 0"
        )
        return int(result) if result else 0

    async def _get_body(self) -> str:
        """Get the full document.body.innerText content."""
        return await self._evaluate(
            "document.body?.innerText || ''"
        )

    # ── Context manager support ─────────────────────────────────────────

    async def __aenter__(self) -> "TabbitCDPClient":
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()
