---
name: screendoc
description: 從前端專案入口出發，產出對外可發表的「故事性操作手冊」。一條龍包辦：偵測專案類型 → 分析截圖清單 → 跑 Playwright 截圖 → 強制 caption 對齊 → UI/UX + SA + 新手 + Developer 四視角並行審視 → 自動修正局部重截 → ralph-loop 迭代直到全數通過 → 全頁重新截圖 → 產出符合品質契約的 HTML 手冊。
user-invocable: true
trigger: 當用戶說 /screendoc、「跑全套截圖」、「產手冊」時觸發
origin: 從 e2e-screenshot + e2e-analyze 整合升級（2026-04-29），合併 ralph-wiggum:ralph-loop 迭代精神
---

# /screendoc — 世界級 E2E 截圖手冊一條龍

> 這個 skill 的目標：別人 `git clone` 一個前端專案，下 `/screendoc .` 就能拿到一份**對外可發表**的故事性操作手冊。每張圖對應系統真實狀態，每句 caption 對應截圖實際元素，經過 4 視角輪番審視通過。

---

## 啟動方式

```
/screendoc <入口路徑> [--code-mode=read|write] [--max-iterations=20]
```

**參數**

| 參數 | 必填 | 預設 | 說明 |
|------|------|------|------|
| `<入口路徑>` | ✅ | — | 專案根目錄、plugin 根、或 e2e/ 目錄 |
| `--code-mode` | ❌ | `read` | `read` = 不改 source code，只改 spec/build/caption；`write` = 審視發現 UI bug 可改 source |
| `--max-iterations` | ❌ | `20` | 4 視角審視→修→局部重截 的迴圈上限 |

**範例**
```bash
/screendoc /path/to/my-react-app
/screendoc . --code-mode=write
/screendoc ./e2e --max-iterations=30
```

---

## 七層設計（這個 skill 的靈魂）

| 層 | 內容 |
|---|---|
| 1. Mission | 一份對外可發表的故事性操作手冊 |
| 2. Mechanics | Phase 0-5 流程 |
| 3. Contracts | Shot 4 欄位 + 4 條 manual-level 契約 |
| 4. Self-correction loops | 4 視角並行 review + ralph-loop 迭代 |
| 5. Failure mode catalog | 編號管理 30+ 條已知坑，自動偵測自動修 |
| 6. Polyglot adaptability | 跨 React/Vue/Next/NocoBase/Angular/Svelte/Remix/Astro/Flutter Web |
| 7. Output quality bar | HTML 手冊 + manifest.json + review-report.md + failure-modes.log |

---

## Phase 0：PRECHECK（環境偵測）

跑這 phase 的目的：別人 clone 後不需要回答任何問題，skill 自己摸清環境。

### 0.1 偵測專案類型

按優先順序試（先命中先用）：

```bash
# NocoBase plugin
test -f dist/server/plugin.js && test -f dist/client/index.js && echo "TYPE=nocobase-plugin"

# Next.js
test -f next.config.js -o -f next.config.mjs -o -f next.config.ts && echo "TYPE=nextjs"

# Remix
test -f remix.config.js && echo "TYPE=remix"

# Astro
test -f astro.config.mjs && echo "TYPE=astro"

# Vue
grep -l '"vue"' package.json 2>/dev/null && echo "TYPE=vue"

# Angular
test -f angular.json && echo "TYPE=angular"

# Svelte
test -f svelte.config.js && echo "TYPE=svelte"

# React (fallback)
grep -l '"react"' package.json 2>/dev/null && echo "TYPE=react"

# Flutter Web
test -f pubspec.yaml && grep -q "flutter:" pubspec.yaml && echo "TYPE=flutter-web"
```

### 0.2 偵測 e2e 工具

```bash
# 已有 Playwright？
test -f playwright.config.ts -o -f playwright.config.js && echo "PW=present"

# 沒有就 init
[ -z "$PW" ] && npx playwright install --with-deps chromium && \
  npx playwright init --quiet
```

### 0.3 偵測認證方式

```bash
# 找 login API
grep -rn "login\|signin\|auth" src/ --include="*.ts" --include="*.tsx" 2>/dev/null | head -5

# 偵測 token 存放
grep -rn "localStorage\|sessionStorage\|cookie" src/api 2>/dev/null | head -5
```

