"""Auto-install Python dependencies if missing or requirements.txt changed.

Runs as SessionStart hook. Compares plugin's requirements.txt against the
copy cached in plugin data dir; pip installs on first run or when changed.

Silent on success — only prints when actually installing.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

from lib import console
from lib.paths import plugin_data_dir, plugin_root


def file_hash(p: Path) -> str:
    if not p.exists():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def deps_installed() -> bool:
    try:
        import googleapiclient  # noqa
        import google_auth_oauthlib  # noqa
        return True
    except ImportError:
        return False


def main():
    console.init()
    root = plugin_root()
    data = plugin_data_dir()
    req = root / "requirements.txt"
    cached_req = data / "requirements.txt"

    if not req.exists():
        return

    if deps_installed() and file_hash(req) == file_hash(cached_req):
        return

    console.info("[yc-plugin] installing/updating Python dependencies...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req), "--quiet"],
            check=True,
        )
        cached_req.write_bytes(req.read_bytes())
        console.ok("yc-plugin dependencies ready")
    except subprocess.CalledProcessError as e:
        console.warn(f"pip install failed (rc={e.returncode})")
        console.info(f"   ↪ run manually: pip install -r {req}")


if __name__ == "__main__":
    main()
