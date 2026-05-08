#!/usr/bin/env python3
"""yc-plugin: pull statistics for my YouTube videos.

Returns view counts / like counts / comment counts for one or more videos —
either explicit IDs or "my latest N uploads".

Note: this only uses YouTube Data API (videos.list with statistics).
Time-series, retention curves, audience demographics need YouTube Analytics
API which has a separate scope (planned for v0.5).

CLI: python youtube_stats.py --help
"""
import argparse
from datetime import datetime, timezone

from lib import console, formatting, youtube_client
from googleapiclient.errors import HttpError


def parse_iso8601_duration(s: str) -> int:
    """Parse YouTube ISO 8601 duration (PT5M30S) to seconds."""
    if not s or not s.startswith("PT"):
        return 0
    s = s[2:]
    total = 0
    num = ""
    for c in s:
        if c.isdigit():
            num += c
        elif c == "H":
            total += int(num) * 3600
            num = ""
        elif c == "M":
            total += int(num) * 60
            num = ""
        elif c == "S":
            total += int(num)
            num = ""
    return total


def fmt_duration(secs: int) -> str:
    if secs <= 0:
        return "?"
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def days_since(iso: str) -> int:
    if not iso:
        return -1
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return -1
    return (datetime.now(tz=timezone.utc) - dt).days


def main():
    p = argparse.ArgumentParser(
        description="Pull statistics for my YouTube videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 我最新 10 部的 stats
  python youtube_stats.py

  # 指定影片
  python youtube_stats.py --video-id Y6ytntuQTgM
  python youtube_stats.py --video-id Y6ytntuQTgM --video-id abc123def

  # 「她的賭注」播放清單裡所有影片
  python youtube_stats.py --playlist 她的賭注

  # JSON 輸出（接 jq / 其他工具用）
  python youtube_stats.py --format json
""",
    )
    p.add_argument("--video-id", action="append", default=[],
                   help="指定影片（可重複）；不指定則拉最新 N 部")
    p.add_argument("--playlist",
                   help="拉指定 playlist 內所有影片的 stats（給名字或 playlist ID）")
    p.add_argument("--limit", type=int, default=10,
                   help="不指定 video-id 時拉最新幾部（預設 10）")
    p.add_argument("--format", choices=["table", "json", "markdown"], default="table")
    p.add_argument("--sort",
                   choices=["views", "likes", "comments", "date", "engagement"],
                   default="date",
                   help="排序欄位（預設 date 由新到舊）")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    console.init(verbose=args.verbose)

    try:
        youtube = youtube_client.client()

        if args.video_id:
            ids = list(args.video_id)
        elif args.playlist:
            # Resolve playlist
            if args.playlist.startswith(("PL", "UU", "FL", "LL", "OL")) and len(args.playlist) >= 20:
                pl_id = args.playlist
            else:
                pl_id = None
                for p_ in youtube_client.list_playlists(youtube):
                    if p_["snippet"]["title"] == args.playlist:
                        pl_id = p_["id"]
                        break
                if not pl_id:
                    console.err(f"playlist not found: {args.playlist}", "用 /youtube-list 看現有 playlist 名")
            ids = []
            next_page = None
            while True:
                resp = youtube.playlistItems().list(
                    part="contentDetails", playlistId=pl_id,
                    maxResults=50, pageToken=next_page,
                ).execute()
                for it in resp.get("items", []):
                    ids.append(it["contentDetails"]["videoId"])
                next_page = resp.get("nextPageToken")
                if not next_page:
                    break
        else:
            shallow = youtube_client.list_my_videos(youtube, max_results=args.limit)
            ids = [v["id"] for v in shallow]

        if not ids:
            console.warn("沒有可查 stats 的影片")
            return

        details = youtube_client.get_video_details(
            youtube, ids, parts="snippet,status,statistics,contentDetails"
        )

        rows = []
        for d in details:
            stats = d.get("statistics", {})
            snippet = d.get("snippet", {})
            content = d.get("contentDetails", {})
            status = d.get("status", {})
            views = int(stats.get("viewCount", 0) or 0)
            likes = int(stats.get("likeCount", 0) or 0)
            comments = int(stats.get("commentCount", 0) or 0)
            engagement = (likes + comments) / views * 100 if views > 0 else 0
            rows.append({
                "id": d["id"],
                "title": snippet.get("title", ""),
                "privacyStatus": status.get("privacyStatus", "?"),
                "publishedAt": snippet.get("publishedAt", ""),
                "date": formatting.format_date(snippet.get("publishedAt", "")),
                "age_days": days_since(snippet.get("publishedAt", "")),
                "duration": fmt_duration(parse_iso8601_duration(content.get("duration", ""))),
                "viewCount": views,
                "likeCount": likes,
                "commentCount": comments,
                "engagement_pct": round(engagement, 2),
                "views": formatting.format_int(views),
                "likes": formatting.format_int(likes),
                "comments": formatting.format_int(comments),
            })

        sort_key_map = {
            "views": lambda r: -r["viewCount"],
            "likes": lambda r: -r["likeCount"],
            "comments": lambda r: -r["commentCount"],
            "engagement": lambda r: -r["engagement_pct"],
            "date": lambda r: r["publishedAt"] or "",
        }
        rows.sort(key=sort_key_map[args.sort], reverse=(args.sort == "date"))

        cols = [
            ("id", "video_id", 11),
            ("title", "標題", 36),
            ("date", "上傳", 10),
            ("age_days", "天前", 5),
            ("duration", "長度", 7),
            ("views", "觀看", 8),
            ("likes", "讚", 6),
            ("comments", "留言", 6),
            ("engagement_pct", "互動%", 6),
        ]

        print(formatting.render(rows, args.format, cols))

        if args.format == "table" and rows:
            total_views = sum(r["viewCount"] for r in rows)
            total_likes = sum(r["likeCount"] for r in rows)
            total_comments = sum(r["commentCount"] for r in rows)
            print(f"\n總計：{len(rows)} 部 | 觀看 {formatting.format_int(total_views)} | "
                  f"讚 {formatting.format_int(total_likes)} | 留言 {formatting.format_int(total_comments)}")
    except HttpError as e:
        console.err(f"YouTube API error: HTTP {e.resp.status} — {e}",
                    "token 過期就跑 /youtube-setup reset 重新授權")


if __name__ == "__main__":
    main()
