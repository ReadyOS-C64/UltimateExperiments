# Optional early SETUP runtime preflight

Build the matched native release, then the release-bound SETUP:

```sh
make start-ini-bundle
make setup-installer-preflight
make setup-installer-preflight-tests
```

`DOS64_SETUP_BUNDLE_RESULT` selects a different qualified coupled `RESULT.json`. Direct native build:

```sh
python3 -B build_support/setup_installer.py --bundle-result /absolute/path/RESULT.json --out build/setup-installer-bound
```

The ordinary `make setup-installer` remains unbound/default-off. The V1 candidate builder explicitly chooses the bound form and rejects an unbound SETUP or SETUP/CONFIG made for different coupled assets.

The optional test command compiles production SETUP and a fresh Peddle model from public source. It runs two native SYS/CIA coordinator checkpoints, six native loader fault groups and eleven host binding/source controls. It uses deterministic DOS-sized loader fixtures and the supplied matched native assets; it requires no DOS images, prebuilt model, Zig or device. This is early dependency validation, not a full installer, guest-DOS or physical acceptance test. The selected test files are `test_preflight_final.py` and `test_runtime_negative.py`; other staged helpers retain fixtures for their original default-mode tests.

Tools: Python3, cc65/ca65/ld65 + none.lib; a C++20 compiler is additionally required for tests. Standard DOS64_CC65/CA65/LD65/CC65_LIB and DOS64_CLANGXX overrides apply. A native-only bound build does not probe or require C++/Peddle/Zig. All failed/finished runs retain source, product and command receipts under the owned output directory. The test result is published only after source/product closure.

Native SETUP checks all eight readonly inputs before output CREATE: three selected DOS images, START.TPL/START.REL, DOS64.PRG/DOS64.REL and START.INO. A missing or mismatched file stops the job before C creation. Signed descriptor identity includes all64 bytes; the fixed full-descriptor CRC alone is insufficient. The build currently requires START's disabled131-byte control capsule to fit within one512-byte source block, and explicitly rejects an unsupported future layout.

Candidate packaging tests are separately opt-in: `make v1-package-tests`. They live outside default tooling discovery and require a freshly built candidate receipt.