寫進 `e2e/fixtures/auth.ts` 適配層，common patterns:
- JWT in localStorage：`page.addInitScript((t) => localStorage.setItem('token', t), jwt)`
- Cookie session：`context.addCookies([{...}])`
- NocoBase：`POST /api/users:signin` → 拿 token → addInitScript

### 0.4 偵測 Design System（影響 caption 用詞和 wait 策略）

```bash
grep -l "antd\|@arco-design\|@mui/material\|@chakra-ui\|mantine\|@radix-ui\|shadcn" package.json
```

偵測到 DS 後 **設環境變數 `DESIGN_SYSTEM=antd|mui|chakra|radix|mantine`**，
`spec-skeleton.ts` 的 design-system adapter 會據此選對 modal close / notification close /
spinner / 內容錨點的選擇器。沒設 → 走 `generic`（靠 ARIA role/aria-label 的通用 fallback，
能跑但不如指定 preset 精準）。

adapter 各 preset 的選擇器（與 `templates/spec-skeleton.ts` 的 `DESIGN_SYSTEMS` 同步）：

| DESIGN_SYSTEM | modal close | notification close | spinner |
|---|---|---|---|
| `antd` | `.ant-modal-close` | `.ant-notification-notice-close` | `.ant-spin-spinning` |
| `mui` | `aria-label*="close" i` | `.MuiSnackbar-root button` | `.MuiCircularProgress-root` |
| `chakra` | `.chakra-modal__close-btn` | `.chakra-toast .chakra-close-button` | `.chakra-spinner` |
| `radix` | `aria-label*="close" i` | `[data-close-button]` | `.animate-spin` |
| `mantine` | `.mantine-Modal-close` | `.mantine-Notification-closeButton` | `.mantine-Loader-root` |
| `generic` | `[role=dialog] [aria-label*=close i]` | `[role=alert] button` | `[role=progressbar]` |

額外：Antd CJK 按鈕有空格（`取 消`），用 `cjkButton('取消')` 產 regex `/取.?消/`（FM-007）。

### 0.5 偵測 i18n（影響 caption 寫哪個語言）

```bash
ls src/locales src/i18n public/locales 2>/dev/null
grep -rn "i18next\|react-intl\|vue-i18n" package.json
```

如果有 i18n，**問用戶手冊用哪個語言**，否則用 `zh-TW`（繁中）。

### 0.6 產出 `e2e/.fullrun-context.json`

```json
{
  "project_type": "nocobase-plugin",
  "design_system": "antd",
  "auth_method": "jwt-localStorage",
  "i18n_locale": "zh-TW",
  "playwright_present": true,
  "code_mode": "read",
  "max_iterations": 20,
  "started_at": "2026-04-29T12:00:00Z"
}
```

後續所有 phase 讀這個 context，不重複偵測。

---

## Phase 1：ANALYZE（產截圖清單草稿）

### 1.1 列 Pages / Views

依 `project_type` 分流：

| 類型 | 命令 |
|------|------|
| react | `find src/pages src/views -name "*.tsx"` |
| vue | `find src/views src/pages -name "*.vue"` |
| next | `find app pages -name "page.tsx" -o -name "index.tsx"` |
| nocobase-plugin | `grep -o "function [A-Z][a-zA-Z]*Page[^(]*(" dist/client/index.js` |
| angular | `find src/app -name "*.component.ts"` |
| svelte | `find src/routes -name "+page.svelte"` |
| flutter-web | `find lib -name "*_page.dart" -o -name "*_screen.dart"` |

### 1.2 列 Routes

```bash
# React Router / TanStack
grep -rn "path:" src/router src/routes src/App.tsx 2>/dev/null

# Next.js / Remix / Astro：目錄即路由
# 不用 grep

# NocoBase
grep -o '"path":"[^"]*"' dist/client/index.js | sort -u

# Vue Router
grep -rn "path:" src/router/ 2>/dev/null
```

### 1.3 列 Modal / Drawer / Dialog

```bash
grep -rn "<Modal\|<Dialog\|<Drawer\|<Sheet\|<Popover" src/ 2>/dev/null
grep -rn "useDisclosure\|useState.*open\|setVisible\|setOpen" src/ 2>/dev/null
```

每個 Modal 至少 2 張：觸發前 + 開啟後。

### 1.4 列特殊狀態頁

