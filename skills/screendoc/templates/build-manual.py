#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
/screendoc: HTML 故事手冊建置器（template 版）

把這個檔案複製到專案 e2e/tools/build_manual.py，依需求改 chapters 內容即可。

設計守則（對應 SKILL.md Contracts C1~C4）：
    C1  每張 PNG 必須在 chapters 中註冊
    C2  Shot.anchors 必須來自截圖實際元素，不可憑記憶
    C3  caption 一律敘事體
    C4  title 100% 手寫（不自動截斷）

使用：
    # 對外發布版（base64 內嵌全解析度圖，~12MB）
    python3 build_manual.py <png_dir> <output.html> [--lang zh-TW|en|ja]

    # Phase 4 reviewer 吃的縮圖版（webp 相對路徑，~2MB，省 60-70% token）
    python3 build_manual.py <png_dir> <output.html> --review-mode

--review-mode：
    自動把 png_dir 的圖批次縮成 800x500 WebP@q80，寫到 <png_dir>/thumbnails/，
    HTML 的 <img> 指相對路徑 thumbnails/*.webp 而非 base64 內嵌。
    這是 SKILL.md Phase 3.4 / Phase 4 的 token 優化機制（reviewer 不需要全解析度）。

可發布版手冊輸出：左側 sticky sidebar + 主內容區 + 內嵌 base64 圖。
"""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path
from typing import NamedTuple

# 縮圖參數（Phase 3.4）：reviewer 看得清版面即可，不需要原解析度
THUMB_MAX_W = 800
THUMB_MAX_H = 500
THUMB_QUALITY = 80
THUMB_DIR_NAME = "thumbnails"


# ============================================================================
# 資料模型 — 4 欄位契約
# ============================================================================

class Shot(NamedTuple):
    """單張截圖的契約。"""

    filename: str          # PNG 檔名（必填，必須存在於 png_dir）
    title: str             # 手寫標題，8~14 字（必填，C4）
    caption: str           # 敘事體說明（必填，C3）
    anchors: list[str]     # 必須能在截圖中肉眼確認的元素（必填，C2）


class Chapter(NamedTuple):
    """一章。"""

    title: str
    intro: str
    shots: list[Shot]


# ============================================================================
# Build helpers
# ============================================================================

def img_to_base64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode("ascii")


def build_thumbnails(png_dir: Path) -> Path:
    """把 png_dir 全部 PNG 批次縮成 WebP，寫到 png_dir/thumbnails/。

    回傳 thumbnails 目錄路徑。已存在且較新的縮圖會跳過（增量）。
    Phase 3.4：原圖總計 ~10MB → 縮圖總計 ~1MB（省 ~89%）。
    """
    from PIL import Image  # 延遲 import：只有 --review-mode 才需要 Pillow

    thumb_dir = png_dir / THUMB_DIR_NAME
    thumb_dir.mkdir(exist_ok=True)
    count = 0
    for png in sorted(png_dir.glob("*.png")):
        out = thumb_dir / (png.stem + ".webp")
        if out.exists() and out.stat().st_mtime >= png.stat().st_mtime:
            continue  # 增量：原圖沒更新就不重縮
        with Image.open(png) as im:
            im = im.convert("RGB")
            im.thumbnail((THUMB_MAX_W, THUMB_MAX_H))
            im.save(out, "WEBP", quality=THUMB_QUALITY)
        count += 1
    print(f"🖼️  thumbnails: {count} 張重縮 / {len(list(thumb_dir.glob('*.webp')))} 張總計 → {thumb_dir}")
    return thumb_dir


def shot_html(shot: Shot, png_dir: Path, review_mode: bool = False) -> str:
    p = png_dir / shot.filename
    if not p.exists():
        return (
            f'<section class="shot missing"><h3>{shot.title}</h3>'
            f'<p class="error">缺檔：{shot.filename}</p></section>'
        )
    if review_mode:
        # 相對路徑指縮圖（webp），不內嵌 base64 → HTML 輕、token 省
        thumb_rel = f"{THUMB_DIR_NAME}/{Path(shot.filename).stem}.webp"
        img_src = thumb_rel
    else:
        # 對外發布版：base64 內嵌全解析度
        img_src = f"data:image/png;base64,{img_to_base64(p)}"
    anchors_li = "".join(f"<li>{a}</li>" for a in shot.anchors)
    return f"""
<section class="shot" id="{shot.filename}">
  <h3>{shot.title}</h3>
  <figure>
    <img alt="{shot.title}" src="{img_src}" />
  </figure>
  <p class="caption">{shot.caption}</p>
  <details class="anchors"><summary>畫面對照（{len(shot.anchors)} 個錨點）</summary>
    <ul>{anchors_li}</ul>
  </details>
</section>
""".strip()


def chapter_html(ch: Chapter, png_dir: Path, review_mode: bool = False) -> str:
    shots = "\n".join(shot_html(s, png_dir, review_mode) for s in ch.shots)
    return f"""
<article class="chapter" id="ch-{ch.title}">
  <h2>{ch.title}</h2>
  <p class="intro">{ch.intro}</p>
  {shots}
</article>
""".strip()


def sidebar_html(chapters: list[Chapter]) -> str:
    """C4: title 100% 手寫，不截斷。"""
    items: list[str] = []
    for ch in chapters:
        items.append(f'<li class="ch"><a href="#ch-{ch.title}">{ch.title}</a><ul>')
        for shot in ch.shots:
            items.append(
                f'<li class="shot-link">'
                f'<a href="#{shot.filename}">{shot.title}</a>'
                f"</li>"
            )
        items.append("</ul></li>")
    return f'<nav class="sidebar"><ul>{"".join(items)}</ul></nav>'


# ============================================================================
# CSS / 樣式
# ============================================================================

CSS = """
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "PingFang TC", "Microsoft JhengHei", sans-serif; line-height: 1.7; color: #1a1a1a; background: #fff; }
.layout { display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }
.sidebar { position: sticky; top: 0; align-self: start; max-height: 100vh; overflow-y: auto; padding: 24px 16px; background: #f7f8fa; border-right: 1px solid #e6e8eb; font-size: 14px; }
.sidebar ul { list-style: none; margin: 0; padding: 0; }
.sidebar li.ch { margin-bottom: 14px; font-weight: 600; }
.sidebar li.shot-link { margin: 4px 0 4px 14px; font-weight: 400; line-height: 1.5; }
.sidebar a { color: #2c3e50; text-decoration: none; display: block; padding: 2px 6px; border-radius: 3px; }
.sidebar a:hover { color: #2563eb; background: #eef2ff; }
.main { padding: 32px 48px; max-width: 1100px; }
h1 { font-size: 28px; margin: 0 0 8px; }
h2 { font-size: 22px; margin: 32px 0 12px; padding-bottom: 8px; border-bottom: 2px solid #2563eb; }
h3 { font-size: 16px; margin: 18px 0 8px; }
.intro { color: #4b5563; margin-bottom: 16px; }
.shot { margin: 24px 0 32px; }
.shot figure { margin: 0; border: 1px solid #e6e8eb; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
.shot img { display: block; width: 100%; cursor: zoom-in; transition: opacity 0.15s; }
.shot img:hover { opacity: 0.92; }
.caption { margin: 10px 0 6px; color: #1f2937; }
.anchors { margin-top: 6px; font-size: 13px; color: #4b5563; }
.anchors ul { margin: 6px 0 0 18px; padding: 0; }
.error { color: #b91c1c; }
.shot.missing { padding: 12px; background: #fef2f2; border-left: 3px solid #b91c1c; }

/* Lightbox overlay */
.lightbox { position: fixed; inset: 0; background: rgba(0,0,0,0.88); display: none; align-items: center; justify-content: center; z-index: 9999; cursor: zoom-out; padding: 24px; }
.lightbox.open { display: flex; }
.lightbox img { max-width: 100%; max-height: 100%; box-shadow: 0 8px 32px rgba(0,0,0,0.5); }
.lightbox .hint { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%); color: #fff; font-size: 12px; opacity: 0.7; }

