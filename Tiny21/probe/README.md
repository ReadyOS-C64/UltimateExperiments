# Tiny 2.1 Ultimate hardware probe

The PRG configures register-controlled 64 MHz turbo, then runs two fixed prompts through the native assembly inference core. The displayed answers are produced by the model on the C64. Time to first output and total response time come from cascaded CIA2 PHI2 timers, separately from the configured turbo CPU clock. The launch worker collects actual VIC video screenshots, validates the raw timing and answer mailbox, and retains the previous turbo configuration for restoration. The probe leaves its final screen visible.

The probe uses an available 64 MHz-capable Ultimate with Command Interface and REU enabled, FTP, and the REST API. The detached worker sets REU capacity to 16 MB when needed and verifies it is left at 16 MB. It takes over C64 RAM, CIA timers and the runtime REU ranges for the run. It leaves drives and other USB files untouched. Verify shared hardware ownership from a live preflight before issuing `run`. A previously running machine program cannot be resumed after running this PRG. Development uses Peddle and reaches the device only after complete inference passes there.

## Build and verify

From the project root after building the core:

```sh
env DEVELOPER_DIR=/Library/Developer/CommandLineTools \
  make all model PYTHON=/opt/homebrew/bin/python3

run_id="$(date -u +%Y%m%d-%H%M%S)"
bundle="$PWD/build/ultimate-probe-$run_id"
/opt/homebrew/bin/python3 probe/build.py \
  --out "$bundle" --remote "/USB1/TINY64-$run_id"
/opt/homebrew/bin/python3 -m probe.check_local "$bundle"
/opt/homebrew/bin/python3 -m probe.check_video
```

The package contains `PROBE.PRG`, the converted `MODEL.BIN`, and the identity manifest. The builder verifies that the PRG contains the same core bytes used by Peddle and records their SHA-256. It uses the bootstrap at `$0801`, code starting at `$1000`, and a cold probe segment relocated from `$5000` to `$A000` before model BSS is used. The model path is compiled into the PRG and must match the owned USB run directory. The `MODEL.BIN` payload is the normal T64M REU image, converted from the pinned upstream checkpoint.

