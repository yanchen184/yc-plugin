---
description: 拉我影片的觀看 / 讚 / 留言 / 互動率，可批次查多部或某 playlist 全部
argument-hint: "[--video-id ID]... [--playlist NAME] [--limit N] [--sort views|likes|engagement|date]"
---

# /youtube-stats

讀 YouTube videos.list 的 statistics。**不需要** YouTube Analytics API，所以拿到的是「目前累積值」，不是時間序列。

## Parse arguments

- 沒參數 → 我最新 10 部的 stats
- `--video-id ID`（可重複）→ 指定影片
- `--playlist NAME` → 整個 playlist 的影片
- `--limit N` → 最新 N 部（預設 10）
- `--sort views|likes|comments|engagement|date`（預設 date）
- `--format json` / `markdown`

## Workflow

跑：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/youtube_stats.py" $ARGUMENTS
```

把輸出貼給使用者。table 已經有總計列。

### 主動洞察（可選）

跑完後如果使用者沒說做什麼，根據結果給 1-2 句 high-level 觀察：

- 哪部互動率最高 / 最低
- 觀看是否還在成長（看「天前」+「觀看」對比）
- 是否有 outlier（某部觀看是其他 5x 以上 → 該主題可深耕）

但**不要**過度詮釋，數字夠用就好。

### 限制提醒（適時）

如果使用者問「為什麼留存率沒看到」「平均觀看時長呢」之類 → 回：

> 這些要 YouTube Analytics API（更深的 metric）。
> 目前 plugin 只用 Data API。要看詳細留存可以開 https://studio.youtube.com → 該影片 → 觀眾續看率。

## Constraints

- 顯示的 statistics 是**從上傳到現在的累積值**，不是某時段的增量
- 留言數會被 YouTube 計入時稍有 delay（幾分鐘）；近期數字可能還在更新
