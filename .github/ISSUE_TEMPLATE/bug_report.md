---
name: Bug report
about: 回報 plugin 出錯
title: "[bug] "
labels: bug
---

## 環境
- OS:                          (例: Windows 11 / macOS 14 / Ubuntu 22)
- Python 版本:                 (跑 `python --version`)
- yc-plugin 版本:              (見 plugin.json 或 git log)

## 怎麼觸發
跑了什麼指令？

```
/youtube-upload ...
```

或直接跑：
```bash
python bin/youtube_upload.py --file ...
```

## 預期行為


## 實際行為


## 完整錯誤訊息
貼最後 30 行（`~/.claude/plugins/data/yc-plugin/log.txt` 也歡迎附）：

```

```

## 已試過什麼
- [ ] 重跑一次
- [ ] `python bin/setup.py --reset` 後重設
- [ ] 確認網路通暢
- [ ] 確認 client_secret.json 沒過期
