"""Standalone OAuth bootstrap for yc-plugin.

Runs the browser auth flow and saves the token to plugin data dir.
Usually you don't need this — the upload script auto-runs auth on first use.

Usage:
  python youtube_auth.py
"""
import io
import os
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def plugin_data_dir() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_DATA")
    if env:
        p = Path(env)
    else:
        p = Path.home() / ".claude" / "plugins" / "data" / "yc-plugin"
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_env(data_dir: Path) -> dict:
    env_file = data_dir / ".env"
    if not env_file.exists():
        return {}
    out = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main():
    data_dir = plugin_data_dir()
    env = load_env(data_dir)
    cs_path = env.get("YOUTUBE_CLIENT_SECRET_PATH", "").strip()
    if not cs_path:
        sys.exit(
            f"YOUTUBE_CLIENT_SECRET_PATH not set in {data_dir / '.env'}\n"
            "see .env.example in the plugin repo for setup."
        )
    client_secret = Path(cs_path).expanduser()
    if not client_secret.exists():
        sys.exit(f"client_secret not found at {client_secret}")
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
    creds = flow.run_local_server(port=0)
    token_file = data_dir / "yt_token.json"
    token_file.write_text(creds.to_json(), encoding="utf-8")
    print(f"token saved: {token_file}")


if __name__ == "__main__":
    main()
