# Failure Mode Catalog

每條 FM 都有：trigger（觸發條件）+ detection（自動偵測）+ fix（怎麼修）+ prevention（怎麼從 contract 避免）。

---

## 截圖技術類（FM-001 ~ FM-013）

### FM-001  page.goto timeout 30s
- **trigger**: playwright.config.ts 全局 `navigationTimeout: 30000` 不足
- **detection**: spec 跑出現 `TimeoutError` exceeding 30000ms
- **fix**: 每個 `page.goto` 加 `{ timeout: 60000 }`
- **prevention**: spec template 預設帶 timeout

### FM-002  截到 spinner / 空白頁
- **trigger**: AMD / lazy chunk 比 networkidle 慢
- **detection**: PNG size < 30KB OR md5 與 loading 樣板相同
- **fix**: `waitReady()` + `waitForSelector('textarea, table, h1')`
- **prevention**: shot() 自動 size warn

### FM-003  docs.length === 0（NocoBase）
- **trigger**: `docDocuments:list` 是框架 action，body.data 是 `{data:[], meta}` 不是 array
- **detection**: console log 顯示 `Cannot read property 'forEach' of undefined`
- **fix**: 用硬碼 projectId / categoryId；或修 ApiHelper 解包 body.data.data
- **prevention**: ApiHelper 自帶層數判斷

### FM-004  版本頁 "文件不存在" toast
- **trigger**: doc 已 destroy，但版本記錄還在
- **detection**: 截圖右上角有紅色 notification
- **fix**: 截圖前 `click('.ant-notification-close-icon').catch(()=>{})`
- **prevention**: resetState() 自帶關 notification

### FM-005  `[E2E-TPL]` locator 失效
- **trigger**: `[]` 被 Playwright 解析成 CSS attribute selector
- **detection**: `locator('[E2E-TPL] xxx')` 找不到任何元素
- **fix**: `page.getByText('[E2E-TPL]...')` 改用文字匹配
- **prevention**: spec template comment 提示

### FM-006  beforeAll ECONNRESET cleanup undefined
- **trigger**: beforeAll 拋錯，cleanup 還沒賦值
- **detection**: afterAll 報 `Cannot read property 'flush' of undefined`
- **fix**: `if (cleanup) await cleanup.flush()`
- **prevention**: spec template 預設帶守衛

### FM-007  CJK 按鈕文字 `取 消`（Antd 雙字插空格）
- **trigger**: Antd 對雙字中文自動插入空格
- **detection**: `filter({ hasText: '取消' })` 找不到，改用 `/取.?消/` 命中
- **fix**: 所有 CJK 按鈕用 regex
- **prevention**: detectors/<antd>.md 列出常見按鈕的正確匹配

### FM-008  ctx.dispose 後讀 body 失敗
- **trigger**: Response 已 disposed
- **detection**: `await res.json()` 報 disposed
- **fix**: 先 `res.json()` 再 `ctx.dispose()`
- **prevention**: ApiHelper 自帶順序

### FM-009  連續兩張完全相同
- **trigger**: navigation/click 沒完成就截下一張
- **detection**: shot() 內 md5 dedup 警告
- **fix**: 加 `waitReady()` 或 `waitForSelector` 確保頁面換了
- **prevention**: shot() 自帶 md5 比對

### FM-010  PDF iframe 截到白板
- **trigger**: iframe 載 PDF 慢，networkidle 不等 iframe
- **detection**: PNG 中 PDF 區域全白
- **fix**: `frameLocator('iframe').locator('body').waitFor()` + `waitForTimeout(2000)`
- **prevention**: 偵測到 iframe 自動加 wait

### FM-011  Seed 資料 [MANUAL] 入鏡
- **trigger**: 截圖看到測試前綴
- **detection**: 圖中文字含 `[E2E]` `[TEST]` `[MANUAL]`
- **fix**: 截圖用的 PREFIX 改成 `''`，cleanup 改靠白名單識別
- **prevention**: spec template PREFIX 預設空字串

### FM-012  空白編輯器
- **trigger**: 沒等 editor content load 就截，或截到 skeleton
- **detection**: textarea value 長度 < 10
- **fix**: `waitForFunction(() => textarea.value?.length > 50)`
- **prevention**: spec template editor wait

