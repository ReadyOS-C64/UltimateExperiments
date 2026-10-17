# Optional native SETUP integration tests

Run from the project root:

```sh
make setup-installer-tests
```

Supply the three locally owned MS-DOS 3.3 360KiB installation images. The default paths are `reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - N of 3.img` for N=1,2,3. To use other paths:

```sh
python3 -B build_support/setup_installer_tests.py \
  --disk1 '/path/disk1.img' --disk2 '/path/disk2.img' --disk3 '/path/disk3.img'
```

The Make target also accepts `DOS64_SETUP_TEST_ARGS` containing these arguments. No DOS disk images are included with the test distribution. Each image is checked for complete 360KiB geometry and valid FAT allocation; disk1 must contain IO.SYS, MSDOS.SYS and COMMAND.COM. Filesystem payloads are used as independent expected inputs, so supply the appropriate three-disk distribution.

Required tools are Python3, make, cc65/ca65/ld65 with none.lib, a C++20 compiler, and the project-compatible Zig compiler. Overrides are `DOS64_PYTHON`, `DOS64_MAKE`, `DOS64_CC65`, `DOS64_CA65`, `DOS64_LD65`, `DOS64_CC65_LIB`, `DOS64_CLANGXX`, and `DOS64_ZIG`. Executable paths are resolved before changing directory. The ordinary project build does not run these tests.

Every invocation creates a fresh directory under `build/setup-installer-tests`, builds the actual public START template and its checked descriptor, and compiles the public production SETUP source graph. The independent C++ Peddle/platform models and tests are then copied into that build's work directory. Tests execute the linked 6510 program; they do not replace the installer with host code, injected producer facts, or previously compiled native binaries. The four full integration cases run as independent subprocesses in parallel; each owns a separate model machine.

The cases cover true BASIC SYS startup through all installer phases, creation and verification of A/B/C/START/CFG, existing-C collision, existing-START collision, and existing-CFG collision. Eight Zig assertions are compiled and directly executed separately. The full case checks exact source-derived FAT contents, producer receipts, write ordering, configured launcher/config bytes, closed file ownership, and the final native caption. The host filesystem oracle parses the resulting image independently.

`RESULT.json` identifies the fresh work directory, executed commands, source/tool hashes, native products, memory layout, and case outcomes. Inputs, staged source copies, tools, and products are hashed before and after execution. Failures retain the first failing phase and logs; any still-running child cases are terminated and reaped. No physical C64 Ultimate is contacted.

This optional lane qualifies the generated installer artifacts in the modeled file/REU environment. It does not boot the generated launcher through guest DOS, test physical firmware, cover every 20MiB or existing-disk import case, or integrate DOS64.INI. Those require separate qualified lanes. Unchanged imported helper modules contain fixtures for their own focused tests; the selected four cases use the real production coordinator and real supplied source files.

The bundled Peddle source and independent platform/model helpers come from the project's existing test tooling. The production native C/ASM is always taken from `build_support/setup_installer.py` and its public source map.
