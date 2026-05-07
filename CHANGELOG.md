# Changelog

All notable changes to yc-plugin documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Planned
- `/youtube-list` — list channel uploads
- `/youtube-update` — update title / description / privacy on existing video
- `/youtube-thumbnail` — set custom thumbnail

## [0.2.0] — 2026-05-07

### Added
- `bin/setup.py` — interactive first-time setup script
- `bin/install_deps.py` + `hooks/hooks.json` — auto pip install on SessionStart
- `requirements.txt` — Python dependencies declared
- Resumable upload with exponential backoff (handles network drops, 429/500/503 retries)
- Post-upload verify: polls YouTube API to confirm processing succeeded
- Token refresh failure recovery: auto-deletes corrupt/revoked token and re-runs OAuth flow
- Title/description trim to YouTube's 100/5000 char limits
- Title hint in description metadata in `plugin.json` / `marketplace.json` (keywords, license, repository, homepage)

### Changed
- `.env` location moved to plugin data dir (was repo root in earlier draft) — secrets never enter git
- Slash command instructions reference `setup.py` instead of writing `.env` directly via LLM (avoids escape issues on Windows paths)

### Fixed
- Removed accidentally committed OAuth credentials and token from git history (repo deleted and recreated)

## [0.1.0] — 2026-05-07

### Added
- Initial plugin skeleton: `commands/youtube-upload.md`, `bin/youtube_upload.py`, `bin/youtube_auth.py`
- `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` for plugin install
- README with basic usage
- MIT LICENSE
