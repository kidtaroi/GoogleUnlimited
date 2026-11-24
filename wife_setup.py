#!/usr/bin/env python3
"""User-friendly Google Photos sign-in helper for GoogleUnlimited.

This app opens a private, temporary browser profile for the Google Embedded
Setup sign-in page. It reads only the `oauth_token` cookie from that isolated
session, exchanges it with the bundled gotohp CLI, and configures the watcher.
It never reads cookies from an existing browser session and never sends the
token anywhere except the local gotohp config file.
"""

import os
import queue
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path

from playwright.sync_api import sync_playwright

SIGNIN_URL = "https://accounts.google.com/embedded/setup/v2/android"
TOKEN_COOKIE = "oauth_token"
REPO = Path(__file__).resolve().parent
DROP_DIR = Path.home() / "Google Photos Uploads"
DOWNLOAD_ALIAS = Path.home() / "Downloads" / "Photo Backup Drop"
GOTOHP_BIN = REPO / "gotohp-cli-macos-universal"
WATCH_SCRIPT = REPO / "google-unlimited.sh"

messages = queue.Queue()
stop_event = threading.Event()


def emit(text):
    messages.put(text)


def run(cmd, **kwargs):
    return subprocess.run(cmd, text=True, capture_output=True, **kwargs)


def ensure_setup():
    if not GOTOHP_BIN.exists():
        emit("First-time setup: installing dependencies and the uploader...")
        result = run([str(WATCH_SCRIPT), "setup"], cwd=REPO)
        if result.returncode != 0:
            raise RuntimeError(f"Setup failed: {result.stderr[-400:]}")
    if not GOTOHP_BIN.exists():
        raise RuntimeError("Uploader binary is missing after setup.")


def capture_token():
    """Open an isolated browser and wait for the sign-in cookie."""
    emit("Opening a private sign-in window. Use the window that appears.")
    with tempfile.TemporaryDirectory(prefix="gu-wife-browser-") as profile:
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                profile, headless=False, args=["--no-first-run"]
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(SIGNIN_URL, timeout=60_000, wait_until="domcontentloaded")
                emit("Sign in, click I agree, then come back here. The page may keep spinning; that is normal.")
                deadline = time.time() + 300
                while time.time() < deadline and not stop_event.is_set():
                    for cookie in context.cookies():
                        if cookie.get("name") == TOKEN_COOKIE and "accounts.google.com" in cookie.get("domain", ""):
                            return cookie.get("value")
                    time.sleep(1)
                return None
            finally:
                context.close()


def configure(token):
    emit("Sign-in detected. Saving the account locally...")
    ensure_setup()

    result = run([str(GOTOHP_BIN), "creds", "add", "-"], input=token + "\n", cwd=REPO)
    if result.returncode != 0:
        raise RuntimeError(f"Could not save credentials: {result.stderr[-400:]}")

    config = Path.home() / "Library/Application Support/gotohp/gotohp.config"
    if config.exists():
        os.chmod(config, 0o600)

    DROP_DIR.mkdir(parents=True, exist_ok=True)
    # Downloads is protected by macOS privacy controls, which block the
    # background watcher. Keep the real folder in the home directory and give
    # her a convenient alias inside Downloads to drag photos into.
    DOWNLOAD_ALIAS.parent.mkdir(parents=True, exist_ok=True)
    if not DOWNLOAD_ALIAS.exists():
        DOWNLOAD_ALIAS.symlink_to(DROP_DIR, target_is_directory=True)

    (REPO / "watch_dirs.txt").write_text(
        "# Only this folder is monitored and backed up.\n" + str(DROP_DIR) + "\n"
    )

    emit("Starting background backups...")
    result = run([str(WATCH_SCRIPT), "enable"], cwd=REPO)
    if result.returncode != 0:
        raise RuntimeError(f"Could not start the watcher: {result.stderr[-400:]}")

    accounts = run([str(GOTOHP_BIN), "creds", "list"], cwd=REPO)
    emit("Done. Active account:")
    emit(accounts.stdout.strip() or "(see gotohp creds list)")
    emit(f"Drop photos into the 'Photo Backup Drop' folder in Downloads.")
    emit(f"(That is a shortcut to {DROP_DIR})")


def worker():
    try:
        token = capture_token()
        if not token:
            emit("No sign-in was detected. Nothing was changed. You can try again.")
            return
        configure(token)
    except Exception as exc:  # noqa: BLE001 - show any failure in the window
        emit(f"ERROR: {exc}")


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Google Photos backup setup")
        self.root.geometry("640x420")

        intro = (
            "This helper signs in to Google Photos for your backup.\n\n"
            "It opens a private browser window just for sign-in. It reads only the\n"
            "oauth_token from that temporary session, saves it locally with\n"
            "restricted permissions, and never sends it anywhere else.\n\n"
            "You must sign in yourself and click I agree."
        )
        tk.Label(self.root, text=intro, justify="left", wraplength=600).pack(padx=18, pady=14)

        self.button = tk.Button(self.root, text="Sign in with Google", command=self.start)
        self.button.pack(pady=6)

        row = tk.Frame(self.root)
        row.pack(pady=2)
        tk.Button(row, text="Check status", command=self.show_status).pack(side="left", padx=4)
        tk.Button(row, text="Open backup folder", command=self.open_folder).pack(side="left", padx=4)
        tk.Button(row, text="Stop backups", command=self.stop_backups).pack(side="left", padx=4)

        tk.Label(self.root, text="Status", font=("Helvetica", 10, "bold")).pack(anchor="w", padx=18, pady=(10, 2))
        self.status = tk.Text(self.root, height=12, wrap="word")
        self.status.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.status.configure(state="disabled")

        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def log(self, text):
        self.status.configure(state="normal")
        self.status.insert("end", text + "\n")
        self.status.see("end")
        self.status.configure(state="disabled")

    def start(self):
        self.button.configure(state="disabled")
        threading.Thread(target=worker, daemon=True).start()
        self.poll()

    def show_status(self):
        result = run([str(WATCH_SCRIPT), "status"], cwd=REPO)
        self.log(result.stdout.strip() or result.stderr.strip() or "No status available.")

    def open_folder(self):
        DROP_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(DROP_DIR)], check=False)

    def stop_backups(self):
        result = run([str(WATCH_SCRIPT), "stop"], cwd=REPO)
        self.log("Backups stopped." if result.returncode == 0 else result.stderr.strip())

    def poll(self):
        while True:
            try:
                text = messages.get_nowait()
            except queue.Empty:
                break
            self.log(text)
        self.root.after(250, self.poll)

    def close(self):
        stop_event.set()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
