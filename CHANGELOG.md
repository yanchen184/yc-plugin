# Changelog

All notable changes documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.7.0] — 2026-05-29

### Added — documentation style discipline

- **`skills/writing-docs`** — auto-applied skill enforcing three doc-writing rules: docs describe present state (not history/archival notes), no self-promotion or decorative headers, neutral factual descriptions. Generalizes the code discipline (no `// removed` comments, no backwards-compat shims) to docs, config comments, API schemas, and UI text.
- **`/docs-lint <file|dir> [--fix]`** — scans markdown for violations of the writing-docs rules (history-archival phrasing, marketing words, decorative emoji titles) and lists dead links pointing at deleted files. Report-only; never auto-edits (style fixes need human context).

## [0.5.0] — 2026-05-08

### Added — 5 new commands for full creator workflow

- **`/youtube-list`** — list my uploads with filters (privacy / playlist / date / query). Foundation command for /update, /stats, /delete.
- **`/youtube-stats`** — pull view / like / comment / engagement-rate stats for one or more videos. Sortable by views / likes / engagement / date.
- **`/youtube-update`** — change title, description, tags (additive add/remove), privacy, playlist (add/remove), thumbnail, caption — without re-uploading. Always supports `--dry-run`.
- **`/youtube-series`** — multi-episode series template manager: define title / description / tags / playlist once, apply per episode with auto-substitution of `{episode}`, `{episode_title}`, `{previous_link_block}` (auto-resolves to previous episode's URL), `{next_episode_title}`. Records uploaded episodes back to template.
- **`/youtube-shorts`** — extract a 9:16 vertical Shorts clip from a horizontal video. Three styles (blur-bg / pillarbox / zoom). Auto-extracts subset of SRT for that time range, time-shifts to t=0, burns in. Optional one-shot upload as Short.

### Added — supporting infrastructure

- `bin/lib/formatting.py` — CJK-aware table / json / markdown renderers shared by list/stats output.
- `bin/lib/youtube_client.py` extensions:
  - `list_my_videos()` — pulls from channel's uploads playlist
  - `get_video_details()` — batched videos.list (handles >50 IDs)
  - `update_video()` — fetches current snippet/status first, merges, sends back (avoids YouTube clearing unspecified fields)
  - `remove_from_playlist()` — find playlistItem by videoId and delete
- `commands/youtube-{list,stats,update,series,shorts}.md` — Claude workflow definitions for each.

### Requirements

- `/youtube-shorts` requires `ffmpeg` on PATH (script fails fast with install hints).

## [0.4.2] — 2026-05-08

### Fixed
- **Cross-platform Python compatibility** — many systems (recent macOS, most modern Linux distros) ship `python3` only, no `python` alias. Plugin would fail to load on those machines.
  - All `commands/*` and `hooks.json` now invoke `python3` explicitly (10 references).
  - `bin/*.py` scripts gained `#!/usr/bin/env python3` shebang and are now executable.

### Added
- **`bin/check_runtime.sh`** — runs at `SessionStart` before `install_deps.py`. If `python3` is missing from PATH, prints OS-specific install hints (brew / apt / dnf / Windows installer) and aborts plugin load early with a clear message.
- **README 系統需求 section** — documents Python 3.10+ requirement plus install commands per OS.

### Notes
- Plugin does **not** auto-install Python — out of scope, requires sudo on most systems, and risks PATH conflicts with pyenv/conda. Detection + guidance is the standard approach.

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
