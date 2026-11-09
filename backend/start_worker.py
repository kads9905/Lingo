"""Runs the PyTorch model worker on this computer and exposes it through a free Cloudflare tunnel.

Run from the backend folder:  python start_worker.py
Keep the window open during the demo. Ctrl+C stops both processes.
"""
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx

PORT = 7861
ROOT = Path(__file__).resolve().parent
CLOUDFLARED = [
    r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
    r"C:\Program Files\cloudflared\cloudflared.exe",
]


def worker_key():
    env = ROOT / ".env"
    for line in env.read_text(encoding="utf-8").splitlines() if env.exists() else []:
        key, _, value = line.partition("=")
        if key.strip() == "WORKER_KEY" and value.strip():
            return value.strip()
    sys.exit("Add WORKER_KEY to backend/.env first. Render needs the same value.")


def find_cloudflared():
    found = shutil.which("cloudflared") or next((p for p in CLOUDFLARED if Path(p).exists()), None)
    if not found:
        sys.exit("cloudflared is not installed. Run: winget install --id Cloudflare.cloudflared")
    return found


def wait_for(url, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=5).status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(2)
    return False


def main():
    key = worker_key()
    tunnel_binary = find_cloudflared()
    env = {**os.environ, "WORKER_KEY": key, "PYTHONIOENCODING": "utf-8"}

    print("Starting the model worker…")
    worker = subprocess.Popen(
        [sys.executable, "-W", "ignore", "-m", "uvicorn", "ml_worker.app:app", "--port", str(PORT), "--log-level", "warning"],
        cwd=ROOT,
        env=env,
    )
    if not wait_for(f"http://localhost:{PORT}/health", 60):
        worker.terminate()
        sys.exit("The worker did not start. Check the messages above.")

    print("Loading MarianMT and MiniLM so the first request is fast…")
    httpx.post(
        f"http://localhost:{PORT}/translate", json={"text": "Hello.", "lang": "hi"}, headers={"X-Worker-Key": key}, timeout=300
    )
    httpx.post(
        f"http://localhost:{PORT}/adequacy",
        json={"source": "Hello.", "translation": "नमस्ते।"},
        headers={"X-Worker-Key": key},
        timeout=300,
    )

    print("Opening the Cloudflare tunnel…")
    tunnel = subprocess.Popen(
        [tunnel_binary, "tunnel", "--no-autoupdate", "--url", f"http://localhost:{PORT}"],
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    url = None
    for line in tunnel.stderr:
        match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
        if match:
            url = match.group(0)
            break
    if not url:
        worker.terminate()
        sys.exit("The tunnel did not start. Check your internet connection and try again.")
    # Keep draining the tunnel's log so it never blocks on a full pipe.
    threading.Thread(target=lambda: [None for _ in tunnel.stderr], daemon=True).start()

    reachable = wait_for(f"{url}/health", 60)
    print()
    print("=" * 64)
    print(" Model worker is live" if reachable else " Tunnel opened, but the health check has not passed yet")
    print()
    print(" On Render, set these environment variables, then save:")
    print(f"   ML_WORKER_URL = {url}")
    print("   WORKER_KEY    = the WORKER_KEY value in backend/.env")
    print()
    print(" The tunnel address changes every time this script starts.")
    print(" Keep this window open. Press Ctrl+C to stop.")
    print("=" * 64)

    try:
        while worker.poll() is None and tunnel.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        tunnel.terminate()
        worker.terminate()
        print("Stopped.")


if __name__ == "__main__":
    main()