| 狀態 | 需要的資料 |
|---|---|
| 空列表 | 不建任何資料、或選空 category |
| 載入中 | 跳過（難穩定） |
| 錯誤狀態 | mock 一個 500 |
| 已鎖定 | 建一筆 + 呼叫 lock API |
| 大量資料分頁 | 建 20+ 筆 |

### 1.5 識別權限角色

如果專案有角色系統（admin/editor/viewer/...），每個角色至少 4 張對比截圖（列表/閱讀/編輯/操作選單）。

### 1.6 產出 `e2e/.fullrun-shotlist.json`（草稿）

```json
{
  "chapters": [
    {
      "no": 1,
      "title": "從零建立示範專案",
      "intro": "...",
      "shots": [
        {
          "filename": "ch1_01_首頁.png",
          "title": "文件庫首頁總覽",
          "caption_draft": "（待 Phase 3 對著 PNG 寫）",
          "anchors": ["左側 Sidebar", "🏠 總覽", "三大群組", "右側文件清單"],
          "url": "/admin/your-plugin",
          "wait": "waitReady(page, 2000)",
          "modal": null,
          "viewport": {"width": 1440, "height": 900},
          "fullPage": false
        }
      ]
    }
  ],
  "beforeAll": {
    "users": ["admin", "editor", "viewer", "subscriber", "outsider"],
    "documents": [
      {"title": "示範文件", "status": "published", "count": 5},
      {"title": "鎖定文件", "locked": true, "count": 1}
    ],
    "templates": ["上版單範本"]
  }
}
```

**關鍵**：`anchors` 在分析階段就鎖死，後續 Phase 3 寫 caption 時逐項比對。`caption_draft` 留空，避免提前虛構。

---

## Phase 2：SCREENSHOT（跑 Playwright spec）

### 2.1 從 template 生成 spec

讀 `templates/spec-skeleton.ts`，把 `e2e/.fullrun-shotlist.json` 的章節 / shots / beforeAll 注入。

生成檔：`e2e/specs/99-fullrun-tour.spec.ts`

### 2.2 強制 helpers（template 自帶）

```typescript
async function shot(page, name, options = {})  // md5 dedup + size warn
async function shotFull(page, name)             // fullPage with warn
async function waitReady(page, extraMs = 1500)  // spinner 消失後再等
async function resetState(page)                 // ESC + close notifications
async function scrollIntoCenter(locator)        // hover 前必呼叫
```

### 2.3 執行

```bash
cd <input_path>/e2e
npx playwright test specs/99-fullrun-tour.spec.ts --reporter=line
```

### 2.4 跑完強制全樹掃描（Contract C1）

```bash
cd e2e/artifacts/screenshots

# 異常小檔案
find . -name "*.png" -size -30k -exec stat -f '%z %N' {} \;

# 跨檔重複（不同 shots 截到同一頁）
md5 $(find . -name "*.png" | sort) | \
  awk -F'=' '{print $2,$1}' | sort | \
  awk 'prev==$1 {print "DUP:",$0} {prev=$1}'
```

任何 `< 30KB` 或 `DUP:` → 寫進 `failure-modes.log`，回 Phase 2 修 spec 重跑。

---

## Phase 3：CAPTION（對著 PNG 寫描述）

### 3.1 強制 Read PNG

對 shotlist 每個 shot：

```
1. Read e2e/artifacts/screenshots/<filename>
2. 對照 anchors 清單，逐項視覺確認：
   ✓ "左側 Sidebar"  → 左邊有 Sidebar 嗎？
   ✓ "🏠 總覽"       → 截圖中真的有「🏠 總覽」字樣嗎？
   ✗ "右上角 ❓"     → 截圖中沒有 ❓ → 從 anchors 刪掉，caption 不可提
3. 寫 caption，只描述真實存在的元素
```

**禁令**（FM-014）：
- ❌ 憑記憶寫「右上角是…」
- ❌ 寫推測性詞彙「應該」「大概」「可能」
- ❌ 提到 anchors 之外的 UI 元素

### 3.2 寫 title（8-14 字手寫）

`title` 用於 sidebar 和 shot-label，**禁止程式自動截斷**（FM-022）。

範例：
- ✅ "文件庫首頁總覽"（7 字，OK）
- ✅ "新專案出現於 Sidebar"（11 字，OK）
- ❌ "文件庫首頁 — 看到的全部文件…"（自動截斷，違反 C4）

### 3.3 更新 shotlist.json 完成版

`caption_draft` → `caption`（完整版），`title` 全部填好。

