
"""
Code Extraction from GLM-5.2 Responses

Parses raw Tabbit Chat responses to extract clean Python source code.
Handles multiple response formats:
  1. Standard markdown code blocks: ```python ... ```
  2. Tabbit's proprietary format: PYTHON\nCopy\n ...
  3. Plain text code (last-resort heuristic)

Also strips Tabbit UI chrome that may contaminate extracted code.
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# UI chrome markers that indicate non-code content in Tabbit responses
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

# Python syntax prefixes used to detect code vs. natural language
CODE_LINE_PREFIXES = (
    ' ', '\t', '#',
    'def ', 'class ', 'import ', 'from ', '@',
    'if ', 'for ', 'while ', 'try:',
    'with ', 'return ', 'else:', 'elif ',
    'except', 'finally', 'pass', 'break',
    'continue', 'raise ', 'yield ', 'assert ',
    'async ', 'await ',
)


def extract_code_block(response: str) -> str | None:
    """Extract the primary Python code block from a GLM-5.2 response.

    Strategy (tried in order):
        1. Markdown fenced code blocks (```python ... ```)
        2. Tabbit's "PYTHON\\nCopy\\n" proprietary format
        3. Heuristic: first indented block that looks like code

    Args:
        response: Raw response text from the model.

    Returns:
        Clean Python source code string, or None if no code detected.
    """
    if not response or not response.strip():
        return None

    # ── Strategy 1: Markdown code blocks ────────────────────────────
    # Matches ```python ... ``` or ```py ... ``` or ``` ... ```
    blocks = re.findall(
        r'```(?:python|py)?\s*\n(.*?)```',
        response,
        re.DOTALL | re.IGNORECASE,
    )

    if blocks:
        # Use the longest block (most likely the actual code)
        code = max(blocks, key=lambda b: len(b.strip()))
        return _strip_ui_trailers(code)

    # ── Strategy 2: Tabbit proprietary format ───────────────────────
    # Tabbit displays code as:
    #   PYTHON
    #   Copy
    #   <actual code>
    for marker in ("PYTHON\nCopy\n", "python\nCopy\n"):
        if marker in response:
            after = response.split(marker, 1)[-1]
            code = _extract_from_tabbit_format(after)
            if code:
                return code

    # ── Strategy 3: Heuristic — find first indented code block ──────
    return _heuristic_extract(response)


def _strip_ui_trailers(code: str) -> str:
    """Remove Tabbit UI chrome that may trail after valid Python code."""
    lines = code.split('\n')
    # Walk backwards, removing UI marker lines
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if any(stripped.startswith(m) for m in UI_MARKERS):
            lines = lines[:i]
        elif any(stripped == m for m in UI_MARKERS):
            lines = lines[:i]
        else:
            break
    return '\n'.join(lines).strip()


def _extract_from_tabbit_format(text: str) -> str | None:
    """Extract code from Tabbit's 'PYTHON\\nCopy\\n' format.

    Stops at UI markers or at lines that look like new natural-language
    instructions (capitalized sentence, >20 chars, no code syntax).
    """
    lines: list[str] = []
    in_code = False

    for line in text.split('\n'):
        stripped = line.strip()

        # Stop at explicit UI markers
        if any(stripped.startswith(m) for m in UI_MARKERS):
            break

        # If we've seen code and this line doesn't look like code,
        # check if it's a new instruction sentence
        if in_code and not _looks_like_code(stripped):
            if _looks_like_instruction(stripped):
                break
            # Also break on plain English text after code block
            if stripped and not any(c in stripped for c in '=:({['):
                break

        if stripped:
            lines.append(line)
            in_code = True
        elif in_code:
            # Preserve blank lines inside code blocks
            lines.append(line)

    return '\n'.join(lines).strip() if lines else None


def _looks_like_code(line: str) -> bool:
    """Check if a line looks like Python code (not natural language)."""
    if not line:
        return True  # blank lines are code-delimiting
    return any(
        line.startswith(prefix) for prefix in CODE_LINE_PREFIXES
    )


def _looks_like_instruction(line: str) -> bool:
    """Check if a line looks like a new task instruction (not code)."""
    if not line:
        return False
    # Capital letter start, reasonable length, no code syntax characters
    return (
        line[0].isupper()
        and len(line) > 20
        and '(' not in line
        and '=' not in line
        and ':' not in line.split()[0] if line.split() else True
    )


def _heuristic_extract(text: str) -> str | None:
    """Last-resort: find the first block of indented or code-like lines."""
    lines = text.split('\n')
    code_lines: list[str] = []
    started = False

    for line in lines:
        stripped = line.strip()

        # Start collecting when we see a code-like line
        if not started:
            if _looks_like_code(stripped) and stripped:
                started = True
                code_lines.append(line)
            continue

        # Stop at UI markers or instruction-like text
        if any(stripped.startswith(m) for m in UI_MARKERS):
            break
        if _looks_like_instruction(stripped):
            break

        code_lines.append(line)

    result = '\n'.join(code_lines).strip()
    return result if len(result) > 20 else None
