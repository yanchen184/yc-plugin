#!/usr/bin/env python3
"""yc-plugin: update an existing YouTube video's metadata.

Change title / description / tags / privacy / playlist / thumbnail / caption
without re-uploading the video. Fetches current snippet and status first so
unspecified fields stay intact (YouTube videos.update otherwise clears them).

CLI: python youtube_update.py --help
"""
import argparse
import json
import sys
from pathlib import Path

from lib import console, youtube_client
from googleapiclient.errors import HttpError


def main():
    p = argparse.ArgumentParser(
        description="Update existing YouTube video metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 改標題
  python youtube_update.py --video-id Y6ytntuQTgM --title "新標題"

  # 改隱私從 unlisted → public
  python youtube_update.py --video-id Y6ytntuQTgM --privacy public

  # 加入播放清單
  python youtube_update.py --video-id Y6ytntuQTgM --add-to-playlist "她的賭注"

  # 從播放清單移除
  python youtube_update.py --video-id Y6ytntuQTgM --remove-from-playlist "她的賭注"

  # 加 tags（保留舊的）
  python youtube_update.py --video-id Y6ytntuQTgM --add-tags "推薦,熱門"

  # 移除 tags
  python youtube_update.py --video-id Y6ytntuQTgM --remove-tags "舊tag1,舊tag2"

  # 取代整個 tag 清單
  python youtube_update.py --video-id Y6ytntuQTgM --tags "tag1,tag2,tag3"

  # 換封面
  python youtube_update.py --video-id Y6ytntuQTgM --thumbnail new_cover.jpg

  # 描述從檔案讀
  python youtube_update.py --video-id Y6ytntuQTgM --description-file desc.txt

  # 只看會送什麼，不真改
  python youtube_update.py --video-id Y6ytntuQTgM --title "新" --dry-run
""",
    )
    p.add_argument("--video-id", required=True, help="目標影片 ID")
    p.add_argument("--title", help="新標題")
    p.add_argument("--description", help="新描述（短）")
    p.add_argument("--description-file", help="從檔案讀新描述")
    p.add_argument("--tags", help="完全取代 tags（逗號分隔）")
    p.add_argument("--add-tags", help="附加 tags（逗號分隔，保留舊的）")
    p.add_argument("--remove-tags", help="移除 tags（逗號分隔）")
    p.add_argument("--privacy", choices=["public", "unlisted", "private"],
                   help="新隱私狀態")
    p.add_argument("--category", help="新分類 ID")
    p.add_argument("--language", help="defaultLanguage / defaultAudioLanguage")
    p.add_argument("--thumbnail", help="新封面圖路徑（jpg/png ≤2MB）")
    p.add_argument("--caption", help="新字幕檔（會新增一個 caption track）")
    p.add_argument("--add-to-playlist",
                   help="加到播放清單（給名字會自動建立，或 playlist ID）")
    p.add_argument("--remove-from-playlist",
                   help="從播放清單移除（給名字或 playlist ID）")
    p.add_argument("--for-kids", action="store_true",
                   help="標記為兒童內容")
    p.add_argument("--not-for-kids", action="store_true",
                   help="取消兒童內容標記")
    p.add_argument("--dry-run", action="store_true",
                   help="只印會送的 metadata，不真改")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    console.init(verbose=args.verbose)

    if args.for_kids and args.not_for_kids:
        console.err("--for-kids 跟 --not-for-kids 衝突，只能擇一", "")

    snippet_updates = {}
    status_updates = {}

    if args.title is not None:
        snippet_updates["title"] = args.title[:100]
    if args.description is not None:
        snippet_updates["description"] = args.description[:5000]
    if args.description_file:
        path = Path(args.description_file)
        if not path.exists():
            console.err(f"description-file 不存在: {path}", "確認路徑")
        snippet_updates["description"] = path.read_text(encoding="utf-8")[:5000]
    if args.category is not None:
        snippet_updates["categoryId"] = args.category
    if args.language is not None:
        snippet_updates["defaultLanguage"] = args.language
        snippet_updates["defaultAudioLanguage"] = args.language

    if args.privacy is not None:
        status_updates["privacyStatus"] = args.privacy
    if args.for_kids:
        status_updates["selfDeclaredMadeForKids"] = True
    if args.not_for_kids:
        status_updates["selfDeclaredMadeForKids"] = False

    needs_tag_logic = bool(args.tags or args.add_tags or args.remove_tags)

    has_metadata_changes = bool(snippet_updates or status_updates or needs_tag_logic)
    has_side_effects = bool(args.thumbnail or args.caption or
                            args.add_to_playlist or args.remove_from_playlist)
    if not has_metadata_changes and not has_side_effects:
        console.err("沒指定要改什麼", "至少給一個 --title / --description / --privacy / ...")

    try:
        youtube = youtube_client.client()

        if needs_tag_logic:
            # tags 的 add/remove 需要先讀目前 tags
            cur = youtube.videos().list(part="snippet", id=args.video_id).execute()
            items = cur.get("items", [])
            if not items:
                console.err(f"video not found: {args.video_id}", "確認 video_id 正確")
            cur_tags = items[0]["snippet"].get("tags", [])

            if args.tags is not None:
                new_tags = [t.strip() for t in args.tags.split(",") if t.strip()]
            else:
                new_tags = list(cur_tags)
                if args.add_tags:
                    for t in (x.strip() for x in args.add_tags.split(",") if x.strip()):
                        if t not in new_tags:
                            new_tags.append(t)
                if args.remove_tags:
                    drop = {t.strip() for t in args.remove_tags.split(",") if t.strip()}
                    new_tags = [t for t in new_tags if t not in drop]

            snippet_updates["tags"] = new_tags

        if args.dry_run:
            console.info("=== DRY RUN — would send ===")
            payload: dict = {"id": args.video_id}
            if snippet_updates:
                payload["snippet"] = snippet_updates
            if status_updates:
                payload["status"] = status_updates
            console.info(json.dumps(payload, ensure_ascii=False, indent=2))
            if args.thumbnail:
                console.info(f"thumbnail: {args.thumbnail}")
            if args.caption:
                console.info(f"caption: {args.caption}")
            if args.add_to_playlist:
                console.info(f"add to playlist: {args.add_to_playlist}")
            if args.remove_from_playlist:
                console.info(f"remove from playlist: {args.remove_from_playlist}")
            console.info("(no changes performed)")
            return

        if snippet_updates or status_updates:
            youtube_client.update_video(
                youtube,
                args.video_id,
                snippet_updates=snippet_updates or None,
                status_updates=status_updates or None,
            )
            console.ok(f"metadata updated: {args.video_id}")

        if args.thumbnail:
            thumb = Path(args.thumbnail)
            if not thumb.exists():
                console.warn(f"thumbnail file not found: {thumb} — skipping")
            else:
                try:
                    youtube_client.set_thumbnail(youtube, args.video_id, thumb)
                    console.ok(f"thumbnail updated: {thumb.name}")
                except HttpError as e:
                    if e.resp.status == 403:
                        console.warn("thumbnail 403 — channel must be verified at https://www.youtube.com/verify")
                    else:
                        console.warn(f"thumbnail update failed: HTTP {e.resp.status}")

        if args.caption:
            cap = Path(args.caption)
            if not cap.exists():
                console.warn(f"caption file not found: {cap} — skipping")
            else:
                try:
                    youtube_client.upload_caption(
                        youtube, args.video_id, cap,
                        language=args.language or "zh-TW", name="",
                    )
                    console.ok(f"caption uploaded: {cap.name}")
                except HttpError as e:
                    console.warn(f"caption upload failed: HTTP {e.resp.status}")

        if args.add_to_playlist:
            try:
                pl = args.add_to_playlist
                if pl.startswith(("PL", "UU", "FL", "LL", "OL")) and len(pl) >= 20:
                    pl_id = pl
                else:
                    pl_id = youtube_client.find_or_create_playlist(youtube, pl)
                youtube_client.add_to_playlist(youtube, pl_id, args.video_id)
                console.ok(f"added to playlist: {args.add_to_playlist}")
            except HttpError as e:
                console.warn(f"playlist add failed: HTTP {e.resp.status}")

        if args.remove_from_playlist:
            try:
                pl = args.remove_from_playlist
                if pl.startswith(("PL", "UU", "FL", "LL", "OL")) and len(pl) >= 20:
                    pl_id = pl
                else:
                    pl_id = None
                    for p_ in youtube_client.list_playlists(youtube):
                        if p_["snippet"]["title"] == pl:
                            pl_id = p_["id"]
                            break
                    if not pl_id:
                        console.warn(f"playlist not found: {pl}")
                        pl_id = None
                if pl_id:
                    if youtube_client.remove_from_playlist(youtube, pl_id, args.video_id):
                        console.ok(f"removed from playlist: {args.remove_from_playlist}")
                    else:
                        console.warn(f"video {args.video_id} not in playlist {args.remove_from_playlist}")
            except HttpError as e:
                console.warn(f"playlist remove failed: HTTP {e.resp.status}")

        console.info("")
        console.info(f"DONE → https://youtu.be/{args.video_id}")
    except HttpError as e:
        console.err(f"YouTube API error: HTTP {e.resp.status} — {e}",
                    "token 過期就跑 /youtube-setup reset 重新授權")


if __name__ == "__main__":
    main()