### 3.4 產生縮圖版手冊（給 Phase 4 reviewer 吃）★ Token 優化

完整手冊（base64 內嵌全部原圖）= ~12 MB；reviewer 不需要原圖解析度，產縮圖版讓 Phase 4 省 60-70% token。

一步到位（縮圖 + review HTML 都在 `build-manual.py --review-mode` 裡）：

```bash
# --review-mode：自動批次縮圖（800×500 WebP@q80，省 ~89%）寫到 <png_dir>/thumbnails/，
#                HTML 的 <img> 指 thumbnails/*.webp 相對路徑（非 base64）
#
# ⚠️ review HTML 必須輸出到 <png_dir> 同層（output 路徑放在 png_dir 底下），
#    因為 <img src> 是相對 thumbnails/ 的路徑，相對的是 HTML 所在目錄。
#    HTML 放別處 → 瀏覽器 / reviewer Read 都會 404 圖全壞。
python3 e2e/tools/build-manual.py <png_dir> <png_dir>/manual-review.html --review-mode
#   🖼️  thumbnails: N 張重縮 → <png_dir>/thumbnails
#   ✅ wrote <png_dir>/manual-review.html [review-mode 縮圖版] (~90 KB HTML + 1 MB 縮圖)
#
# 發布版（base64 內嵌，路徑無此限制，HTML 放哪都行）：
# python3 e2e/tools/build-manual.py <png_dir> manual.html
```

實作參考：
- `templates/build-manual.py` — 單一檔同時管發布版與 review 版：
  - 不帶旗標 → base64 內嵌全解析度（~12 MB，對外發布用）
  - 帶 `--review-mode` → 內建 Pillow 批次縮圖 + 指相對路徑（增量縮圖，原圖沒更新就跳過）
  - 需要 `pip install Pillow`（縮圖）；C1 的 pHash 需要 `pip install imagehash`

產出物：
- `manual-review.html`（HTML ~90 KB + 圖檔 ~1 MB，總載入 ~1 MB，是原 12 MB 的 1/12）
  — **Phase 4 reviewer 吃這個**
- `manual.html`（~12 MB 完整版）— 對外發表用，Phase 5 才產（同一支 build-manual.py 不帶旗標）

---

## Phase 4：REVIEW LOOP（4 視角並行審視 + ralph-loop 迭代）

這是這個 skill 的核心。

### 4.1 並行啟動 4 個 review agent

每個 iteration 用單一 message 多 tool call，4 agent 同時跑。

| Agent | subagent_type | prompt 檔 |
|---|---|---|
| UI/UX | `frontend-ui-designer`（行動裝置產品改用 `mobile-uiux-advisor`） | `templates/review-prompts/uiux.md` |
| SA | `system-analyst` | `templates/review-prompts/sa.md` |
| 新手 | `general-purpose`（在 prompt 強調「沒看過 source、沒用過產品」） | `templates/review-prompts/newcomer.md` |
| Developer | `code-reviewer`（或 `<lang>-reviewer`：python-reviewer/typescript-reviewer 等） | `templates/review-prompts/dev.md` |

每個 agent 的輸入（**Token 優化版** — 別吃 12 MB 完整 HTML）：
1. **`manual-review.html` 縮圖版**（不是原版 `manual.html`）— 縮圖 800×500 + WebP，整本 ~2 MB，是原版 1/6
2. shotlist.json（純文字，~50 KB）
3. failure-modes.md（共同基準，**只挑 4-6 條相關的**，不要整份吃下去）
4. **縮圖 PNG 目錄絕對路徑** — 強制每個 agent 對每張縮圖呼叫 `Read`，原圖只在「視覺細節有疑問」時才看

**強制 contract（C5：Per-PNG Review）**：
- 每張 PNG 至少要被**負責的 reviewer** Read 過縮圖一次
- 每張 PNG 至少要在 review-report.md 留**至少一筆**具體視覺評語（不是「OK」就算）
- 違反者：iteration 不通過，必須補完才能進下一輪
- 為什麼：抽樣 N/總數 在「整批視覺一致 = schema bug」這類 pattern 下會漏掉（FM-037）

**Token 預算（每輪 review）**：
- iter 1（broad）: 4 視角全跑，預算 ~1.5M tokens
- iter 2+（focused）: 只跑「上一輪有 issue 的視角」+ sanity 1 個，預算 ~600K tokens
- 連續 2 輪零 issue → 退出，**不要再多跑「確認輪」**（曾經跑到 iter 6 才退出 = 浪費 4 輪）

