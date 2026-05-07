"""Auto-install Python dependencies if missing or requirements changed.

Runs as SessionStart hook. Compares plugin's requirements.txt against the
copy cached in plugin data dir; pip installs on first run or when changed.

Silent on success — only prints when actually installing.
"""
import hashlib
import io
import os
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent


def plugin_data_dir() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_DATA")
    if env:
        p = Path(env)
    else:
        p = Path.home() / ".claude" / "plugins" / "data" / "yc-plugin"
    p.mkdir(parents=True, exist_ok=True)
    return p


def file_hash(p: Path) -> str:
    if not p.exists():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def deps_installed() -> bool:
    """Quick check: try importing the top-level packages."""
    try:
        import googleapiclient  # noqa
        import google_auth_oauthlib  # noqa
        return True
    except ImportError:
        return False


def main():
    root = plugin_root()
    data = plugin_data_dir()
    req = root / "requirements.txt"
    cached_req = data / "requirements.txt"

    if not req.exists():
        return  # nothing to install

    if deps_installed() and file_hash(req) == file_hash(cached_req):
        return  # already up to date

    print(f"[yc-plugin] installing/updating Python dependencies...", flush=True)
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req), "--quiet"],
            check=True,
        )
        cached_req.write_bytes(req.read_bytes())
        print("[yc-plugin] dependencies ready.", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"[yc-plugin] WARN: pip install failed (rc={e.returncode}).", flush=True)
        print(f"[yc-plugin] you may need to manually run: pip install -r {req}", flush=True)


if __name__ == "__main__":
    main()
