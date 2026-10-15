# Peddle (host test dependency)

Vendored from https://github.com/dirkwhoffmann/Peddle at commit
`c23e34a7e6516b284750b8c7caaa8c41948a407a`. The downloaded archive hash and
each copied file hash are recorded in `UPSTREAM.json`; `make manifest` checks
the files against that pin. MIT license is preserved in `LICENSE`.

Only the upstream `Peddle/` source directory and license are copied. The core
is compiled into the Zig host tests, never the C64 PRG. Project integration
lives in `tests/host/peddle_bridge.cpp`.

The embedding application must increment `clock` for each `execute()`
microcycle. Peddle's `executeInstruction()` does not advance it. Our bridge
steps bounded microcycles and an exact LDA/RTS test checks the cycle counter.
