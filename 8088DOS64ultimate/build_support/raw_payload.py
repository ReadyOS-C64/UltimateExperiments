"""Strip the checked PRG header to expose identical bytes for raw unit loading."""
import sys
from pathlib import Path
data = Path(sys.argv[1]).read_bytes()
if data[:2] != b"\x01\x08":
    raise SystemExit("Unexpected PRG load address")
Path(sys.argv[2]).write_bytes(data[2:])
