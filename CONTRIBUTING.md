# Contributing

歡迎貢獻 yc-plugin！

## 怎麼開始

1. Fork 這個 repo
2. Clone 你的 fork：`git clone https://github.com/<你>/yc-plugin.git`
3. 建一個 feature branch：`git checkout -b feat/your-feature`
4. 改 code
5. 跑測試（見下方）
6. 開 PR

## 開發環境

```bash
# 裝 deps
pip install -r requirements.txt

# 跑 setup（用你自己的 OAuth credential）
python bin/setup.py --client-secret /path/to/client_secret.json

# 跑 dry-run 測試
python bin/youtube_upload.py --file test.mp4 --title "test" --dry-run
```

## 測試

目前 plugin 沒有自動化 test suite — 因為 Google OAuth 很難 mock 得有意義。實際測試方式：

1. **Syntax check**：`python -m py_compile bin/**/*.py`
2. **Dry-run**：所有 PR 至少要跑過一次 dry-run 看 metadata payload 對不對
3. **真上傳測試**：用 `--privacy private` 上傳一個小檔案到自己頻道測過

## 程式風格

- 簡潔 > 完整 — 一個 function 做一件事
- 訊息全用繁體中文（user-facing）；註解用英文
- 錯誤訊息一定要有「下一步」hint（`console.err(msg, hint)`）
- `bin/lib/` 放共用邏輯，`bin/*.py` 各自一個 entry point
- 路徑用 `pathlib.Path`，不用 `os.path`
- 不寫不必要的註解

## Commit 訊息

[Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>: <description>

types: feat | fix | refactor | docs | test | chore | perf
```

例：
- `feat: add --thumbnail flag for custom video thumbnail`
- `fix: handle 403 on thumbnail upload (unverified channel)`
- `docs: add Q9 about playlist auto-create`

## 加新 command

跟著 [NAMING.md](NAMING.md) 命名規則：
1. `commands/<area>-<verb>.md` — 命令定義
2. `bin/<area>_<verb>.py` — 對應 Python entry
3. 共用邏輯放 `bin/lib/<area>_client.py`
4. 更新 README + CHANGELOG

## 報 bug

開 [issue](https://github.com/yanchen184/yc-plugin/issues/new/choose) 用 bug template。請附：

- 作業系統 + Python 版本
- 跑哪個指令
- 完整 error 訊息（`~/.claude/plugins/data/yc-plugin/log.txt` 末尾貼出來）
- 預期行為 vs 實際行為

## 提功能

開 issue 用 feature template 講清楚：

- 你想做什麼
- 為什麼現在的做法不夠
- 你會怎麼用（指令範例）

## License

貢獻的 code 自動以 [MIT License](LICENSE) 釋出。
