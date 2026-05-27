# /screendoc

> 一條龍：從前端專案入口出發，產出對外可發表的「故事性操作手冊」。

## 解決什麼問題

用 LLM agent 自動產生產品操作手冊，常見幾個 pain point：

1. caption **憑記憶寫**，描述了畫面上不存在的元素
2. 截圖跑出來才發現 **截到 spinner / 空白頁 / 殘留 modal**
3. 跑出 73 張 PNG 之後，sidebar 全是 `…` 截斷不知道在哪一張
4. 修了一張之後，沒有掃整本，**同類問題重複出現**
5. agent 把 spec 跑過 = 截圖正確（**錯**，要實際看圖）

`/screendoc` 把這些教訓全部寫進 contract 與 failure-mode catalog，
搭配 4 個視角的並行審視 + ralph-loop 的迭代收斂機制，產出可發表的手冊。

## 使用方式

```text
/screendoc <frontend_entry_path> [options]
```

- `<frontend_entry_path>`：前端專案根目錄、entry index、或 NocoBase plugin 目錄
- `--code-mode=read|write`（預設 `read`）：是否允許 agent 修改 source code 來修圖文落差
- `--max-iterations=20`（預設 20）：4 視角審視最多迭代幾輪
- `--lang=zh-TW|en|ja`（依 i18n_locale 自動偵測）：手冊語言

範例：

```text
/screendoc storage/plugins/@nocobase/plugin-doc-hub
/screendoc apps/web --code-mode=write --max-iterations=30
/screendoc . --lang=en
```

## 內部 5 階段

1. **Phase 0 - Precheck**：偵測框架（react / vue / next / nocobase / angular / svelte / remix / astro / flutter-web），讀 i18n locale，確認服務跑著
2. **Phase 1 - Analyze**：掃 source code，列出所有可截圖的 UI feature 與資料前置需求
3. **Phase 2 - Screenshot**：產生 `manual.spec.ts` 跑 Playwright，內建 size + md5 + dedup 檢查
4. **Phase 3 - Caption**：對每張 PNG **強制 Read 確認**，寫敘事體 caption，title 100% 手寫不截斷
5. **Phase 4 - Review Loop**（核心）：
   - 並行跑 4 個 reviewer agent：UI/UX、SA、新手、Developer
   - 蒐集所有 issue，依 severity 排序
   - 修圖文 / 改 spec → 局部重截 → 重新 review
   - 直到 4 視角都 pass 或達 `max-iterations`
6. **Phase 5 - Full Rebuild**：全部重新截圖一次（避免局部重截造成跨章節資料漂移），產出最終 manual.html

## 4 視角審視

| 視角 | Agent | 關注 |
|---|---|---|
| UI/UX | `frontend-ui-designer` | 視覺層次、圖文一致、敘事節奏 |
| SA | `system-analyst` | 功能完整性、使用者旅程、資料流 |
| 新手 | `general-purpose`（強調未見過系統） | 術語、前提、預期結果、跨章跳躍 |
| Developer | `code-reviewer`（或語言特定） | 與 source code 的技術一致性 |

每個視角的 prompt 在 `templates/review-prompts/`，輸出統一 JSON，主 agent 收口聚合。

## 已內建 35 條 Failure Mode

從 DocHub 73 張手冊製作經驗萃取出的踩坑：截圖技術、caption 文字、資料環境、review loop 四大類。詳見 [`failure-modes.md`](./failure-modes.md)。

## 4 條 Manual 契約

- **C1 — Shot Coverage**：每張 PNG 必須在 chapters 中註冊
- **C2 — Anchor Reality**：anchors 必須來自截圖實際元素，不可憑記憶
- **C3 — Narrative Caption**：caption 一律敘事體，不允許 bullet list
- **C4 — Hand-written Title**：title 100% 手寫，不允許 helper 自動截斷

## 不適用

- 純後端服務（沒有 UI）
- 完全 canvas 的 game / WebGL（截圖能跑，但 4 視角審視會挫敗）
- iOS / Android 原生（未來再說）

## 與其他 skill 的關係

替代了：
- `e2e-screenshot` — 已併入本 skill 的 Phase 2/3
- `e2e-analyze` — 已併入本 skill 的 Phase 1

仍可獨立使用：
- `e2e-testing` — 一般 E2E 測試（非手冊）
- `frontend-design:frontend-design` — 從零做新 UI（不是審視既有 UI）

## 發布定位

這個 skill 把「產品操作手冊」這件事從**手工寫 markdown 配截圖**，
升級為**可重複、可審視、可發布**的標準流程。

適合：技術文件作者、PM、教學影片前置作業、客戶交付包。
