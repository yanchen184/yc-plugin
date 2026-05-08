---
description: 多集系列模板管理 — 定義一次標題格式 / 描述模板 / tags / playlist，後續每集自動套
argument-hint: "init|list|show|delete|add-episode|apply <series-id> [其他參數]"
---

# /youtube-series

把多集連載的 metadata 做成模板：標題格式（含 EP{episode:02d} 變數）、描述（含上集連結 / 下集預告）、tags、playlist、語言、隱私一次定義好。

之後每集只要給：episode 號、本集標題、本集摘要 → 自動填出完整 metadata 並上傳，省一輪互動。

## Parse arguments

`$ARGUMENTS` 第一個 token 是子命令：

- `init <id>` — 建立模板（互動 or flag）
- `list` — 列所有 series
- `show <id>` — 印模板 JSON
- `delete <id>` — 移除（要確認）
- `add-episode <id>` — 補登已上傳的影片到 series 紀錄
- `apply <id>` — 用模板上傳一集

## Workflow

### init

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/youtube_series.py" init <id> $REST
```

如果 user 沒提供 flags，腳本會走互動模式問：name / playlist / title-template / description-template / tags / language / privacy / category。

引導 user 設計模板時可用變數：

| 變數 | 意義 |
|------|------|
| `{episode}` `{episode:02d}` | 集數（補零）|
| `{next_episode:02d}` | 下集集數（自動 episode+1）|
| `{previous_episode:02d}` | 上集集數 |
| `{episode_title}` | 本集副標 |
| `{episode_summary}` | 本集摘要 |
| `{next_episode_title}` | 下集副標（apply 時傳入）|
| `{previous_link_block}` | 自動填入「上集回顧：〈X〉<URL>」（從已記錄的 episodes 抓）|

**標題模板範例**：
```
床前故事｜她的賭注 EP{episode:02d} {episode_title}
```

**描述模板範例**：
```
〈床前故事｜她的賭注 EP{episode:02d}〉

{episode_summary}

— — —

{previous_link_block}下集預告：〈她的賭注 EP{next_episode:02d} {next_episode_title}〉

#床前故事 #她的賭注 #校園戀愛
```

### list / show / delete

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/youtube_series.py" list
python3 "${CLAUDE_PLUGIN_ROOT}/bin/youtube_series.py" show <id>
python3 "${CLAUDE_PLUGIN_ROOT}/bin/youtube_series.py" delete <id>
```

`delete` 會二次確認。

### add-episode

把已上傳但 series 還沒登錄的影片補進去（例如 ep01 在你定義 series 之前就上了）：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/youtube_series.py" add-episode <id> \
  --episode N --episode-title "..." --video-id <ID> [--summary "..."]
```

### apply（核心）

用模板上傳新一集：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/youtube_series.py" apply <id> \
  --episode N \
  --episode-title "本集副標" \
  --summary "本集摘要" \
  --next-title "下集副標" \
  --video <video-path> \
  [--thumbnail <path>] [--caption <path>]
```

apply 流程：

1. 載入 series 模板
2. 算出 title / description / tags / playlist / privacy 等
3. **第一輪用 `--dry-run` 給 user 看 resolved 的 metadata**
4. user 確認後去掉 `--dry-run` 真上傳
5. 上傳成功自動把 video_id 記回 series

## Constraints

- **第一次 apply 一集前，先跑 `--dry-run`** 讓 user 看 resolved metadata
- title 模板必填；description 模板有預設但建議讓 user 自訂
- `previous_link_block` 只有在 `add-episode` 或 `apply` 過上集才會有 URL
- delete 要二次確認，沒有 `--force` 跳過機制
- series 檔在 `~/.claude/plugins/data/yc-plugin/series/<id>.json`，user 也可以手動編輯
