#!/bin/zsh
set -eu
TASK=/Users/karlprosserpp/dev/c64projects/UltimateExperiments/8088DOS64ultimate/agentworking/scratch/native-final-ui-purpose-20261017/work
: ${DOS64_TERMINAL_WINDOW:?Owned Terminal identity required}
[[ "$DOS64_TERMINAL_WINDOW" == <-> ]] || exit 1
[[ ! -e "$TASK/supervisor.pid" && ! -e "$TASK/detached" ]] || exit 1
mkdir "$TASK/dispatch-claim"
nohup /usr/bin/python3 -B "$TASK/supervisor.py" --entry "$TASK/launch.py" --manifest "$TASK/LAUNCH_MANIFEST.json" --sha "$(cat "$TASK/LAUNCH_SHA.txt")" --output "$TASK/detached" --terminal "$DOS64_TERMINAL_WINDOW" </dev/null >"$TASK/supervisor-launch.log" 2>&1 &
task_supervisor=$!
printf '%s\n' "$task_supervisor" >"$TASK/supervisor.pid"
printf 'Detached supervisor PID %s\n' "$task_supervisor"
