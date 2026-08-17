"""Twilio Media Stream <-> OpenAI Realtime bridge.

Twilio holds the phone call open with <Connect><Stream> and sends us 8 kHz G.711
u-law frames as base64. The OpenAI Realtime API accepts and emits that same
format ("audio/pcmu"), so audio moves between the two legs as an untouched base64
string. No resampling, no transcoding, no audio library in the hot path.

One WebSocket route, three concurrent tasks per call: phone->model, model->phone,
and a watchdog that stops two AI agents from politely waiting each other out.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket

from scenarios import SCENARIOS, Scenario

load_dotenv()

CALLS_DIR = Path(__file__).parent / "calls"

# Mutual silence handling. Their agent pauses, our bot waits for the pause to end,
# nobody speaks. Nudge first, give up second.
#
# Tuned up from 10s after the first loopback run: a voice agent can genuinely take
# 15-20s to come back on a lookup, and a premature "are you still there?" reads far
# worse on a recording than simply waiting does.
NUDGE_AFTER = 18.0
HANGUP_AFTER = 35.0
MAX_NUDGES = 2

# If Twilio never echoes our goodbye mark back, close anyway.
DRAIN_TIMEOUT = 10.0

HANG_UP_TOOL = {
    "type": "function",
    "name": "hang_up",
    "description": (
        "End the phone call. Only call this after you have already said goodbye "
        "out loud."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": (
                    "Short note on how the call ended, e.g. 'appointment booked "
                    "for Tue 9am' or 'agent could not access billing'."
                ),
            }
        },
        "required": ["reason"],
    },
}


# --------------------------------------------------------------------------- #
# Call record
# --------------------------------------------------------------------------- #


@dataclass
class Turn:
    at: float  # seconds from the start of the stream
    speaker: str  # "agent" = Pretty Good AI, "patient" = our bot
    text: str


class CallLog:
    """Collects everything one call produces and writes it out on close."""

    def __init__(self, scenario: Scenario, out_dir: Path):
        self.scenario = scenario
        self.dir = out_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.t0 = time.monotonic()
        self.turns: list[Turn] = []
        self.errors: list[dict] = []
        self.meta: dict = {
            "scenario": scenario.name,
            "goal": scenario.goal.strip(),
            "probing": scenario.probing.strip(),
            "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self._events = (self.dir / "events.jsonl").open("w")

    def elapsed(self) -> float:
        return time.monotonic() - self.t0

    def add(self, speaker: str, text: str) -> None:
        text = (text or "").strip()
        if text:
            self.turns.append(Turn(round(self.elapsed(), 1), speaker, text))

    def event(self, ev: dict) -> None:
        """Full event firehose, minus the audio payloads. Debugging gold."""
        slim = {k: v for k, v in ev.items()}
        for key in ("delta", "audio"):
            if isinstance(slim.get(key), str):
                slim[key] = f"<{len(slim[key])} b64 chars>"
        slim["_at"] = round(self.elapsed(), 2)
        self._events.write(json.dumps(slim) + "\n")
        self._events.flush()

    def close(self, ended: str) -> None:
        self.meta["ended_reason"] = ended
        self.meta["duration_seconds"] = round(self.elapsed(), 1)
        self.meta["turns"] = len(self.turns)
        self.meta["errors"] = self.errors

        (self.dir / "meta.json").write_text(json.dumps(self.meta, indent=2) + "\n")
        (self.dir / "transcript.json").write_text(
            json.dumps([t.__dict__ for t in self.turns], indent=2) + "\n"
        )
        (self.dir / "transcript.txt").write_text(self._pretty())
        self._events.close()

    def _pretty(self) -> str:
        head = [
            f"CALL: {self.dir.name}",
            f"SCENARIO: {self.scenario.name}",
            f"GOAL: {' '.join(self.scenario.goal.split())}",
            f"STARTED: {self.meta['started_utc']}",
            f"DURATION: {self.meta.get('duration_seconds')}s",
            f"ENDED: {self.meta.get('ended_reason')}",
            "-" * 78,
        ]
        body = []
        for t in self.turns:
            stamp = f"[{int(t.at) // 60:02d}:{int(t.at) % 60:02d}]"
            label = "AGENT  " if t.speaker == "agent" else "PATIENT"
            body.append(f"{stamp} {label}  {t.text}")
        return "\n".join(head + body) + "\n"


# --------------------------------------------------------------------------- #
# Live call state
# --------------------------------------------------------------------------- #


@dataclass
class State:
    stream_sid: str = ""
    started: float = field(default_factory=time.monotonic)
    last_activity: float = field(default_factory=time.monotonic)
    bot_speaking: bool = False
    response_active: bool = False
    # response.done means the model finished *generating*. Our audio is still
    # playing out over the phone for a while after that, so silence is measured
    # from when Twilio echoes the drain mark back, not from response.done.
    draining_since: float = 0.0
    marks: int = 0
    nudges: int = 0
    hanging_up: bool = False
    ended: str = ""

    def touch(self) -> None:
        self.last_activity = time.monotonic()


def vad_config() -> dict:
    """When to decide the other party has finished talking.

    This is the single most consequential setting in the project. Too short and
    you cut them off mid-sentence, reply to half a thought, then talk over the
    rest — the first loopback run at 500 ms did exactly that, chopping one agent
    turn into four and making our patient repeat itself. Too long and the call
    fills with dead air. 900 ms clears the ordinary mid-sentence pause.
    """
    if os.getenv("VAD_TYPE", "server_vad") == "semantic_vad":
        return {
            "type": "semantic_vad",
            "eagerness": os.getenv("VAD_EAGERNESS", "medium"),
        }
    return {
        "type": "server_vad",
        "threshold": 0.5,
        "prefix_padding_ms": 200,
        "silence_duration_ms": int(os.getenv("VAD_SILENCE_MS", "900")),
    }


def session_config(scenario: Scenario) -> dict:
    return {
        "type": "session.update",
        "session": {
            "type": "realtime",
            "output_modalities": ["audio"],
            "instructions": scenario.instructions(),
            "audio": {
                "input": {
                    "format": {"type": "audio/pcmu"},
                    "turn_detection": vad_config(),
                    "transcription": {
                        "model": os.getenv("TRANSCRIBE_MODEL", "whisper-1")
                    },
                },
                "output": {
                    "format": {"type": "audio/pcmu"},
                    "voice": scenario.voice,
                },
            },
            "tools": [HANG_UP_TOOL],
            "tool_choice": "auto",
        },
    }


def stream_path(scenario: str, out_dir: Path) -> str:
    """Query string for the /ws route.

    Lives here rather than in the callers because both run_calls.py and the
    loopback harness need it escaped identically — the repo path contains spaces,
    and an unescaped one produces a request line the server rejects outright.
    """
    from urllib.parse import quote

    return f"/ws?scenario={quote(scenario)}&dir={quote(str(out_dir))}"


async def open_realtime():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set (see .env.example)")
    model = os.getenv("REALTIME_MODEL", "gpt-realtime-2.1")
    url = f"wss://api.openai.com/v1/realtime?model={model}"
    headers = {"Authorization": f"Bearer {key}"}
    try:
        return await websockets.connect(url, additional_headers=headers)
    except TypeError:  # websockets < 14 spells it differently
        return await websockets.connect(url, extra_headers=headers)


# --------------------------------------------------------------------------- #
# The three tasks
# --------------------------------------------------------------------------- #


async def phone_to_model(phone: WebSocket, model, st: State, log: CallLog) -> str:
    """Twilio -> OpenAI. Audio passes through as the base64 string Twilio sent."""
    async for raw in phone.iter_text():
        msg = json.loads(raw)
        event = msg.get("event")

        if event == "start":
            start = msg.get("start", {})
            st.stream_sid = start.get("streamSid", "")
            log.meta["call_sid"] = start.get("callSid", "")
            log.meta["stream_sid"] = st.stream_sid

        elif event == "media":
            await model.send(
                json.dumps(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": msg["media"]["payload"],
                    }
                )
            )

        elif event == "mark":
            # Twilio echoes a mark once everything queued before it has played.
            name = msg.get("mark", {}).get("name", "")
            if name == "goodbye":
                return "bot_hung_up"
            if name.startswith("drain-"):
                # Our last turn has actually finished playing. Only now is the
                # line genuinely quiet, so only now does the silence clock start.
                st.bot_speaking = False
                st.draining_since = 0.0
                st.touch()

        elif event == "stop":
            return "far_end_hung_up"

    return "stream_closed"


async def model_to_phone(phone: WebSocket, model, st: State, log: CallLog) -> str:
    """OpenAI -> Twilio, plus transcript capture and barge-in handling."""
    async for raw in model:
        ev = json.loads(raw)
        kind = ev.get("type", "")
        log.event(ev)

        if kind == "response.output_audio.delta":
            st.bot_speaking = True
            await phone.send_json(
                {
                    "event": "media",
                    "streamSid": st.stream_sid,
                    "media": {"payload": ev["delta"]},
                }
            )

        elif kind == "input_audio_buffer.speech_started":
            # Their agent started talking. Flush whatever of ours is still queued
            # on the line, otherwise both voices play at once.
            if st.bot_speaking:
                await phone.send_json(
                    {"event": "clear", "streamSid": st.stream_sid}
                )
                st.bot_speaking = False
            if st.response_active:
                await model.send(json.dumps({"type": "response.cancel"}))

        elif kind == "input_audio_buffer.speech_stopped":
            st.touch()

        elif kind == "response.created":
            st.response_active = True

        elif kind in ("response.done", "response.cancelled"):
            st.response_active = False
            st.touch()
            if st.bot_speaking and st.stream_sid:
                st.marks += 1
                st.draining_since = time.monotonic()
                await phone.send_json(
                    {
                        "event": "mark",
                        "streamSid": st.stream_sid,
                        "mark": {"name": f"drain-{st.marks}"},
                    }
                )
            else:
                st.bot_speaking = False

        elif kind == "conversation.item.input_audio_transcription.completed":
            log.add("agent", ev.get("transcript", ""))

        elif kind == "response.output_audio_transcript.done":
            log.add("patient", ev.get("transcript", ""))

        elif kind == "error":
            log.errors.append(ev.get("error", ev))

        # The GA API has moved function-call plumbing around between versions, so
        # accept either shape rather than betting on one.
        elif kind == "response.function_call_arguments.done":
            if ev.get("name") == "hang_up":
                await _begin_hangup(phone, st, log, ev.get("arguments", ""))
        elif kind == "response.output_item.done":
            item = ev.get("item", {})
            if item.get("type") == "function_call" and item.get("name") == "hang_up":
                await _begin_hangup(phone, st, log, item.get("arguments", ""))

    return "model_closed"


async def _begin_hangup(phone: WebSocket, st: State, log: CallLog, args: str) -> None:
    if st.hanging_up:
        return
    st.hanging_up = True
    try:
        log.meta["hangup_reason"] = json.loads(args or "{}").get("reason", "")
    except json.JSONDecodeError:
        log.meta["hangup_reason"] = args
    # Queue a mark behind the goodbye audio; phone_to_model closes when it lands.
    await phone.send_json(
        {"event": "mark", "streamSid": st.stream_sid, "mark": {"name": "goodbye"}}
    )


async def watchdog(model, st: State, scenario: Scenario) -> str:
    """Kill dead air, cap call length, and never let a call run away on cost."""
    while True:
        await asyncio.sleep(1.0)
        now = time.monotonic()

        if now - st.started > scenario.max_seconds:
            return "max_duration"

        if st.hanging_up:
            if now - st.last_activity > DRAIN_TIMEOUT:
                return "hangup_drain_timeout"
            continue

        # A mark that never comes back would wedge the call open until the hard
        # duration cap. Assume drained after a while and carry on.
        if st.draining_since and now - st.draining_since > DRAIN_TIMEOUT * 3:
            st.bot_speaking = False
            st.draining_since = 0.0
            st.touch()

        if st.bot_speaking or st.response_active:
            continue

        quiet = now - st.last_activity
        if quiet > HANGUP_AFTER:
            return "mutual_silence"
        if quiet > NUDGE_AFTER and st.nudges < MAX_NUDGES:
            st.nudges += 1
            st.touch()
            await model.send(
                json.dumps(
                    {
                        "type": "response.create",
                        "response": {
                            "instructions": (
                                "The line has gone quiet. Briefly and naturally "
                                "check whether they're still there."
                            )
                        },
                    }
                )
            )


# --------------------------------------------------------------------------- #
# Route
# --------------------------------------------------------------------------- #

app = FastAPI()


@app.get("/health")
async def health():
    return {"ok": True, "scenarios": sorted(SCENARIOS)}


@app.websocket("/ws")
async def media_stream(phone: WebSocket):
    await phone.accept()

    name = phone.query_params.get("scenario", "")
    scenario = SCENARIOS.get(name)
    if scenario is None:
        await phone.close(code=1008, reason=f"unknown scenario {name!r}")
        return

    out_dir = Path(phone.query_params.get("dir") or CALLS_DIR / f"adhoc-{name}")
    log = CallLog(scenario, out_dir)
    st = State()
    ended = "unknown"

    try:
        model = await open_realtime()
    except Exception as exc:  # no model, no call — record why and drop
        log.errors.append({"stage": "connect", "message": str(exc)})
        log.close("realtime_connect_failed")
        await phone.close(code=1011)
        raise

    try:
        await model.send(json.dumps(session_config(scenario)))

        # Deliberately no opening response.create: the practice answers the phone
        # and greets us. Our bot speaks second, like a caller would.
        tasks = [
            asyncio.create_task(phone_to_model(phone, model, st, log), name="up"),
            asyncio.create_task(model_to_phone(phone, model, st, log), name="down"),
            asyncio.create_task(watchdog(model, st, scenario), name="watchdog"),
        ]
        done, pending = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        first = done.pop()
        ended = first.result() if not first.exception() else f"error: {first.exception()}"
    finally:
        await model.close()
        log.close(ended)
        try:
            await phone.close()
        except RuntimeError:
            pass  # already gone
        print(f"[{out_dir.name}] {ended} — {len(log.turns)} turns, "
              f"{log.meta.get('duration_seconds')}s")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
