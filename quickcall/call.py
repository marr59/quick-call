#!/usr/bin/env python3
"""Quick outbound interview call via ElevenLabs Conversational AI + Twilio.

  call.py --to +1XXXXXXXXXX --name Anna --preset truck-driver [--lang ru]
  call.py --to +1XXXXXXXXXX --name Anna --questions "Q1?|Q2?" --topic "the warehouse position"
  call.py --to +1XXXXXXXXXX --name Vendor --script-file scripts/vendor.txt
  call.py --status conv_xxx          # just fetch and report a finished conversation
  --dry prints the script without calling; --no-wait returns right after dial-out.
"""
import argparse, datetime, json, os, pathlib, re, sys, time, urllib.parse, urllib.request
from script import build_script

HERE = pathlib.Path(__file__).resolve().parent
KEY = os.environ["ELEVENLABS_API_KEY"]
AGENT = os.environ["ELEVENLABS_AGENT_ID"]
PHONE = os.environ["ELEVENLABS_PHONE_NUMBER_ID"]
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")


def api(method, path, body=None):
    req = urllib.request.Request("https://api.elevenlabs.io/v1" + path, method=method,
                                 headers={"xi-api-key": KEY, "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def tg(text):
    if not TG_TOKEN or not TG_CHAT:
        return
    try:
        data = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": text[:4000]}).encode()
        urllib.request.urlopen("https://api.telegram.org/bot%s/sendMessage" % TG_TOKEN, data=data, timeout=30).read()
    except Exception as e:
        print("tg failed:", e, file=sys.stderr)


def fetch(conv_id):
    return api("GET", "/convai/conversations/" + conv_id)


def report(d, to="", started=None):
    """Status, duration, summary and the turn-by-turn transcript, as text + a Markdown file."""
    md = d.get("metadata") or {}
    an = d.get("analysis") or {}
    lines = ["Call %s: %s, %s s" % (to, d.get("status"), md.get("call_duration_secs"))]
    if an.get("transcript_summary"):
        lines += ["", "Summary: " + an["transcript_summary"]]
    turns = ["%s: %s" % (t.get("role"), t.get("message")) for t in d.get("transcript") or [] if t.get("message")]
    if turns:
        lines += ["", "Transcript:"] + turns
    text = "\n".join(lines)
    out = HERE.parent / "calls"
    out.mkdir(exist_ok=True)
    stamp = (started or datetime.datetime.now()).strftime("%Y%m%d-%H%M")
    p = out / ("%s_%s.md" % (stamp, d.get("conversation_id", "conv")))
    p.write_text(text + "\n\n```json\n" + json.dumps(d, ensure_ascii=False, indent=1) + "\n```\n")
    return text, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to"); ap.add_argument("--name", default="there")
    ap.add_argument("--preset"); ap.add_argument("--questions"); ap.add_argument("--script-file")
    ap.add_argument("--lang", default="en", choices=["en", "ru"])
    ap.add_argument("--caller", default="the assistant"); ap.add_argument("--behalf", default="the employer")
    ap.add_argument("--topic", default="the open position")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--status"); ap.add_argument("--no-wait", action="store_true")
    ap.add_argument("--no-tg", action="store_true"); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    if a.status:
        text, p = report(fetch(a.status))
        print(text); print("saved:", p)
        if not a.no_tg: tg(text)
        return

    if not a.to or not re.match(r"^\+\d{8,15}$", a.to):
        sys.exit("--to must be E.164, e.g. +14085550123")
    if a.script_file:
        script = open(a.script_file).read()
    else:
        if a.questions:
            qs = a.questions.split("|")
        elif a.preset:
            f = HERE.parent / "presets" / ("%s.%s.txt" % (a.preset, a.lang))
            if not f.exists():
                f = HERE.parent / "presets" / (a.preset + ".txt")
            qs = f.read_text().splitlines()
        else:
            sys.exit("need --preset, --questions or --script-file")
        script = build_script(a.lang, a.name, a.caller, a.behalf, a.topic, qs)
    print("=== SCRIPT ===\n" + script + "\n==============")
    if a.dry:
        return

    started = datetime.datetime.now()
    # The script travels as a dynamic variable; the agent's prompt is just {{script}}.
    r = api("POST", "/convai/twilio/outbound-call", {
        "agent_id": AGENT, "agent_phone_number_id": PHONE, "to_number": a.to,
        "conversation_initiation_client_data": {"dynamic_variables": {"script": script}}})
    conv = r.get("conversation_id")
    if not r.get("success") or not conv:
        tg("Call to %s did not start: %s" % (a.to, json.dumps(r)[:300])); sys.exit(1)
    if not a.no_tg:
        tg("Calling %s (%s). Report follows when they hang up." % (a.name, a.to))
    if a.no_wait:
        print("conversation_id:", conv); return

    # Poll until the conversation is done and the summary has been generated.
    t0 = time.time(); d = {}
    while time.time() - t0 < a.timeout:
        time.sleep(8)
        d = fetch(conv)
        if d.get("status") in ("done", "failed"):
            for _ in range(6):
                if (d.get("analysis") or {}).get("transcript_summary"):
                    break
                time.sleep(5); d = fetch(conv)
            break
    text, p = report(d, a.to, started)
    print(text); print("saved:", p)
    if not a.no_tg: tg(text)


if __name__ == "__main__":
    main()
