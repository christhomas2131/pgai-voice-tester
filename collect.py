"""Download the call recordings from Twilio as MP3.

Recordings show up a few seconds after a call ends, so this polls. Safe to rerun:
it skips calls that already have a recording on disk.

    python collect.py
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

CALLS_DIR = Path(__file__).parent / "calls"
POLL_ATTEMPTS = 15
POLL_SLEEP = 3


def call_sid_for(d: Path) -> str | None:
    sid_file = d / "call_sid.txt"
    if sid_file.exists():
        return sid_file.read_text().strip()
    meta = d / "meta.json"
    if meta.exists():
        return json.loads(meta.read_text()).get("call_sid") or None
    return None


def download(url: str, dest: Path, account_sid: str, token: str) -> None:
    auth = base64.b64encode(f"{account_sid}:{token}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req) as r, dest.open("wb") as f:
        f.write(r.read())


def main() -> None:
    for var in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"):
        if not os.getenv(var):
            sys.exit(f"{var} is not set. Copy .env.example to .env and fill it in.")

    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    token = os.environ["TWILIO_AUTH_TOKEN"]
    client = Client(account_sid, token)

    dirs = sorted(d for d in CALLS_DIR.iterdir() if d.is_dir()) if CALLS_DIR.exists() else []
    if not dirs:
        sys.exit("No call directories found. Run run_calls.py first.")

    got = 0
    for d in dirs:
        dest = d / "recording.mp3"
        if dest.exists():
            print(f"{d.name}: already have recording.mp3")
            got += 1
            continue

        sid = call_sid_for(d)
        if not sid:
            print(f"{d.name}: no call SID on disk, skipping")
            continue

        recordings = []
        for _ in range(POLL_ATTEMPTS):
            recordings = client.recordings.list(call_sid=sid, limit=5)
            if recordings:
                break
            time.sleep(POLL_SLEEP)

        if not recordings:
            print(f"{d.name}: no recording available for {sid}")
            continue

        rec = recordings[0]
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Recordings/{rec.sid}.mp3"
        download(url, dest, account_sid, token)
        channels = getattr(rec, "channels", None)
        layout = {1: "mono", 2: "dual-channel"}.get(channels, f"channels={channels}")
        size_kb = dest.stat().st_size // 1024
        print(f"{d.name}: recording.mp3 ({size_kb} KB, {rec.duration}s, {layout})")
        got += 1

    print(f"\n{got}/{len(dirs)} call(s) have audio.")


if __name__ == "__main__":
    main()