### FM-013  Row hover 按鈕截不到
- **trigger**: 目標 row 在 viewport 外，hover 無效
- **detection**: hover 後 button 不可見
- **fix**: 先 `scrollIntoCenter(row)` 再 hover
- **prevention**: scrollIntoCenter helper 強制使用

---

## Caption / 文字類（FM-014 ~ FM-024）

### FM-014  虛構 UI 元素（憑記憶寫 caption）★★★
- **trigger**: caption 描述了截圖中**不存在**的 UI 元素
- **detection**: Phase 3 強制 Read PNG，逐 anchor 視覺確認
- **fix**: 刪除虛構元素，補一個真實存在的 anchor
- **prevention**: Contract C2 — Shot.anchors 鎖死，禁止憑記憶
- **真實案例**: DocHub Ch1.1 寫「中間總覽」「右上角 ❓」，實際總覽在左、❓不存在

### FM-015  「test pass = 截圖正確」假設 ★
- **trigger**: 只看 spec exit code，沒實際看圖
- **detection**: 用戶反饋圖內容錯
- **fix**: 每次跑完逐張 Read，size + md5 + 視覺確認
- **prevention**: Phase 2 強制 Contract C1 + Phase 3 強制 Read

### FM-016  一次只修一張（沒掃整本）★★
- **trigger**: 修了 A 圖只重拍 A，沒看 B/C/D 是否也有同樣問題
- **detection**: 用戶第二輪審視時又找出同類問題
- **fix**: 修任何圖後，4 視角重跑整本 review
- **prevention**: Phase 4 ralph-loop 強制每次都過完整 4 視角

### FM-017  反問用戶「要不要修」★
- **trigger**: 用戶提出問題，agent 又問「要修嗎」
- **detection**: 主 agent 自我檢查訊息有「要不要」「需要嗎」「修嗎」
- **fix**: 用戶提出 = 修，沒有例外。需要設計選擇時提供 1-2 句方案 + 動手
- **prevention**: skill prompt 內建禁問規則

### FM-018  不存在的功能名稱
- **trigger**: caption 寫了一個系統根本沒有的功能
- **detection**: dev agent review 抓
- **fix**: 對著截圖只描述看得到的，不發明功能名
- **prevention**: anchors 必須來自截圖實際元素
- **真實案例**: DocHub Ch2.2 寫「卡片放大看」，但這不是功能

### FM-019  錯誤的位置描述
- **trigger**: 「中間」「右上角」等位置詞和實際不符
- **detection**: uiux agent review 抓
- **fix**: Phase 3 寫前先 Read，目視確認位置
- **prevention**: anchors 包含位置語詞時必須對照

### FM-020  推測性詞彙
- **trigger**: 「應該」「大概」「可能」「也許」
- **detection**: grep 命中
- **fix**: 確認後改成肯定句，不確認的刪除
- **prevention**: skill 內建禁用詞清單

### FM-021  錯誤的技術細節
- **trigger**: API path / SQL / commit hash / 數字錯
- **detection**: dev agent 比對 source code
- **fix**: 對著 source 修
- **prevention**: dev review 視角強制查 code

### FM-022  顯示文字被自動截斷（…）★★★
- **trigger**: sidebar / shot-label / 任何顯示文字出現 `…`
- **detection**: rebuild 後 `grep '…' manual.html` > 0
- **fix**: 移除 short_caption() 等 helper，補手寫 title
- **prevention**: Contract C4 — title 100% 手寫
- **真實案例**: DocHub 73 張全部 sidebar 都被截斷

### FM-023  未翻譯字串
- **trigger**: 手冊語言設 zh-TW，但 caption 混 EN
- **detection**: 簡單字串檢查
- **fix**: 統一用 i18n_locale 的語言
- **prevention**: Phase 0 偵測 i18n 後鎖定語言

### FM-024  時態 / 語氣不一致
- **trigger**: 同章混用「點擊」「點」「按下」
- **detection**: uiux agent review
- **fix**: 全冊統一動詞用法
- **prevention**: review-prompts/uiux.md 列檢查項

---

## 資料 / 環境類（FM-025 ~ FM-030）

