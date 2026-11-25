"""Shared helpers for PatternGuard browser tests.

- serve_repo(): serves the repository root with http.server on a free local port.
- launch(ext_dir): persistent Chromium context with the unpacked extension loaded
  (new headless mode via channel="chromium").
- summary(page): reads the JSON summary the content script writes to
  <html data-patternguard>. Reading it does not change detection.
"""
import contextlib
import functools
import http.server
import json
import os
import shutil
import socket
import tempfile
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extension"


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def serve_repo():
    port = free_port()
    handler = functools.partial(_QuietHandler, directory=str(ROOT))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()


@contextlib.contextmanager
def launch(ext_dir=EXT, headless=True):
    user_dir = tempfile.mkdtemp(prefix="pg-profile-")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_dir,
            channel="chromium",
            headless=headless,
            args=[f"--disable-extensions-except={ext_dir}", f"--load-extension={ext_dir}"],
            viewport={"width": 1280, "height": 900},
        )
        try:
            sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker", timeout=15000)
            ctx.pg_sw = sw
            ctx.pg_ext_id = sw.url.split("/")[2]
            yield ctx
        finally:
            ctx.close()
            shutil.rmtree(user_dir, ignore_errors=True)


def clear_storage(ctx):
    ctx.pg_sw.evaluate("chrome.storage.local.clear()")


def summary(page):
    raw = page.evaluate("document.documentElement.getAttribute('data-patternguard')")
    return json.loads(raw) if raw else None


def wait_summary(page, after_ms=None, href_contains=None, timeout=15.0, settle=0.0):
    """Wait until a scan summary exists that was produced after `after_ms`
    (epoch ms) and whose href contains `href_contains`. Optional settle time lets
    a throttled follow-up rescan finish."""
    end = time.time() + timeout
    s = None
    while time.time() < end:
        s = summary(page)
        if s and (after_ms is None or s["scanAt"] >= after_ms) and (href_contains is None or href_contains in s["href"]):
            break
        time.sleep(0.1)
    else:
        raise TimeoutError(f"no PatternGuard summary (last={s and s.get('href')})")
    if settle:
        time.sleep(settle)
        s = summary(page)
    return s


def now_ms():
    return int(time.time() * 1000)


def categories(s):
    return sorted(d["key"] for d in s["detections"])


def copy_extension(config_patch=None):
    """Copy extension/ to a temp dir, optionally patching config.json. Returns path."""
    d = Path(tempfile.mkdtemp(prefix="pg-ext-")) / "extension"
    shutil.copytree(EXT, d)
    if config_patch is not None:
        cfg_path = d / "config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        config_patch(cfg)
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return d