每個 agent 的輸出：JSON issue list（schema 與 `templates/review-prompts/*.md` 一致）

```json
{
  "agent": "uiux",
  "iteration": 1,
  "overall_score": 3,
  "pass": false,
  "issues": [
    {
      "shot_id": "ch1_01_首頁.png",
      "severity": "high",
      "category": "B",
      "description": "caption 寫『中間總覽』但截圖中總覽在左側",
      "suggested_fix": "改為『左側 Sidebar 頂部總覽』",
      "requires_rescreenshot": false
    }
  ]
}
```

主 agent 聚合時用：
- `shot_id` 找對應截圖
- `severity` 排序
- `requires_rescreenshot` 判斷是否進入局部重截
- `category` 用 reviewer 各自的編碼（uiux=A-H、sa=A-G、newcomer=block_type、dev=tech 字段）

### 4.2 合併 + 去重

主 agent 收集 4 個 list → 去重（同一 shot 同類問題只留一條）→ 排序（severity DESC）。

### 4.3 修正

對每個 issue：
- `caption_mismatch` → 改 caption（不用重截）
- `title_truncated` → 改 title（不用重截）
- `ui_bug` + `code-mode=write` → 改 source code → 標記需重截
- `ui_bug` + `code-mode=read` → 寫進 outstanding-issues.md，不改
- `screenshot_quality` → 改 spec → 標記需重截

### 4.4 局部重截

```bash
# 只重跑「需重截」的 shots
SHOTS_TO_REDO="ch1_01,ch3_05,ch7_02a_editor_列表頁"
npx playwright test specs/99-fullrun-tour.spec.ts \
  --grep "$(echo $SHOTS_TO_REDO | sed 's/,/|/g')"
```

### 4.5 重新審視（ralph-loop，token-optimized）

```python
iteration = 1
consecutive_pass = 0
last_issue_agents = ["uiux", "sa", "newcomer", "dev"]  # iter 1 全跑

while iteration <= max_iterations:
    if iteration == 1:
        agents_to_run = ["uiux", "sa", "newcomer", "dev"]  # broad
    else:
        # focused: 只跑上一輪有 issue 的視角 + sanity（1 個）
        sanity = random.choice([a for a in ALL_AGENTS if a not in last_issue_agents])
        agents_to_run = list(set(last_issue_agents + [sanity]))

    issues = parallel_review(agents_to_run, input="manual-review.html")  # 縮圖版

    if not issues:
        consecutive_pass += 1
        if consecutive_pass >= 2:
            break  # 連續 2 輪零 issue → 退出（不再跑「確認輪」）
    else:
        consecutive_pass = 0
        last_issue_agents = sorted(set(i.agent for i in issues))
        apply_fixes(issues)
        rescreenshot(affected_shots)

    iteration += 1

if iteration > max_iterations:
    write_outstanding_issues()  # 不偷藏未解 issue
```

**關鍵差異**：
- `manual-review.html` 縮圖版（~2 MB）取代原版（~12 MB）：省 60-70% Phase 4 token
- iter 2+ 只跑 last-issue agents + 1 sanity（通常 2-3 個 agent，不是 4 個）：再省 ~30%
- 連續 2 輪 PASS 退出（不是跑到「確認輪」全 PASS 才退）：省 1-2 輪

---

## Phase 5：FULL REBUILD（最終全跑）

### 5.1 全部重新截圖

不管 Phase 4 局部重截過幾次，這裡**整個目錄清空全跑一次**。理由：避免局部修留下不一致的中間狀態。

```bash
rm -rf e2e/artifacts/screenshots/*
npx playwright test specs/99-fullrun-tour.spec.ts
```

### 5.2 Rebuild HTML

讀 `templates/build-manual.py`，產出 `<input>/manual.html`。

### 5.3 Contract 最終驗收

```bash
# C1: size + md5
find . -name "*.png" -size -30k && echo "FAIL C1"
md5 $(find . -name "*.png") | sort | uniq -d -w32 && echo "FAIL C1 dup"

# C3: forbidden tokens
grep -E '…|undefined|null|NaN|Invalid Date' manual.html && echo "FAIL C3"

# C4: title 100% 手寫
python3 -c "
import json
data = json.load(open('e2e/.fullrun-shotlist.json'))
for ch in data['chapters']:
    for s in ch['shots']:
        assert s['title'] and len(s['title']) <= 14, f'title 違規: {s}'
print('PASS C4')
"
```

