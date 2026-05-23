# Event schema

All events share a common envelope:

```json
{
  "device_id": "dev_XXXX",         // stable per device
  "room_id":   "room_XX",          // current room the device is in (rarely changes)
  "type":      "heartbeat | presence | motion | sleep_state | fall_warn | net_status",
  "ts":        "2026-05-23T18:53:49.123Z",  // device wall clock, ISO 8601 with ms
  "seq":       1234                 // monotonic per-device sequence number
}
```

## Per-type fields

### `heartbeat`
No additional fields. Expected ~1Hz.

### `presence`
```json
{ "in_room": true }
```
Emitted when state changes.

### `motion`
```json
{ "magnitude": 0.81 }   // 0..1
```
Emitted at variable rate (more when there's motion).

### `sleep_state`
```json
{ "state": "asleep" | "awake" | "unknown" }
```
Emitted on transition.

### `fall_warn`
```json
{ "confidence": 0.92 }   // 0..1
```
**May be emitted multiple times within a few seconds** for a single physical fall (sensor jitter). You must deduplicate to one logical event per fall.

### `net_status`
```json
{ "rssi": -68 }
```
Periodic; degrades when device is in poor signal.

## Time and ordering

- `ts` is the **device wall clock** and is the authoritative time for ordering and aggregation.
- Devices have **clock drift** of up to ±30s under normal conditions, occasionally more.
- `seq` is **monotonic per device** but may have gaps when a device misses events during local buffer overflow (uncommon).
- Per-device ordering by `ts` is correct; per-room ordering across devices is not guaranteed.

## Acceptance rules

- Reject events with `ts` more than **1 hour in the future** (clearly broken clock).
- Accept events with `ts` up to **1 hour in the past** (offline buffer replay).
- Reject events with malformed or missing required fields.
