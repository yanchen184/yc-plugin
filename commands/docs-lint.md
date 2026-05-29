---
description: 掃一份技術文件（或整個目錄）揪出違反 writing-docs 風格的字眼——歷史考古註記、自我推銷、裝飾標題——並列出指向已刪檔的死連結。只報告不自動改。
argument-hint: "<檔案或目錄> [--fix]"
---

# /docs-lint

掃描技術文件，揪出違反 **writing-docs** skill 三條紀律的內容 + 死連結。對齊規則見 `${CLAUDE_PLUGIN_ROOT}/skills/writing-docs/SKILL.md`。

## Parse arguments

- 第一個 arg = 要掃的 `.md` 檔或目錄（必填）。目錄 → 遞迴掃所有 `.md`
- `--fix` → 列出每條違規的「建議刪除/改寫」，但**不自動寫檔**（風格判斷有語境，要人看過）

沒給路徑 → 印用法，不要猜。

## Workflow

對每個目標 `.md` 檔跑三組 grep + 死連結檢查。**用 `/usr/bin/grep`**（macOS 內建 BSD grep 認 `-E`）。

### 1. 紀律 1 — 歷史考古註記

```bash
/usr/bin/grep -nE '已被.*取代|已(刪除|歸檔|移除|棄用)|考古|先前版本|原本是.*現在|以前叫|過去叫|舊版.*見' "$FILE"
```

抓到 → 報「歷史考古：文件只寫現狀，這行該整句刪（歷史歸 git）」。

### 2. 紀律 2 — 自我推銷 / 裝飾

```bash
# 推銷字眼
/usr/bin/grep -nE '消化版|消化過|精華版|重點整理|可以直接念|直接念稿|開會(主用|用)|會議用|給主管看|必看|最完整|首選版' "$FILE"
# 裝飾 emoji（標題或行內強調符）
/usr/bin/grep -nE '[🎯📚⭐🔥✨🚀]|★|☆' "$FILE"
```

抓到 → 報「自我推銷／裝飾：技術文件不推銷自己，刪掉形容詞與裝飾符」。

**誤判排除**：領域術語的「首選」不算（「高血壓首選藥」）。報告前自己判斷該行是不是醫學/領域語境，是 → 不報。

### 3. 死連結

從每個本地 markdown 連結抽路徑，檢查目標存不存在：

```bash
DIR=$(dirname "$FILE")
/usr/bin/grep -oE '\]\([^)]+\)' "$FILE" | sed -E 's/^\]\(//; s/\)$//' \
  | /usr/bin/grep -vE '^https?:|^#|^mailto:' \
  | while read -r link; do
      target="${link%%#*}"            # 砍掉錨點
      [ -z "$target" ] && continue
      [ -e "$DIR/$target" ] || echo "DEAD: $link"
    done
```

`DEAD:` → 報「死連結：連結與整句一起刪，不要改寫成『已刪除』」。

## Output

依檔案分組，每條給 `行號｜違規類型｜原文片段｜建議`。結尾一行總計。

範例：

```
docs/README.md
  L9   歷史考古   「舊散落文件已被 SPEC 取代並刪除」   → 整句刪
  L17  死連結     [操作手冊](_archive/manual.html)      → 連結與整句一起刪
docs/_sidebar.md
  L4   裝飾標題   「📚 歸檔（已被 SPEC 取代）」          → 刪 emoji + 刪整節

3 條違規，2 檔。沒有 --fix → 只報告，你決定怎麼改。
```

`--fix` 時：對每條多給一行具體 diff 建議，但仍**不寫檔**——風格修正要人看過語境。

## Constraints

- 純報告工具，**永不自動改檔**（即使 `--fix`，只給建議）
- pattern 是 heuristic，不是 100% 精準。寧可多報讓人判斷，不要漏報
- 不掃 `.git/` / `node_modules/` / `_generator/`（產生器與歷史快照不是現行文件）
- 領域術語「首選」「精華」等出現在醫學/業務語境時自行排除誤判
