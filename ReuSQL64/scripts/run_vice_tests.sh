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
  run-plan --plan tests/vice/rsql64_storage.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_query.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_aggregate.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_fixedagg.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_variable.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_varupdate.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_join.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_nested.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_wide.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_wide_scalar.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_joinagg.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_result.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_ctas.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_checkpoint.yaml --close-vice
"${DOTNET}" run --project "${HARNESS_PROJECT}" -- \
  run-plan --plan tests/vice/rsql64_shell.yaml --close-vice
# The target checks KERNAL return counts; independently extract and compare the
# file so VICE/D81 persistence itself is part of the automated contract.
C1541="${RSQL_C1541:-$(command -v c1541 || true)}"
if [[ -z "${C1541}" || ! -x "${C1541}" ]]; then
  echo "c1541 is required to verify the D81 selected export" >&2
  exit 1
fi
EXPORT_TMP="$(mktemp -d)"
trap 'rm -rf "${EXPORT_TMP}"' EXIT
"${C1541}" -attach build/rsql64_checkpoint.d81 \
  -read 'cpexport,s,r' "${EXPORT_TMP}/cpexport.bin"
python3 - "${EXPORT_TMP}/cpexport.bin" <<'PY'
import pathlib
import sys

actual = pathlib.Path(sys.argv[1]).read_bytes()
expected = bytes([
    0x52, 0x53, 0x51, 0x58, 0x01, 0x03,
    0x52, 0x03, 0x00, 0x02, 0x00, 0x01, 0x00,
    0x09, 0x00, 0x05, 0x00, 0xC1, 0xCC, 0xD0, 0xC8, 0xC1,
    0x0B, 0x00, 0x01, 0x00, 0x01,
    0x52, 0x03, 0x00, 0x02, 0x00, 0x02, 0x00,
    0x09, 0x00, 0x04, 0x00, 0xC2, 0xC5, 0xD4, 0xC1,
    0x0B, 0x00, 0x01, 0x00, 0x02,
    0xFF, 0x02, 0x00, 0x00, 0x00,
])
if actual != expected:
    raise SystemExit(
        f"D81 export mismatch: expected {len(expected)} bytes, "
        f"got {len(actual)}: {actual.hex(' ')}"
    )
print("VICE D81 selected export verified byte-for-byte (52-byte RSQLX v1)")
PY

"${C1541}" -attach build/rsql64_shell.d81 \
  -read 'shellex,s,r' "${EXPORT_TMP}/shellex.bin"
python3 - "${EXPORT_TMP}/shellex.bin" <<'PY'
import pathlib
import sys

actual = pathlib.Path(sys.argv[1]).read_bytes()
expected = bytes([
    0x52, 0x53, 0x51, 0x58, 0x01, 0x03,
    0x52, 0x03, 0x00, 0x02, 0x00, 0xFE, 0xFF,
    0x09, 0x00, 0x09, 0x00,
    0x4C, 0x4F, 0x4E, 0x47, 0x20, 0x4E, 0x4F, 0x54, 0x45,
    0x0B, 0x00, 0x01, 0x00, 0x02,
    0xFF, 0x01, 0x00, 0x00, 0x00,
])
if actual != expected:
    raise SystemExit(
        f"shell D81 export mismatch: expected {len(expected)} bytes, "
        f"got {len(actual)}: {actual.hex(' ')}"
    )
print("VICE shell D81 selected export verified byte-for-byte (36-byte RSQLX v1)")
PY
