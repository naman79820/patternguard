"""Record tool versions into report/environment.json (values are read, not typed)."""
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip() or None
    except Exception:
        return None


def main():
    from importlib.metadata import version, PackageNotFoundError
    pkgs = {}
    for p in ["playwright", "pandas", "scikit-learn", "matplotlib", "numpy", "python-docx", "torch", "transformers", "datasets"]:
        try:
            pkgs[p] = version(p)
        except PackageNotFoundError:
            pkgs[p] = None
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chromium", headless=True)
        chromium = b.version
        b.close()
    env = {
        "python": sys.version.split()[0],
        "node": run(["node", "--version"]),
        "chromium": chromium,
        "playwright": pkgs["playwright"],
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "machine": platform.machine(),
        "processor": platform.processor(),
        "git": run(["git", "--version"]),
        "python_packages": pkgs,
    }
    out = ROOT / "report" / "environment.json"
    out.write_text(json.dumps(env, indent=2), encoding="utf-8")
    print(json.dumps(env, indent=2))


if __name__ == "__main__":
    main()
