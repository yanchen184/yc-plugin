---
description: 一鍵上傳影片到 YouTube。OAuth 自動處理，第一次跑會引導你做 ~3 分鐘的 Google Cloud Console 設定。
argument-hint: <video_path> [title]
---

# /youtube-upload

Upload a video to YouTube.

## Parse arguments

`$ARGUMENTS` may contain:
- A video file path (required, first non-flag token)
- An optional title in quotes after the path

Examples the user might type:
- `/youtube-upload D:/videos/ep1.mp4`
- `/youtube-upload D:/videos/ep1.mp4 "EP1 校園愛情故事"`
- `/youtube-upload ./final.mp4 "My Video"`

## Workflow

### Step 1 — Verify the video exists

Run `Read` or `Bash ls` on the video path. If the file is missing, ask the user for the correct path. Stop until they give a real one.

### Step 2 — Check setup state

Look for `~/.claude/plugins/data/yc-plugin/.env` (Linux/Mac) or `%USERPROFILE%\.claude\plugins\data\yc-plugin\.env` (Windows).

**If `.env` exists**, skip to Step 4.

**If `.env` is missing**, do Step 3 first.

### Step 3 — First-time setup (only if .env missing)

Tell the user:

> 第一次使用 yc-plugin，需要先做一次 Google Cloud Console 的 OAuth 設定（~3 分鐘，一次性）。
>
> 步驟：
> 1. 打開 https://console.cloud.google.com/
> 2. 建一個新 project（任意名字，例如 yc-plugin）
> 3. APIs & Services → Library → 搜「YouTube Data API v3」→ Enable
> 4. APIs & Services → OAuth consent screen → External → Create
>    填 App name / Support email / Developer contact，下一步
>    Test users 加你自己的 Gmail，完成
> 5. APIs & Services → Credentials → Create Credentials → OAuth client ID
>    Application type 選 Desktop app → Create → Download JSON
> 6. 把下載的 JSON 檔放到你常用的位置（例如 `~/Documents/youtube_client_secret.json`）
>
> 拿到 JSON 檔後，告訴我它的「絕對路徑」。

After the user provides the path, run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/bin/setup.py" --client-secret "<USER_PROVIDED_PATH>"
```

If exit code is non-zero, show the user the error message — usually the path is wrong or the JSON is the wrong format. Help them fix and re-run.

If exit 0, confirm: "✓ 設定完成。第一次跑會跳出瀏覽器要 Google 登入，按 Allow 即可。" Continue to Step 4.

### Step 4 — Gather metadata if needed

If the user did NOT supply a title in `$ARGUMENTS`, ask in one batched text message:

> 上傳前確認：
> - 標題（按 enter 用檔名 `<filename_stem>`）：
> - 隱私（public / unlisted / private，按 enter 用 .env 預設）：
> - 描述（可貼長文，或輸入 skip 跳過）：
> - Tags（逗號分隔，按 enter 用 .env 預設）：

Skip this batch if the user already gave a title — assume `.env` defaults for the rest.

### Step 5 — Run the upload

```bash
python "${CLAUDE_PLUGIN_ROOT}/bin/youtube_upload.py" \
  --file "<VIDEO_PATH>" \
  [--title "<TITLE>"] \
  [--privacy "<PRIVACY>"] \
  [--description "<DESC>" | --description-file <PATH>] \
  [--tags "<TAGS>"]
```

Use `run_in_background: true` because uploads of large files take minutes (network speed × file size). Use `Monitor` on the output file with grep pattern `upload:|UPLOADED|processing:|⚠|error|failed` to surface progress.

### Step 6 — Surface result

When the script prints `url: https://youtu.be/...`, share that URL with the user. Mention:
- Privacy status (if `unlisted`, remind them to flip to public in YouTube Studio when ready)
- Processing status — if `succeeded`, video is playable now; if `timeout`, processing continues server-side and will finish on its own

## Constraints

- **Never** echo or log the contents of `client_secret.json` or `yt_token.json`.
- If the upload script returns non-zero, show the last 20 lines of stderr.
- This is single-user single-channel. Don't add multi-account UX.
- The `setup.py` script handles all `.env` writing — never write `.env` from the command directly. This avoids inconsistent escaping on Windows paths.
