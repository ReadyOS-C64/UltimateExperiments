# Build Tiny 2.1 from source

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
[native probe build notes](../probe/README.md) for packaging a PRG and model
with the legacy fallback USB path. The current menu workflow loads the raw image named `MODEL.REU` into REU at offset zero. The PRG can be run from any folder after that step. The v0.6 release uses the pinned [upstream Tiny 2.1 checkpoint](https://github.com/WollyMonjac/Tiny-2.1).

## Development models with up to 255 positions

The v0.7 group-eight core accepts T64M layout 4. Use a TNY2 checkpoint with
the same 97 character tokens, width 96, four layers, four heads and 256-wide
feed-forward layers. Include one learned position row per supported token
position, between the token embedding and the first layer. Each source row
has a float32 scale followed by 96 signed weight bytes. The converter derives
the context length from the checkpoint size and accepts 128–255 positions.
The original Tiny 2.1 checkpoint has 128 learned absolute positions.

```sh
python3 -m tools.model path/to/checkpoint.bin build/extended.reu --layout group8-context
python3 -m tools.run_peddle --verify --core-dir build/group8 --layout group8-context \
  path/to/checkpoint.bin 'your prompt'
```

Pass `--model-image build/extended.reu` to the native probe builder to produce a
matching PRG with the model's CRC. The PRG accepts one image at a time at REU
offset zero. The context is a shared budget for the prompt, delimiter and
generated tokens. The editor reserves 56 positions for the delimiter and
response, allowing up to 199 prompt characters with a 255-position model.

Layout 4 keeps the original directory and first 128 position rows in place.
Header byte 52 stores the position count, and the extra rows follow the gains
in the same tiled format. The loader validates the count, image length and
directory. A longer model uses REU `$080000–$0BFFFF` with a 64 KiB stride per
layer. Scores for all heads fit in CPU RAM under KERNAL at `$E000–$FFDF`.

## Build and install the two-model console

The console requires **64 MHz C64 Ultimate turbo**, **a 16 MB REU**, and
**Command Interface enabled** for Ultimate DOS. Use the C64U Turbo Registers
setting so that the console can select and verify full speed.

```sh
make build/group8/core.bin
python3 -m tools.model reference/TINY.BIN build/group8-model.reu --layout group8
python3 -m probe.package_models --out build/Tiny21-v0.7-C64PROGINFO.zip \
  --tiny build/group8-model.reu --programmer models/C64PROGINFO.BIN
```

Unzip the package. Copy `PROBE.PRG`, `MODEL.BIN`, and `C64PROGINFO.BIN` to
`/USB1/TINY64-MODELS` on the Ultimate and run `PROBE.PRG` from its menu.
Press **F1** for Tiny 2.1 or **F3** for C64PROGINFO. A build made with
`--remote` can use a different location.

Tiny 2.1 resides at REU `$000000` and C64PROGINFO at `$100000`. The second
image carries its name in the T64M header. The console checks the active
model's image CRC and loads a matching file with Ultimate DOS if needed.
Each successful switch resets the shared KV cache's logical position.
The active model and its context size are determined when it is admitted.

Try `show assembler code to set border to red` or
`show basic code to clear the screen and print ready` in C64PROGINFO.
The assembler answer is displayed as two separate lines, `LDA #$02`
followed by `STA $D020`.

For a longer example, ask
`show assembler code to start only sprite 0 at x 64 y 80 using data at 3072 on the default screen`.
The reply fills ten lines. This example assumes the normal VIC bank and
screen addresses. A pattern must already be at decimal address 3072.
[More checked prompts](../training/native_checks.txt).