### FM-025  beforeAll Enum 欄位猜錯
- **trigger**: 直接猜 type 值，DB 不接受
- **detection**: insert 報 enum value invalid
- **fix**: `docker exec db psql -c "SELECT DISTINCT type FROM table"` 先查
- **prevention**: Phase 0 自動列 enum 值
- **真實案例**: AMI 專案 MeasurementSource 只有 SELF_REPORT 和 HIS

### FM-026  Backend endpoint 不存在
- **trigger**: 前端呼叫的 API 後端沒實作，dashboard 永遠空
- **detection**: 截圖顯示「尚無資料」+ network 200 但 data: []
- **fix**: 先 grep 後端 controller 確認，沒有的話先實作
- **prevention**: Phase 1 同步檢查前後端 API 對應

### FM-027  axios interceptor 解包
- **trigger**: client 把 `response.data.data` 解包成 `response.data`
- **detection**: mock body 結構錯
- **fix**: mock body 多包一層
- **prevention**: Phase 0 偵測 axios interceptor 寫進 context

### FM-028  React SPA 需要 JWT 才看得到內容
- **trigger**: SPA auth guard，goto 前 localStorage 空
- **detection**: 截到 login page 而非目標頁
- **fix**: `page.addInitScript((t) => localStorage.setItem('token', t), jwt)`
- **prevention**: auth.ts 適配層自動處理

### FM-029  beforeAll timeout（資料量大）
- **trigger**: 全域 timeout 30s 不夠塞 50+ 筆
- **detection**: beforeAll 超時報錯
- **fix**: `playwright.config.ts` 加 `timeout: 300000`
- **prevention**: spec template 預設 5 分鐘

### FM-030  跨 chapter 截到同一頁 ★★★
- **trigger**: 某 chapter navigation 失敗，留在前一章頁面就截了
- **detection**: per-shot md5 抓不到（不是連續），全樹 md5 才抓得到
- **fix**: 修 spec navigation 邏輯
- **prevention**: Phase 2 強制全樹 md5 掃描

---

## Review Loop 類（FM-031 ~ FM-035）

### FM-031  Review agent 給空回應
- **trigger**: agent 沒讀完 manual 就回 `[]`
- **detection**: issue list 空但用戶實際看仍有問題
- **fix**: 在 review prompt 內強制至少看完 N 個 sample
- **prevention**: review-prompts 內建驗證問題

### FM-032  Review 視角同質化
- **trigger**: 4 個 agent 給的 issue 70% 重疊
- **detection**: 去重後剩 < 30%
- **fix**: 強化每個視角的 prompt 差異
- **prevention**: review-prompts 各自獨立的關注點

### FM-033  Iteration 無收斂
- **trigger**: 連續 3 iter issue 數量不減反增
- **detection**: 自動偵測 issue trend
- **fix**: 停下來問用戶（可能 review prompt 太嚴格）
- **prevention**: 加上 trend 監控

### FM-034  局部重截後不一致
- **trigger**: 局部重截某張，後續流程資料變了
- **detection**: 跨 shot 關聯性檢查
- **fix**: Phase 5 強制全部重截一次
- **prevention**: skill 流程內建 Phase 5 全跑

### FM-035  Outstanding issue 被偷藏
- **trigger**: 達 max-iter 但 agent 不告知未解 issue
- **detection**: 比對 final review vs 最終手冊
- **fix**: 強制寫 outstanding-issues.md
- **prevention**: Phase 4 收尾邏輯內建寫檔

### FM-037  資料 schema 缺欄位 → UI fallback 到誤導預設值 ★★★
- **trigger**: backend item schema 缺某個欄位（例：priority/status/severity），前端 normalize 函式有「lazy default」（`?? 'MEDIUM'`、`?? 'success'`），結果**整批**卡片視覺都一樣
- **detection**:
  - **視覺層**：同一頁所有同類元件視覺完全一致 — 全黃、全紅、所有 badge 同一個 icon、所有 status 同一顆綠燈
  - **資料層**：拿 API response 或 DB 抓 5+ 筆 → 真實資料應該有異質性（HIGH/MEDIUM/LOW 混雜），如果**全部都是同一個值** → 看是 backend 沒填還是 UI 蓋掉了
  - **code 層**：grep 前端 normalize 函式找 `?? 'MEDIUM'` / `|| 'success'` / `?? DEFAULT_X` 這種 lazy fallback
