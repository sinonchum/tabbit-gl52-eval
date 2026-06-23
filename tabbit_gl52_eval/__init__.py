"""
Tabbit GLM-5.2 Free Provider

Access GLM-5.2 for free through Tabbit browser's AI Panel.
No API key, no payment, no daily quota.

Usage:
    from tabbit_gl52_eval.cdp_client import TabbitCDPClient

    async with TabbitCDPClient() as client:
        response = await client.send_and_read("Your prompt here")
"""

from .cdp_client import TabbitCDPClient, TabbitCDPError, TabbitTargetNotFoundError
from .platform_detect import detect_platform, get_download_url, get_platform_label

__all__ = [
    "TabbitCDPClient",
    "TabbitCDPError",
    "TabbitTargetNotFoundError",
    "detect_platform",
    "get_download_url",
    "get_platform_label",
]
__version__ = "1.0.0"
