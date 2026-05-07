# Command Naming Convention

Future commands in this plugin follow this pattern:

```
/<area>-<verb>
```

Examples:
- `/youtube-upload` — upload video to YouTube
- `/youtube-list` — list uploads
- `/youtube-update` — update video metadata
- `/youtube-delete` — delete video
- `/blog-create` — generate blog post
- `/blog-publish` — publish to Firestore + GitHub Pages

Rules:
1. Lowercase, hyphen-separated
2. `<area>` first (matches the platform / domain), `<verb>` second
3. Verbs are imperative: `upload`, `list`, `create`, `delete`
4. Avoid abbreviations — clarity over brevity
5. Each command has its own `commands/<command-name>.md`

## Why this convention?

- Discoverability: typing `/youtube-` should autocomplete to all YouTube commands
- Grouping: future plugins can be split out by `<area>` if needed
- Searchability: `gh search code "/youtube-upload"` finds all relevant code
