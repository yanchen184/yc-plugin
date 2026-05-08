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


def remove_from_playlist(youtube, playlist_id: str, video_id: str) -> bool:
    """Find the playlistItem matching video_id and delete it. Returns True if removed."""
    next_page = None
    while True:
        resp = youtube.playlistItems().list(
            part="id,snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page,
        ).execute()
        for it in resp.get("items", []):
            if it["snippet"]["resourceId"]["videoId"] == video_id:
                youtube.playlistItems().delete(id=it["id"]).execute()
                return True
        next_page = resp.get("nextPageToken")
        if not next_page:
            return False


def get_my_uploads_playlist_id(youtube) -> str:
    """Each channel has a special 'uploads' playlist that lists every video the user uploaded."""
    ch = youtube.channels().list(part="contentDetails", mine=True).execute()
    items = ch.get("items", [])
    if not items:
        raise RuntimeError("無法取得 channel — 確認 OAuth 帳號有 YouTube channel")
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def list_my_videos(youtube, max_results: int = 50, since: str | None = None) -> list[dict]:
    """List my uploaded videos (from the channel's uploads playlist).

    Returns shallow info: id, title, publishedAt, thumbnail. Use get_video_details()
    for full snippet/status/statistics.

    since: ISO date string ('2026-05-01') — filter to videos published on/after.
    """
    uploads_pl = get_my_uploads_playlist_id(youtube)
    items = []
    next_page = None
    while True:
        remaining = max_results - len(items)
        if remaining <= 0:
            break
        resp = youtube.playlistItems().list(
            part="contentDetails,snippet",
            playlistId=uploads_pl,
            maxResults=min(50, remaining),
            pageToken=next_page,
        ).execute()
        for it in resp.get("items", []):
            published = it["contentDetails"].get("videoPublishedAt", "")
            if since and published and published[:10] < since:
                continue
            items.append({
                "id": it["contentDetails"]["videoId"],
                "title": it["snippet"]["title"],
                "publishedAt": published,
                "thumbnail": (it["snippet"].get("thumbnails") or {}).get("default", {}).get("url", ""),
            })
            if len(items) >= max_results:
                return items
        next_page = resp.get("nextPageToken")
        if not next_page:
            break
    return items


def get_video_details(youtube, video_ids: list[str], parts: str = "snippet,status,statistics,contentDetails") -> list[dict]:
    """Fetch full details for one or more video IDs. API allows up to 50 IDs per call."""
    if not video_ids:
        return []
    results = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        resp = youtube.videos().list(part=parts, id=",".join(batch)).execute()
        results.extend(resp.get("items", []))
    return results


def update_video(
    youtube,
    video_id: str,
    snippet_updates: dict | None = None,
    status_updates: dict | None = None,
) -> dict:
    """Update video metadata. Fetches current snippet/status first to preserve unspecified fields.

    snippet_updates: dict with keys like title, description, tags, categoryId, defaultLanguage, defaultAudioLanguage
    status_updates:  dict with keys like privacyStatus, selfDeclaredMadeForKids, publishAt
    """
    if not snippet_updates and not status_updates:
        raise ValueError("沒有可更新的欄位")

    cur = youtube.videos().list(part="snippet,status", id=video_id).execute()
    items = cur.get("items", [])
    if not items:
        raise RuntimeError(f"video not found: {video_id}")
    cur_snippet = items[0]["snippet"]
    cur_status = items[0]["status"]

    parts = []
    body: dict = {"id": video_id}

    if snippet_updates:
        merged = {
            "title": cur_snippet.get("title", ""),
            "description": cur_snippet.get("description", ""),
            "tags": cur_snippet.get("tags", []),
            "categoryId": cur_snippet.get("categoryId", "22"),
            "defaultLanguage": cur_snippet.get("defaultLanguage"),
            "defaultAudioLanguage": cur_snippet.get("defaultAudioLanguage"),
        }
        merged.update(snippet_updates)
        merged = {k: v for k, v in merged.items() if v is not None}
        body["snippet"] = merged
        parts.append("snippet")

    if status_updates:
        merged = {
            "privacyStatus": cur_status.get("privacyStatus", "private"),
            "selfDeclaredMadeForKids": cur_status.get("selfDeclaredMadeForKids", False),
        }
        merged.update(status_updates)
        body["status"] = merged
        parts.append("status")

    return youtube.videos().update(part=",".join(parts), body=body).execute()
