"""
Tabbit GLM-5.2 Feiyue Evaluator — Architecture Detection Module

Detects the host operating system and CPU architecture to select the correct
Tabbit binary download. Handles macOS (arm64/x86_64), Linux, and Windows,
with fallback error messages and recovery instructions for each case.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from enum import Enum


class OS(Enum):
    MACOS = "macos"
    LINUX = "linux"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


class Arch(Enum):
    ARM64 = "arm64"
    X86_64 = "x86_64"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PlatformInfo:
    """Detected host platform information."""
    os: OS
    arch: Arch
    raw_os: str
    raw_arch: str

    @property
    def is_macos(self) -> bool:
        return self.os == OS.MACOS

    @property
    def is_linux(self) -> bool:
        return self.os == OS.LINUX

    @property
    def is_windows(self) -> bool:
        return self.os == OS.WINDOWS

    @property
    def is_arm64(self) -> bool:
        return self.arch == Arch.ARM64

    @property
    def is_x86_64(self) -> bool:
        return self.arch == Arch.X86_64


# ── Tabbit download URLs by platform ────────────────────────────────────
# These map to the latest stable Tabbit release.
# When Tabbit updates, change TABBIT_VERSION and the corresponding URLs.

TABBIT_VERSION = "1.1.2"

TABBIT_DOWNLOADS: dict[tuple[OS, Arch], str | None] = {
    (OS.MACOS, Arch.ARM64): (
        f"https://www.tabbit.ai/download/Tabbit-{TABBIT_VERSION}-arm64.dmg"
    ),
    (OS.MACOS, Arch.X86_64): (
        f"https://www.tabbit.ai/download/Tabbit-{TABBIT_VERSION}-x86_64.dmg"
    ),
    (OS.LINUX, Arch.X86_64): (
        f"https://www.tabbit.ai/download/Tabbit-{TABBIT_VERSION}-amd64.deb"
    ),
    (OS.WINDOWS, Arch.X86_64): (
        f"https://www.tabbit.ai/download/Tabbit-{TABBIT_VERSION}-x64.exe"
    ),
    # Note: Linux arm64 and Windows arm64 may not have official builds.
    # Check https://www.tabbit.ai for platform availability.
}

# Human-readable platform descriptions
PLATFORM_LABELS: dict[tuple[OS, Arch], str] = {
    (OS.MACOS, Arch.ARM64): "macOS (Apple Silicon — M1/M2/M3/M4)",
    (OS.MACOS, Arch.X86_64): "macOS (Intel — x86_64)",
    (OS.LINUX, Arch.X86_64): "Linux (x86_64/amd64)",
    (OS.WINDOWS, Arch.X86_64): "Windows (x86_64)",
}


def detect_platform() -> PlatformInfo:
    """Detect the current OS and CPU architecture.

    Returns:
        PlatformInfo with detected OS and architecture.

    Raises:
        RuntimeError: if the platform cannot be determined or is unsupported.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    # ── OS detection ────────────────────────────────────────────────
    if system == "darwin":
        detected_os = OS.MACOS
    elif system == "linux":
        detected_os = OS.LINUX
    elif system in ("windows", "win32"):
        detected_os = OS.WINDOWS
    else:
        detected_os = OS.UNKNOWN

    # ── Architecture detection ──────────────────────────────────────
    # macOS: platform.machine() returns "arm64" for Apple Silicon
    # Linux: may return "aarch64", "arm64", "x86_64", "amd64"
    # Windows: may return "AMD64", "x86_64", "ARM64"
    arm_patterns = ("arm64", "aarch64", "armv8", "armv9")
    x86_patterns = ("x86_64", "amd64", "x64", "intel")

    if any(p in machine for p in arm_patterns):
        detected_arch = Arch.ARM64
    elif any(p in machine for p in x86_patterns):
        detected_arch = Arch.X86_64
    else:
        detected_arch = Arch.UNKNOWN

    return PlatformInfo(
        os=detected_os,
        arch=detected_arch,
        raw_os=system,
        raw_arch=machine,
    )


def get_download_url(info: PlatformInfo | None = None) -> str | None:
    """Get the Tabbit download URL for the detected platform.

    Args:
        info: Platform info (auto-detected if None).

    Returns:
        Download URL string, or None if no download is available.
    """
    if info is None:
        info = detect_platform()
    return TABBIT_DOWNLOADS.get((info.os, info.arch))


def get_platform_label(info: PlatformInfo | None = None) -> str:
    """Get a human-readable platform description."""
    if info is None:
        info = detect_platform()
    return PLATFORM_LABELS.get(
        (info.os, info.arch),
        f"{info.raw_os} ({info.raw_arch}) — UNSUPPORTED",
    )


def _raise_unsupported(info: PlatformInfo) -> None:
    """Build a detailed error message for unsupported platforms."""
    lines = [
        f"Unsupported platform: {info.raw_os} / {info.raw_arch}",
        "",
        "Tabbit GLM-5.2 Evaluator requires Tabbit browser to be installed.",
    ]

    if info.os == OS.LINUX and info.arch == Arch.ARM64:
        lines.extend([
            "",
            "⚠️  Linux ARM64 (e.g., Raspberry Pi 5, AWS Graviton) may not have",
            "    an official Tabbit build. Check https://www.tabbit.ai for updates.",
            "",
            "Workaround: Use an x86_64 Linux machine or macOS/Windows."
        ])
    elif info.os == OS.MACOS and info.arch == Arch.ARM64:
        lines.extend([
            "",
            "💡 Tip: Make sure you are downloading the Apple Silicon (arm64) version.",
            "    If you accidentally installed the Intel (x86_64) version:",
            "    1. Delete Tabbit from /Applications",
            "    2. Download the arm64 version from https://www.tabbit.ai",
        ])
    elif info.os == OS.MACOS and info.arch == Arch.X86_64:
        lines.extend([
            "",
            "💡 Tip: Make sure you are downloading the Intel (x86_64) version.",
            "    If you accidentally installed the Apple Silicon (arm64) version:",
            "    1. Delete Tabbit from /Applications",
            "    2. Download the x86_64 version from https://www.tabbit.ai",
            "    (The arm64 build will fail with 'App is damaged' on Intel Macs.)",
        ])
    elif info.os == OS.WINDOWS and info.arch == Arch.ARM64:
        lines.extend([
            "",
            "⚠️  Windows ARM64 (Snapdragon X) may not have an official Tabbit build.",
            "    Check https://www.tabbit.ai for updates.",
        ])
    elif info.os == OS.UNKNOWN:
        lines.extend([
            "",
            "Your operating system was not recognized. Supported platforms:",
            "  - macOS 12+ (Apple Silicon or Intel)",
            "  - Linux (x86_64)",
            "  - Windows 10/11 (x86_64)",
        ])

    raise RuntimeError("\n".join(lines))


# ── Quick CLI test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    info = detect_platform()
    print(f"Platform: {get_platform_label(info)}")
    print(f"  OS:      {info.os.value}")
    print(f"  Arch:    {info.arch.value}")
    print(f"  Raw:     {info.raw_os} / {info.raw_arch}")

    try:
        url = get_download_url(info)
        print(f"  Download: {url}")
    except RuntimeError as e:
        print(f"  Download: NOT AVAILABLE\n{e}")
