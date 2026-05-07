# Changelog

All notable changes documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.4.1] — 2026-05-08

### Added
- **`/youtube-setup`** slash command — unified credential management:
  - `/youtube-setup` (no args) → show state + list actions
  - `/youtube-setup init` → OAuth setup walkthrough
  - `/youtube-setup export <path>` → bundle creds for transfer
  - `/youtube-setup import <path>` → restore from a transfer zip
  - `/youtube-setup reset` → wipe credentials (with confirmation)

### Changed
- README now points users at slash command shorthand (e.g. `/youtube-setup export`) instead of the longer python invocation
- README opening line lists both commands (`/youtube-upload` + `/youtube-setup`)

## [0.4.0] — 2026-05-08

### Added
- **`setup.py --export PATH`** — bundle `client_secret.json` + `yt_token.json` into a zip for cross-machine transfer or sharing with collaborators
- **`setup.py --import PATH`** — restore credentials from an export zip; new machine can upload immediately without browser auth
- README section: 「換電腦 / 分享給夥伴」with prominent security warning about token sharing risks

### Use cases unlocked
- Switching machines without re-running OAuth browser flow
- Letting an editor / VA upload videos to your channel on your behalf
- Backing up credentials to a secure vault (1Password etc.)

### Security
- Export prints loud multi-line warning about credential sensitivity and revocation URL
- Import validates JSON structure before installing

## [0.3.0] — 2026-05-07

### Added
- **`bin/lib/`** shared modules:
  - `paths.py` — plugin data dir / token / log path resolution
  - `console.py` — info/warn/err with file logging, UTF-8 stdout for Windows
  - `youtube_client.py` — OAuth + thumbnails + playlists + captions helpers
- **`--thumbnail PATH`** — upload custom thumbnail (≤2MB jpg/png)
- **`--publish-at "YYYY-MM-DD HH:MM"`** — schedule publish; auto-converts local→UTC, sets privacy=private
- **`--playlist NAME_OR_ID`** — add to playlist by name (auto-create) or ID
- **`--caption PATH`** — upload SRT/VTT subtitle (auto-detects same-name file alongside video)
- **`--language zh-TW`** — set defaultLanguage / defaultAudioLanguage
- **`--for-kids`** — selfDeclaredMadeForKids flag
- **`--dry-run`** — preview metadata payload without uploading
- **`--verbose`** — debug-level logging
- **`--no-auto-caption`** — disable auto subtitle detection
- **Log file** at `${data_dir}/log.txt` for forensics
- **Friendly error messages** with actionable next-step hints (`console.err(msg, hint)`)
- `setup.py --reset` to wipe and start over
- CONTRIBUTING.md + .github/ISSUE_TEMPLATE/ + PULL_REQUEST_TEMPLATE.md
- README: full feature table + 12 FAQs + system architecture diagram + badges

### Changed
- Refactored `youtube_upload.py`: split helpers (`build_body`, `do_upload`, `verify_processing`, etc.)
- All scripts now use `lib/console` for consistent output + logging
- `youtube_auth.py` simplified — uses `lib/youtube_client.get_credentials()`

### Deps
- Bumped scopes to include `youtube` and `youtube.force-ssl` (for thumbnails / captions / playlists)

## [0.2.0] — 2026-05-07

### Removed
- `.env` file entirely. Setup now copies `client_secret.json` into plugin data dir; defaults are constants in code.
- `YOUTUBE_DEFAULT_*` env-var plumbing
- `YOUTUBE_CHANNEL_NAME` (was never read)

### Changed
- `setup.py` simplified from 165 → 110 lines

## [0.1.0] — 2026-05-07

### Added
- Initial plugin skeleton with `/youtube-upload`, OAuth, resumable upload, retry/backoff, post-upload verify