- **真實案例（AMI 2026-04）**：CDSS 9 張卡片全部 🟡 中優先 + 文字截斷。原因：ai-service 只回 `list[str]`，前端 fallback 到 MEDIUM。Phase 4 reviewer 抽樣 5 張沒看出「整批一致」是 bug 徵兆。
- **fix**（最佳實踐路）：
  1. **Backend 加 schema 欄位**（首選）— Pydantic / TypeScript / Java DTO 補 priority 欄位
  2. **Frontend 拿掉 lazy default** — 改用 nullable + 顯示「未標註」的中性樣式
  3. **加 panel-level disclaimer** — 「本批資料尚未標註 priority，僅顯示類型徽章」
  4. ❌ **嚴禁的快修**：`if (!priority) priority = 'MEDIUM'` —— 這就是當初的 bug
- **prevention**:
  - Phase 4 dev 視角強制檢查項 G「Schema vs UI 真實性」：所有同類卡片視覺一致 → 立刻去 DB / API 對照
  - Phase 4 uiux 視角強制檢查「整批視覺異質性」：真實業務資料應有異質性，整片一致 = bug 徵兆
  - review prompts 改為**強制 Read 每張 PNG**，不可抽樣（抽 5/70 = 7%，整批一致 pattern 看不出來）

### FM-036  相鄰兩張 caption 語意重複 ★★★
- **trigger**: 同一 modal / 同一 panel 被切成「入口」+「內容」兩張，但兩張的 caption 都在描述同一組畫面元素（例：2.1「點+新增文件彈出 Modal — 看到 4 張卡片並列」、2.2「Modal 內 4 張卡片並列」）
- **真實案例（DocHub 2026-04-30）**：ch2_01「新增方式選擇 Modal」+ ch2_02b「四種方式 Modal」實質是同一個 UI 狀態，只差截圖時間戳。連跑 6 輪 4 視角審視（共 24 次 review）全部 5/5 PASS，使用者一眼指出「2-1 / 2-2 幾乎一樣」。原因：4 個視角的職責（架構 / 排版 / 新手體驗 / 技術正確性）剛好都不負責逐張比對畫面差異 —— 這是 4 視角分工的設計盲點。
- **detection**:
  - **md5 層**（FM-009 已涵蓋）：完全相同的 PNG → 抓得到
  - **pHash 層（本 FM 新增）**：跨 shot 算 perceptual hash，相鄰兩張 hamming distance < 5 → 視覺重複
    ```bash
    pip install imagehash pillow
    python3 -c "
    from PIL import Image
    import imagehash, glob, os
    shots = sorted(glob.glob('e2e/artifacts/screenshots/**/*.png', recursive=True))
    hashes = [(s, imagehash.phash(Image.open(s))) for s in shots]
    for i in range(len(hashes)-1):
        a, b = hashes[i], hashes[i+1]
        dist = a[1] - b[1]
        if dist < 5:
            print(f'VISUAL_DUP dist={dist}: {os.path.basename(a[0])} <=> {os.path.basename(b[0])}')
    "
    ```
  - **語意層**：相鄰兩張 caption 的關鍵名詞集合（ex.「Modal」「卡片」「並列」）重疊率 > 60%
  - **規劃層**：Phase 1 規劃時要求每張 shot 必須能用一句話說出「這張比上一張多了什麼可見元素」，回答不出來就刪掉
- **fix**：兩種選擇
  1. **合併**：刪掉一張，留下的 caption 改成「入口操作 + 內容說明」一句話（首選）
  2. **差異化**：第二張改成不同狀態（例：hover 某張卡片高亮、或滑到第 2 個選項展開時）
- **prevention**:
  - Phase 1 analyze 階段檢查：同一 modal/page 是否被切成 ≥2 張
  - Phase 2 截完後**強制跑 pHash 全樹掃描**（Contract C1 升級 — 不只 md5 unique，還要 hamming distance ≥ 5）
  - Phase 3 caption 階段：對相鄰兩張做關鍵詞重疊率檢查
  - Phase 4 加入「**截圖差異審視員**」第 5 視角，專責逐張比對相鄰 shot 的視覺差異（4 個現有視角都不負責這件事 —— 設計盲點）
  - Review prompts 加入「相鄰章節是否語意重複」檢查項
