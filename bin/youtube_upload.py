#!/usr/bin/env python3
"""yc-plugin: YouTube upload script with full feature set.

Features:
  - Resumable upload with exponential backoff
  - Custom thumbnail upload (--thumbnail)
  - Scheduled publish (--publish-at "YYYY-MM-DD HH:MM" or ISO 8601)
  - Auto-detect + upload SRT/ASS subtitles next to the video
  - Add to playlist by name (auto-create if missing) or ID
  - Dry-run (--dry-run) to preview metadata without uploading
  - Verbose (--verbose) for HTTP-level diagnostics
  - Post-upload processing-status verification
  - Token refresh failure recovery
  - All runs logged to plugin data dir

CLI: python youtube_upload.py --help
"""
import argparse
import http.client
import json
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Initialise console / utf-8 / log first, before importing google libs.
from lib import console, youtube_client
from lib.paths import plugin_data_dir

from googleapiclient.errors import HttpError, ResumableUploadError
from googleapiclient.http import MediaFileUpload

DEFAULT_PRIVACY = "unlisted"
DEFAULT_CATEGORY = "22"
DEFAULT_LANGUAGE = "zh-TW"

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


def parse_publish_at(s: str) -> str:
    """Convert user input to RFC3339 UTC timestamp YouTube accepts.

    Accepts:
      - ISO 8601 with timezone: 2026-05-10T20:00:00+08:00
      - "YYYY-MM-DD HH:MM" (assumed local time)
      - "YYYY-MM-DD HH:MM:SS"
    """
    s = s.strip()
    try:
        # Already RFC3339?
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"):
            try:
                dt = datetime.strptime(s, fmt)
                dt = dt.astimezone()  # attach local tz
                break
            except ValueError:
                continue
        else:
            console.err(
                f"無法解析 publish-at: {s}",
                "用 ISO 8601 (2026-05-10T20:00:00+08:00) 或 'YYYY-MM-DD HH:MM' 格式",
            )
    if dt.tzinfo is None:
        dt = dt.astimezone()
    if dt < datetime.now(tz=dt.tzinfo):
        console.warn(f"publish-at 是過去時間 ({dt.isoformat()}) — YouTube 會立即發布")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_subtitle(video_path: Path) -> Path | None:
    """Auto-detect <video>.srt or <video>.ass alongside the video file."""
    for ext in (".srt", ".vtt"):
        candidate = video_path.with_suffix(ext)
        if candidate.exists():
            return candidate
    return None


def resumable_upload(req, label: str = "upload") -> dict:
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
                    console.info(f"  {label}: {pct}%")
                    last_pct = pct
        except HttpError as e:
            if e.resp.status in RETRYABLE_STATUS_CODES:
                error = f"HTTP {e.resp.status}"
            else:
                raise
        except ResumableUploadError:
            raise
        except RETRYABLE_EXCEPTIONS as e:
            error = f"{type(e).__name__}: {e}"

        if error:
            retry += 1
            if retry > MAX_RETRIES:
                console.err(
                    f"upload failed after {MAX_RETRIES} retries: {error}",
                    "確認網路穩定後重跑同一個指令即可（YouTube 會自動續傳，不會從頭開始）",
                )
            sleep = min(2 ** retry, 64)
            console.warn(f"{error} — retrying in {sleep}s ({retry}/{MAX_RETRIES})")
            time.sleep(sleep)
            error = None

    return response


def verify_processing(youtube, video_id: str, timeout_s: int = 300) -> str:
    console.info("  verifying YouTube processing status...")
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout_s:
        try:
            r = youtube.videos().list(part="processingDetails,status", id=video_id).execute()
        except HttpError as e:
            console.warn(f"verify polling: HTTP {e.resp.status}")
            time.sleep(5)
            continue
        if not r.get("items"):
            time.sleep(3)
            continue
        v = r["items"][0]
        proc = v.get("processingDetails", {}).get("processingStatus", "?")
        upload = v.get("status", {}).get("uploadStatus", "?")
        if (proc, upload) != last:
            console.info(f"  status: processing={proc} upload={upload}")
            last = (proc, upload)
        if proc in ("succeeded", "failed", "terminated"):
            return proc
        if upload == "failed":
            return "upload_failed"
        time.sleep(5)
    return "timeout"


