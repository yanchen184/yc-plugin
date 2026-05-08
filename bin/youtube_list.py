#!/usr/bin/env python3
"""yc-plugin: list my YouTube uploads.

Shows video_id + title + privacy + publish date + view count for videos
the authenticated account uploaded. Filters by playlist / date range / privacy.

Used as input for /youtube-update, /youtube-stats, /youtube-delete (when added).

CLI: python youtube_list.py --help
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

from lib import console, formatting, youtube_client
from googleapiclient.errors import HttpError


def filter_by_privacy(videos: list[dict], wanted: str) -> list[dict]:
    return [v for v in videos if v.get("privacyStatus") == wanted]


def filter_by_query(videos: list[dict], q: str) -> list[dict]:
    q = q.lower()
    return [v for v in videos if q in v.get("title", "").lower()]


def filter_by_until(videos: list[dict], until: str) -> list[dict]:
    return [v for v in videos if v.get("publishedAt", "")[:10] <= until]


def filter_by_playlist(youtube, videos: list[dict], playlist: str) -> list[dict]:
    """Keep only videos that are in the named playlist (or playlist ID)."""
    if playlist.startswith(("PL", "UU", "FL", "LL", "OL")) and len(playlist) >= 20:
        pl_id = playlist
    else:
        for p in youtube_client.list_playlists(youtube):
            if p["snippet"]["title"] == playlist:
                pl_id = p["id"]
                break
        else:
            console.warn(f"playlist not found: {playlist}; returning empty list")
            return []

    in_playlist: set[str] = set()
    next_page = None
    while True:
        resp = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=pl_id,
            maxResults=50,
            pageToken=next_page,
        ).execute()
        for it in resp.get("items", []):
            in_playlist.add(it["contentDetails"]["videoId"])
        next_page = resp.get("nextPageToken")
        if not next_page:
            break

    return [v for v in videos if v["id"] in in_playlist]


def enrich_with_details(youtube, shallow: list[dict]) -> list[dict]:
    """Add privacyStatus / viewCount / likeCount / commentCount via videos.list."""
    if not shallow:
        return []
    ids = [v["id"] for v in shallow]
    details = youtube_client.get_video_details(youtube, ids, parts="snippet,status,statistics")
    detail_by_id = {d["id"]: d for d in details}
    enriched = []
    for v in shallow:
        d = detail_by_id.get(v["id"], {})
        snippet = d.get("snippet", {})
        status = d.get("status", {})
        stats = d.get("statistics", {})
        enriched.append({
            **v,
            "privacyStatus": status.get("privacyStatus", "?"),
            "uploadStatus": status.get("uploadStatus", "?"),
            "viewCount": stats.get("viewCount", "0"),
            "likeCount": stats.get("likeCount", "0"),
            "commentCount": stats.get("commentCount", "0"),
            "categoryId": snippet.get("categoryId", ""),
            "tags": snippet.get("tags", []),
        })
    return enriched


def main():
    p = argparse.ArgumentParser(
        description="List my YouTube uploads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 最近 20 部
  python youtube_list.py

  # 只看 public 影片
  python youtube_list.py --privacy public

  # 標題含「她的賭注」的
  python youtube_list.py --query 她的賭注

  # 「她的賭注」播放清單裡的
  python youtube_list.py --playlist 她的賭注

  # 2026-05 之後上傳的，輸出 JSON
  python youtube_list.py --since 2026-05-01 --format json

  # 簡略模式（不查 statistics，省 quota）
  python youtube_list.py --shallow
""",
    )
    p.add_argument("--limit", type=int, default=20,
                   help="最多回傳幾部（預設 20）")
    p.add_argument("--privacy", choices=["public", "unlisted", "private"],
                   help="只列指定隱私的影片")
    p.add_argument("--playlist",
                   help="只列在此播放清單的影片（給名字或 playlist ID）")
    p.add_argument("--since",
                   help="只列此日期 (YYYY-MM-DD) 後上傳的")
    p.add_argument("--until",
                   help="只列此日期 (YYYY-MM-DD) 前上傳的")
    p.add_argument("--query", "-q",
                   help="標題子字串搜尋 (case-insensitive)")
    p.add_argument("--format", choices=["table", "json", "markdown"], default="table",
                   help="輸出格式（預設 table）")
    p.add_argument("--shallow", action="store_true",
                   help="不查 statistics（省 API quota，只回 id/title/published）")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    console.init(verbose=args.verbose)

    if args.since:
        try:
            datetime.strptime(args.since, "%Y-%m-%d")
        except ValueError:
            console.err(f"--since 格式不對: {args.since}", "用 YYYY-MM-DD")
    if args.until:
        try:
            datetime.strptime(args.until, "%Y-%m-%d")
        except ValueError:
            console.err(f"--until 格式不對: {args.until}", "用 YYYY-MM-DD")

    try:
        youtube = youtube_client.client()
        # Pull more than --limit if filters are active so post-filter still has rows
        fetch_n = args.limit
        if args.privacy or args.query or args.until or args.playlist:
            fetch_n = max(args.limit * 5, 100)
        videos = youtube_client.list_my_videos(youtube, max_results=fetch_n, since=args.since)

        if not args.shallow:
            videos = enrich_with_details(youtube, videos)

        if args.privacy:
            videos = filter_by_privacy(videos, args.privacy)
        if args.query:
            videos = filter_by_query(videos, args.query)
        if args.until:
            videos = filter_by_until(videos, args.until)
        if args.playlist:
            videos = filter_by_playlist(youtube, videos, args.playlist)

        videos = videos[:args.limit]

        # Pre-format numbers/dates for display
        for v in videos:
            v["date"] = formatting.format_date(v.get("publishedAt", ""))
            v["views"] = formatting.format_int(v.get("viewCount"))
            v["likes"] = formatting.format_int(v.get("likeCount"))
            v["comments"] = formatting.format_int(v.get("commentCount"))

        if args.shallow:
            cols = [
                ("id", "video_id", 11),
                ("title", "標題", 50),
                ("date", "上傳日", 10),
            ]
        else:
            cols = [
                ("id", "video_id", 11),
                ("title", "標題", 40),
                ("privacyStatus", "隱私", 8),
                ("date", "上傳日", 10),
                ("views", "觀看", 8),
                ("likes", "讚", 6),
                ("comments", "留言", 6),
            ]

        print(formatting.render(videos, args.format, cols))
        if args.format == "table":
            print(f"\n共 {len(videos)} 部")
    except HttpError as e:
        console.err(f"YouTube API error: HTTP {e.resp.status} — {e}",
                    "確認 token 還有效；token 過期跑 /youtube-setup reset 重新授權")


if __name__ == "__main__":
    main()
