"""Read-only hardware inventory; launch from a Terminal-owned shell on macOS."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--host", required=True)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
(args.output/"pid.txt").write_text(str(os.getpid())+"\n")
report = {"scope": "read-only C64U discovery, no machine/media changes", "host": args.host,
          "started_utc": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(), "requests": {}}
routes = {"version": "version", "info": "info", "drives": "drives",
          "turbo": "configs/U64%20Specific%20Settings",
          "machine": "configs/C64%20and%20Cartridge%20Settings"}
for label, route in routes.items():
    try:
        with urllib.request.urlopen(f"http://{args.host}/v1/{route}", timeout=3) as response:
            data = response.read()
        value = json.loads(data)
        (args.output/(label+".json")).write_bytes(data)
        report["requests"][label] = {"status": "ok", "sha256": hashlib.sha256(data).hexdigest(),
                                     "api_errors": value.get("errors", [])}
    except (OSError, ValueError, urllib.error.URLError) as exc:
        report["requests"][label] = {"status": "failed", "error": str(exc)}
    (args.output/"progress.json").write_text(json.dumps(report, indent=2)+"\n")
report["finished_utc"] = datetime.now(timezone.utc).isoformat()
report["status"] = "success" if all(v["status"] == "ok" and not v["api_errors"] for v in report["requests"].values()) else "failed"
(args.output/"result.json").write_text(json.dumps(report, indent=2)+"\n")
print(report["status"])
raise SystemExit(report["status"] != "success")
