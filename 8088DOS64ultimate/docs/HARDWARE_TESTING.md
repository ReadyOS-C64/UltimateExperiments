# Physical C64U cache verification

Verified 2026-10-14 on C64 Ultimate firmware 3.14, FPGA 121, core 1.47, PAL, enabled 16 MB REU. The native cache probe passed under **Manual turbo settings 1, 16 and 64 MHz**. Each readback contained all 1,536 expected bytes; captured executable bytes matched the uploaded PRG. This proves integrity at those settings, not calibrated throughput or target DOS boot.

[Compact evidence](../agentworking/evidence/c64u-cache-20261014.json) pins binaries, device, firmware speed options, byte hashes and restoration results. Raw Terminal-owned run: `agentworking/runs/c64u-cache-20261014-231652`.

## Procedure and recovery scope

Build with `make hardware-helpers`. Launch `build_support/c64u_probe.py --host <host> --output <new-owned-local-run-directory>` through the established macOS Terminal-owned shell workflow. Tests need exclusive use of the machine. PRGs upload directly to volatile RAM through REST; no disk image/file is created on the Ultimate and networking is not a runtime dependency.

The runner inventories actual configuration, captures C64 RAM for recovery and executes the native REU backup helper. It saves exactly 07FC00–0803FF, split into two 1 KiB transfers at 080000. This encloses every page the cache probe writes, including partial-page neighbors. It then applies supported manual speed settings and executes the same cache probe as Zig/Peddle and VICE.

Cleanup builds an owned restoration PRG with the saved 2 KiB payload at host 6000. It executes restoration, reruns backup, and requires byte-for-byte equality with the original envelope. Restored SHA-256: `32bfa7834e0c6f117ad40eb75cad39e0c945bec449e6de26687504396c43fdb5`. Prior turbo/speed, machine configuration and mounted-media settings also matched. Cleanup resets/resumes the C64. RAM capture is recovery evidence; it does not resume the old program at its prior CPU state. Volatile REU registers are not an execution snapshot either.

First attempt `c64u-cache-20261014-231434` failed with HTTP 400 on speed configuration before a cache-probe run. Backup/restoration and prior configuration still verified. Option discovery showed firmware expects the exact padded string **`" 1"`**, rather than `"1"`, for 1 MHz. The runner now selects advertised strings without trimming what it sends. Workflow tests cover this and failure-time cleanup.

## Limits

The physical REU is 16 MiB; test addresses stay below the 4 MiB baseline. Peddle additionally covers 4/8/16 MiB capacity models. No calibrated elapsed timing, UCI/IEC persistence, video quality, keyboard, DOS boot or complete IRQ/NMI behavior was tested. REST launch/poll duration is not a throughput benchmark. Timing probes must calibrate timer units and account for display/badline/I/O effects, preserving configuration and overwritten REU bytes in the same way.


## Native DOS3.3 physical milestone —2026-10-15

The frozen three-overlay647eca target passed actual native UCI360KiB import, genuineDOS/COMMAND.COM, VER and exactDIR /P atManual64MHz.35 names/sizes,9216free,14 BIOS-enqueued keys,1pagination and returnedA> are verified over108 coherent observations. Code/source/floppy/CGA identities pass. All first4MiB were backed, exhaustively delta-scanned/restored and independently reread; root byte comparison, priorconfiguration/media equality andreset/resume pass. [Evidence](../agentworking/evidence/c64u-native-dos-20261015.json).

This accepts scripted native DOS execution and physical bitmap bytes, not human matrix keyboard,40column/graphics presentation, external HDMI readability, persistent saves/HD/IEC or XT-speed ratio. The newer five-overlay timer/CGA target remains a distinct Peddle proof and has not run physically. Native bitmap reconstruction uses capturedRAM and an illustrativepalette, not a screenshot. The earlier pre-load RESTattachment failure remains retained.