### 5.4 a11y + 連結檢查（世界級附加）

```bash
# axe-core a11y
npx @axe-core/cli manual.html --save axe-report.json

# 內部錨點檢查
grep -oE 'href="#[^"]+"' manual.html | sort -u | while read link; do
  anchor="${link#href=\"#}"
  anchor="${anchor%\"}"
  grep -q "id=\"$anchor\"" manual.html || echo "BROKEN: $anchor"
done
```

### 5.5 產出附帶物

```
<input>/
├── manual.html                    主產出
├── manual_v<N>.html               歷史版本（每跑一次自動 vN+1）
├── e2e/
│   ├── artifacts/screenshots/     PNG 來源
│   ├── .fullrun-context.json      Phase 0 偵測結果
│   ├── .fullrun-shotlist.json     完整 shotlist
│   ├── .fullrun-manifest.json     每張圖的 metadata（給其他工具消費）
│   ├── .fullrun-review-report.md  4 視角的 review log（透明度）
│   ├── .fullrun-failure-modes.log 這次跑遇到並修掉的 FM 編號
│   └── .fullrun-outstanding.md    達 max-iter 仍未解的 issue（如果有）
```

---

## Contracts（強制條款）

```
C1  每張 PNG 必須通過 size > 30KB AND md5 unique AND 相鄰 shot pHash hamming distance ≥ 5
    違反 → Phase 2 修 spec 重跑（或 Phase 1 合併重複 shot）
    偵測 → find -size -30k + md5 dedup + imagehash.phash 跨 shot 比對
    為什麼 → md5 只抓得到「完全相同的 PNG」；pHash 抓得到「畫面實質一樣但時間戳不同」（FM-036）

C2  每個 Shot.anchors 必須是 caption 中至少出現一次的 UI 元素
    違反 → Phase 3 重寫 caption
    偵測 → for anchor in anchors: assert anchor in caption (substring)

C3  HTML rebuild 後 grep '…|undefined|null|NaN|Invalid Date' 必須 0 命中
    違反 → 找出來源（caption / data 渲染失敗 / 自動截斷）後修
    偵測 → grep -E

C4  sidebar 顯示文字 100% 來自 Shot.title（手寫），禁止程式截斷
    違反 → 移除任何 short_caption() 等 helper，補手寫 title
    偵測 → diff(rendered_label, shot.title) == 0

C5  Phase 4 每張 PNG 必須被所有 4 個 reviewer Read 過，且每張至少 1 句具體視覺評語
    違反 → 該 iteration 不通過，補完才能進下一輪
    偵測 → review-report.md 對每張 PNG 至少有 4 筆 entries（uiux/sa/newcomer/dev 各一）
    為什麼 → 抽樣會漏掉「整批視覺一致 = schema bug」這類 pattern（FM-037）
```

違反任何一條 → 不准進下一階段。

---

## Failure Mode Catalog

詳見 `failure-modes.md`，編號管理。常見 30+ 條，每條結構：

```
FM-XXX  <名稱>
  trigger:    什麼條件下會發生
  detection:  自動偵測命令 / 規則
  fix:        怎麼修
  prevention: 怎麼從 contract 避免
```

精選 10 條（完整見 failure-modes.md）：

| 編號 | 名稱 |
|---|---|
| FM-001 | `page.goto` timeout 30s |
| FM-002 | 截到 spinner / 空白頁（AMD 模組慢） |
| FM-007 | CJK 按鈕文字 `取 消`（Antd 雙字插空格） |
| FM-014 | 虛構 UI 元素（憑記憶寫 caption） |
| FM-015 | 「test pass = 截圖正確」假設 |
| FM-016 | 一次只修一張（沒掃整本） |
| FM-017 | 反問用戶「要不要修」（提出 = 修） |
| FM-022 | 顯示文字被自動截斷（…） |
| FM-025 | beforeAll 資料塞錯（Enum 欄位猜錯） |
| FM-030 | 跨 chapter 截到同一頁（全樹 md5 才抓得到） |
| FM-037 | 資料 schema 缺欄位 → UI fallback 到誤導預設值（整批視覺一致 = bug 徵兆） ★★★ |

---

## Polyglot Adapters

