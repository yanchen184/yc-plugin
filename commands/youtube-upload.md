---
description: 一鍵上傳影片到 YouTube。支援封面、排程、播放清單、字幕，OAuth 自動處理。
argument-hint: <video_path> [title]
---

# /youtube-upload

完整的 YouTube 影片上傳流程。第一次使用會引導 Google Cloud Console OAuth 設定（~3 分鐘）。

## Parse arguments

`$ARGUMENTS` 第一個非旗標 token 是影片路徑，引號內是標題。

範例：
- `/youtube-upload D:/videos/ep1.mp4`
- `/youtube-upload D:/videos/ep1.mp4 "EP1 校園愛情故事"`

## Workflow

### Step 1 — Verify the video file

確認 `<video_path>` 存在。不存在就請使用者修正路徑後再試。

### Step 2 — Check setup state

跑 `python "${CLAUDE_PLUGIN_ROOT}/bin/setup.py" --show` 確認 client_secret 已安裝。

如果 `client_secret.json: (missing)`，跳到 Step 3。否則跳到 Step 4。

### Step 3 — First-time setup (only if missing)

告訴使用者：

> 第一次用，需要 Google Cloud Console 的 OAuth credential（一次性 ~3 分鐘）。
>
> 1. 打開 https://console.cloud.google.com/
> 2. 建一個 project（任意名字，例如 yc-plugin）
> 3. APIs & Services → Library → 搜「YouTube Data API v3」→ Enable
> 4. APIs & Services → OAuth consent screen → External → Create
>    填 App name / Support email / Developer contact
>    Test users 加你自己的 Gmail
> 5. APIs & Services → Credentials → Create Credentials → OAuth client ID
>    Application type 選 Desktop app → Create → Download JSON
>
> 拿到 JSON 檔後，告訴我絕對路徑。

收到路徑後，跑：

```bash
python "${CLAUDE_PLUGIN_ROOT}/bin/setup.py" --client-secret "<USER_PROVIDED_PATH>"
```

非零結束就把錯誤訊息給使用者並協助修正。

### Step 4 — Gather metadata interactively

如果 `$ARGUMENTS` 已含標題，使用者可能想直接送出，**仍應先問下面這些選項**（除非使用者明說「全部用預設」）。

問一次包含全部欄位（**不要分多次問**），讓使用者一次答完：

```
上傳前確認（不填就用預設）:

1. 標題: <filename_stem>
2. 描述: (可貼長文，最多 5000 字)
3. Tags: (逗號分隔，例如 "校園,廣播劇,有聲故事")
4. 隱私: unlisted (其他選項: public / private)
5. 封面圖: (路徑，jpg/png ≤2MB；按 enter 跳過)
6. 排程發布: (例如 "2026-05-10 20:00"；按 enter 立即發布)
7. 播放清單: (名稱會自動建立，或 playlist ID；按 enter 跳過)
8. 字幕檔: 自動偵測同名 .srt/.vtt（找到: <auto-detected>；如果不要請說「不要字幕」）
9. 兒童內容: 否（如果是請說「是」）
```

**自動偵測規則**：
- 同目錄下 `<video_basename>.srt` 或 `.vtt` 自動列出來
- 同目錄下 `cover.jpg`、`thumbnail.jpg`、`<video_basename>.jpg` 自動建議
- 描述若 user 說「AI 寫」，從影片字幕檔讀內容後自動草擬一段，給 user 確認

### Step 5 — Show dry-run + confirm

跑 dry-run 把要送的 metadata payload 印給使用者看：

```bash
python "${CLAUDE_PLUGIN_ROOT}/bin/youtube_upload.py" \
  --file "<VIDEO>" --title "<T>" --description "<D>" \
  --tags "<TAGS>" --privacy "<P>" \
  [--thumbnail "<THUMB>"] [--playlist "<PL>"] \
  [--publish-at "<TIME>"] [--for-kids] \
  --dry-run
```

把 JSON 給使用者看，問一句：「以上正確嗎？我送出？」

得到肯定回覆後，去掉 `--dry-run` 跑同一條指令。

### Step 6 — Run the upload

```bash
python "${CLAUDE_PLUGIN_ROOT}/bin/youtube_upload.py" \
  --file "<VIDEO>" \
  ... (所有 user 確認過的 flags)
```

用 `run_in_background: true`，因為大檔上傳要幾分鐘。同時用 `Monitor` 看 stdout，grep pattern：`upload:|UPLOADED|processing:|\[OK\]|\[WARN\]|\[ERROR\]|DONE →|url:`

### Step 7 — Surface result

當看到 `DONE → https://youtu.be/...` 時把 URL 給使用者。

提醒：
- 如果是 `unlisted` 或排程：影片需要在 YouTube Studio 確認狀態
- 如果處理 timeout：YouTube 還在處理，幾分鐘後就好
- 如果有警告（例如 thumbnail 403 因為頻道未驗證）：告訴使用者怎麼解

## Constraints

- **絕不** echo `client_secret.json` 或 `yt_token.json` 內容
- 上傳腳本失敗就把它印出的錯誤訊息給使用者，**不要包裝**或 `自行解讀`
- 所有 setup 都透過 `bin/setup.py` 處理，不要手動 copy 檔案
- 大檔上傳一定 background + Monitor，不要前景 block 對話
