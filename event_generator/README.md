# Event generator

Simulates 5,000 devices streaming events at the rates and patterns described in the repo root README.

This stub will be fleshed out before public release. Until then, treat the spec below as the contract your service must satisfy.

## Modes

```
baseline    , 5,000 devices × ~1 event/sec each, mixed types
burst       , 10x burst for 30 seconds, twice during the run
offline     , 20% of devices go offline for 60 seconds, replay buffered events on reconnect
adversarial , combination of the above plus random clock skew
```

## Transport

Configurable; defaults to HTTP POST to `http://localhost:8080/events`. WebSocket and MQTT modes are also planned.

## Event schema

See [`../docs/event_schema.md`](../docs/event_schema.md).

## Running locally

```bash
# fleshing-out: docker run --network=host teton-challenge-event-generator --mode baseline
```

> **Note:** until this is shipped, infer the interface from the spec above and the README in the repo root. We will run your service against the real generator when grading.
