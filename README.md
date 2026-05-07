# yc-plugin

A Claude Code plugin for personal content workflows.

Currently ships:

- **`/youtube-upload`** — Upload a video to YouTube via Google's official API. OAuth handled automatically; first run pops a browser for one-click Google login, after that it's silent.

## Install

```
/plugin marketplace add yanchen184/yc-plugin
/plugin install yc-plugin@yc-plugin
```

## First-time setup

The first time you run `/youtube-upload`, the plugin will walk you through getting a Google OAuth credential — about 3 minutes, one-time.

If you want to do it ahead of time:

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (any name)
3. **APIs & Services → Library** → search "YouTube Data API v3" → **Enable**
4. **APIs & Services → OAuth consent screen** → **External** → fill the basics → add yourself as a Test user (Google verification not required for personal use)
5. **APIs & Services → Credentials → Create Credentials → OAuth client ID** → application type **Desktop app** → name it anything → **Create**
6. **Download JSON.** Save the file somewhere safe (e.g. `~/Documents/youtube_client_secret.json`).

The first time you run `/youtube-upload`, give Claude that file path. Claude will save the config to your plugin data dir; it never enters git.

## Usage

```
/youtube-upload <video_path> [title]
```

Examples:

```
/youtube-upload D:/videos/episode_1.mp4
/youtube-upload D:/videos/episode_1.mp4 "EP1 — Title"
```

Without a title, the script uses the filename. Description, tags, and privacy fall back to `.env` defaults unless overridden in the conversation.

### Direct CLI usage (no Claude)

```bash
python ~/.claude/plugins/installed/yc-plugin/bin/youtube_upload.py \
  --file path/to/video.mp4 \
  --title "My Title" \
  --privacy unlisted
```

## Files

- `commands/youtube-upload.md` — slash command definition (Claude reads this)
- `bin/youtube_upload.py` — main upload script
- `bin/youtube_auth.py` — standalone OAuth bootstrap (rarely needed)
- `.env.example` — template for the config file Claude writes during setup

## Privacy

This repo contains **no secrets**. Your OAuth credentials live in `~/.claude/plugins/data/yc-plugin/` on your machine and are never uploaded anywhere.

## License

MIT — share and remix freely.
