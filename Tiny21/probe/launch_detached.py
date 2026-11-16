"""Start an Ultimate operation in a detached Terminal-owned background shell."""
import argparse
from pathlib import Path
import shlex
import subprocess
import sys

SOURCE = Path(__file__).resolve().parent


def launch(out, args):
    cwd = shlex.quote(str(Path.cwd()))
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
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
        'exit "$status"\n'
    )
    launch_cmd = (" /usr/bin/nohup /bin/bash " + shlex.quote(str(worker))
                  + " </dev/null >" + shlex.quote(str(out / "worker.log"))
                  + " 2>&1 & disown")
    subprocess.run(
        ["/usr/bin/osascript",
         "-e", "on run argv",
         "-e", 'tell application "Terminal" to do script (item 1 of argv)',
         "-e", "end run", launch_cmd], check=True, timeout=20,
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
