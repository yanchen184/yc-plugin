---
description: Upload a video to YouTube via Google's official API. OAuth handled automatically.
argument-hint: <video_path> [title]
---

# /youtube-upload

Upload a video file to YouTube.

## Arguments

`$ARGUMENTS` may contain:
- A video file path (required) — absolute or relative
- An optional title in quotes after the path

Examples the user might type:
- `/youtube-upload D:/videos/ep1.mp4`
- `/youtube-upload D:/videos/ep1.mp4 "EP1 校園愛情故事"`
- `/youtube-upload ./final.mp4 "My Video"`

## Behavior

### Step 1 — First-time setup check

Before doing anything else, check whether `${CLAUDE_PLUGIN_DATA}/.env` exists.

**If `.env` is missing → walk the user through setup, do NOT upload yet.**

Use AskUserQuestion (or plain text prompt if AskUserQuestion is unavailable) to ask:

> 第一次使用 yc-plugin 的 youtube-upload，需要你提供 OAuth client_secret.json 的路徑。
>
> 還沒有的話，先去拿一份（一次性，~3 分鐘）：
> 1. 開 https://console.cloud.google.com/
> 2. 建一個 project（任意名字）
> 3. APIs & Services → Library → 搜 "YouTube Data API v3" → Enable
> 4. APIs & Services → OAuth consent screen → External → 填基本資料 → 把自己加進 Test users
> 5. APIs & Services → Credentials → Create Credentials → OAuth client ID → Desktop app
> 6. 下載 JSON
>
> 拿到了之後，把 JSON 檔案的絕對路徑貼給我（例如 `C:/Users/you/Downloads/client_secret_xxx.json`）。

After the user provides the path:

1. Verify the file exists. If not, tell them and stop.
2. Read `.env.example` from `${CLAUDE_PLUGIN_ROOT}/.env.example`.
3. Substitute `YOUTUBE_CLIENT_SECRET_PATH=` with the user's path.
4. Write the result to `${CLAUDE_PLUGIN_DATA}/.env` (create the directory if needed).
5. Confirm to the user: "已寫入 `${CLAUDE_PLUGIN_DATA}/.env`. 之後不會再問。"
6. Continue to Step 2.

### Step 2 — Verify the video file

Confirm `<video_path>` exists. If missing, ask the user to fix the path.

### Step 3 — Gather metadata if needed

If the user did NOT supply a title in `$ARGUMENTS`, and this looks like a real upload (not a smoke test), ask in one batched question:

- Title (default = filename stem)
- Privacy: public / unlisted / private (default from `.env`)
- Description (or "skip")
- Tags (comma-separated, default from `.env`)

Skip this question if the user already gave a title — assume `.env` defaults for the rest.

### Step 4 — Run the upload

```bash
python "${CLAUDE_PLUGIN_ROOT}/bin/youtube_upload.py" \
  --file "<VIDEO_PATH>" \
  --title "<TITLE>" \
  --privacy "<PRIVACY>" \
  [--description "<DESC>" | --description-file <PATH>] \
  [--tags "<TAGS>"]
```

Use `run_in_background: true` because uploads of large files take minutes. Wait for the background-task completion notification.

**On first run after setup**, the script pops a browser tab for Google login. Tell the user this will happen so they're ready to click "Allow".

### Step 5 — Surface the result

Print the `url:` line from the script output and the privacy status. Remind the user that `unlisted` videos need to be made public manually in YouTube Studio if they want them discoverable.

## Constraints

- Never log or echo the contents of `client_secret.json` or `yt_token.json`.
- If the upload script returns a non-zero exit, show the last 20 lines of its stderr.
- Don't add multi-account UX — one user, one channel, simple.
