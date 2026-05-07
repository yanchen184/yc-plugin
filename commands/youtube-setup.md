---
description: yc-plugin 設定管理 — 初始化、查看狀態、匯出/匯入 OAuth credentials、重設
argument-hint: [show|init|export|import|reset] [path]
---

# /youtube-setup

統一管理 yc-plugin 的 OAuth credentials。

## Parse arguments

`$ARGUMENTS` 第一個 token 是 sub-command，其餘是參數：

- `(空)` 或 `show` — 顯示當前 setup 狀態
- `init` — 第一次設定（OAuth client_secret）
- `export <path>` — 打包 credentials 成 zip
- `import <path>` — 從 zip 還原 credentials
- `reset` — 清空所有 credentials（要二次確認）

範例：
- `/youtube-setup`                                    顯示狀態
- `/youtube-setup init`                               走 OAuth 設定流程
- `/youtube-setup export ~/Desktop/creds.zip`         打包
- `/youtube-setup import ~/Downloads/creds.zip`       還原
- `/youtube-setup reset`                              清空（要確認）

## Workflow

### show / no args

跑：

```bash
python "${CLAUDE_PLUGIN_ROOT}/bin/setup.py" --show
```

把輸出貼給使用者，然後告訴他可用的 actions：

```
可用操作：
  /youtube-setup init                            第一次設定
  /youtube-setup export <path-to-zip>            打包 credentials
  /youtube-setup import <path-to-zip>            從 zip 還原
  /youtube-setup reset                           清空（危險）

要做哪個？
```

### init

走 `/youtube-upload` 命令裡 Step 3 一樣的流程：解釋 Google Cloud Console 6 步驟，等使用者貼路徑，然後跑：

```bash
python "${CLAUDE_PLUGIN_ROOT}/bin/setup.py" --client-secret "<USER_PROVIDED_PATH>"
```

如果失敗就把錯誤告訴使用者協助修正。成功就確認「[OK] 設定完成。可以跑 /youtube-upload 了。」

### export <path>

如果使用者沒給 path，問他：「export 到哪？例如 `~/Desktop/yc-plugin-creds.zip`」

跑：

```bash
python "${CLAUDE_PLUGIN_ROOT}/bin/setup.py" --export "<PATH>"
```

腳本本身會印安全警告，**完整原樣**轉達給使用者，並補一句：

> ⚠️ 這個 zip 等於你 YouTube 頻道的鑰匙。
> - 用 end-to-end 加密管道傳（Signal、iMessage、1Password Secure Sharing）
> - **不要**用 email、Slack、Discord、雲端硬碟
> - 信任出問題就去 https://myaccount.google.com/permissions 撤銷 OAuth client

### import <path>

如果使用者沒給 path，問他：「zip 在哪？例如 `~/Downloads/wb_creds.zip`」

跑：

```bash
python "${CLAUDE_PLUGIN_ROOT}/bin/setup.py" --import "<PATH>"
```

成功就告訴使用者：「[OK] 已還原。直接跑 /youtube-upload <video> 就會上到原帳號的頻道，不用瀏覽器登入。」

### reset

**危險操作。** 先二次確認：

> 這會刪掉 client_secret.json + yt_token.json，下次要重新 setup。確定？(yes/no)

得到 `yes` / `確定` / `y` 才跑：

```bash
python "${CLAUDE_PLUGIN_ROOT}/bin/setup.py" --reset
```

任何其他回應都當取消，告訴使用者「已取消」。

## Constraints

- **絕不** echo `client_secret.json` 或 `yt_token.json` 內容
- export 的 zip path 預設不要放在公共目錄（提醒使用者放 `~/Desktop` 或 `~/Documents`，避免 `/tmp` 被別 process 看到）
- import 失敗時把腳本錯誤訊息**完整**傳給使用者，不要包裝
- reset 一定要二次確認，沒有 `--force` 或 `--yes` 跳過機制
