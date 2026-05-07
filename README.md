# yc-plugin

> Claude Code 插件 — 把日常重複的內容工作自動化。
> 第一個指令：**`/youtube-upload`**，從你終端機一行指令上傳到 YouTube。

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Made for Claude Code](https://img.shields.io/badge/made%20for-Claude%20Code-orange)](https://claude.com/claude-code)
[![繁體中文](https://img.shields.io/badge/lang-繁體中文-blue)](README.md)

---

## 為什麼用這個

不用打開 YouTube Studio 拖檔。一行指令，搞定：

- ✅ **影片** + 自定義 **封面圖**
- ✅ **排程發布**（指定日期時間，YouTube 自動公開）
- ✅ **加到播放清單**（給名字自動建立，或丟 playlist ID）
- ✅ **字幕自動偵測**（同名 `.srt` / `.vtt` 自動上傳）
- ✅ **斷網續傳**（resumable，6 次指數退避重試，不用整段重來）
- ✅ **發布後驗證**（自動 polling YouTube 確認影片真的能播）
- ✅ **完整 dry-run**（送出前看 JSON payload 確認）
- ✅ 100% 用你自己的 Google 帳號 / 自己的 OAuth credential — 沒有共用授權、沒有第三方 server

## 安裝

```
/plugin marketplace add yanchen184/yc-plugin
/plugin install yc-plugin@yc-plugin
```

第一次跑會自動 `pip install` 必要的 Python 套件。完成。

## 第一次設定（一次性，~3 分鐘）

直接跑 `/youtube-upload <影片>`，Claude 會引導你拿 OAuth credential。或預先跟著做：

### 1. Google Cloud Console 開個 project
打開 [Google Cloud Console](https://console.cloud.google.com/) → 左上角下拉選單 → **NEW PROJECT** → 任意名字 → **CREATE**

### 2. 啟用 YouTube Data API v3
左側 → **APIs & Services** → **Library** → 搜 `YouTube Data API v3` → **ENABLE**

### 3. 設定 OAuth consent screen
左側 → **APIs & Services** → **OAuth consent screen** → **External** → **CREATE**

填：
- **App name**：任意
- **User support email**：你的 Gmail
- **Developer contact information**：你的 Gmail

**Test users** 那頁加你自己的 Gmail 進去。

> 為什麼？你的 app 沒過 Google 驗證，預設只有 test user 能授權。每個 app 上限 100 個 test users，個人用足夠。

### 4. 建立 OAuth client
左側 → **APIs & Services** → **Credentials** → **+ CREATE CREDENTIALS** → **OAuth client ID**
- **Application type**：選 **Desktop app**（很重要）
- **Name**：任意
- 點 **CREATE** → **DOWNLOAD JSON**

### 5. 把 JSON 給 Claude
```
/youtube-upload <影片路徑>
```
第一次會問 client_secret 在哪，貼上絕對路徑就好。

## 使用範例

### 最簡單
```
/youtube-upload D:/videos/ep1.mp4
```
Claude 會問你標題、隱私、描述、tags、封面、排程、播放清單。

### 在指令裡帶標題
```
/youtube-upload D:/videos/ep1.mp4 "EP1 校園愛情故事"
```

### 從命令列直接跑（不透過 Claude）
```bash
python ~/.claude/plugins/cache/yc-plugin/yc-plugin/<version>/bin/youtube_upload.py \
  --file ep1.mp4 \
  --title "EP1 校園愛情故事" \
  --description-file desc.txt \
  --tags "校園,廣播劇,有聲故事" \
  --thumbnail cover.jpg \
  --playlist "WB故事空間" \
  --publish-at "2026-05-10 20:00" \
  --language zh-TW
```

### 只看會送什麼，不真上傳
```bash
python ... --file ep1.mp4 --title "test" --dry-run
```

## 完整 CLI flags

| Flag | 說明 |
|------|------|
| `--file PATH` | 影片檔案（必填） |
| `--title T` | 標題（預設用檔名） |
| `--description D` | 短描述（直接傳） |
| `--description-file PATH` | 從檔案讀描述（適合長文） |
| `--tags "a,b,c"` | 逗號分隔 tags |
| `--privacy public/unlisted/private` | 預設 `unlisted`，用 `--publish-at` 時自動變 `private` |
| `--category ID` | YouTube 分類 id（預設 22 = People & Blogs） |
| `--language zh-TW` | 影片語言（預設 zh-TW） |
| `--thumbnail PATH` | 封面圖 jpg/png ≤2MB（需驗證頻道） |
| `--playlist NAME_OR_ID` | 播放清單名（自動建立）或 ID |
| `--publish-at "YYYY-MM-DD HH:MM"` | 排程發布時間（本地時區） |
| `--caption PATH` | 字幕檔（不指定會自動偵測同名 .srt / .vtt） |
| `--for-kids` | 標記兒童內容 |
| `--no-auto-caption` | 關閉自動字幕偵測 |
| `--no-verify-processing` | 跳過上傳完的 status 確認 |
| `--dry-run` | 只印 metadata，不真上傳 |
| `--verbose` | debug 訊息 |

## 自動偵測

Plugin 會自動：
- **字幕**：同目錄找 `<video>.srt` 或 `<video>.vtt`，找到自動上傳（`--no-auto-caption` 可關）
- **章節**：影片描述開頭如果有 `00:00 開場` 這種行，YouTube 自動辨識成章節（不需 API）
- **分類**：預設 `22` (People & Blogs)。常見其他：`24` Entertainment、`27` Education、`10` Music、`23` Comedy、`26` Howto

## 系統架構

```
                                Claude Code
                                     │
                          /youtube-upload my.mp4
                                     │
        ┌────────────────────────────┴────────────────────────────┐
        │                                                          │
        ▼                                                          ▼
   commands/youtube-upload.md  ──────►  bin/setup.py        bin/youtube_upload.py
   (對話流程定義)                       (1 次初始化)         (主邏輯)
                                              │                    │
                                              ▼                    ▼
                                       ~/.claude/plugins/data/yc-plugin/
                                         ├── client_secret.json  (你的 OAuth)
                                         ├── yt_token.json       (refresh token)
                                         └── log.txt             (所有上傳紀錄)
                                                                 │
                                                                 ▼
                                                          YouTube Data API v3
                                                          (videos / thumbnails /
                                                           captions / playlists)
```

## 安全與隱私

- ✅ **此 repo 完全不含 secret** — credential / token 全在你電腦的 `~/.claude/plugins/data/yc-plugin/`
- ✅ **每個用戶各自的 OAuth client** — 互不影響、quota 各自承擔
- ✅ **沒有第三方 server** — 直接打 Google API
- ⚠️ **如果 credential 不小心外洩**：去 [credentials 頁面](https://console.cloud.google.com/apis/credentials) 刪掉重建即可

## 換電腦 / 分享給夥伴

### 自己換電腦

整個 `~/.claude/plugins/data/yc-plugin/` 搬過去就好（裡面有 `client_secret.json` + `yt_token.json`）。新機器裝完 plugin 之後直接可用。

或者用內建的 export/import：

```bash
# 舊電腦
python ~/.claude/plugins/cache/yc-plugin/.../bin/setup.py --export ~/Desktop/creds.zip

# 新電腦（裝完 plugin 後）
python ~/.claude/plugins/cache/yc-plugin/.../bin/setup.py --import ~/Downloads/creds.zip
```

### 讓夥伴幫你上傳

例如你給剪輯師處理影片，最後要上你的頻道：

```bash
# 你
python .../bin/setup.py --export creds.zip
# 用安全管道（Signal / 1Password 共享）把 zip 給夥伴

# 夥伴
python .../bin/setup.py --import creds.zip
# 接下來他跑 /youtube-upload，影片會上你的頻道，不需要瀏覽器登入
```

⚠️ **重要安全警告**：

- `creds.zip` 內含你 YouTube 頻道的「**完整鑰匙**」
- 持有這個 zip 的人可以**上傳、刪除、修改**你頻道任何影片
- 90 天內 refresh_token 都有效
- **不要**用 email、Slack、Discord、雲端硬碟分享 — 用 end-to-end 加密（Signal / iMessage / 1Password Secure Sharing）
- 信任崩盤就去 https://myaccount.google.com/permissions 撤銷該 OAuth client，所有人手上的 token 立即失效

## FAQ

### Q1: 我可以上傳到別人的頻道嗎？
不行。OAuth credential 是綁你 Google 帳號 + 你建的 OAuth client。別的頻道要用別的 credential。

### Q2: YouTube 顯示「This app isn't verified」怎麼辦？
點 **Advanced** → **Go to <你的 app> (unsafe)** 繼續就好。是你自己的 app，「unsafe」只是 Google 的標準警告，個人用不需要驗證。

### Q3: 上傳到一半斷網會怎樣？
自動續傳（resumable upload）。最多重試 6 次，間隔 2/4/8/16/32/64 秒。撐不過去會印錯誤；網路恢復後重跑同一指令即可。

### Q4: 「access_denied」是什麼？
你沒把自己加到 OAuth consent screen 的 Test users。回 Step 3 加。

### Q5: token 過期了怎辦？
腳本自動偵測 refresh 失敗 → 刪舊 token → 重跑 OAuth flow。瀏覽器會再跳一次，不用手動。

### Q6: 我每天可以上傳幾部？
YouTube Data API 預設每天 10000 quota units，每次上傳 ~1600。所以 ~6 部/天。
要更多去 [Quotas 頁面](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas) 申請增加。

### Q7: 封面圖不能上傳？
需要**驗證頻道**才能用自定義縮圖。去 https://www.youtube.com/verify 用手機驗證。

### Q8: 排程發布怎麼用？
`--publish-at "2026-05-10 20:00"`（本地時區）。隱私會自動變 `private`，到時間 YouTube 自動轉 `public`。

### Q9: 我想加到播放清單，但清單不存在？
給名字就好，不存在會自動建立。已存在會用同名清單。
要精確指定也可以給 playlist ID（PL... 開頭、20+ 字元）。

### Q10: 字幕怎麼自動上傳？
影片旁邊放同名 `.srt` 或 `.vtt`（例如 `ep1.mp4` + `ep1.srt`），就會自動上。
不想自動：加 `--no-auto-caption`。

### Q11: log 在哪看？
`~/.claude/plugins/data/yc-plugin/log.txt`，每次上傳都會 append。

### Q12: 怎麼重設一切？
```bash
python ~/.claude/plugins/cache/yc-plugin/.../bin/setup.py --reset
```

## 檔案結構

```
yc-plugin/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── commands/youtube-upload.md      # /youtube-upload 命令定義
├── hooks/hooks.json                # SessionStart hook (auto pip install)
├── bin/
│   ├── lib/
│   │   ├── paths.py                # plugin data dir / token / log paths
│   │   ├── console.py              # info/warn/err with file logging
│   │   └── youtube_client.py       # OAuth + upload helpers
│   ├── youtube_upload.py           # 主上傳腳本
│   ├── setup.py                    # 第一次設定
│   ├── youtube_auth.py             # 獨立 OAuth bootstrap
│   └── install_deps.py             # 自動 pip install
├── requirements.txt
├── README.md (你正在看的)
├── CHANGELOG.md
├── CONTRIBUTING.md
├── NAMING.md
└── LICENSE
```

## License

[MIT](LICENSE) — 自由使用、修改、分享。

## Contributing

歡迎 issue / PR！詳見 [CONTRIBUTING.md](CONTRIBUTING.md)。

## Changelog

[CHANGELOG.md](CHANGELOG.md)。

## 作者

[Bob Chen (yanchen184)](https://github.com/yanchen184)

> 這個 plugin 的誕生：原本只是想幫自己自動化上傳廣播劇的流程，做著做著想到「不如分享出來」，於是有了 yc-plugin。如果你也想做類似的工具，歡迎交流。
