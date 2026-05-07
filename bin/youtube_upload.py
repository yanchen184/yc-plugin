"""yc-plugin: YouTube upload script.

Reads .env from CLAUDE_PLUGIN_DATA dir, stores OAuth token there too.
Triggers browser flow on first run; subsequent runs use refresh token.

CLI:
  python youtube_upload.py --file VIDEO --title TITLE [--description DESC]
                           [--tags TAG1,TAG2] [--privacy public|unlisted|private]
                           [--category 22] [--description-file PATH]
"""
import argparse
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def plugin_data_dir() -> Path:
    """Locate plugin data dir.

    Prefer CLAUDE_PLUGIN_DATA env var (set by Claude Code at runtime).
    Fall back to ~/.claude/plugins/data/yc-plugin for direct CLI usage.
    """
    env = os.environ.get("CLAUDE_PLUGIN_DATA")
    if env:
        p = Path(env)
    else:
        p = Path.home() / ".claude" / "plugins" / "data" / "yc-plugin"
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_env(data_dir: Path) -> dict:
    """Parse simple KEY=VALUE .env file."""
    env_file = data_dir / ".env"
    if not env_file.exists():
        return {}
    out = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def ensure_setup(data_dir: Path) -> dict:
    """Verify .env exists and YOUTUBE_CLIENT_SECRET_PATH points to a real file.

    Returns the parsed env dict. Exits with a friendly setup message otherwise.
    """
    env = load_env(data_dir)
    env_file = data_dir / ".env"
    if not env_file.exists():
        sys.exit(
            "no .env found.\n"
            f"create one at: {env_file}\n"
            "see .env.example in the plugin repo for a template + setup steps."
        )
    cs_path = env.get("YOUTUBE_CLIENT_SECRET_PATH", "").strip()
    if not cs_path:
        sys.exit(
            f"YOUTUBE_CLIENT_SECRET_PATH not set in {env_file}\n"
            "follow the setup steps in .env.example to get a client_secret.json from\n"
            "Google Cloud Console, then set the absolute path here."
        )
    cs = Path(cs_path).expanduser()
    if not cs.exists():
        sys.exit(
            f"client_secret not found at {cs}\n"
            f"check YOUTUBE_CLIENT_SECRET_PATH in {env_file}"
        )
    return env


def get_credentials(client_secret: Path, token_file: Path) -> Credentials:
    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("first-time auth: browser will open for Google login...", flush=True)
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds


def upload(args, env: dict, data_dir: Path) -> dict:
    client_secret = Path(env["YOUTUBE_CLIENT_SECRET_PATH"]).expanduser()
    token_file = data_dir / "yt_token.json"
    creds = get_credentials(client_secret, token_file)
    youtube = build("youtube", "v3", credentials=creds)

    title = args.title or Path(args.file).stem
    description = args.description or ""
    if args.description_file:
        description = Path(args.description_file).read_text(encoding="utf-8")
    tags_raw = args.tags or env.get("YOUTUBE_DEFAULT_TAGS", "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    privacy = args.privacy or env.get("YOUTUBE_DEFAULT_PRIVACY", "unlisted")
    category = args.category or env.get("YOUTUBE_DEFAULT_CATEGORY", "22")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        args.file, chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4"
    )
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"uploading: {args.file}", flush=True)
    print(f"  title: {title}", flush=True)
    print(f"  privacy: {privacy}", flush=True)
    if tags:
        print(f"  tags: {', '.join(tags)}", flush=True)

    resp = None
    last_pct = -1
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            if pct != last_pct:
                print(f"  upload: {pct}%", flush=True)
                last_pct = pct

    print("DONE", flush=True)
    print(f"video_id: {resp['id']}", flush=True)
    print(f"url: https://youtu.be/{resp['id']}", flush=True)
    return resp


def main():
    p = argparse.ArgumentParser(description="Upload a video to YouTube")
    p.add_argument("--file", required=True, help="Path to video file")
    p.add_argument("--title", help="Video title (default: filename without extension)")
    p.add_argument("--description", default="", help="Video description")
    p.add_argument("--description-file", help="Read description from text file")
    p.add_argument("--tags", default="", help="Comma-separated tags")
    p.add_argument("--privacy", choices=["public", "unlisted", "private"])
    p.add_argument("--category", help="YouTube category id")
    args = p.parse_args()

    data_dir = plugin_data_dir()
    env = ensure_setup(data_dir)
    upload(args, env, data_dir)


if __name__ == "__main__":
    main()
