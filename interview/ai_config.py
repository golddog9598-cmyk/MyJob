"""Environment-only AI configuration for the standalone interview service.

The interview service is intentionally isolated from MyJob's browser-side
recruitment platform runtime and never reads platform cookies or cached data.
"""

from __future__ import annotations

import os


def load_ai_config() -> dict[str, str]:
    """Return AI settings without consulting any MyJob or platform database."""
    return {
        "api_key": os.getenv("MYJOB_AI_API_KEY", "").strip(),
        "base_url": os.getenv("MYJOB_AI_BASE_URL", "https://api.deepseek.com").strip().rstrip("/"),
        "model": os.getenv("MYJOB_AI_MODEL", "deepseek-chat").strip() or "deepseek-chat",
    }
