"""Path helpers for yc-plugin."""
import os
from pathlib import Path


def plugin_data_dir() -> Path:
    """Plugin's persistent data dir. Survives plugin updates.

    Prefers CLAUDE_PLUGIN_DATA env var (set by Claude Code at runtime),
    falls back to ~/.claude/plugins/data/yc-plugin for direct CLI usage.
    """
    env = os.environ.get("CLAUDE_PLUGIN_DATA")
    p = Path(env) if env else Path.home() / ".claude" / "plugins" / "data" / "yc-plugin"
    p.mkdir(parents=True, exist_ok=True)
    return p


def plugin_root() -> Path:
    """Plugin's install dir. Changes on every plugin update.

    Prefers CLAUDE_PLUGIN_ROOT env var. Falls back to two levels up from
    this file (assumes bin/lib/paths.py).
    """
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent.parent


def client_secret_file() -> Path:
    return plugin_data_dir() / "client_secret.json"


def token_file() -> Path:
    return plugin_data_dir() / "yt_token.json"


def log_file() -> Path:
    return plugin_data_dir() / "log.txt"
