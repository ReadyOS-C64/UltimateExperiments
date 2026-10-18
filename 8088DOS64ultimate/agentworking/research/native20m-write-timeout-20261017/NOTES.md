# Native20MiB write timeout — investigation, not a proven diagnosis

The failed clean import is retained in `runs/c64u-physical-gallery-install-tp-clean-20261017`; its coherent terminal RAM is in `runs/c64u-gallery-write-error-capture-20261017/dotnet/RAM.bin`. Native SETUP9e1e632a imported the302-file source and added the original DOS archives, then failed output. The raw private diagnostic bytes are `04 08 02 03 01 00`: first error4, WRITE_NEW8, bulk leaf transport2, UCI timeout3, known-closed1. SI result is `01 04 03 00 00 00 01 00 00 00 00 00 00 00 00 00`: SAVE phase3,65536 bytes produced, no verification yet. The failed SAVE is ambiguous; do not repeat it or overwrite the partial C.

This differs from the successful2MiB fresh installation and from the successful runtime's small sector writes. The actual Turbo source/EXE/output all persist through native CLOSE and match independently generated Peddle files. The device and20MiB runtime backend are usable; the failure is specifically in this installer path.

Three hypotheses need controlled tests:

1. `install_writer.c::op` copies `si_now` into `br_now`. Outer `fat_worker.s::writer` refreshes `si_now` before begin and between polls. `nf_next` inside a poll can perform substantial metadata work or synchronous source-cache I/O, whose `nc_service` updates `ps_ticks`. Test whether a command can start with an old epoch after that callback. Advance the mocked clock *within* producer/source callbacks, not merely between host calls. A fresh clock handoff at every real command boundary may be needed, but it is not yet established as the hardware cause.
2. The .NET installer observer reads1000 screen bytes every100ms. Hardware memory inspection can perturb CPU scheduling while CIA/firmware time advances. Compare unchanged native binaries with a less intrusive completion observer before treating a delay extension as a source repair.
3. Measure actual command/start/poll timing and ready/status state against the captured UCI timeout300. Separate firmware/SD latency from a stale caller epoch. Retain bounded asynchronous protocol recovery; do not add fixed sleeps or retry an ambiguous write.

Pinned3.14 primary source has distinct `Dos dos1(1)` and `Dos dos2(2)` objects, each with its own `file` member. A shared-single-handle explanation is not supported by that source. Physical two-context qualification still needs its own proof.

Keep the exact failed package/outputs. Reproduce a negative case in the actual assembled writer under Peddle, repair the verified cause, then run a fresh owned-folder hardware attempt. The runtime fixture and screenshot success do not count as native installer acceptance.
