"""yc-plugin: YouTube upload script (hardened).

Reads .env from plugin data dir, stores OAuth token there.
Triggers browser flow on first run; subsequent runs use refresh token.
Resumable upload with exponential backoff. Verifies post-upload processing.

CLI:
  python youtube_upload.py --file VIDEO --title TITLE
                           [--description DESC | --description-file PATH]
                           [--tags TAG1,TAG2]
                           [--privacy public|unlisted|private]
                           [--category 22]
                           [--no-verify-processing]
"""
import argparse
import http.client
import io
import json
import os
import socket
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError, ResumableUploadError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]

RETRYABLE_EXCEPTIONS = (
    http.client.BadStatusLine,
    http.client.IncompleteRead,
    http.client.RemoteDisconnected,
    ConnectionError,
    ConnectionResetError,
    TimeoutError,
    socket.timeout,
    socket.gaierror,
    OSError,
)
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
MAX_RETRIES = 6


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


def ensure_setup(data_dir: Path) -> dict:
    """Verify .env exists and points at a valid client_secret. Bail with friendly error otherwise."""
    env_file = data_dir / ".env"
    env = load_env(data_dir)
    if not env_file.exists():
        sys.exit(
            f"yc-plugin not yet set up. .env missing at {env_file}\n"
            f"run setup first: python {Path(__file__).parent / 'setup.py'}"
        )
    cs_path = env.get("YOUTUBE_CLIENT_SECRET_PATH", "").strip()
    if not cs_path:
        sys.exit(f"YOUTUBE_CLIENT_SECRET_PATH not set in {env_file}")
    cs = Path(cs_path).expanduser()
    if not cs.exists():
        sys.exit(
            f"client_secret not found at {cs}\n"
            f"check YOUTUBE_CLIENT_SECRET_PATH in {env_file}"
        )
    return env


def get_credentials(client_secret: Path, token_file: Path) -> Credentials:
    """Get valid creds. Auto-recover from expired/revoked tokens by re-running OAuth."""
    creds = None
    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        except (ValueError, json.JSONDecodeError):
            print("[yc-plugin] token file corrupted, re-authenticating...", flush=True)
            token_file.unlink(missing_ok=True)
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            token_file.write_text(creds.to_json(), encoding="utf-8")
            return creds
        except RefreshError as e:
            print(f"[yc-plugin] token refresh failed ({e}); re-authenticating...", flush=True)
            token_file.unlink(missing_ok=True)
            creds = None

    print("[yc-plugin] first-time auth — browser will open for Google login...", flush=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
    creds = flow.run_local_server(port=0)
    token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds


def resumable_upload(req, label: str = "upload") -> dict:
    """Run resumable upload with exponential backoff on transient errors."""
    response = None
    error = None
    retry = 0
    last_pct = -1

    while response is None:
        try:
            status, response = req.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                if pct != last_pct:
                    print(f"  {label}: {pct}%", flush=True)
                    last_pct = pct
        except HttpError as e:
            if e.resp.status in RETRYABLE_STATUS_CODES:
                error = f"HTTP {e.resp.status}"
            else:
                raise
        except ResumableUploadError as e:
            raise
        except RETRYABLE_EXCEPTIONS as e:
            error = f"{type(e).__name__}: {e}"

        if error:
            retry += 1
            if retry > MAX_RETRIES:
                sys.exit(f"upload failed after {MAX_RETRIES} retries: {error}")
            sleep = min(2 ** retry, 64)
            print(f"  [WARN] {error} — retrying in {sleep}s ({retry}/{MAX_RETRIES})", flush=True)
            time.sleep(sleep)
            error = None

    return response


def verify_processing(youtube, video_id: str, timeout_s: int = 300) -> str:
    """Poll videos.list until processing finishes or timeout. Returns final status."""
    print("  verifying YouTube processing status...", flush=True)
    t0 = time.time()
    last_status = None
    while time.time() - t0 < timeout_s:
        try:
            r = youtube.videos().list(part="processingDetails,status", id=video_id).execute()
        except HttpError as e:
            print(f"  [WARN] verify polling: {e.resp.status}", flush=True)
            time.sleep(5)
            continue
        if not r.get("items"):
            time.sleep(3)
            continue
        v = r["items"][0]
        proc = v.get("processingDetails", {}).get("processingStatus", "?")
        upload = v.get("status", {}).get("uploadStatus", "?")
        if (proc, upload) != last_status:
            print(f"  status: processing={proc} upload={upload}", flush=True)
            last_status = (proc, upload)
        if proc in ("succeeded", "failed", "terminated"):
            return proc
        if upload == "failed":
            return "upload_failed"
        time.sleep(5)
    return "timeout"


def upload(args, env: dict, data_dir: Path) -> dict:
    client_secret = Path(env["YOUTUBE_CLIENT_SECRET_PATH"]).expanduser()
    token_file = data_dir / "yt_token.json"
    creds = get_credentials(client_secret, token_file)
    youtube = build("youtube", "v3", credentials=creds)

    title = args.title or Path(args.file).stem
    description = args.description or ""
    if args.description_file:
        description = Path(args.description_file).read_text(encoding="utf-8")
    tags_raw = args.tags if args.tags is not None else env.get("YOUTUBE_DEFAULT_TAGS", "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    privacy = args.privacy or env.get("YOUTUBE_DEFAULT_PRIVACY", "unlisted")
    category = args.category or env.get("YOUTUBE_DEFAULT_CATEGORY", "22")

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
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

    file_size = Path(args.file).stat().st_size
    print(f"uploading: {args.file} ({file_size // 1024 // 1024} MB)", flush=True)
    print(f"  title: {title}", flush=True)
    print(f"  privacy: {privacy}", flush=True)
    if tags:
        print(f"  tags: {', '.join(tags)}", flush=True)

    resp = resumable_upload(req, "upload")
    video_id = resp["id"]
    print("UPLOADED", flush=True)
    print(f"video_id: {video_id}", flush=True)
    print(f"url: https://youtu.be/{video_id}", flush=True)

    if not args.no_verify_processing:
        final = verify_processing(youtube, video_id)
        if final == "succeeded":
            print("processing: [OK] succeeded — video is playable", flush=True)
        elif final == "timeout":
            print("processing: still going (timeout reached, but upload succeeded)", flush=True)
        else:
            print(f"processing: [WARN] status={final} — check YouTube Studio", flush=True)

    return resp


def main():
    p = argparse.ArgumentParser(description="Upload a video to YouTube")
    p.add_argument("--file", required=True, help="Path to video file")
    p.add_argument("--title", help="Video title (default: filename stem)")
    p.add_argument("--description", default="", help="Video description")
    p.add_argument("--description-file", help="Read description from text file")
    p.add_argument("--tags", default=None, help="Comma-separated tags (override .env default)")
    p.add_argument("--privacy", choices=["public", "unlisted", "private"])
    p.add_argument("--category", help="YouTube category id")
    p.add_argument("--no-verify-processing", action="store_true",
                   help="Skip post-upload processing-status check")
    args = p.parse_args()

    if not Path(args.file).exists():
        sys.exit(f"video file not found: {args.file}")

    data_dir = plugin_data_dir()
    env = ensure_setup(data_dir)
    upload(args, env, data_dir)


if __name__ == "__main__":
    main()
