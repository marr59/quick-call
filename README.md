# Quick-call

Outbound voice agent that phones a real person, runs a short scripted interview or vendor inquiry, and sends the transcript summary to Telegram. One command, call starts within a minute.

**This is a showcase repository.** The working copy lives offline. No call recordings, transcripts, phone numbers, names or credentials from real calls are included. The example transcript in `docs/example-report.md` is invented and marked as such.

## What it does

```
./call.py --to +1XXXXXXXXXX --name "First name" --preset truck-driver
./call.py --to +1XXXXXXXXXX --name "Vendor" --questions "Q1?|Q2?|Q3?" --topic "portable toilets for a campground"
./call.py --to +1XXXXXXXXXX --name "Vendor" --script-file scripts/my-script.txt
./call.py --status conv_xxx        # re-fetch the report for a finished call
```

1. Builds the agent script: identity, consent disclosure, questions one at a time, closing, guard rails.
2. Starts an outbound call through ElevenLabs Conversational AI over a Twilio number, passing the script as a dynamic variable.
3. Polls the conversation until it is done, then posts the status, duration, transcript and summary to Telegram and writes a Markdown report.

## Architecture

```
call.py ──POST /convai/twilio/outbound-call──▶ ElevenLabs ConvAI agent ──SIP──▶ Twilio ──PSTN──▶ person
   │                                                 │
   │◀────── GET /convai/conversations/{id} ──────────┘  (status, transcript, analysis.transcript_summary)
   │
   └──▶ Telegram Bot API (progress + final report)  +  calls/<timestamp>_<conversation>.md
```

The agent itself is a stock ElevenLabs Conversational AI agent whose system prompt is a single dynamic variable, `{{script}}`. All behaviour lives in the script the CLI builds, so the same agent runs an English hiring screen, a Russian one, or a vendor inquiry without touching the agent config.

## Consent disclosure

Every call opens with a fixed line before any question:

> "Hi, is this {name}? My name is {caller}. Before we start, I'm an automated assistant calling on behalf of {behalf} about {topic}, and this call is being recorded. Is it alright if I ask you a few quick questions?"

If the person declines, the agent thanks them and ends the call. California is a two-party consent state, so the disclosure is not optional and is not a dynamic variable the caller can remove. See `quickcall/script.py`.

## Turn control

The first live call showed the agent interrupting short answers and re-asking. The fix is in the script, not the model: after each question the agent is told to stop talking and wait for a full answer, never interrupt, ask once to repeat if unclear, acknowledge briefly, and move on. Questions are numbered and asked strictly one at a time. Off-script questions (who exactly the employer is, pay, anything else) get a fixed deflection and a promise that a person will follow up. See `quickcall/script.py`.

## Honest numbers

Measured on the working copy, October 14 to 23, 2026:

| Metric | Value |
|---|---|
| Outbound calls placed | 12 |
| Full conversations (4+ replies from the person) | 5 |
| Rest | voicemail or a short decline |
| Call duration | 20 to 151 seconds |

This is a small sample from a personal tool, not a benchmark. Use cases so far: a hiring screen for a truck driver position on behalf of an employer, and outreach to fire districts, county public works and vendors for a campground project. Those parties' details are not in this repository.

## Files

- `quickcall/call.py`: CLI, outbound call, polling, report. Secrets come from environment variables only.
- `quickcall/script.py`: script builder with the consent disclosure, turn-control rules and guard rails, English and Russian.
- `presets/truck-driver.txt`: example question set.
- `docs/example-report.md`: an invented example of what the Telegram report looks like.
- `.env.example`: variable names, no values.

## Setup

```
cp .env.example .env     # fill in your own keys
python3 quickcall/call.py --to +1XXXXXXXXXX --name Test --preset truck-driver --dry
```

`--dry` prints the generated script and does not place a call. Only the Python standard library is used.
