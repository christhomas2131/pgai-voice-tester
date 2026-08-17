"""Tests for the parts that don't need a phone line.

The conversational behaviour is exercised by tests/loopback.py, which runs a real
call against a fake receptionist. These cover the pieces that would silently
corrupt a transcript or dial the wrong number.
"""

import asyncio
import base64
import json

import pytest

import bridge
import run_calls
from scenarios import ORDER, SCENARIOS


# --- the guard that matters most -------------------------------------------- #


def test_target_number_is_the_assessment_line():
    assert run_calls.TARGET == "+18054398008"


# --- scenarios --------------------------------------------------------------- #


def test_every_scenario_is_complete():
    assert len(SCENARIOS) >= 10, "the brief requires at least 10 calls"
    for s in SCENARIOS.values():
        assert s.goal.strip() and s.identity.strip() and s.probing.strip()
        assert 60 <= s.max_seconds <= 300


def test_instructions_include_persona_and_goal():
    s = SCENARIOS["refill"]
    text = s.instructions()
    assert "lisinopril" in text
    assert "CVS" in text
    assert "hang_up" in text  # the bot has to know how to end the call


def test_behaviour_only_appears_when_set():
    assert "HOW YOU BEHAVE" in SCENARIOS["barge_in"].instructions()
    assert "HOW YOU BEHAVE" not in SCENARIOS["refill"].instructions()


def test_voices_avoid_the_broken_ones():
    # fable/onyx/nova are documented as producing distorted audio over u-law.
    good = {"alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse",
            "marin", "cedar"}
    for s in SCENARIOS.values():
        assert s.voice in good, f"{s.name} uses unsupported voice {s.voice}"


# --- session config ---------------------------------------------------------- #


def test_session_config_is_ulaw_both_directions():
    cfg = bridge.session_config(SCENARIOS["book_new"])["session"]
    assert cfg["audio"]["input"]["format"] == {"type": "audio/pcmu"}
    assert cfg["audio"]["output"]["format"] == {"type": "audio/pcmu"}


def test_session_config_transcribes_the_other_side():
    cfg = bridge.session_config(SCENARIOS["book_new"])["session"]
    assert cfg["audio"]["input"]["transcription"]["model"]


def test_session_config_exposes_hang_up():
    cfg = bridge.session_config(SCENARIOS["book_new"])["session"]
    assert [t["name"] for t in cfg["tools"]] == ["hang_up"]


def test_vad_type_switches(monkeypatch):
    monkeypatch.setenv("VAD_TYPE", "semantic_vad")
    assert bridge.vad_config()["type"] == "semantic_vad"
    monkeypatch.setenv("VAD_TYPE", "server_vad")
    cfg = bridge.vad_config()
    assert cfg["type"] == "server_vad"
    assert cfg["silence_duration_ms"] == 500


# --- transcript -------------------------------------------------------------- #


def test_transcript_is_ordered_labelled_and_stamped(tmp_path):
    log = bridge.CallLog(SCENARIOS["refill"], tmp_path)
    log.t0 -= 65  # pretend 65 seconds have passed
    log.add("agent", "  Thank you for calling.  ")
    log.add("patient", "Hi, I need a refill.")
    log.add("agent", "")  # empty transcripts are dropped, not logged as blanks
    log.close("bot_hung_up")

    text = (tmp_path / "transcript.txt").read_text()
    assert "[01:05] AGENT    Thank you for calling." in text
    assert "[01:05] PATIENT  Hi, I need a refill." in text
    assert text.index("AGENT") < text.index("PATIENT")

    turns = json.loads((tmp_path / "transcript.json").read_text())
    assert [t["speaker"] for t in turns] == ["agent", "patient"]

    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["ended_reason"] == "bot_hung_up"
    assert meta["turns"] == 2


def test_event_log_strips_audio_payloads(tmp_path):
    log = bridge.CallLog(SCENARIOS["refill"], tmp_path)
    log.event({"type": "response.output_audio.delta", "delta": "A" * 4096})
    log.close("done")
    line = json.loads((tmp_path / "events.jsonl").read_text().splitlines()[0])
    assert line["delta"] == "<4096 b64 chars>"


