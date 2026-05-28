"""
Eval runner for the streaming-backend challenge.

Runs the event generator against your service, then queries your read
endpoints and compares them to ground truth. Prints a scorecard.

Run:
    python eval/check.py --target http://localhost:8080 baseline

Your service is expected to expose at least:

    GET /devices/{device_id}/health
        -> { "last_heartbeat_ts": "...", "availability_5m": 0.0..1.0 }

    GET /rooms/{room_id}/occupancy?window=1m|5m|1h
        -> { "in_room": bool, "occupied_pct": 0.0..1.0 }

    GET /alarms?since=<ts>
        -> { "alarms": [ { event_id, room_id, ts, confidence }, ... ] }

If your endpoints look different, pass --map to define the URLs (see --help).
This eval focuses on the dedup invariant and overall correctness, not the
full grading harness — we run a bigger one when scoring.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def fetch_json(url: str) -> dict:
    try:
        with urlopen(url, timeout=5) as resp:
            return json.loads(resp.read())
    except (URLError, HTTPError, OSError, ValueError):
        return {}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("scenario", choices=["smoke", "baseline", "burst", "offline", "adversarial"])
    p.add_argument("--target", default="http://localhost:8080")
    p.add_argument("--devices", type=int, default=50)
    p.add_argument("--duration", type=float)
    args = p.parse_args()

    # Default durations chosen to keep local runs short.
    duration = args.duration or {
        "smoke":       30,
        "baseline":    60,
        "burst":       180,
        "offline":     120,
        "adversarial": 240,
    }[args.scenario]

    mode = "baseline" if args.scenario == "smoke" else args.scenario

    cmd = [
        sys.executable, os.path.join(ROOT, "event_generator", "generate.py"),
        "--mode", mode,
        "--target", args.target,
        "--devices", str(args.devices),
        "--duration", str(duration),
    ]
    print(f"Running scenario '{args.scenario}' ({mode}) against {args.target}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)

    # Parse the ground-truth line emitted on stderr
    gt = None
    for line in proc.stderr.splitlines():
        if line.strip().startswith('{"ground_truth"'):
            gt = json.loads(line)["ground_truth"]
    if gt is None:
        sys.exit("Could not read ground truth from event_generator output")

    print("\nWaiting 3s for in-flight late events to settle…")
    time.sleep(3)

    # Query a small sample of endpoints
    alarms = fetch_json(f"{args.target}/alarms?since=0").get("alarms", [])
    print(f"\n=== Scorecard: {args.scenario} ===")
    print(f"  events generated      {gt['total']} (incl. fall jitter)")
    print(f"  HTTP ingested ok      {gt['sent_ok']}")
    print(f"  HTTP failed           {gt['failed']}")
    print(f"  distinct falls (gt)   {gt['distinct_falls']}")
    print(f"  alarms returned       {len(alarms)}")

    # Dedup check
    if not alarms:
        print("  ⚠ /alarms returned no alarms — endpoint missing or empty")
    else:
        delta = len(alarms) - gt["distinct_falls"]
        if delta > 0:
            print(f"  ⚠ {delta} extra alarms — dedup is leaking duplicates")
        elif delta < 0:
            print(f"  ⚠ {-delta} missing alarms — some falls were dropped or filtered out")
        else:
            print(f"  ✓ alarm count matches distinct falls")

    # Sample per-room occupancy on a known room
    sample_room = "room_000"
    occ = fetch_json(f"{args.target}/rooms/{sample_room}/occupancy?window=1m")
    if not occ:
        print(f"  ⚠ /rooms/{sample_room}/occupancy returned nothing — endpoint missing")
    else:
        print(f"  /rooms/{sample_room}/occupancy?window=1m: {occ}")

    # Sample device health
    sample_dev = "dev_0000"
    health = fetch_json(f"{args.target}/devices/{sample_dev}/health")
    if not health:
        print(f"  ⚠ /devices/{sample_dev}/health returned nothing — endpoint missing")
    else:
        print(f"  /devices/{sample_dev}/health: {health}")


if __name__ == "__main__":
    main()
