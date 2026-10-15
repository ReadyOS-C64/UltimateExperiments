"""Generate symbol-based VICE integrity plan and run the established .NET harness."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess


from vice_capture import verify_capture

parser = argparse.ArgumentParser()
parser.add_argument("--prepare", action="store_true")
parser.add_argument("--verify-existing", type=Path)
parser.add_argument("--evidence", type=Path, default=Path("build/reu-vice-evidence.json"))
args = parser.parse_args()
project = Path(__file__).resolve().parents[1]
os.chdir(project)
symbols = {}
for line in Path("build/dos64-reu-probe.labels").read_text().splitlines():
    fields = line.split()
    if len(fields) == 3 and fields[0] == "al":
        symbols[fields[2].lstrip(".")] = int(fields[1],16)
status = symbols["dos64_mailbox"]+1
error = symbols["dos64_mailbox"]+4
plan = f'''version: 1
kind: vice_task_plan
plan_id: dos64_reu_integrity
run_mode: gui_vice
global_defaults:
  monitor_host: 127.0.0.1
  monitor_port_start: 8902
  monitor_port_span: 40
  retry_policy:
    max_attempts: 1
    backoff_ms: 250
    jitter: false
  timeouts:
    launch_s: 45
    step_s: 30
    read_s: 2
  artifact_policy:
    capture_screen: false
    capture_state: true
    capture_dump: true
  vice:
    autostart_prg: "build/dos64-reu-probe.prg"
    drive8_enabled: false
    drive9_enabled: false
    true_drive: false
    close_vice: true
    headless: true
    speed_percent: 100
steps:
  - id: launch
    type: vice.launch
    params:
      kill_stale: false
  - id: complete
    type: assert.memory
    retry:
      max_attempts: 40
      backoff_ms: 100
      jitter: false
    params:
      start: {status}
      end: {status}
      equals_hex: "a5"
  - id: no_error
    type: assert.memory
    params:
      start: {error}
      end: {error}
      equals_hex: "00"
  - id: capture
    type: state.capture
    params:
      label: reu_integrity
  - id: dump
    type: dump.memory_ranges
    params:
      ranges:
        - label: mailbox
          start: {symbols['dos64_mailbox']}
          end: {symbols['dos64_mailbox']+7}
        - label: restored_data
          start: 24576
          end: 28671
'''
path = Path("build/dos64-reu-probe.vice.yaml")
path.write_text(plan)
if args.verify_existing:
    result = verify_capture(args.verify_existing.resolve(), project)
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, indent=2)+"\n")
    print(f"VICE captured bytes verified: {args.evidence}")
elif not args.prepare:
    harness = Path(os.environ.get("DOS64_VICE_TASKS", project/"../../agenticdevharness/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj")).resolve()
    dotnet = os.environ.get("DOS64_DOTNET", shutil.which("dotnet") or "/usr/local/share/dotnet/dotnet")
    if not harness.exists():
        raise SystemExit(f"VICE harness unavailable: {harness}")
    existing = set(Path("logs").glob("vice_auto_*/manifest.json"))
    subprocess.run([dotnet,"run","--project",str(harness),"--","run-plan","--plan",str(path),"--close-vice"],check=True)
    created = set(Path("logs").glob("vice_auto_*/manifest.json")) - existing
    matching = [p.parent for p in created if json.loads(p.read_text(encoding="utf-8-sig")).get("plan_id") == "dos64_reu_integrity"]
    if len(matching) != 1:
        raise SystemExit(f"Expected one new probe run, found {len(matching)}")
    result = verify_capture(matching[0].resolve(), project)
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(result, indent=2)+"\n")
    print(f"VICE captured bytes verified: {args.evidence}")
