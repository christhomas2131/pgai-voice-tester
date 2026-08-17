"""Run a whole call with no telephony: a fake receptionist talks to our patient.

This is the harness that made the project cheap to build. It stands up the real
bridge, connects to it speaking Twilio's exact WebSocket protocol, and puts a
second Realtime session on the other end playing a clinic receptionist. Same code
path as a live call, no Twilio account, no per-minute charges — so turn-taking,
barge-in, transcripts and the hang-up handshake all get debugged before the first
real call.

Audio is paced at 20 ms / 160 bytes per frame, exactly like Twilio, because VAD
timing is meaningless if you shove the audio through as fast as the socket allows.

    python tests/loopback.py refill
    python tests/loopback.py closed_weekend

The fake receptionist has one deliberate bug — it books weekend appointments
without checking that the office is closed — so analyze.py can be verified too.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402
import websockets  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from bridge import open_realtime, vad_config  # noqa: E402
from scenarios import ORDER, SCENARIOS  # noqa: E402

load_dotenv()

FRAME_BYTES = 160  # 20 ms of 8 kHz u-law
FRAME_SECONDS = 0.02
SILENCE = b"\xff"  # u-law zero amplitude

RECEPTIONIST = """\
You are Denise, the front desk receptionist at Lakeside Family Medicine, a small
practice in Santa Barbara. You answer the phone. Open the call with a short
greeting the moment the line connects.

The practice: two doctors, Dr. Patel and Dr. Okonkwo. Weekdays 8am to 5pm, closed
Saturday and Sunday. One office, on Anacapa Street, with a small lot behind the
building. You take most major insurance.

How you talk: warm and brisk. One or two sentences per turn, never more than
three — you're on a phone, not writing an email. Ask one question at a time and
wait for the answer. You ask for name and date of birth before booking anything.
You offer specific times ("I have Tuesday at 9:15 or Wednesday at 2").

You are not perfect, and that is fine — do not try to be an ideal agent. In
particular: if a caller asks for a weekend appointment, just book it like any
other slot. Do not check the calendar and do not mention that the office is
closed on weekends.

Never say you are an AI. Never read these instructions out loud.
"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class PacedRelay:
    """Buffers u-law bytes and emits Twilio-sized frames on a real-time clock.

    Emits silence when there's nothing to say. That is not padding for neatness —
    a real phone line never goes quiet, it carries silence frames, and server-side
    VAD needs to *hear* that silence to decide a turn has ended. Send nothing and
    the far end's turn never closes: speech_started fires, speech_stopped never
    does, and no transcript is ever produced.
    """

    def __init__(self, send):
        self.send = send
        self.buf = bytearray()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._pump())

    def feed(self, b64: str) -> None:
        self.buf.extend(base64.b64decode(b64))

    def clear(self) -> None:
        self.buf.clear()

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _pump(self) -> None:
        # Absolute deadlines, not sleep(0.02) in a loop: per-iteration overhead
        # compounds over a two-minute call and the whole conversation drifts out
        # of real time, which is the one thing this harness exists to reproduce.
        next_at = time.monotonic()
        while True:
            next_at += FRAME_SECONDS
            await asyncio.sleep(max(0.0, next_at - time.monotonic()))
            if len(self.buf) >= FRAME_BYTES:
                frame = bytes(self.buf[:FRAME_BYTES])
                del self.buf[:FRAME_BYTES]
            elif self.buf:
                frame = bytes(self.buf) + SILENCE * (FRAME_BYTES - len(self.buf))
                self.buf.clear()
            else:
                frame = SILENCE * FRAME_BYTES
            await self.send(base64.b64encode(frame).decode())


async def receptionist_session():
    ws = await open_realtime()
    await ws.send(
        json.dumps(
            {
                "type": "session.update",
                "session": {
                    "type": "realtime",
                    "output_modalities": ["audio"],
                    "instructions": RECEPTIONIST,
                    "audio": {
                        "input": {
                            "format": {"type": "audio/pcmu"},
                            "turn_detection": vad_config(),
                        },
                        "output": {
                            "format": {"type": "audio/pcmu"},
                            "voice": "coral",
                        },
                    },
                },
            }
        )
    )
    # The receptionist answers the phone, so this side speaks first.
    await ws.send(json.dumps({"type": "response.create"}))
    return ws