# --- twiml ------------------------------------------------------------------- #


def test_twiml_wires_scenario_and_output_dir(tmp_path):
    xml = run_calls.twiml_for("wss://x.ngrok.app", "closed_weekend", tmp_path / "call-01")
    assert xml.startswith("<Response><Connect><Stream url=") and xml.endswith("/></Connect></Response>")
    assert "scenario=closed_weekend" in xml
    assert "wss://x.ngrok.app/ws?" in xml


def test_twiml_is_valid_xml_with_two_query_params(tmp_path):
    # A bare & between query parameters is not valid XML, and Twilio rejects the
    # whole document. Parse it rather than trusting the string.
    from xml.etree import ElementTree

    xml = run_calls.twiml_for("wss://x.ngrok.app", "refill", tmp_path / "call-01")
    url = ElementTree.fromstring(xml).find("Connect/Stream").attrib["url"]
    assert "scenario=refill" in url and "dir=" in url


def test_twiml_escapes_paths_with_spaces(tmp_path):
    # The repo lives under "Automata Projects - Mac" — an unescaped space here
    # produces TwiML Twilio silently refuses to parse.
    from xml.etree import ElementTree

    xml = run_calls.twiml_for("wss://x.ngrok.app", "refill", tmp_path / "a b" / "c")
    url = ElementTree.fromstring(xml).find("Connect/Stream").attrib["url"]
    assert " " not in url


def test_call_dirs_increment(tmp_path, monkeypatch):
    monkeypatch.setattr(run_calls, "CALLS_DIR", tmp_path / "calls")
    first = run_calls.next_call_dir("refill")
    second = run_calls.next_call_dir("cancel")
    assert first.name == "call-01-refill"
    assert second.name == "call-02-cancel"


# --- paced relay ------------------------------------------------------------- #


def test_paced_relay_emits_twilio_sized_frames():
    from tests.loopback import FRAME_BYTES, PacedRelay

    sent = []

    async def scenario():
        relay = PacedRelay(lambda p: _collect(sent, p))
        relay.start()
        relay.feed(base64.b64encode(b"\xff" * (FRAME_BYTES * 3)).decode())
        await asyncio.sleep(0.15)
        relay.stop()

    async def _collect(dest, payload):
        dest.append(payload)

    asyncio.run(scenario())
    assert len(sent) == 3
    assert all(len(base64.b64decode(p)) == FRAME_BYTES for p in sent)


def test_paced_relay_clear_drops_queued_audio():
    from tests.loopback import FRAME_BYTES, PacedRelay

    relay = PacedRelay(lambda p: None)
    relay.feed(base64.b64encode(b"\x00" * FRAME_BYTES * 5).decode())
    assert len(relay.buf) == FRAME_BYTES * 5
    relay.clear()
    assert relay.buf == b""


# --- watchdog ---------------------------------------------------------------- #


@pytest.mark.parametrize("quiet,expect_nudge", [(5, False), (12, True)])
def test_watchdog_nudges_only_after_silence(quiet, expect_nudge, monkeypatch):
    sent = []

    class FakeModel:
        async def send(self, raw):
            sent.append(json.loads(raw))

    st = bridge.State()
    st.last_activity -= quiet

    async def scenario():
        task = asyncio.create_task(watch())
        await asyncio.sleep(1.3)
        task.cancel()

    async def watch():
        await bridge.watchdog(FakeModel(), st, SCENARIOS["refill"])

    asyncio.run(scenario())
    nudged = any(m.get("type") == "response.create" for m in sent)
    assert nudged is expect_nudge


def test_watchdog_stops_at_max_duration():
    class FakeModel:
        async def send(self, raw):
            pass

    st = bridge.State()
    st.started -= SCENARIOS["refill"].max_seconds + 1
    reason = asyncio.run(bridge.watchdog(FakeModel(), st, SCENARIOS["refill"]))
    assert reason == "max_duration"
