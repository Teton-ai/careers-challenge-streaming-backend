# Teton Challenge, Real-time Streaming Backend

> **No prior experience required. The solution is the signal.**
> Every submission gets feedback within 7 days. → `info@teton.ai`

---

A Teton sensor sits in a care room. It streams events, heartbeats, presence, motion, sleep state, fall warnings, network status, to our backend, all day, every day. We have a few thousand of those right now. We will have a few hundred thousand. Each event matters; some matter more than others; all of them have to land in the right place quickly.

This challenge is about building the part of our backend that **takes in those events, makes sense of them in real time, and stays correct under pressure**.

## The problem

Build a service that ingests events from **5,000 simulated devices**, each streaming multiple event types at variable rates, and produces correct real-time aggregations.

You will receive events that look like:

```json
{ "device_id": "dev_0001", "room_id": "room_14", "type": "heartbeat",   "ts": "2026-05-23T18:53:49.123Z" }
{ "device_id": "dev_0001", "room_id": "room_14", "type": "presence",    "ts": "...", "in_room": true }
{ "device_id": "dev_0001", "room_id": "room_14", "type": "motion",      "ts": "...", "magnitude": 0.81 }
{ "device_id": "dev_0001", "room_id": "room_14", "type": "sleep_state", "ts": "...", "state": "asleep" }
{ "device_id": "dev_0001", "room_id": "room_14", "type": "fall_warn",   "ts": "...", "confidence": 0.92 }
{ "device_id": "dev_0001", "room_id": "room_14", "type": "net_status",  "ts": "...", "rssi": -68 }
```

You receive them via your choice of transport, HTTP/gRPC/WebSocket/MQTT, from the event generator we provide. Your job:

### Required outputs, queryable in real time

1. **Per-device health.** For every device, the latest heartbeat and a rolling availability over the last 5 minutes (heartbeats expected at ~1Hz).
2. **Per-room occupancy.** For every room, current `in_room` boolean (latest presence event wins) and the percentage of time the room was occupied over the last 1 minute, 5 minutes, and 1 hour.
3. **Fall warnings, deduplicated.** A device sometimes sends the same fall warning multiple times within a few seconds (sensor jitter). Emit each distinct fall event exactly once, and persist them with their original timestamp.
4. **Active alarms feed.** A real-time feed (long-poll, SSE, WebSocket, your choice) that consumers can subscribe to and receive new fall warnings as they happen, in order per room, within 1 second of ingestion.

### The complications you must handle

This is where the challenge is.

- **Per-device ordering.** Events from the same device arrive in order most of the time, but not always, devices buffer when offline and replay when reconnecting. Order by `ts`, not by arrival.
- **Clock skew.** Devices have wall clocks that drift. Trust `ts` for ordering and aggregation, but reject events more than 1 hour in the future (clearly broken) and accept events up to 1 hour in the past (offline buffer).
- **Late events.** A device may go offline for 20 minutes and replay every event when it reconnects. Your aggregations must update correctly when historical events arrive.
- **Backpressure.** When ingest spikes 10x for 30 seconds, you must not lose events. You may *delay* them. You may *prioritize* `fall_warn` over `heartbeat`. You must not drop them silently.
- **Restart correctness.** Kill the service; bring it back up. State for per-device health, per-room occupancy, and recent alarms must be recoverable. You decide how (persistent log, periodic snapshot, fresh from replay, whatever, but it must work).

## What "good" looks like

Not "passes the tests once". Good means:

- **At 10x burst rate** (50,000 events/sec sustained for 30s), the alarm feed still emits within 1s of ingest p95.
- **After a hard restart**, every consumer that was subscribed reconnects and resumes without missing alarms generated during the gap.
- **Late events from an offline device** correctly fix up the per-room occupancy history (i.e., if room was actually occupied during that gap, the 1h window reflects it after replay).
- **Adding a 5,001st device** doesn't require redeploying anything.

## What we evaluate

We run a grader that:

- Launches the event generator at baseline rate (5k devices × ~1 event/sec mixed) for 5 minutes.
- Spikes to 10x for 30 seconds, twice.
- Simulates 20% of devices going offline for 60 seconds and replaying their buffered events on reconnect.
- Hard-kills your service after 3 minutes and brings it back.
- At regular intervals queries: per-device health, per-room occupancy windows, dedup counts on fall warnings, and the live alarm feed.
- Checks for correctness against ground truth (we know exactly what the generator emitted).

## Scoring (out of 100)

| Category | Points |
|---|---|
| Correctness of aggregations under all conditions | 30 |
| Behavior under burst load and backpressure | 20 |
| Restart / recovery correctness | 15 |
| Alarm feed latency p95 | 15 |
| Code quality and design clarity | 15 |
| Observability (logs, metrics) | 5 |

**Pass bar:** 75. Below it we won't say yes, but we always reply.

## What's in this repo

```
.
├── README.md          , this file
├── SUBMISSION.md      , fill in with your submission
├── event_generator/   , simulates the 5k devices (single binary or Docker)
├── eval/              , the scenarios we run plus a ground-truth checker
└── docs/
    └── event_schema.md, the full event spec
```

## What we are **not** looking for

- Kafka-just-because. Use it if it earns its place. Justify it briefly.
- Hand-rolled distributed consensus.
- A pretty dashboard. Your service exposes HTTP/gRPC endpoints; that's enough.
- Long architectural prose. Show the thinking, not the slideware.

## What to send us

Email **info@teton.ai** with subject **`Solution: Real-time streaming backend`** and:

1. Link to your fork (public) or a tarball.
2. Writeup (under 400 words):
   - Stack and storage choice, why.
   - How you handle late events and ordering.
   - How you handle backpressure.
   - One thing you would change if you had another week.
3. How to run your service against `event_generator/` locally.
4. Your **CV** (attached), plus **LinkedIn** and **GitHub** links so we can put the work in context.

**We reply with feedback within 7 days, every submission, no exceptions.** If your work hits the bar, the next step is a conversation with engineers.

## Notes

- Time: strong candidates spend 10–25 hours on this. Spend more if you want.
- Stack: any language, any database, any message broker. We will run it locally, say so if you need Docker Compose, Nix, or just `make run`.
- LLMs: use them as you would on any other day. We don't care how you got there. We care that you can explain every choice.

Good luck.

The Teton engineering team
