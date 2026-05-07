# yc-plugin

> Claude Code 插件 — 把日常重複的內容工作自動化。
> 目前提供：**`/youtube-upload`** 一鍵上傳影片到 YouTube。

## 為什麼用這個

- 一行指令上傳影片到自己的頻道，不用打開 YouTube Studio 拖檔
- OAuth 自動處理，第一次裝完之後一勞永逸
- Resumable upload — 中途斷網會自動續傳，不用整段重來
- 上傳完自動驗證 YouTube 後台處理狀態，確認影片真的可以播
- 100% 用你自己的 Google 帳號 / 自己的 OAuth credential，沒有共用授權、沒有第三方 server

## 安裝

在 Claude Code 裡輸入：

```
/plugin marketplace add yanchen184/yc-plugin
/plugin install yc-plugin@yc-plugin
```

第一次跑會自動 `pip install` 必要的 Python 套件（`google-api-python-client`, `google-auth-oauthlib`），不用手動裝。

## 第一次設定（一次性，~3 分鐘）

第一次用 `/youtube-upload` 時，Claude 會引導你拿一份 OAuth credential。如果你想先做好，照下面步驟：

### 1. Google Cloud Console 開個 project

打開 [Google Cloud Console](https://console.cloud.google.com/)，左上角點下拉選單 → **NEW PROJECT** → 任意名字（例如 `yc-plugin`）→ **CREATE**。

### 2. 啟用 YouTube Data API v3

左側選單 → **APIs & Services** → **Library** → 搜 `YouTube Data API v3` → 點進去 → **ENABLE**。

### 3. 設定 OAuth consent screen

左側 → **APIs & Services** → **OAuth consent screen** → 選 **External** → **CREATE**。

填這幾個欄位：
- **App name**：任意，例如 `yc-plugin`
- **User support email**：你的 Gmail
- **Developer contact information**：你的 Gmail
- 其他空白都可以，下一步

**Scopes** 那頁不用加任何 scope，直接 SAVE AND CONTINUE。

**Test users** 那頁點 `+ ADD USERS`，把你自己的 Gmail 加進去。

> 為什麼要加 Test user？因為你的 app 沒過 Google 驗證，預設只有 test user 可以授權。每個 app 上限 100 個 test user。如果只有你自己用，加你一個就夠。

### 4. 建立 OAuth client

左側 → **APIs & Services** → **Credentials** → **+ CREATE CREDENTIALS** → **OAuth client ID**。

- **Application type**：選 **Desktop app**（很重要，不要選 Web app）
- **Name**：任意

點 **CREATE**，跳出視窗點 **DOWNLOAD JSON**。

### 5. 把 JSON 檔放在固定位置

把下載的 JSON 檔重新命名成你記得住的，例如 `youtube_client_secret.json`，放到你常用的目錄，例如：
- Mac/Linux: `~/Documents/youtube_client_secret.json`
- Windows: `C:\Users\你\Documents\youtube_client_secret.json`

接下來在 Claude Code 裡跑 `/youtube-upload <影片路徑>`，第一次會問你 client_secret 檔案在哪，貼上絕對路徑就好。

## 使用

```
/youtube-upload <影片路徑> [標題]
```

範例：

```
/youtube-upload D:/videos/episode_1.mp4
/youtube-upload D:/videos/episode_1.mp4 "EP1 — 校園愛情故事"
/youtube-upload ~/Movies/test.mp4 "測試"
```

如果沒帶標題，Claude 會問你標題、隱私、描述、tags。沒填的就用 `.env` 裡的預設。

### 預設值改怎麼改

`.env` 在你的 plugin data dir：
- Mac/Linux: `~/.claude/plugins/data/yc-plugin/.env`
- Windows: `%USERPROFILE%\.claude\plugins\data\yc-plugin\.env`

格式長這樣：
```
YOUTUBE_CLIENT_SECRET_PATH=/Users/you/Documents/youtube_client_secret.json
YOUTUBE_DEFAULT_PRIVACY=unlisted
YOUTUBE_DEFAULT_CATEGORY=22
YOUTUBE_DEFAULT_TAGS=
YOUTUBE_CHANNEL_NAME=
```

或者重跑 setup：
```
python ~/.claude/plugins/cache/yc-plugin/yc-plugin/<version>/bin/setup.py
```

### 直接從命令列用（不透過 Claude）

```bash
python ~/.claude/plugins/cache/yc-plugin/yc-plugin/<version>/bin/youtube_upload.py \
  --file path/to/video.mp4 \
  --title "標題" \
  --privacy unlisted \
  --description "描述..." \
  --tags "tag1,tag2"
```

## 安全與隱私

- **此 repo 完全不含 secret** — 你的 OAuth credential 跟 token 全部存在你電腦的 `~/.claude/plugins/data/yc-plugin/`，永遠不會進 git、不會上傳到任何地方
- **每個用戶各自的 OAuth client** — 你建的 OAuth credential 只能上傳到你自己的 YouTube channel；別人裝這個 plugin 也是用他們自己的 credential
- **如果你的 credential 不小心外洩**：去 [credentials 頁面](https://console.cloud.google.com/apis/credentials) 刪掉重建即可

## 疑難排解

### 「access_denied」錯誤
你沒把自己加到 OAuth consent screen 的 Test users。回去 step 3 加。

### 「This app isn't verified」警告
正常的，因為你的 app 沒過 Google 驗證（個人用不需要驗證）。點 **Advanced** → **Go to <你的 app> (unsafe)** 繼續就好。是你自己的 app，「unsafe」只是 Google 的標準警告。

### 上傳到一半斷網
Resumable upload 會自動重試最多 6 次，每次間隔指數退避（2/4/8/16/32/64 秒）。撐不過去就會印錯誤；網路恢復後重跑同一個指令即可。

### token 過期 / 被 revoke
腳本會自動偵測到 refresh 失敗，刪掉舊 token，重跑一次 OAuth flow。瀏覽器會再跳一次。

### Quota 不夠用
YouTube Data API 預設每天 10000 quota units，每次上傳消耗 1600。所以一天可以上 ~6 部影片。需要更多去 [Quotas 頁面](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas) 申請增加。

## 檔案結構

```
yc-plugin/
├── .claude-plugin/
│   ├── plugin.json          # plugin metadata
│   └── marketplace.json     # marketplace 註冊
├── commands/
│   └── youtube-upload.md    # /youtube-upload 命令定義
├── hooks/
│   └── hooks.json           # SessionStart hook (auto pip install)
├── bin/
│   ├── youtube_upload.py    # 主上傳腳本
│   ├── setup.py             # 互動式 .env 設定
│   ├── youtube_auth.py      # 獨立 OAuth bootstrap
│   └── install_deps.py      # SessionStart hook 用
├── requirements.txt         # Python 依賴
├── .env.example             # 設定範本
├── README.md                # 你正在看的這份
├── CHANGELOG.md             # 版本更新紀錄
└── LICENSE                  # MIT
```

## License

MIT — 自由使用、修改、分享。

## Changelog

見 [CHANGELOG.md](./CHANGELOG.md)。

## 作者

[Bob Chen (yanchen184)](https://github.com/yanchen184)
