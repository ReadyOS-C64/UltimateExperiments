# Physical native SAVE write investigation

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


The current ab2d/06a4 target boots DOS and completes a real COPY on the Ultimate, but its first physical whole-floppy SAVE failed verification. All720 output sectors contain the same unexpected512-byte block. Independent FTP retrieval confirms the failure; the authoritative changed floppy is intact. All original4MiB REU bytes, settings, media and reset were recovered. See retained evidence (local development record, not distributed).

The failure is after successful write acknowledgements, CLOSE, reopen and exact FILE_INFO length368640, at first content comparison. The native compare staging contains the correct DOS boot sector. Its read buffer matches the independently retrieved wrong file. Thus this is a real write-path failure, rather than an erroneous comparison or a read-only problem. The installed cause remains unconfirmed.

## Primary-source hypothesis

The inspected upstream v3.14 commit is `830665cd9b41bc34b868f5c1a1179c5baa4989af`. The installed firmware and FPGA report3.14/121, but their complete binaries are not proven identical to this source. In particular, platform address definitions may differ.

1. [DOS WRITE](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/software/filemanager/dos.cc) passes `command->message+4` directly to the open file. The command payload offset is correct.
2. [FatFS f_write](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/software/chan_fat/ff14/source/ff.c) passes full sectors directly to `disk_write` when the file position is sector-aligned. Short writes copy through the file/volume sector buffer instead.
3. [USB bulk_out](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/software/io/usb/usb_base.cc) forwards the source pointer to a DMA descriptor. [USB memory control](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/fpga/io/usb2/vhdl_source/usb_memory_ctrl.vhd) retains only address bits25..0.
4. The public default [I/O map](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/software/system/iomap.h) and [command interface](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/software/io/command_interface/command_intf.h) place command RAM at04044800. The [command-buffer offset](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/fpga/io/command_interface/vhdl_source/command_if_pkg.vhd) is zero. Truncating payload pointer04044804 to26 bits gives00044804, a different memory domain.

This chain predicts a repeated block from the wrong memory region for aligned512-byte writes. It is a hypothesis about the installed failure, not an installed-core proof. The inspected20-file source cohort and hashes are retained under `agentworking/scratch/save-write-protocol-root-20261015/PRIMARY_SOURCE_MANIFEST.json`.

## Discriminating tests

First run source-bound patterned ECHO with exact total command lengths18/257/258/516, retaining complete command snapshots, complete replies and actual uploader positions/operands. ECHO uses a CPU copy and therefore can pass even when a later USB DMA write fails. It does not establish SAVE acceptance.

Then create fresh owned files and compare a full512-byte WRITE against two256-byte WRITEs of the same independent pattern. CLOSE/reopen/INFO/read and independent FTP must agree on every byte. Never reuse or overwrite the failed SAVE file. If shorter writes work, the complete whole-floppy exporter must still pass all360KiB comparison, EOF, final closure, cancellation, paused guest/cache and REU authority tests before promotion. A split-write model is a regression for the observed failure, not proof of the installed implementation.

The existing native HD backend also uses full-sector writes. Its physical persistence remains unaccepted; a floppy-specific workaround cannot silently establish HD correctness. Bulk SAVE_REU is a separate possible path requiring its own response, ownership and verification proof.
