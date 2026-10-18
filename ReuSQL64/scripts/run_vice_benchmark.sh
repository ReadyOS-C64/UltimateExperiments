#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HARNESS_PROJECT="${RSQL_VICE_TASKS:-${PROJECT_ROOT}/../../agenticdevharness/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj}"
DOTNET="${RSQL_DOTNET:-/usr/local/share/dotnet/dotnet}"

if [[ ! -f "${HARNESS_PROJECT}" ]]; then
  echo "VICE .NET task harness not found: ${HARNESS_PROJECT}" >&2
  exit 1
fi
if [[ ! -x "${DOTNET}" ]]; then
  echo ".NET executable not found: ${DOTNET}" >&2
  exit 1
fi

cd "${PROJECT_ROOT}"
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_benchmark.yaml --close-vice
python3 scripts/report_benchmark.py logs/vice_auto_latest \
  --json logs/vice_auto_latest/benchmark_report.json
