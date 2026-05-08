---
description: 列出我上傳到 YouTube 的影片，可篩 privacy / playlist / 日期 / 標題關鍵字
argument-hint: "[--limit N] [--privacy public|unlisted|private] [--playlist NAME] [--query keyword]"
---

# /youtube-list

列出我頻道上的影片。給 video_id 給 `/youtube-update`、`/youtube-stats` 用。

## Parse arguments

`$ARGUMENTS` 是給 `youtube_list.py` 的 flag。常見：

- 沒參數 → 最近 20 部
- `--limit 50` 改數量上限
- `--privacy public` / `unlisted` / `private`
- `--playlist "她的賭注"` 只看某 playlist 的
- `--query 關鍵字` 標題子字串
- `--since 2026-05-01`、`--until 2026-05-08` 日期區間
- `--format json` / `markdown`（預設 table）
- `--shallow` 不查 statistics（省 quota）

## Workflow

跑：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/youtube_list.py" $ARGUMENTS
```

把輸出**完整**貼給使用者。如果要 table 並且很多列，可以額外摘要「最熱門 3 部 + 觀看數 / 互動率」做 quick summary。

如果 `$ARGUMENTS` 為空且 user 沒明說要做什麼，跑完後問一句：

```
列出來了。要做什麼？
  - 看某部 stats → /youtube-stats --video-id <ID>
  - 改某部 metadata → /youtube-update --video-id <ID> --title "..."
  - 切 Shorts → /youtube-shorts --video <檔> --start <時間>
```

## Constraints

- 失敗時把 Python 錯誤訊息**完整**轉達；常見錯誤：token 過期 → 引導到 `/youtube-setup reset`
- `--shallow` 模式請主動建議：當 user 只是想找 video_id 時用，省 quota
