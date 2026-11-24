"""Start an Ultimate operation in a background shell managed by launchd."""
import argparse
from pathlib import Path
import shlex
import subprocess
import sys
from uuid import uuid4

SOURCE = Path(__file__).resolve().parent


def launch(out, args):
    cwd = shlex.quote(str(Path.cwd()))
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    label = f"org.readyos.tiny21.probe.{uuid4().hex}"
    cmd = shlex.join([sys.executable, str(SOURCE / "physical.py"), *args,
                      "--out", str(out / "evidence")])
    worker = out / "worker.sh"
    worker.write_text(
        "#!/bin/bash\n"
        "set -u\n"
        f"printf '%s\\n' \"$$\" > {shlex.quote(str(out / 'pid'))}\n"
        f"cd -- {cwd} && TINY64_DETACHED=1 {cmd}\n"
        "status=$?\n"
        f"printf '%s\\n' \"$status\" > {shlex.quote(str(out / 'status'))}\n"
        f"/bin/launchctl remove {label}\n"
        "exit 0\n"
    )
    subprocess.run(
        ["/bin/launchctl", "submit", "-l", label, "--", "/bin/bash", "-c",
         'exec /bin/bash "$1" </dev/null >"$2" 2>&1',
         "tiny21-probe", str(worker), str(out / "worker.log")],
        check=True, timeout=20,
    )
    print(out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    options = args.args[1:] if args.args[:1] == ["--"] else args.args
    if not options:
        parser.error("pass observe or run and arguments after --")
    launch(args.out, options)