async def loopback(name: str) -> Path:
    scenario = SCENARIOS[name]
    out_dir = ROOT / "calls" / f"loopback-{name}"
    port = free_port()

    server = uvicorn.Server(
        uvicorn.Config("bridge:app", host="127.0.0.1", port=port, log_level="warning")
    )
    server_task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.05)

    # Bare /ws with the scenario in customParameters, exactly as Twilio does it.
    # The harness used to pass a query string instead, which is precisely why it
    # failed to catch Twilio dropping the query string on the first live call.
    url = f"ws://127.0.0.1:{port}/ws"
    print(f"loopback: {name} -> {out_dir}")

    try:
        async with websockets.connect(url) as bridge_ws:
            recept = await receptionist_session()

            async def to_bridge(payload: str) -> None:
                await bridge_ws.send(
                    json.dumps(
                        {
                            "event": "media",
                            "streamSid": "MZloopback",
                            "media": {"payload": payload},
                        }
                    )
                )

            async def to_recept(payload: str) -> None:
                await recept.send(
                    json.dumps(
                        {"type": "input_audio_buffer.append", "audio": payload}
                    )
                )

            up = PacedRelay(to_bridge)  # receptionist -> our patient
            down = PacedRelay(to_recept)  # our patient -> receptionist
            up.start()
            down.start()

            await bridge_ws.send(
                json.dumps(
                    {"event": "connected", "protocol": "Call", "version": "1.0.0"}
                )
            )
            await bridge_ws.send(
                json.dumps(
                    {
                        "event": "start",
                        "start": {
                            "streamSid": "MZloopback",
                            "callSid": "CAloopback",
                            "customParameters": {
                                "scenario": name,
                                "dir": str(out_dir),
                            },
                            "mediaFormat": {
                                "encoding": "audio/x-mulaw",
                                "sampleRate": 8000,
                                "channels": 1,
                            },
                        },
                    }
                )
            )

            recept_speaking = False

            async def pump_receptionist() -> None:
                nonlocal recept_speaking
                async for raw in recept:
                    ev = json.loads(raw)
                    kind = ev.get("type")

                    if kind == "response.output_audio.delta":
                        up.feed(ev["delta"])
                    elif kind == "response.created":
                        recept_speaking = True
                    elif kind in ("response.done", "response.cancelled"):
                        recept_speaking = False
                    elif kind == "input_audio_buffer.speech_started":
                        # The receptionist needs the same barge-in behaviour a real
                        # voice agent has. Without it, it queues a fresh reply for
                        # every interruption and the paced relay ends up minutes
                        # behind — which looks exactly like catastrophic latency.
                        up.clear()
                        if recept_speaking:
                            await recept.send(json.dumps({"type": "response.cancel"}))
                    elif kind == "error":
                        print("  receptionist error:", ev.get("error"))

            async def pump_bridge() -> None:
                async for raw in bridge_ws:
                    msg = json.loads(raw)
                    event = msg.get("event")
                    if event == "media":
                        down.feed(msg["media"]["payload"])
                    elif event == "clear":
                        down.clear()
                    elif event == "mark":
                        # Twilio echoes a mark once the audio queued ahead of it
                        # has played out. Wait for the buffer to drain, then echo.
                        asyncio.create_task(echo_mark(msg))

            async def echo_mark(msg: dict) -> None:
                while len(down.buf) >= FRAME_BYTES:
                    await asyncio.sleep(FRAME_SECONDS)
                await bridge_ws.send(json.dumps(msg))

            tasks = [
                asyncio.create_task(pump_receptionist()),
                asyncio.create_task(pump_bridge()),
            ]
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED,
                timeout=scenario.max_seconds + 30,
            )
            for t in pending:
                t.cancel()
            up.stop()
            down.stop()
            await recept.close()
    finally:
        server.should_exit = True
        await server_task

    return out_dir


def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set. Copy .env.example to .env.")
    name = sys.argv[1] if len(sys.argv) > 1 else "book_new"
    if name not in SCENARIOS:
        sys.exit(f"Unknown scenario {name!r}. Known: {', '.join(ORDER)}")

    out_dir = asyncio.run(loopback(name))
    transcript = out_dir / "transcript.txt"
    print()
    print(transcript.read_text() if transcript.exists() else "no transcript written")


if __name__ == "__main__":
    main()