/* Mobile-responsive: collapse sidebar to top toggle */
@media (max-width: 1100px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar { position: relative; max-height: none; border-right: none; border-bottom: 1px solid #e6e8eb; padding: 16px; }
  .sidebar.collapsed ul { display: none; }
  .sidebar-toggle { display: block; cursor: pointer; font-weight: 600; padding: 4px 0; user-select: none; }
  .sidebar-toggle::before { content: "▼ "; font-size: 11px; }
  .sidebar.collapsed .sidebar-toggle::before { content: "▶ "; }
  .main { padding: 20px 16px; }
}
@media (min-width: 1101px) { .sidebar-toggle { display: none; } }

/* Print: black/white friendly, hide sidebar */
@media print {
  .layout { display: block; }
  .sidebar, .lightbox { display: none !important; }
  .main { max-width: 100%; padding: 0; }
  .shot { page-break-inside: avoid; margin: 16px 0; }
  .shot figure { box-shadow: none; border: 1px solid #999; }
  h2 { border-bottom-color: #000; page-break-after: avoid; }
  a { color: #000; text-decoration: none; }
  body { color: #000; background: #fff; }
}
"""

LIGHTBOX_JS = """
(function () {
  var box = document.createElement('div');
  box.className = 'lightbox';
  box.innerHTML = '<img alt="zoom" /><div class="hint">點擊任一處或按 ESC 關閉</div>';
  document.body.appendChild(box);
  var img = box.querySelector('img');
  document.addEventListener('click', function (e) {
    var t = e.target;
    if (t && t.tagName === 'IMG' && t.closest('.shot')) {
      img.src = t.src;
      img.alt = t.alt || '';
      box.classList.add('open');
    } else if (e.target === box || e.target === img) {
      box.classList.remove('open');
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') box.classList.remove('open');
  });
  // Mobile sidebar toggle
  var sidebar = document.querySelector('.sidebar');
  if (sidebar) {
    var toggle = document.createElement('div');
    toggle.className = 'sidebar-toggle';
    toggle.textContent = '目錄';
    sidebar.insertBefore(toggle, sidebar.firstChild);
    if (window.matchMedia('(max-width: 1100px)').matches) sidebar.classList.add('collapsed');
    toggle.addEventListener('click', function () { sidebar.classList.toggle('collapsed'); });
  }
})();
"""


# ============================================================================
# 主流程
# ============================================================================

def build(
    chapters: list[Chapter],
    png_dir: Path,
    out: Path,
    lang: str = "zh-TW",
    review_mode: bool = False,
) -> None:
    if review_mode:
        build_thumbnails(png_dir)  # 先批次縮圖，HTML 再指相對路徑
    body_chs = "\n".join(chapter_html(c, png_dir, review_mode) for c in chapters)
    sidebar = sidebar_html(chapters)
    html = f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8" />
<title>產品操作手冊</title>
<style>{CSS}</style>
</head>
<body>
<div class="layout">
{sidebar}
<main class="main">
<h1>產品操作手冊</h1>
{body_chs}
</main>
</div>
<script>{LIGHTBOX_JS}</script>
</body>
</html>"""
    out.write_text(html, encoding="utf-8")
    mode_tag = "review-mode 縮圖版" if review_mode else "發布版 base64"
    size_kb = out.stat().st_size / 1024
    print(
        f"✅ wrote {out} [{mode_tag}] "
        f"({len(chapters)} chapters, {sum(len(c.shots) for c in chapters)} shots, HTML {size_kb:.0f}KB)"
    )


# ============================================================================
# 範例 chapters — 真實使用時把這段換成自己的
# ============================================================================

EXAMPLE_CHAPTERS: list[Chapter] = [
    Chapter(
        title="第一章：建立第一個專案",
        intro="從登入開始，一步步走完從零到一個可用專案的旅程。",
        shots=[
            Shot(
                filename="01-01-home.png",
                title="首頁總覽",
                caption="登入後首先看到的工作空間，左側是專案樹，主區塊是最近文件。",
                anchors=["左側專案樹", "主區塊『最近文件』標題", "右上角使用者名稱"],
            ),
        ],
    ),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("png_dir", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--lang", default="zh-TW")
    ap.add_argument(
        "--review-mode",
        action="store_true",
        help="產縮圖版（webp 相對路徑，給 Phase 4 reviewer 吃，省 60-70% token）",
    )
    args = ap.parse_args()

    if not args.png_dir.exists():
        print(f"❌ png_dir not found: {args.png_dir}", file=sys.stderr)
        return 1

    build(EXAMPLE_CHAPTERS, args.png_dir, args.out, args.lang, review_mode=args.review_mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