Ultimate DOS target 2 opens the file read-only, checks its exact length, issues `LOAD_REU` for address zero, and closes it. The probe drains asynchronous data and status blocks with a CIA deadline. A complete CRC32 walk through REU DMA verifies that the expected image arrived before the inference core validates the header and directory. [Ultimate DOS protocol](https://1541u-documentation.readthedocs.io/en/latest/uci/ultimate_dos_target.html) · [UCI transport](https://1541u-documentation.readthedocs.io/en/latest/uci/core_uci_architecture.html)

To package the faster mixed-layout console, build the packed core and generate its model image before using the same detached launch procedure. Use a fresh `run_id` when building either variant.

```sh
make all build/group4/core.bin
python3 -m tools.model reference/TINY.BIN build/group4/model.reu --layout group4
run_id="$(date -u +%Y%m%d-%H%M%S)"
bundle="$PWD/build/ultimate-packed-$run_id"
python3 probe/build.py --out "$bundle" --remote "/USB1/TINY64-$run_id" \
  --core-dir build/group4 --model-image build/group4/model.reu --interactive --qualify-reu
python3 -m probe.check_local "$bundle"
python3 -m probe.check_console "$bundle"
```

## Observe and run in a detached shell

Set `host` to the Ultimate's configured address. Every device transaction is executed by a Terminal-owned `nohup` background worker with stdin closed. The launcher returns while the job runs. The output directory contains `pid`, `status`, and `worker.log`.

```sh
/opt/homebrew/bin/python3 probe/launch_detached.py \
  --out "agentworking/evidence/ultimate-observe-$run_id" -- \
  observe --host "$host"
```

Inspect the preflight screenshot and make sure the device is available. An active DOS session or a process that can still write to mounted media needs to be shut down or released before launch. No C64 RAM is read while observing the device or while the probe loads and computes.

```sh
/opt/homebrew/bin/python3 probe/launch_detached.py \
  --out "agentworking/evidence/ultimate-run-$run_id" -- \
  run --host "$host" --bundle "$bundle" --device-available
```

The worker creates only the new owned USB directory, verifies the remote PRG and model hashes, and selects the register-control enum offered by the firmware (C64U Turbo Registers on firmware 3.14). The probe writes max speed and disables badline throttling in `$D031`, verifies readback, and checks that a known CPU loop completes within the 64 MHz PHI2 range. It rejects a 48 MHz board. The PAL/NTSC PHI2 rates come from the KERNAL standard flag and the report retains raw ticks. [Ultimate turbo registers](https://1541u-documentation.readthedocs.io/en/latest/config/turbo_mode.html)

Each probe build carries a unique color-bar identity and mailbox nonce so the observer can capture early errors, even if the loading frame passes unseen. Cyan and purple border phases indicate prompts one and two. Three consecutive marked green or red frames gate terminal mailbox reads. `result.json` contains separate loader time, native first-output and total times, answer text, token count, and host elapsed time. `complete.png` shows both answers and native timings. `prompt-one.png` and `prompt-two.png` capture the progress phases. There are no simulated pictures in a hardware result.

The physical run passed on C64 Ultimate firmware 3.14, FPGA 121, core 1.47. Ultimate DOS loaded 380,995 bytes in 0.214 s and CRC32 matched `e834b870`. Arithmetic returned “7 times 8 is 56.” in 48.294 s (first character 23.201 s). The Peru prompt returned “Lima.” in 46.008 s (first character 37.893 s). Raw mailbox/timings and real VIC screenshots are under `agentworking/evidence/ultimate-probe-physical-uci-diag/`. The distinct 256-byte cap run used identical model bytes and answers. It took 49.097 s and 46.776 s respectively, recorded under `agentworking/evidence/ultimate-probe-physical-dma256/`. Both runs verified unchanged turbo configuration and retained 16 MB REU. A fresh baseline rerun returned both answers at 48.295 s and 46.008 s respectively. Its total times agree with the first baseline within 0.4 ms. The machine was left on this answer screen. Evidence is under `agentworking/evidence/ultimate-probe-physical-a2/`.

## Transport microbenchmarks

Use `python3 -m probe.build_transport --out ... --remote /USB1/TINY64-... --mode reu` or `--mode georam`, then run the same detached hardware command on that bundle. The microprobe embeds a deterministic 4 KiB slice of the canonical converted checkpoint. It seeds that slice into the selected expansion mapping and verifies the result byte for byte after each timed lane.

The 17xx REU leg measures eight sweeps of one 4 KiB transfer, separate 256-byte DMA calls, and separate one-byte DMA calls. The GeoRAM leg measures CPU loads from the $DE00 aperture, using a 256-byte page and unrolling eight reads per page loop. Both time an unrolled internal C64 RAM copy for reference. All lanes copy the same 32,768 bytes to the same C64 buffer at 1 and 64 MHz, with an independent timer calibration at each setting. The microbench's 256-byte loop calls the normal driver for every chunk. The whole-prompt 256-byte variant splits within the driver. Their exact throughput and overhead therefore differ.

The physical standard-mode results below use verified 1 and 64 MHz settings and a PAL CIA2 clock. Higher is faster.

| Transfer path | MiB/s at 1 MHz | MiB/s at 64 MHz |
| --- | ---: | ---: |
| One 4 KiB DMA per sweep | 0.854 | 3.984 |
| Sixteen 256-byte DMA calls per sweep | 0.407 | 3.050 |
| One DMA per byte | 0.00277 | 0.0557 |
| Unrolled copy from internal C64 RAM | 0.101 | 6.330 |

GeoRAM is a mutually exclusive alternate expansion mapping listed by the tested Ultimate. The native aperture did not pass verification. The first read returned `$FF` against expected `$99`; disabling competing I/O mappings, explicitly reinitializing the cartridge, and qualifying seed writes at 1 MHz still left reads at `$FF`. GeoRAM has no measured throughput to report from this session. Each attempt restored ordinary REU mode, old audio and Command Interface settings, and left 16 MB configured. The transport microbench does not switch inference itself to GeoRAM.

Evidence for the standard transport benchmark is under `agentworking/evidence/ultimate-transport-physical-reu/`. The failed aperture checks are under the sibling `ultimate-transport-physical-georam*` directories.

## Interactive console

Use the same build and detached launch procedure with `--interactive` passed to `probe/build.py`. The PRG loads `MODEL.BIN` from the build's USB directory as before. Launch from that directory using the Ultimate menu or the detached worker. A successful detached launch verifies the ready state and saves `ready.png`. The same model stays in the REU across questions.

Type a question and press RETURN. DEL removes the last character. RUN/STOP clears the input line while idle. During computation, hold RUN/STOP until the console returns to input. Cancellation occurs between token ingests, so it can take the rest of the current token to respond. SHIFT enters uppercase letters and punctuation. The input line accepts up to 72 printable characters. Hardware reset leaves the console.

The Peddle test exercises the exact linked CIA1 scanner with a functional matrix and directly preloads model bytes before running the native question code. It checks editing, uppercase normalization, exact logits, cancellation, and restart using that same model. The physical console build reaches the ready screen after model loading and checksum validation on firmware 3.14. The board returned HTTP 404 for the REST keyboard endpoint, so keyboard and cancel qualification on the physical board use its keyboard. [Commodore C64 service manual, keyboard interface](https://www.retro-kit.co.uk/user/custom/Commodore/C64/manuals/C64C_Service_Manual.pdf#page=13)

For the physical keyboard check, type `what is 7 times 8`, press RETURN, and hold RUN/STOP until the prompt returns with a cancellation message. Then type `what is the capital of peru` and press RETURN. The next answer should be `Lima.` without a second load. Capture the cancellation and answer screens as separate observations.

```sh
python3 -m probe.check_console build/ultimate-console-ready
```

## Full-context diagnostic

Build with `--context-test` for a scripted 72-character out-of-domain prompt that fills the context. The diagnostic computes its entire cache from an empty history and checks that the 129th token is rejected with the position still at 128. It then starts the usual Peru question without another model load. The result decoder requires the overflow proof and both exact answers. Use a distinct owned USB directory for this longer run.

```sh
python3 -m probe.check_context "$bundle"
```

The Peddle check uses the linked native question code and seeds only the model, a static clock sample and cache-end canaries. The check reached position 128, rejected the extra token, preserved the four canaries and answered the next question from the same model. Physical timing uses the CIA clock. Use the normal detached procedure with `--timeout 420` for this longer run.

## Full REU address qualification

Add `--qualify-reu` to the build command to exercise the full 24-bit address range on cold start. The diagnostic uses the standard inference DMA driver before model admission. It saves and checks 16 bytes from the end of each of the 32 banks, plus the first 16 bytes of the highest two banks. It writes distinct tags, tests both directions across `$F7FFFF/$F80000`, checks the wrap guard and the last byte at `$FFFFFF`, and checks that the driver rejects capacity and address overflow. It restores and rereads the original 544 bytes. This is a bank-addressing and boundary check.

Peddle verified the whole backing image hash after a passing run and after detecting deliberately aliased 8 MiB and 512 KiB configurations. The actual C64 Ultimate passed all 32 sample ranges, both boundary directions and restoration before loading the model. The detached worker keeps `reu-qualification.bin`, `result.json` and `ready.png` together under `agentworking/evidence/ultimate-reu-qualify-physical/`.

```sh
python3 -m probe.check_reu_qualification build/ultimate-reu-qualify
```

## Record the hardware question set

The optional automation build accepts the harness's checked PETSCII queue
alongside the physical keyboard. Both paths use the same console editor and
inference routine. The .NET client publishes one key at a time at normal
typing cadence. Its local relay keeps Ultimate traffic in the detached
Terminal worker. The default console has no queue adapter.

Build the harness adapter from this project root with the sibling
`agenticdevharness` checkout present.

```sh
dotnet build probe/video_input/VideoInput.csproj -o build/video-input
run_id="$(date -u +%Y%m%d-%H%M%S)"
bundle="$PWD/build/ultimate-video-$run_id"
python3 probe/build.py --out "$bundle" \
  --remote "/USB1/automation/vice_tasks_dotnet/TINY64-$run_id" \
  --core-dir build/group4 --model-image build/group4/model.reu --interactive --automation
```

After the same ownership preflight, pass `video` in place of `run` to the
detached launcher. The worker records the VIC stream's changed frames and
timestamps, waits for three ready frames, verifies each answer and CIA timing
on the native screen, and writes a screenshot per question. The fixture is
`tests/fixtures/video-queries.json`. Submit-to-completion measurements retained
in the result JSON use both native screen timing and the host's VIC timestamps.

With Pillow and FFmpeg installed, edit the recording from the detached run's
`evidence` directory. The editor preserves typing speed, uses two seconds of
time-lapse per inference, then holds the completed screen for two seconds.

```sh
python3 probe/video_edit.py "$evidence" "$soundtrack" "$output_mp4"
```

## Qualify the physical keyboard

Use a distinct interactive bundle without `--automation`. After the same
ownership preflight, run the detached launcher in `keyboard` mode with the
bundle. `--keyboard-timeout` sets the observation window after startup.
Wait for `keyboard-ready.json`, then type `what is 7 times 8` on the C64,
press RETURN, and hold RUN/STOP until the console displays “Cancelled. Ready.”
Release RUN/STOP, enter the same question, and wait for `7 times 8 is 56.`
The recorder verifies the submitted question and status, saves a screenshot
of each result, and records the elapsed time. The host sends no keyboard events.

## Build the group-eight timing candidate

The optional v3 candidate reuses the same model values, with eight-channel
weight masks in Q/K/V and F1. Build a matched PRG and model as a separate run.
Use the ordinary wide group-four bundle for the current physical baseline.

```sh
make build/group8/core.bin
python3 -m tools.model reference/TINY.BIN build/group8/model.reu --layout group8
python3 -m tools.run_peddle --verify --core-dir build/group8 --layout group8 \
  reference/TINY.BIN 'what is 7 times 8' 'what is the capital of peru'
run_id="$(date -u +%Y%m%d-%H%M%S)"
python3 probe/build.py --out "build/ultimate-group8-$run_id" \
  --remote "/USB1/TINY64-GROUP8-$run_id" \
  --core-dir build/group8 --model-image build/group8/model.reu
```

When the matching CIA1-only console is already on screen, pass
`watch-keyboard` with its recorded bundle instead. The observer confirms the
live console's marker and nonce before opening the keyboard-check window.
It leaves the program running throughout.
