---
description: 改現有 YouTube 影片的標題、描述、tags、隱私、播放清單、封面、字幕，不用重新上傳
argument-hint: "--video-id ID [--title T] [--description D] [--tags ...] [--privacy ...] [--add-to-playlist NAME] [--thumbnail PATH]"
---

# /youtube-update

更新已上傳影片的 metadata。**不重新上傳影片本身**，只改 metadata + 可選的封面/字幕/playlist。

## Parse arguments

`--video-id` 必填。其他 flag 至少要一個：

| Flag | 作用 |
|------|------|
| `--title T` | 改標題 |
| `--description D` 或 `--description-file PATH` | 改描述 |
| `--tags "a,b,c"` | **取代**整個 tags |
| `--add-tags "x,y"` | 在現有 tags 上加 |
| `--remove-tags "z"` | 從現有 tags 移除 |
| `--privacy public/unlisted/private` | 改隱私 |
| `--add-to-playlist NAME` / `--remove-from-playlist NAME` | 進/出 playlist |
| `--thumbnail PATH` | 換封面 |
| `--caption PATH` | 加字幕（新增 caption track，不取代現有）|
| `--for-kids` / `--not-for-kids` | 兒童內容旗標 |
| `--dry-run` | 只看 payload 不真改 |

## Workflow

### Step 1 — 預覽

第一輪一定要跑 `--dry-run`，把要改的 payload 給 user 看：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/youtube_update.py" $ARGUMENTS --dry-run
```

把 JSON 顯示給 user，問一句：「以上正確嗎？我送出？」

### Step 2 — 真改

得到肯定回覆才跑（去掉 `--dry-run`）：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/youtube_update.py" $ARGUMENTS
```

成功訊息會印 `[OK] metadata updated: <id>` + `DONE → https://youtu.be/<id>`，把 URL 給 user。

### 特殊情況

- 如果 user 不確定 video_id：先建議跑 `/youtube-list` 找
- 如果只想加 tag 不改其他：建議用 `--add-tags` 而不是 `--tags`，避免不小心刪掉現有 tags
- 如果要改隱私從 unlisted → public（剛上完想 promote）：直接 `--privacy public`，不用其他

## Constraints

- **絕對先跑 `--dry-run`**，metadata 改錯影響觀眾體驗（搜尋變差、playlist 錯位）
- 不要只改 description 不告訴 user 新舊差異 — 預覽時要列明
- 失敗時把錯誤完整轉達；常見：HTTP 403 = 影片不是這帳號的；HTTP 404 = video_id 錯
