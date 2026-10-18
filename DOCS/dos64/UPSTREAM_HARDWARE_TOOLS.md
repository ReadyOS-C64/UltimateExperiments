# Optional hardware automation

The physical demonstrations used an external .NET Ultimate harness with memory inspection and real VIC video-stream capture. It is not included and is not required to build or run the emulator. No personal checkout paths or device addresses are needed by the public build.

The harness uses the Ultimate REST memory and stream routes. The physical video stream supplies screenshots; independent guest/native RAM, font and cursor checks validate display contents. A C64 RAM read is not a REU dump or live processor-port latch proof.

Keep physical control single-owner, detached and bounded. Verify backing-file closure before reset. The application itself uses Ultimate DOS/UCI directly; REST, FTP and the .NET harness are development tools. [Hardware workflow](HARDWARE_TESTING.md), [current status](STATUS.md).