def build_body(args, scheduled_at_utc: str | None) -> dict:
    title = (args.title or Path(args.file).stem)[:100]
    description = args.description or ""
    if args.description_file:
        description = Path(args.description_file).read_text(encoding="utf-8")
    description = description[:5000]
    tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]

    privacy = args.privacy or DEFAULT_PRIVACY
    if scheduled_at_utc:
        # publishAt requires privacy=private
        privacy = "private"

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": args.category or DEFAULT_CATEGORY,
            "defaultLanguage": args.language or DEFAULT_LANGUAGE,
            "defaultAudioLanguage": args.language or DEFAULT_LANGUAGE,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": bool(args.for_kids),
        },
    }
    if scheduled_at_utc:
        body["status"]["publishAt"] = scheduled_at_utc
    return body


def do_upload(youtube, args, body: dict) -> dict:
    file_path = Path(args.file)
    media = MediaFileUpload(
        str(file_path), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4"
    )
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    file_size = file_path.stat().st_size
    console.info(f"uploading: {file_path} ({file_size // 1024 // 1024} MB)")
    console.info(f"  title: {body['snippet']['title']}")
    console.info(f"  privacy: {body['status']['privacyStatus']}")
    if body["status"].get("publishAt"):
        console.info(f"  publish at (UTC): {body['status']['publishAt']}")
    if body["snippet"]["tags"]:
        console.info(f"  tags: {', '.join(body['snippet']['tags'])}")

    resp = resumable_upload(req, "upload")
    console.ok(f"UPLOADED video_id={resp['id']}")
    console.info(f"url: https://youtu.be/{resp['id']}")
    return resp


def upload_thumbnail_if_provided(youtube, video_id: str, thumbnail: Path | None):
    if not thumbnail:
        return
    if not thumbnail.exists():
        console.warn(f"thumbnail file not found: {thumbnail} — skipping")
        return
    if thumbnail.stat().st_size > 2 * 1024 * 1024:
        console.warn(f"thumbnail >2MB ({thumbnail.stat().st_size} bytes) — YouTube may reject")
    try:
        youtube_client.set_thumbnail(youtube, video_id, thumbnail)
        console.ok(f"thumbnail set: {thumbnail.name}")
    except HttpError as e:
        if e.resp.status == 403:
            console.warn(
                "thumbnail upload forbidden (403). Custom thumbnails require a verified channel.\n"
                "   ↪ verify at https://www.youtube.com/verify"
            )
        else:
            console.warn(f"thumbnail upload failed: HTTP {e.resp.status} — {e}")


def upload_caption_if_found(youtube, video_id: str, video_path: Path, language: str, explicit: Path | None):
    """Upload caption file. Use explicit path if given, else auto-detect alongside video."""
    cap = explicit if explicit else find_subtitle(video_path)
    if not cap:
        return
    if not cap.exists():
        console.warn(f"caption file not found: {cap} — skipping")
        return
    try:
        youtube_client.upload_caption(youtube, video_id, cap, language=language, name="")
        console.ok(f"caption uploaded: {cap.name}")
    except HttpError as e:
        console.warn(f"caption upload failed: HTTP {e.resp.status} — {e}")


def add_to_playlist_if_provided(youtube, video_id: str, playlist: str | None):
    if not playlist:
        return
    try:
        # Heuristic: looks like a YouTube playlist id (PL...) → use as-is, else look up by name.
        if playlist.startswith(("PL", "UU", "FL", "LL", "OL")) and len(playlist) >= 20:
            pl_id = playlist
        else:
            pl_id = youtube_client.find_or_create_playlist(youtube, playlist)
            console.info(f"playlist: {playlist} → {pl_id}")
        youtube_client.add_to_playlist(youtube, pl_id, video_id)
        console.ok(f"added to playlist: {playlist}")
    except HttpError as e:
        console.warn(f"playlist add failed: HTTP {e.resp.status} — {e}")


