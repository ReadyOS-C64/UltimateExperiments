#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
/usr/bin/osascript -e "tell application \"Terminal\" to do script \" python3 '$root/build_support/capture_readyfs_demo_failure.py' > '$root/logs/readyfs_c64u/demo-failure-capture.log' 2>&1\""
