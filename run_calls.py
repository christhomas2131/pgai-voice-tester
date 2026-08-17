"""Place the test calls.

Runs the whole stack from one command: starts the bridge in-process, finds (or
opens) a public tunnel so Twilio can reach it, then dials the assessment line
once per scenario and waits for each call to finish before starting the next.

    python run_calls.py --all
    python run_calls.py --scenario refill closed_weekend
    python run_calls.py --all --dry-run     # no calls placed, no money spent
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from twilio.rest import Client

from scenarios import ORDER, SCENARIOS

load_dotenv()

# The assessment line. Hardcoded on purpose: the brief is explicit that this is
# the only number to call, and a typo here dials a stranger.
TARGET = "+18054398008"

CALLS_DIR = Path(__file__).parent / "calls"
GAP_BETWEEN_CALLS = 8  # seconds, so we're not hammering their line
DONE = {"completed", "failed", "busy", "no-answer", "canceled"}


# --------------------------------------------------------------------------- #
# Plumbing
# --------------------------------------------------------------------------- #


def next_call_dir(scenario: str) -> Path:
    CALLS_DIR.mkdir(exist_ok=True)
    n = len([p for p in CALLS_DIR.iterdir() if p.is_dir()]) + 1
    d = CALLS_DIR / f"call-{n:02d}-{scenario}"
    # Created now, not by the bridge, so the next call gets the next number even
    # if this one never connects.
    d.mkdir(exist_ok=True)
    return d


def start_ngrok(port: int) -> tuple[str, subprocess.Popen]:
    """Open a tunnel and read the public URL back out of ngrok's local API."""
    if not shutil.which("ngrok"):
        sys.exit(
            "ngrok is not installed and PUBLIC_WSS_URL is not set.\n"
            "Either `brew install ngrok && ngrok config add-authtoken <token>`, "
            "or put a public wss:// URL in .env as PUBLIC_WSS_URL."
        )
    proc = subprocess.Popen(
        ["ngrok", "http", str(port), "--log", "stdout"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(40):
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as r:
                tunnels = json.load(r).get("tunnels", [])
            for t in tunnels:
                if t.get("public_url", "").startswith("https://"):
                    return t["public_url"].replace("https://", "wss://"), proc
        except Exception:
            pass
        import time

        time.sleep(0.5)
    proc.terminate()
    sys.exit("ngrok started but never reported a public URL. Check `ngrok http 8080`.")


def twiml_for(wss_url: str, scenario: str, out_dir: Path) -> str:
    from urllib.parse import quote
    from xml.sax.saxutils import quoteattr

    url = f"{wss_url}/ws?scenario={quote(scenario)}&dir={quote(str(out_dir))}"
    # quoteattr, not an f-string: TwiML is parsed as XML, so the & separating the
    # query parameters has to be escaped or Twilio rejects the document.
    # <Connect> holds the call open for as long as the stream lives, which means
    # the bridge closing the socket is what ends the call.
    return f"<Response><Connect><Stream url={quoteattr(url)}/></Connect></Response>"


# --------------------------------------------------------------------------- #
# Calling
# --------------------------------------------------------------------------- #


def place_call(client: Client, from_number: str, twiml: str) -> str:
    call = client.calls.create(
        to=TARGET,
        from_=from_number,
        twiml=twiml,
        record=True,
        recording_channels="dual",  # falls back to mono if the leg can't be split
        recording_track="both",
    )
    return call.sid


def wait_for_call(client: Client, sid: str, limit: int = 300) -> str:
    import time

    for _ in range(limit):
        status = client.calls(sid).fetch().status
        if status in DONE:
            return status
        time.sleep(1)
    return "timeout"


async def run(args) -> None:
    port = int(os.getenv("PORT", "8080"))
    names = ORDER if args.all else args.scenario
    unknown = [n for n in names if n not in SCENARIOS]
    if unknown:
        sys.exit(f"Unknown scenario(s): {', '.join(unknown)}\nKnown: {', '.join(ORDER)}")

    if args.dry_run:
        wss = os.getenv("PUBLIC_WSS_URL") or "wss://example.invalid"
        for n in names:
            print(f"\n--- {n} ---")
            print(twiml_for(wss, n, next_call_dir(n)))
        print(f"\n{len(names)} call(s) would be placed to {TARGET}. Nothing sent.")
        return

    for var in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"):
        if not os.getenv(var):
            sys.exit(f"{var} is not set. Copy .env.example to .env and fill it in.")

    client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    from_number = os.environ["TWILIO_FROM_NUMBER"]

    # Bridge first, so the tunnel has something to point at.
    server = uvicorn.Server(
        uvicorn.Config("bridge:app", host="0.0.0.0", port=port, log_level="warning")
    )
    server_task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.1)

    ngrok = None
    wss = args.public_url or os.getenv("PUBLIC_WSS_URL")
    if wss:
        print(f"Using tunnel from config: {wss}")
    else:
        wss, ngrok = start_ngrok(port)
        print(f"Opened ngrok tunnel: {wss}")

    print(f"Calling {TARGET} from {from_number} — {len(names)} scenario(s)\n")

    try:
        for i, name in enumerate(names, 1):
            out_dir = next_call_dir(name)
            print(f"[{i}/{len(names)}] {name} -> {out_dir.name}")
            try:
                sid = place_call(client, from_number, twiml_for(wss, name, out_dir))
            except Exception as exc:
                print(f"    could not place call: {exc}")
                continue
            status = await asyncio.to_thread(wait_for_call, client, sid)
            print(f"    {sid} {status}")
            (out_dir / "call_sid.txt").write_text(sid + "\n")
            await asyncio.sleep(GAP_BETWEEN_CALLS)
    finally:
        server.should_exit = True
        await server_task
        if ngrok:
            ngrok.terminate()

    print("\nDone. Next: python collect.py   (downloads the MP3s)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="run every scenario in order")
    g.add_argument("--scenario", nargs="+", metavar="NAME", help="run named scenarios")
    p.add_argument("--public-url", help="wss:// base URL, overrides PUBLIC_WSS_URL")
    p.add_argument("--dry-run", action="store_true", help="print TwiML, place nothing")
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