def main():
    p = argparse.ArgumentParser(
        description="Upload a video to YouTube with thumbnail / schedule / playlist / captions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 最簡單
  python youtube_upload.py --file ep1.mp4

  # 完整
  python youtube_upload.py --file ep1.mp4 \\
    --title "EP1 校園愛情故事" \\
    --description-file desc.txt \\
    --tags "校園,廣播劇,有聲故事" \\
    --thumbnail cover.jpg \\
    --playlist "WB故事空間" \\
    --publish-at "2026-05-10 20:00" \\
    --language zh-TW

  # dry-run (只看會送什麼，不真上傳)
  python youtube_upload.py --file ep1.mp4 --title "test" --dry-run
""",
    )
    p.add_argument("--file", required=True, help="影片檔案路徑")
    p.add_argument("--title", help="標題（預設用檔名）")
    p.add_argument("--description", default="", help="影片描述（短）")
    p.add_argument("--description-file", help="從檔案讀描述（可貼長文）")
    p.add_argument("--tags", default="", help="逗號分隔的 tags")
    p.add_argument("--privacy", choices=["public", "unlisted", "private"],
                   help=f"預設: {DEFAULT_PRIVACY}（用 --publish-at 時自動變 private）")
    p.add_argument("--category", help=f"YouTube 分類 id (預設: {DEFAULT_CATEGORY} People & Blogs)")
    p.add_argument("--language", help=f"defaultLanguage / defaultAudioLanguage (預設: {DEFAULT_LANGUAGE})")
    p.add_argument("--thumbnail", help="封面圖路徑 (jpg/png, ≤2MB)")
    p.add_argument("--playlist", help="播放清單名稱（自動建立）或 playlist ID")
    p.add_argument("--publish-at", dest="publish_at",
                   help="排程發布時間。格式: 'YYYY-MM-DD HH:MM' (本地時區) 或 ISO 8601")
    p.add_argument("--caption", help="字幕 SRT/VTT 檔案路徑（不指定會自動偵測同名檔）")
    p.add_argument("--for-kids", action="store_true", help="標記為兒童內容")
    p.add_argument("--no-verify-processing", action="store_true",
                   help="跳過上傳完的 processingStatus 確認")
    p.add_argument("--no-auto-caption", action="store_true",
                   help="不要自動偵測同名 .srt/.vtt 字幕檔")
    p.add_argument("--dry-run", action="store_true",
                   help="只印會送的 metadata，不真上傳")
    p.add_argument("--verbose", action="store_true", help="多印 debug 訊息")
    args = p.parse_args()

    console.init(verbose=args.verbose)

    file_path = Path(args.file)
    if not file_path.exists():
        console.err(
            f"video file not found: {args.file}",
            "確認路徑正確（注意 Windows 用正斜線 / 或雙反斜線 \\\\）",
        )

    scheduled_at_utc = parse_publish_at(args.publish_at) if args.publish_at else None
    body = build_body(args, scheduled_at_utc)

    if args.dry_run:
        console.info("=== DRY RUN — would send ===")
        console.info(json.dumps(body, ensure_ascii=False, indent=2))
        if args.thumbnail:
            console.info(f"thumbnail: {args.thumbnail}")
        if args.playlist:
            console.info(f"playlist: {args.playlist}")
        cap = Path(args.caption) if args.caption else (None if args.no_auto_caption else find_subtitle(file_path))
        if cap:
            console.info(f"caption: {cap}")
        console.info("(no upload performed)")
        return

    youtube = youtube_client.client()

    resp = do_upload(youtube, args, body)
    video_id = resp["id"]

    if args.thumbnail:
        upload_thumbnail_if_provided(youtube, video_id, Path(args.thumbnail))

    if not args.no_auto_caption or args.caption:
        explicit = Path(args.caption) if args.caption else None
        upload_caption_if_found(youtube, video_id, file_path, body["snippet"]["defaultLanguage"], explicit)

    if args.playlist:
        add_to_playlist_if_provided(youtube, video_id, args.playlist)

    if not args.no_verify_processing:
        final = verify_processing(youtube, video_id)
        if final == "succeeded":
            console.ok("processing succeeded — video is playable")
        elif final == "timeout":
            console.info("processing still going (timeout reached, but upload succeeded)")
        else:
            console.warn(f"processing status: {final} — check YouTube Studio")

    console.info("")
    console.info(f"DONE → https://youtu.be/{video_id}")


if __name__ == "__main__":
    main()
