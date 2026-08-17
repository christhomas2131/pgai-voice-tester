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
import re
import shutil
import subprocess
import sys
import time
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


class TunnelError(RuntimeError):
    """A tunnel failed to come up. Retryable."""


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


def start_cloudflared(port: int) -> tuple[str, subprocess.Popen]:
    """Cloudflare quick tunnel. Anonymous — no account, no authtoken.

    Waits for "Registered tunnel connection", not just for the URL. cloudflared
    prints the hostname several seconds before the tunnel is actually registered
    at the edge, and a call placed in that window reaches nothing.
    """
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    # Quick tunnel hostnames are several dash-separated words. Must not match
    # api.trycloudflare.com, which cloudflared prints in its own startup banner
    # and which resolves perfectly well while serving none of your traffic.
    pattern = re.compile(r"https://(?:[a-z0-9]+-){2,}[a-z0-9]+\.trycloudflare\.com")
    url = ""
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        line = proc.stderr.readline()
        if not line and proc.poll() is not None:
            break
        if not url:
            found = pattern.search(line)
            if found:
                url = found.group(0)
        if url and "Registered tunnel connection" in line:
            return url.replace("https://", "wss://"), proc
    proc.terminate()
    raise TunnelError("cloudflared never registered a tunnel connection")


def start_ngrok(port: int) -> tuple[str, subprocess.Popen]:
    """Open a tunnel and read the public URL back out of ngrok's local API."""
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
        time.sleep(0.5)
    proc.terminate()
    raise TunnelError(
        "ngrok never reported a public URL. Most likely the authtoken is wrong — "
        "note that the dashboard shows both an API key (ng-...) and an authtoken, "
        "and only the authtoken works here."
    )


def tunnel_is_reachable(
    wss_url: str, timeout: float = 90.0, initial_delay: float = 8.0
) -> str:
    """Confirm the tunnel serves traffic from the public internet. '' if it does.

    Without this check, an unregistered tunnel looks exactly like a bug in the
    bridge: Twilio dials, reaches nothing, hangs up after about a second, and
    reports a WebSocket error against your server.

    The initial delay is load-bearing, not politeness. Probe before the hostname
    is published and macOS caches the NXDOMAIN, after which every retry in this
    loop fails from cache even once the record exists — the resolver, not the
    tunnel, becomes the problem. (`host` appears to work throughout, because it
    queries DNS directly and never consults the OS cache.) So: wait for the
    record to exist before asking about it even once, then allow a window long
    enough to outlast a negative TTL if we lose that race anyway.
    """
    health = wss_url.replace("wss://", "https://") + "/health"
    time.sleep(initial_delay)
    deadline = time.monotonic() + timeout
    last = "no attempt made"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health, timeout=5) as r:
                if json.load(r).get("ok"):
                    return ""
            last = "/health did not report ok"
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(3.0)
    return last


def establish_tunnel(port: int, attempts: int = 3) -> tuple[str, subprocess.Popen]:
    """Open a tunnel and don't return until traffic actually flows through it.

    Quick tunnels fail to come up often enough that one attempt isn't enough, and
    a dead tunnel costs a wasted phone call to discover.
    """
    # cloudflared first because quick tunnels need no account, but anonymous
    # tunnels get rate limited, so fall through to ngrok rather than giving up.
    tools = [
        (name, fn)
        for name, fn in (("cloudflared", start_cloudflared), ("ngrok", start_ngrok))
        if shutil.which(name)
    ]
    if not tools:
        sys.exit(
            "No tunnel available and PUBLIC_WSS_URL is not set.\n"
            "Install one: `brew install cloudflared` (no account needed), or set "
            "PUBLIC_WSS_URL in .env to your own public wss:// URL."
        )

    last = ""
    for tool, start in tools:
        for attempt in range(1, attempts + 1):
            try:
                wss, proc = start(port)
            except TunnelError as exc:
                last = f"{tool}: {exc}"
                print(f"  {tool} {attempt}/{attempts}: {exc}")
                continue
            problem = tunnel_is_reachable(wss)
            if not problem:
                return wss, proc
            last = f"{tool}: {problem}"
            print(f"  {tool} {attempt}/{attempts}: {wss} unreachable ({problem})")
            proc.terminate()
    sys.exit(f"Could not establish a working tunnel. Last error — {last}")


def twiml_for(wss_url: str, scenario: str, out_dir: Path) -> str:
    """Build the TwiML for one call.

    Scenario and output directory travel as <Parameter> children, not as a query
    string on the url. Twilio discards the query string, and the bridge then has
    no idea which patient to play — it connects and is immediately refused.
    """
    from xml.sax.saxutils import quoteattr

    params = "".join(
        f"<Parameter name={quoteattr(k)} value={quoteattr(str(v))}/>"
        for k, v in (("scenario", scenario), ("dir", out_dir))
    )
    # <Connect> holds the call open for as long as the stream lives, which means
    # the bridge closing the socket is what ends the call.
    return (
        f"<Response><Connect><Stream url={quoteattr(wss_url + '/ws')}>"
        f"{params}</Stream></Connect></Response>"
    )


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
        problem = await asyncio.to_thread(tunnel_is_reachable, wss)
        if problem:
            sys.exit(f"{wss} is not reachable from the public internet ({problem})")
    else:
        print("Opening tunnel...")
        wss, ngrok = await asyncio.to_thread(establish_tunnel, port)
        print(f"Tunnel up and reachable: {wss}")

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
