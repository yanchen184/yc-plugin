#!/usr/bin/env python3
"""yc-plugin: series template management.

Define a multi-episode series once (title format / description template /
tags / playlist / language / privacy), then upload subsequent episodes
with `apply <series-id> --episode N --episode-title "..."` and the template
fills in everything automatically.

Templates are stored as JSON in ~/.claude/plugins/data/yc-plugin/series/<id>.json.
After successful uploads, episode info (video_id, title, date) is appended
back to the template — used to auto-cross-link in description (previous /
next episode references).

CLI: python youtube_series.py --help
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from lib import console
from lib.paths import plugin_data_dir, plugin_root

SERIES_DIR_NAME = "series"


def series_dir() -> Path:
    d = plugin_data_dir() / SERIES_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def series_path(series_id: str) -> Path:
    return series_dir() / f"{series_id}.json"


def load_series(series_id: str) -> dict:
    p = series_path(series_id)
    if not p.exists():
        console.err(f"找不到 series: {series_id}",
                    "用 `youtube_series.py list` 看現有 series 或 `init` 建一個")
    return json.loads(p.read_text(encoding="utf-8"))


def save_series(series_id: str, data: dict) -> None:
    p = series_path(series_id)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_series() -> list[dict]:
    out = []
    for p in sorted(series_dir().glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            out.append({
                "id": p.stem,
                "name": d.get("name", "?"),
                "episodes": len(d.get("episodes", [])),
                "playlist": d.get("playlist", ""),
            })
        except Exception:
            continue
    return out


# ---------------- init ----------------

def cmd_init(args) -> int:
    sid = args.id
    if series_path(sid).exists() and not args.force:
        console.err(f"series 已存在: {sid}", "用 --force 覆寫，或 delete 先移除")

    name = args.name or input("系列名（顯示用）: ").strip()
    playlist = args.playlist or input(f"YouTube 播放清單名（按 enter 用「{name}」）: ").strip() or name
    title_template = args.title_template or input(
        '標題模板（變數: {episode:02d} {episode_title}）\n'
        '例: 床前故事｜她的賭注 EP{episode:02d} {episode_title}\n> '
    ).strip()
    if not title_template:
        console.err("標題模板不能空白", "")

    print("\n描述模板（變數: {episode:02d} {episode_title} {episode_summary} {previous_link_block} {next_episode_title}）")
    print("結束輸入打 EOF（Ctrl-D / Ctrl-Z）：")
    desc_lines = []
    if not args.description_template:
        try:
            while True:
                desc_lines.append(input())
        except EOFError:
            pass
        description_template = "\n".join(desc_lines).strip() or "{episode_summary}"
    else:
        description_template = args.description_template

    tags_raw = args.tags or input("\nTags (逗號分隔): ").strip()
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    language = args.language or input("Language（預設 zh-TW）: ").strip() or "zh-TW"
    privacy = args.privacy or input("Privacy [public/unlisted/private] (預設 public): ").strip() or "public"
    category = args.category or input("Category id（預設 22）: ").strip() or "22"

    data = {
        "id": sid,
        "name": name,
        "title_template": title_template,
        "description_template": description_template,
        "playlist": playlist,
        "tags": tags,
        "language": language,
        "privacy": privacy,
        "category": category,
        "episodes": [],
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_series(sid, data)
    console.ok(f"series '{sid}' created → {series_path(sid)}")
    console.info(f"  name:     {name}")
    console.info(f"  playlist: {playlist}")
    console.info(f"  tags:     {', '.join(tags)}")
    console.info("")
    console.info(f"下一步：apply 第一集")
    console.info(f"  python {Path(__file__).name} apply {sid} \\")
    console.info(f"    --episode 1 --episode-title \"...\" \\")
    console.info(f"    --video <path>")
    return 0


# ---------------- list / show / delete ----------------

def cmd_list(args) -> int:
    items = list_series()
    if not items:
        console.info("(沒有 series)")
        return 0
    for s in items:
        print(f"{s['id']:20s}  {s['name']:30s}  {s['episodes']:3d} 集  → {s['playlist']}")
    return 0


def cmd_show(args) -> int:
    data = load_series(args.id)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def cmd_delete(args) -> int:
    p = series_path(args.id)
    if not p.exists():
        console.err(f"series 不存在: {args.id}", "")
    if not args.force:
        ans = input(f"確定刪 series '{args.id}'？(yes/no): ").strip().lower()
        if ans not in ("yes", "y", "確定"):
            console.info("已取消")
            return 0
    p.unlink()
    console.ok(f"deleted: {args.id}")
    return 0


# ---------------- add-episode ----------------

def cmd_add_episode(args) -> int:
    """Manually record an already-uploaded episode in the series.

    Use case: ep01 was uploaded before this series was defined; we want to
    register it so cross-links work for ep02.
    """
    data = load_series(args.id)
    rec = {
        "episode": args.episode,
        "title": args.episode_title,
        "video_id": args.video_id,
        "uploaded_at": args.uploaded_at or datetime.now().isoformat(timespec="seconds"),
    }
    if args.summary:
        rec["summary"] = args.summary

    # Replace if already exists
    data["episodes"] = [e for e in data["episodes"] if e["episode"] != args.episode]
    data["episodes"].append(rec)
    data["episodes"].sort(key=lambda e: e["episode"])
    save_series(args.id, data)
    console.ok(f"recorded EP{args.episode:02d} ({args.video_id}) into series '{args.id}'")
    return 0


# ---------------- apply ----------------

def render_template(template: str, vars: dict) -> str:
    """Use Python str.format with the given vars dict. Missing keys → empty string."""
    class _SafeDict(dict):
        def __missing__(self, key):
            return ""
    try:
        return template.format_map(_SafeDict(vars))
    except (IndexError, ValueError) as e:
        console.err(f"template 解析失敗: {e}",
                    "檢查 {episode:02d} 等格式是否正確")


def build_previous_link_block(episodes: list[dict], current_episode: int) -> str:
    """Pick the previous episode and render a one-line YouTube link block."""
    prev = [e for e in episodes if e["episode"] < current_episode]
    if not prev:
        return ""
    p = max(prev, key=lambda e: e["episode"])
    return f"上集回顧：〈{p['title']}〉https://youtu.be/{p['video_id']}\n"


def cmd_apply(args) -> int:
    data = load_series(args.id)

    # Resolve next-episode title — explicit > looking up in series episodes
    next_title = args.next_title or ""
    if not next_title:
        nxt = [e for e in data["episodes"] if e["episode"] > args.episode]
        if nxt:
            n = min(nxt, key=lambda e: e["episode"])
            next_title = n["title"]

    template_vars = {
        "episode": args.episode,
        "next_episode": args.episode + 1,
        "previous_episode": args.episode - 1,
        "episode_title": args.episode_title,
        "episode_summary": args.summary or "",
        "next_episode_title": next_title,
        "previous_link_block": build_previous_link_block(data["episodes"], args.episode),
    }

    title = render_template(data["title_template"], template_vars)[:100]

    if args.description_file:
        # Allow user to override description with a file
        path = Path(args.description_file)
        if not path.exists():
            console.err(f"description-file 不存在: {path}", "")
        description = path.read_text(encoding="utf-8")
    else:
        description = render_template(data["description_template"], template_vars)
    description = description[:5000]

    tags = list(data.get("tags", []))
    if args.add_tags:
        for t in (x.strip() for x in args.add_tags.split(",") if x.strip()):
            if t not in tags:
                tags.append(t)

    privacy = args.privacy or data.get("privacy", "public")
    language = args.language or data.get("language", "zh-TW")
    category = args.category or data.get("category", "22")
    playlist = args.playlist or data.get("playlist", "")

    if args.dry_run:
        console.info("=== series apply DRY RUN ===")
        console.info(f"series:   {args.id}")
        console.info(f"episode:  {args.episode}")
        console.info(f"title:    {title}")
        console.info(f"playlist: {playlist}")
        console.info(f"privacy:  {privacy}")
        console.info(f"tags:     {', '.join(tags)}")
        console.info(f"language: {language}")
        console.info(f"category: {category}")
        console.info("--- description ---")
        console.info(description)
        console.info("--- end description ---")
        if args.video:
            console.info(f"video:    {args.video}")
        if args.thumbnail:
            console.info(f"thumbnail: {args.thumbnail}")
        if args.caption:
            console.info(f"caption:  {args.caption}")
        return 0

    if not args.video:
        console.err("--video 必填（除非 --dry-run）", "")

    # Write description to a temp file and call youtube_upload.py
    desc_file = plugin_data_dir() / f"_series_apply_desc_{args.id}_ep{args.episode}.txt"
    desc_file.write_text(description, encoding="utf-8")

    upload_script = plugin_root() / "bin" / "youtube_upload.py"
    cmd = [
        sys.executable, str(upload_script),
        "--file", str(args.video),
        "--title", title,
        "--description-file", str(desc_file),
        "--tags", ",".join(tags),
        "--privacy", privacy,
        "--category", category,
        "--language", language,
    ]
    if playlist:
        cmd += ["--playlist", playlist]
    if args.thumbnail:
        cmd += ["--thumbnail", str(args.thumbnail)]
    if args.caption:
        cmd += ["--caption", str(args.caption)]
    if args.publish_at:
        cmd += ["--publish-at", args.publish_at]
    if args.for_kids:
        cmd += ["--for-kids"]

    console.info(f"→ 透過 youtube_upload.py 上傳…")
    console.info(f"  title: {title}")
    console.info(f"  playlist: {playlist}")
    console.info("")

    proc = subprocess.run(cmd, capture_output=True, text=True)
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)

    desc_file.unlink(missing_ok=True)

    if proc.returncode != 0:
        console.err(f"upload 失敗 (rc={proc.returncode})", "看上面的錯誤訊息")

    # Parse video_id from upload output
    video_id = None
    for line in proc.stdout.splitlines():
        if "video_id=" in line:
            video_id = line.split("video_id=", 1)[1].strip()
            break

    if video_id and not args.no_record:
        rec = {
            "episode": args.episode,
            "title": args.episode_title,
            "video_id": video_id,
            "uploaded_at": datetime.now().isoformat(timespec="seconds"),
        }
        if args.summary:
            rec["summary"] = args.summary
        data["episodes"] = [e for e in data["episodes"] if e["episode"] != args.episode]
        data["episodes"].append(rec)
        data["episodes"].sort(key=lambda e: e["episode"])
        save_series(args.id, data)
        console.ok(f"recorded into series: EP{args.episode:02d} = {video_id}")

    return 0


# ---------------- main ----------------

def main():
    p = argparse.ArgumentParser(
        description="Series template manager for yc-plugin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 建立 series
  python youtube_series.py init her-bet --name "床前故事｜她的賭注" \\
    --playlist "她的賭注" --tags "床前故事,她的賭注,有聲書"

  # 列出所有 series
  python youtube_series.py list

  # 看 series 內容
  python youtube_series.py show her-bet

  # 把已上傳的 ep01 補登進 series
  python youtube_series.py add-episode her-bet --episode 1 \\
    --episode-title "她說喜歡我，是因為賭輸了" --video-id Y6ytntuQTgM

  # 用 series 上傳 ep02（自動套標題、描述、tags、playlist）
  python youtube_series.py apply her-bet --episode 2 \\
    --episode-title "她寫了二十四封信，他全沒拆" \\
    --summary "..." \\
    --video stories/wb_ep02_letters/final.mp4 \\
    --thumbnail stories/wb_ep02_letters/cover.jpeg \\
    --caption stories/wb_ep02_letters/subtitles.srt
""",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="建立新 series 模板")
    pi.add_argument("id", help="series id (URL-safe，e.g. her-bet)")
    pi.add_argument("--name")
    pi.add_argument("--playlist")
    pi.add_argument("--title-template")
    pi.add_argument("--description-template")
    pi.add_argument("--tags")
    pi.add_argument("--language")
    pi.add_argument("--privacy", choices=["public", "unlisted", "private"])
    pi.add_argument("--category")
    pi.add_argument("--force", action="store_true", help="覆寫既有 series")

    pl = sub.add_parser("list", help="列出所有 series")

    ps = sub.add_parser("show", help="印出 series 內容")
    ps.add_argument("id")

    pd = sub.add_parser("delete", help="刪除 series")
    pd.add_argument("id")
    pd.add_argument("--force", action="store_true")

    pae = sub.add_parser("add-episode", help="補登已上傳的影片到 series 紀錄")
    pae.add_argument("id")
    pae.add_argument("--episode", type=int, required=True)
    pae.add_argument("--episode-title", required=True)
    pae.add_argument("--video-id", required=True)
    pae.add_argument("--summary")
    pae.add_argument("--uploaded-at")

    pa = sub.add_parser("apply", help="用 series 模板上傳一集")
    pa.add_argument("id")
    pa.add_argument("--episode", type=int, required=True)
    pa.add_argument("--episode-title", required=True)
    pa.add_argument("--summary", help="本集摘要（用於 {episode_summary}）")
    pa.add_argument("--next-title", help="下集標題（給描述模板的 {next_episode_title}）；"
                    "不指定會從已記錄的 episodes 找比 N 大的最近一集")
    pa.add_argument("--video", help="影片檔案路徑")
    pa.add_argument("--thumbnail")
    pa.add_argument("--caption")
    pa.add_argument("--description-file", help="覆寫描述（不用模板）")
    pa.add_argument("--add-tags", help="追加 tags（在 series 預設 tags 之上）")
    pa.add_argument("--playlist", help="覆寫 series 預設 playlist")
    pa.add_argument("--privacy", choices=["public", "unlisted", "private"])
    pa.add_argument("--language")
    pa.add_argument("--category")
    pa.add_argument("--publish-at")
    pa.add_argument("--for-kids", action="store_true")
    pa.add_argument("--no-record", action="store_true",
                    help="上傳成功後不要把 video_id 記回 series")
    pa.add_argument("--dry-run", action="store_true")

    args = p.parse_args()
    console.init()

    handlers = {
        "init": cmd_init,
        "list": cmd_list,
        "show": cmd_show,
        "delete": cmd_delete,
        "add-episode": cmd_add_episode,
        "apply": cmd_apply,
    }
    sys.exit(handlers[args.cmd](args))


if __name__ == "__main__":
    main()