`detectors/<framework>.md` 定義每個框架的：
- Page 偵測規則
- Route 解析規則
- Auth 適配
- Design system 預設

支援列表（v1）：
- ✅ React (Vite/CRA)
- ✅ Vue 3
- ✅ Next.js (App Router / Pages Router)
- ✅ Remix
- ✅ Astro
- ✅ Angular
- ✅ Svelte / SvelteKit
- ✅ NocoBase Plugin
- ✅ Flutter Web

---

## 4 視角 Review Prompts 摘要

完整版見 `templates/review-prompts/<role>.md`。

### UI/UX
- 版面對齊、間距、視覺權重
- 動線是否流暢、按鈕優先級是否正確
- 色彩搭配、可讀性
- 一致性（同類元素的 hover / active 狀態）

### SA
- 架構圖是否完整
- 資料流是否清晰
- 邊界條件、錯誤處理是否有截到
- 角色 / 權限對比是否完備

### 新手（從未用過此系統）
- 第一眼能不能看懂主畫面在做什麼
- 章節順序是否符合「first-time user」的學習路徑
- 名詞是否在第一次出現就解釋
- 有沒有跳躍（B 章用了 A 章沒提的功能）

### Developer
- 截圖跟描述的功能對得上嗎
- 技術細節（API path / SQL / commit hash）有沒有錯
- code-related caption 是否準確
- 範例是否可重現

---

## Output Quality Bar

最終 manual.html 必須符合：

```
✓ Sidebar：sticky 左側，深色，章節 + 子標題 + 編號
✓ Lightbox：點圖放大，ESC 關閉，半透明背景
✓ 響應式：手機 < 1100px sidebar 隱藏
✓ Hero：架構圖 + 名詞表 + 角色表（如有角色）
✓ 列印友善：黑白印刷可讀
✓ a11y：axe-core 0 critical、0 serious
✓ 內部錨點：100% 可達（無 broken link）
```

---

## 與其他 skill / agent 的關係

| 工具 | 角色 |
|---|---|
| `/screendoc` | 主入口，本 skill |
| `mobile-uiux-advisor` | Phase 4 UI/UX 視角 |
| `system-analyst` | Phase 4 SA 視角 |
| `general-purpose` | Phase 4 新手扮演 |
| `code-reviewer` | Phase 4 Dev 視角 |
| `planner` | 複雜場景規劃 shotlist |
| `e2e-runner` | 通用 E2E（不專做截圖手冊） |

舊 skill `/e2e-screenshot` 和 `/e2e-analyze` 已合併進來，不再單獨存在。

---

## 執行範例（典型流程）

```bash
$ /screendoc /path/to/my-app

[Phase 0] 偵測 → react + Antd + JWT + zh-TW
[Phase 1] 分析 → 8 章 73 shots，beforeAll 5 users + 22 docs
[Phase 2] 截圖 → 73 PNG，md5 全 unique，size 全 > 30KB ✓
[Phase 3] caption → 對 73 PNG 逐張比對 anchors ✓
[Phase 4] iter 1: uiux=8, sa=3, newcomer=12, dev=5 issues → 修 → 局部重截 23 張
[Phase 4] iter 2: uiux=2, sa=0, newcomer=4, dev=1 issues → 修 → 局部重截 8 張
[Phase 4] iter 3: 0 issues ✓
[Phase 5] 全部重截 73 → rebuild → Contract C1-C4 全 PASS → a11y 0 critical ✓

✅ 完成：/path/to/my-app/manual.html (12 MB, 73 shots, 9 chapters)
📊 Review report: /path/to/my-app/e2e/.fullrun-review-report.md
```

---

## 可重入 / 可中斷

每個 phase 的產出物（`.fullrun-*.json`）都會落檔，下次跑 `/screendoc` 時：
- 偵測到 `.fullrun-context.json` 存在 → 問是否從上次中斷處繼續
- 任何 phase 失敗中斷 → 下次重跑只從失敗 phase 開始

---

## 持續優化

這個 skill 設計成可被 user 在使用過程持續微調：
- 新踩坑 → 加進 `failure-modes.md`
- 新框架 → 加進 `detectors/<framework>.md`
- review 視角不足 → 加 `templates/review-prompts/<new-role>.md`
- output 品質要求變高 → 改 Phase 5 contracts

每次 user 說「這次跑得不夠好」，主 agent 應該主動問「要不要把這個教訓加進 skill」。
