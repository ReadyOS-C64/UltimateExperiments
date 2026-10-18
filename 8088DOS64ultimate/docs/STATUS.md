# Current status and limitations

Snapshot: 17 October 2026. This page is the current qualification summary. Other implementation notes describe particular slices and may retain historical measurements; they do not override this page. This project is a development preview, not a qualified V1 release.

| Area | Demonstrated | Remaining |
|---|---|---|
| CPU and RAM | Original-8088 interpreter; 640 KiB guest RAM in REU; real DOS 3.3 boot | Functional interpreter, not bus/prefetch cycle accuracy or universal PC compatibility |
| Text | Physical DOS VER, DIR, DIR pipe MORE, TYPE in 40/80 columns | Final human keyboard/readability qualification |
| Graphics | Modeled/native CGA 4/5/6 reduction; physical 40-column colour-text RIPPLE | Native graphics palette/reduction compromises; no EGA/VGA or 16-colour CGA graphics |
| GW-BASIC | Physical hangman autoplay, LIST, SYSTEM and DOS return | Broader BASIC/application compatibility |
| Turbo Pascal | Original 7.01 IDE edit, correction, save, Disk compile, IDE/DOS run, cold reopen; RIPPLE compile/run | Broader compiler/library compatibility and final human qualification |
| A/B floppies | Separate images, write tracking, modeled media operations; earlier physical complete-image save proof | Current native swap/Save/Finish workflow with C online needs complete physical qualification |
| C drive | 2/20 MiB cached backend; physical writes, native close, complete 20 MiB retrieval, original payload preservation and cold restart | Power-failure durability is not established; no C-only boot qualification |
| Native installer | Physical fresh 2 MiB install, generated launcher and DOS boot | 20 MiB creation fails at WRITE_NEW with UCI error 03 after 65,536 produced bytes; cause not proven |
| CONFIG and disk menu | Source builds and actual-assembly/model workflows | Complete physical relocation, configuration, Save/Finish and recovery acceptance |
| Performance | Historical kernels measured about 2.65% and 3.96% of a modeled 4 MHz 8088 | 50%/85% objectives unmet; no current whole-DOS XT speed claim; optimization deferred until after V1 |

The successful 20 MiB Turbo sessions used host-prepared development media/configuration, with genuine native A/B components. They must not be represented as successful native 20 MiB installation. The download is freshly source-built; prior hardware demonstrations do not qualify every rebuilt package byte for byte.

Floppy writes stay in REU until explicitly saved. C is file-backed and cached; use native Finish after returning to DOS, and wait for the safe completion screen before resetting. Native Finish qualification is still open. Keep original media and work backups.

No networking, 8087, EGA/VGA or general sound hardware is provided. Only specifically supported timer/port compatibility is implemented. Unknown hardware accesses may be rejected rather than silently accepted.

The RIPPLE screenshot session took about 24 seconds from accepted launch to completed capture, including EXE loading and paused observation/video capture. It is not pure drawing time or an XT performance benchmark.

[Install](INSTALL.md) · [Build and tests](BUILD.md) · [V1 endpoint](V1_ENDPOINT.md) · [Screenshots](SCREENSHOTS.md)
