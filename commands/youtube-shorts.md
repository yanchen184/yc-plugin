---
description: 從橫式影片切 9:16 直式 Shorts 片段（≤60s），可燒字幕，可一條龍上傳
argument-hint: --video PATH --start 5:30 [--duration 30] [--style blur-bg|pillarbox|zoom] [--add-caption SRT] [--upload --title "..."]
---

# /youtube-shorts

把長集數中的高潮片段抓出來，轉成 1080×1920 直式，給 YouTube Shorts feed 引流用。

需要 `ffmpeg` 在 PATH（macOS: `brew install ffmpeg`，Ubuntu: `sudo apt install ffmpeg`）。

## Parse arguments

| Flag | 必填 | 說明 |
|------|------|------|
| `--video PATH` | ✓ | 原始橫式影片 |
| `--start TS` | ✓ | 起始時間，例 `5:30` / `00:05:30` / 純秒數 |
| `--duration N` | | 片段秒數（≤60，預設 30）|
| `--style blur-bg/pillarbox/zoom` | | 9:16 轉換風格（預設 blur-bg）|
| `--add-caption PATH` | | SRT 字幕，會自動抽該時段 burn-in |
| `--output PATH` | | 預設 `<video>_short_<start>s.mp4` |
| `--upload` | | 切完直接上傳成 Short |
| `--title T` | （--upload 時必填）| 自動加 `#Shorts` |
| `--privacy` `--tags` `--playlist` | | 上傳用 metadata |

## 三種 style 怎麼選

- **blur-bg**（推薦，預設）：模糊背景 + 中間清晰 16:9，最 cinematic
- **pillarbox**：上下黑邊，乾淨但偏老氣
- **zoom**：直接裁中央 9:16，畫面緊但會切掉左右兩邊

故事 / 有聲書頻道 → blur-bg。
教學 / 主講人對鏡頭 → zoom（讓臉填滿）。
複雜畫面 / 信息圖 → pillarbox（保完整）。

## Workflow

### 純切片（不上傳）

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/youtube_shorts.py" $ARGUMENTS
```

切完印 `[OK] short ready: <path>`。把路徑給 user，建議他先預覽 mp4 確認再決定要不要上傳。

### 切片 + 上傳

如果 `$ARGUMENTS` 已含 `--upload --title "..."`：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/youtube_shorts.py" $ARGUMENTS
```

腳本會切完自動 fork 給 `youtube_upload.py` 上傳，並在 title 自動加 `#Shorts` 後綴（如果沒帶）。把上傳完的 URL 給 user。

### 主動建議

如果 user 給了一支長影片但沒指定 start：

> 你想抓哪個片段做 Short？建議先想：
> - 最戲劇的對白 / 反轉時刻
> - 最有疑問句的開場（"為什麼..."、"妳知道嗎..."）
> - 30s 內聽完還想知道下文的 cliffhanger
>
> 給我時間戳（例 `5:30`）+ 長度（建議 20-40s）。

## Constraints

- duration > 60s 會印 warn — Shorts 上限 60s，超過 YouTube 不會放進 Shorts feed
- 字幕燒入會挑該時段內的 cues、time-shift 到 t=0
- 如果該時段沒對應字幕 → 不燒、印 warn
- 上傳走 `--no-auto-caption`（短片字幕已 burn-in，不需要再傳 SRT track）
- ffmpeg 缺失會 fail fast 並提示安裝指令
