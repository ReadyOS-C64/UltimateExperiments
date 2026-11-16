# Build Tiny 2.1 v0.6 from source

The release download page prepares a matched PRG and model ZIP in the browser.
For development builds, the command-line converter and Peddle tooling are
available in the [Tiny21 source directory](https://github.com/ReadyOS-C64/UltimateExperiments/tree/main/Tiny21).

From the Tiny21 project directory, use Python 3, a C++20 compiler, ca65, and ld65.

```sh
make reference all build/group8/core.bin
python3 -m tools.model reference/TINY.BIN build/group8/model.reu --layout group8
python3 -m tools.run_peddle --verify --core-dir build/group8 --layout group8 \
  reference/TINY.BIN 'what is 7 times 8'
```

The host copies the model directly into Peddle’s mocked REU. See the
[native probe build notes](https://github.com/ReadyOS-C64/UltimateExperiments/blob/main/Tiny21/probe/README.md) for packaging a PRG and model
with the legacy fallback USB path. The current menu workflow loads the raw image named `MODEL.REU` into REU at offset zero. The PRG can be run from any folder after that step. Both converters use a pinned [upstream Tiny 2.1 checkpoint](https://github.com/WollyMonjac/Tiny-2.1).
