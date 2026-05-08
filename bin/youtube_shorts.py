#!/usr/bin/env python3
"""yc-plugin: extract a vertical 9:16 Shorts clip from a horizontal video.

Cuts a 15-60s segment, converts to 9:16 (1080×1920), optionally overlays
a subset of an SRT file, and optionally uploads to YouTube as a Short.

Three vertical-conversion styles:
  - blur-bg (default): blurred 16:9 background + sharp 16:9 in middle
  - pillarbox:        16:9 in middle, black bars top+bottom
  - zoom:             crop to 9:16 strip from center

CLI: python youtube_shorts.py --help
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from lib import console
from lib.paths import plugin_root


def _which_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if not found:
        console.err(
            "ffmpeg 不在 PATH — 這個指令需要 ffmpeg 來剪片",
            "macOS: brew install ffmpeg | Ubuntu: sudo apt install ffmpeg | "
            "Windows: https://ffmpeg.org/download.html",
        )
    return found


def _which_ffprobe() -> str:
    return shutil.which("ffprobe") or "ffprobe"


def parse_timestamp(s: str) -> float:
    """Accept '330', '5:30', '00:05:30', '00:05:30.5'."""
    s = str(s).strip()
    if ":" not in s:
        return float(s)
    parts = s.split(":")
    try:
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    except ValueError:
        pass
    raise ValueError(f"無法解析時間戳: {s}（用 'M:SS' 或 'H:MM:SS' 或純秒數）")


def fmt_srt_ts(t: float) -> str:
    if t < 0:
        t = 0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def parse_srt_ts(s: str) -> float:
    """'00:05:30,123' → 330.123s"""
    s = s.replace(",", ".").strip()
    h, m, rest = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def srt_subset(srt_path: Path, start: float, duration: float) -> str:
    """Extract the cues in [start, start+duration] from the SRT, time-shifted to t=0."""
    end = start + duration
    text = srt_path.read_text(encoding="utf-8")
    blocks = text.strip().split("\n\n")
    out_blocks = []
    idx = 0
    for blk in blocks:
        lines = blk.strip().splitlines()
        if len(lines) < 3:
            continue
        # lines[0] = number, lines[1] = "HH:MM:SS,mmm --> HH:MM:SS,mmm", lines[2:] = text
        try:
            ts_line = lines[1]
            tstart_s, tend_s = ts_line.split(" --> ")
            cue_start = parse_srt_ts(tstart_s)
            cue_end = parse_srt_ts(tend_s)
        except ValueError:
            continue
        if cue_end <= start or cue_start >= end:
            continue
        new_start = max(0.0, cue_start - start)
        new_end = min(duration, cue_end - start)
        if new_end <= new_start:
            continue
        idx += 1
        body = "\n".join(lines[2:])
        out_blocks.append(f"{idx}\n{fmt_srt_ts(new_start)} --> {fmt_srt_ts(new_end)}\n{body}")
    return "\n\n".join(out_blocks) + ("\n" if out_blocks else "")


# ---- vertical filter graphs (output 1080x1920) ----

def vf_blur_bg(burn_srt: str | None, font_size: int, font: str) -> tuple[str, str]:
    parts = [
        "[0:v]split[bgsrc][fgsrc];",
        "[bgsrc]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=30[bg];",
        "[fgsrc]scale=1080:-2[fg];",
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[v]",
    ]
    chain = "".join(parts)
    if burn_srt:
        style = (
            f"FontName={font},FontSize={font_size},"
            "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            "BorderStyle=1,Outline=3,Shadow=0,"
            "MarginV=120,MarginL=60,MarginR=60,Alignment=2"
        )
        srt_escaped = burn_srt.replace(":", r"\:")
        chain += f";[v]subtitles={srt_escaped}:force_style='{style}'[vout]"
        return chain, "[vout]"
    return chain, "[v]"


def vf_pillarbox(burn_srt: str | None, font_size: int, font: str) -> tuple[str, str]:
    chain = "[0:v]scale=1080:-2,pad=1080:1920:0:(1920-ih)/2:black[v]"
    if burn_srt:
        style = (
            f"FontName={font},FontSize={font_size},"
            "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            "BorderStyle=1,Outline=3,Shadow=0,"
            "MarginV=200,MarginL=60,MarginR=60,Alignment=2"
        )
        srt_escaped = burn_srt.replace(":", r"\:")
        chain += f";[v]subtitles={srt_escaped}:force_style='{style}'[vout]"
        return chain, "[vout]"
    return chain, "[v]"


def vf_zoom(burn_srt: str | None, font_size: int, font: str) -> tuple[str, str]:
    chain = "[0:v]crop=ih*9/16:ih,scale=1080:1920[v]"
    if burn_srt:
        style = (
            f"FontName={font},FontSize={font_size},"
            "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            "BorderStyle=1,Outline=3,Shadow=0,"
            "MarginV=120,MarginL=60,MarginR=60,Alignment=2"
        )
        srt_escaped = burn_srt.replace(":", r"\:")
        chain += f";[v]subtitles={srt_escaped}:force_style='{style}'[vout]"
        return chain, "[vout]"
    return chain, "[v]"


STYLE_FNS = {"blur-bg": vf_blur_bg, "pillarbox": vf_pillarbox, "zoom": vf_zoom}


def main():
    p = argparse.ArgumentParser(
        description="Extract a YouTube Shorts (9:16, ≤60s) clip from a horizontal video",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 從 ep01 第 5:30 開始切 30 秒
  python youtube_shorts.py --video ep01.mp4 --start 5:30 --duration 30

  # 帶字幕（從原 SRT 抽對應時段）
  python youtube_shorts.py --video ep01.mp4 --start 5:30 --duration 45 \\
    --add-caption ep01.srt

  # 不同 vertical 風格
  python youtube_shorts.py --video ep01.mp4 --start 0:30 --duration 20 --style pillarbox
  python youtube_shorts.py --video ep01.mp4 --start 0:30 --duration 20 --style zoom

  # 直接上傳成 Short
  python youtube_shorts.py --video ep01.mp4 --start 5:30 --duration 30 \\
    --add-caption ep01.srt \\
    --upload --title "預告：她的賭注 EP01 #Shorts" --privacy public
""",
    )
    p.add_argument("--video", required=True, help="原始影片（橫式）")
    p.add_argument("--start", required=True, help="起始時間，例 '5:30' 或 '00:05:30' 或秒數")
    p.add_argument("--duration", type=float, default=30,
                   help="片段秒數（最多 60，預設 30）")
    p.add_argument("--style", choices=list(STYLE_FNS), default="blur-bg",
                   help="9:16 轉換風格")
    p.add_argument("--output", help="輸出檔；預設 <video>_short_<start>.mp4")
    p.add_argument("--add-caption", help="字幕 SRT（會 burn-in 到對應時段）")
    p.add_argument("--font", default="WenQuanYi Zen Hei")
    p.add_argument("--font-size", type=int, default=18)
    p.add_argument("--upload", action="store_true",
                   help="完成後直接走 youtube_upload.py 上傳成 Short")
    p.add_argument("--title", help="上傳用標題（含 #Shorts 自動加）")
    p.add_argument("--description", default="", help="上傳用描述")
    p.add_argument("--tags", default="", help="上傳用 tags")
    p.add_argument("--privacy", choices=["public", "unlisted", "private"], default="unlisted")
    p.add_argument("--playlist", help="加到的 playlist 名/ID")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    console.init(verbose=args.verbose)

    if args.duration > 60:
        console.warn(f"duration={args.duration}s > 60s — YouTube Shorts 上限 60 秒，會被當一般影片")
    if args.duration < 1:
        console.err("duration 太短", "至少 1 秒")

    video = Path(args.video)
    if not video.exists():
        console.err(f"video not found: {video}", "確認路徑")

    try:
        start = parse_timestamp(args.start)
    except ValueError as e:
        console.err(str(e), "")

    out = Path(args.output) if args.output else video.with_name(
        f"{video.stem}_short_{int(start)}s.mp4"
    )

    # SRT subset (if provided)
    burn_srt_path: str | None = None
    tmp_srt: Path | None = None
    if args.add_caption:
        srt = Path(args.add_caption)
        if not srt.exists():
            console.err(f"caption not found: {srt}", "")
        subset = srt_subset(srt, start, args.duration)
        if not subset.strip():
            console.warn("該時段沒有對應字幕 — 不燒字幕")
        else:
            tmp_srt = Path(tempfile.mktemp(suffix=".srt", prefix="yc_short_"))
            tmp_srt.write_text(subset, encoding="utf-8")
            burn_srt_path = str(tmp_srt)

    filter_complex, last_label = STYLE_FNS[args.style](burn_srt_path, args.font_size, args.font)

    ffmpeg = _which_ffmpeg()
    cmd = [
        ffmpeg, "-y",
        "-ss", str(start),
        "-t", str(args.duration),
        "-i", str(video),
        "-filter_complex", filter_complex,
        "-map", last_label,
        "-map", "0:a:0?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-r", "30",
        "-movflags", "+faststart",
        str(out),
    ]
    console.info(f"→ ffmpeg 處理中… ({args.style}, {args.duration}s @ {start}s)")
    if args.verbose:
        console.info(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if tmp_srt:
        tmp_srt.unlink(missing_ok=True)
    if result.returncode != 0:
        console.err(f"ffmpeg failed (rc={result.returncode})", "看下面 stderr")
        print(result.stderr[-2000:], file=sys.stderr)
        sys.exit(1)

    out_size = out.stat().st_size
    console.ok(f"short ready: {out} ({out_size // 1024} KB)")

    if not args.upload:
        console.info(f"預覽：{out}")
        return

    # ---- 自動上傳 ----
    if not args.title:
        console.err("--upload 需要 --title", "")
    title = args.title
    if "#shorts" not in title.lower():
        title = f"{title} #Shorts"

    upload_script = plugin_root() / "bin" / "youtube_upload.py"
    cmd = [
        sys.executable, str(upload_script),
        "--file", str(out),
        "--title", title,
        "--privacy", args.privacy,
        "--description", args.description or title,
        "--no-auto-caption",
    ]
    if args.tags:
        cmd += ["--tags", args.tags]
    if args.playlist:
        cmd += ["--playlist", args.playlist]

    console.info(f"→ 上傳成 Short…")
    result = subprocess.run(cmd, text=True)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
