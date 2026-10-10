"""
Chaos controller with file-backed state.

Both the FastAPI server and the agent process read the same JSON file,
so chaos toggled via the API is visible to the agent's tools and vice versa.
"""

import json
from pathlib import Path
from typing import Any


CHAOS_FILE = Path(__file__).parent / "chaos_state.json"

DEFAULT_CHAOS: dict[str, Any] = {
    "api_500_on": None,
    "timeout_on": None,
    "selector_override": {},
    "missing_field": None,
    "duplicate_invoice": False,
    "ambiguous_vendor": False,
    "corrupt_create_amount": False,
}


def load_chaos() -> dict[str, Any]:
    """Read the current chaos config from disk."""
    if not CHAOS_FILE.exists():
        return dict(DEFAULT_CHAOS)
    try:
        data = json.loads(CHAOS_FILE.read_text())
        # Ensure all default keys are present (in case file is partial)
        merged = dict(DEFAULT_CHAOS)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_CHAOS)


def save_chaos(config: dict[str, Any]) -> None:
    """Write the chaos config to disk."""
    CHAOS_FILE.write_text(json.dumps(config, indent=2))


def update_chaos(updates: dict[str, Any]) -> dict[str, Any]:
    """Merge updates into the current config and persist."""
    config = load_chaos()
    config.update(updates)
    save_chaos(config)
    return config


def reset_chaos() -> dict[str, Any]:
    """Reset to defaults."""
    config = dict(DEFAULT_CHAOS)
    save_chaos(config)
    return config