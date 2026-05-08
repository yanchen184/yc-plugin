"""Output formatters for tabular data — table / json / markdown.

Used by /youtube-list, /youtube-stats, /youtube-update list output.

Column spec is `(key, header, width)` for table mode; `(key, header)` for markdown.
"""
import json
from typing import Iterable


def display_width(s: str) -> int:
    """Approximate terminal display width — CJK characters count as 2 columns."""
    w = 0
    for c in s:
        o = ord(c)
        if (
            0x1100 <= o <= 0x115F or
            0x2E80 <= o <= 0x9FFF or
            0xA000 <= o <= 0xA4CF or
            0xAC00 <= o <= 0xD7A3 or
            0xF900 <= o <= 0xFAFF or
            0xFE30 <= o <= 0xFE4F or
            0xFF00 <= o <= 0xFF60 or
            0xFFE0 <= o <= 0xFFE6
        ):
            w += 2
        else:
            w += 1
    return w


def truncate(s: str, width: int, ellipsis: str = "…") -> str:
    """Truncate to fit display width, append ellipsis if cut."""
    if display_width(s) <= width:
        return s
    out = ""
    used = 0
    cap = width - display_width(ellipsis)
    for c in s:
        cw = 2 if display_width(c) == 2 else 1
        if used + cw > cap:
            break
        out += c
        used += cw
    return out + ellipsis


def pad(s: str, width: int) -> str:
    """Right-pad string to display width (CJK-aware)."""
    extra = width - display_width(s)
    return s + (" " * extra) if extra > 0 else s


def as_table(rows: list[dict], columns: list[tuple[str, str, int]]) -> str:
    """Render rows as a fixed-width table. columns = [(key, header, width), ...]."""
    if not rows:
        return "(no rows)"
    lines = []
    header = "  ".join(pad(h, w) for _, h, w in columns)
    lines.append(header)
    lines.append("-" * display_width(header))
    for row in rows:
        cells = []
        for k, _, w in columns:
            v = row.get(k, "")
            cells.append(pad(truncate(str(v), w), w))
        lines.append("  ".join(cells))
    return "\n".join(lines)


def as_json(rows: list[dict]) -> str:
    return json.dumps(rows, ensure_ascii=False, indent=2)


def as_markdown(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    """Render as GitHub-flavored markdown table."""
    if not rows:
        return "(no rows)"
    keys = [k for k, _ in columns]
    headers = [h for _, h in columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        cells = [str(row.get(k, "")).replace("|", "\\|") for k in keys]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render(rows: list[dict], format: str, columns: list[tuple[str, str, int]]) -> str:
    """Dispatch to one of the renderers by format name."""
    if format == "json":
        return as_json(rows)
    if format == "markdown":
        return as_markdown(rows, [(k, h) for k, h, _ in columns])
    return as_table(rows, columns)


def format_int(n) -> str:
    """1,234 with thousand separator. Accepts str or int; returns '-' on parse fail."""
    if n is None or n == "":
        return "-"
    try:
        return f"{int(n):,}"
    except (ValueError, TypeError):
        return str(n)


def format_date(iso: str) -> str:
    """'2026-05-08T15:37:04Z' → '2026-05-08'."""
    if not iso:
        return ""
    return iso[:10]
