"""YouTube API client wrapper for yc-plugin.

Handles OAuth (with auto-recovery from expired/revoked tokens),
exposes a single `client()` function returning an authed googleapiclient
youtube resource, plus high-level helpers (set_thumbnail, add_to_playlist,
upload_caption, list_playlists).
"""
import json
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from . import console
from .paths import client_secret_file, token_file

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube",  # for thumbnails / playlists / captions
    "https://www.googleapis.com/auth/youtube.force-ssl",  # caption uploads
]


def _ensure_client_secret() -> Path:
    cs = client_secret_file()
    if not cs.exists():
        console.err(
            f"client_secret.json not found at {cs}",
            "run setup first: python bin/setup.py  (or /youtube-upload triggers it)",
        )
    return cs


def get_credentials() -> Credentials:
    """Get valid creds. Auto-recover from expired/revoked tokens."""
    cs = _ensure_client_secret()
    tf = token_file()
    creds = None
    if tf.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(tf), SCOPES)
        except (ValueError, json.JSONDecodeError):
            console.warn("token file corrupted, re-authenticating...")
            tf.unlink(missing_ok=True)
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            tf.write_text(creds.to_json(), encoding="utf-8")
            return creds
        except RefreshError as e:
            console.warn(f"token refresh failed ({e}); re-authenticating...")
            tf.unlink(missing_ok=True)

    console.info("first-time auth — browser will open for Google login...")
    flow = InstalledAppFlow.from_client_secrets_file(str(cs), SCOPES)
    creds = flow.run_local_server(port=0)
    tf.write_text(creds.to_json(), encoding="utf-8")
    return creds


def client():
    """Return an authed YouTube v3 resource."""
    return build("youtube", "v3", credentials=get_credentials())


def set_thumbnail(youtube, video_id: str, thumb_path: Path):
    """Upload custom thumbnail. Requires verified channel."""
    media = MediaFileUpload(str(thumb_path), mimetype="image/jpeg", resumable=False)
    return youtube.thumbnails().set(videoId=video_id, media_body=media).execute()


def upload_caption(youtube, video_id: str, srt_path: Path, language: str = "zh-TW", name: str = ""):
    """Upload SRT subtitle to a video."""
    body = {
        "snippet": {
            "videoId": video_id,
            "language": language,
            "name": name,
            "isDraft": False,
        }
    }
    media = MediaFileUpload(str(srt_path), mimetype="text/plain", resumable=False)
    return youtube.captions().insert(part="snippet", body=body, media_body=media).execute()


def list_playlists(youtube, mine: bool = True, max_results: int = 50):
    items = []
    next_page = None
    while True:
        req = youtube.playlists().list(
            part="id,snippet,contentDetails",
            mine=mine,
            maxResults=min(50, max_results - len(items)),
            pageToken=next_page,
        )
        resp = req.execute()
        items.extend(resp.get("items", []))
        next_page = resp.get("nextPageToken")
        if not next_page or len(items) >= max_results:
            break
    return items


def find_or_create_playlist(youtube, name: str) -> str:
    """Return playlistId. Match by exact title; create if missing."""
    for p in list_playlists(youtube):
        if p["snippet"]["title"] == name:
            return p["id"]
    body = {
        "snippet": {"title": name, "description": ""},
        "status": {"privacyStatus": "private"},
    }
    resp = youtube.playlists().insert(part="snippet,status", body=body).execute()
    return resp["id"]


def add_to_playlist(youtube, playlist_id: str, video_id: str):
    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
    }
    return youtube.playlistItems().insert(part="snippet", body=body).execute()
