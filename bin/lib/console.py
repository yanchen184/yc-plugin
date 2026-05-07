"""Console / logging helpers for yc-plugin.

- Forces UTF-8 stdout on Windows cp950
- Provides info/warn/err/ok with consistent prefixes
- Appends to log file in plugin data dir for forensics
"""
import datetime
import io
import sys
from pathlib import Path

from .paths import log_file

_log_initialized = False
_verbose = False


def _init_stdout_utf8():
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# Force UTF-8 immediately on module import — argparse --help fires before init()
_init_stdout_utf8()


def _init_log():
    global _log_initialized
    if _log_initialized:
        return
    try:
        log_file().parent.mkdir(parents=True, exist_ok=True)
        with log_file().open("a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.datetime.now().isoformat(timespec='seconds')} ---\n")
        _log_initialized = True
    except Exception:
        # logging is best-effort; never crash the upload because of log issues
        pass


def init(verbose: bool = False):
    """Call once at script start."""
    global _verbose
    _verbose = verbose
    _init_stdout_utf8()
    _init_log()


def _emit(level: str, msg: str):
    line = f"[{level}] {msg}"
    print(line, flush=True)
    try:
        with log_file().open("a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {line}\n")
    except Exception:
        pass


def info(msg: str):
    print(msg, flush=True)
    try:
        with log_file().open("a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {msg}\n")
    except Exception:
        pass


def ok(msg: str):
    _emit("OK", msg)


def warn(msg: str):
    _emit("WARN", msg)


def err(msg: str, hint: str = ""):
    """Print error with optional next-step hint, then exit 1."""
    _emit("ERROR", msg)
    if hint:
        print(f"   ↪ {hint}", flush=True)
        try:
            with log_file().open("a", encoding="utf-8") as f:
                f.write(f"   ↪ {hint}\n")
        except Exception:
            pass
    sys.exit(1)


def debug(msg: str):
    if _verbose:
        _emit("DEBUG", msg)
