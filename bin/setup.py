"""yc-plugin first-time setup.

One job: copy the user's OAuth client_secret JSON into the plugin data dir.
After this, /youtube-upload knows where to find it without any config.

Usage:
  python setup.py                              # interactive
  python setup.py --client-secret PATH         # non-interactive
  python setup.py --show                       # report current state
  python setup.py --reset                      # delete client_secret + token
"""
import argparse
import json
import shutil
from pathlib import Path

from lib import console
from lib.paths import client_secret_file, plugin_data_dir, token_file


SETUP_INSTRUCTIONS = """
yc-plugin 第一次設定
=====================

需要一份 Google OAuth client_secret JSON（一次性，~3 分鐘）：

  1. https://console.cloud.google.com/
  2. 建一個 project（任意名字）
  3. APIs & Services → Library → 搜 "YouTube Data API v3" → Enable
  4. APIs & Services → OAuth consent screen → External → Create
     填 App name / Support email / Developer contact
     Test users 加你自己的 Gmail
  5. APIs & Services → Credentials → Create Credentials → OAuth client ID
     Application type: Desktop app → Create → Download JSON

把下載的 JSON 檔案絕對路徑貼下面。
"""


def validate_client_secret(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"檔案不存在: {path}"
    if path.is_dir():
        return False, f"是目錄不是檔案: {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if "installed" not in data and "web" not in data:
            return False, "JSON 格式不對 — 缺 'installed' 或 'web' key。確認下載的是 Desktop app credentials。"
        if "web" in data and "installed" not in data:
            return False, "下載的是 Web app credentials — yc-plugin 需要 Desktop app 類型。"
        return True, "OK"
    except Exception as e:
        return False, f"無法解析 JSON: {e}"


def install_client_secret(src: Path) -> Path:
    dst = client_secret_file()
    shutil.copyfile(src, dst)
    return dst


def show_state() -> None:
    cs = client_secret_file()
    tok = token_file()
    print(f"data dir: {plugin_data_dir()}")
    print(f"  client_secret.json: {'OK' if cs.exists() else '(missing — run setup)'}")
    print(f"  yt_token.json:      {'OK (already authenticated)' if tok.exists() else '(missing — first upload triggers browser auth)'}")


def reset() -> None:
    cs = client_secret_file()
    tok = token_file()
    removed = []
    for f in (cs, tok):
        if f.exists():
            f.unlink()
            removed.append(str(f))
    if removed:
        print("removed:")
        for f in removed:
            print(f"  {f}")
    else:
        print("nothing to remove (already clean)")


def interactive() -> Path:
    print(SETUP_INSTRUCTIONS)
    while True:
        try:
            raw = input("client_secret.json 絕對路徑: ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            console.err("中斷 setup", "")
        if not raw:
            print("不能空白，再試一次。")
            continue
        path = Path(raw).expanduser()
        ok, msg = validate_client_secret(path)
        if ok:
            return path
        print(f"  [X] {msg}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--client-secret", help="Absolute path to OAuth client_secret JSON")
    p.add_argument("--show", action="store_true", help="Show current setup state")
    p.add_argument("--reset", action="store_true",
                   help="Delete client_secret.json and yt_token.json (requires re-setup)")
    args = p.parse_args()

    console.init()

    if args.show:
        show_state()
        return

    if args.reset:
        reset()
        return

    if args.client_secret:
        path = Path(args.client_secret).expanduser()
        ok, msg = validate_client_secret(path)
        if not ok:
            console.err(
                f"client_secret invalid: {msg}",
                "去 Google Cloud Console 重下載一份 (Application type 必須是 Desktop app)",
            )
    else:
        path = interactive()

    dst = install_client_secret(path)
    console.ok(f"client_secret 已複製到: {dst}")
    console.info("第一次跑 /youtube-upload 時會跳出瀏覽器要 Google 登入授權。")


if __name__ == "__main__":
    main()
