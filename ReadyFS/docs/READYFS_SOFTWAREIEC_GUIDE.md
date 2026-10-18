# SoftwareIEC: logical partitions and mapped folders

**SoftwareIEC is the Ultimate's software IEC filesystem.** ReadyFS addresses its logical partitions with `s0:/`, `s3:/`, and similar paths. A logical partition exposes a mapped root; the location after the colon is interpreted within that mapping. ReadyFS discovers the SoftwareIEC IEC bus through the Ultimate Command Interface.

SD2IEC is a separate device and backend. Its native paths use an IEC address and optional partition suffix, such as `10.1:/`. Its partition queries, extension settings and image-mount rules belong in the [SD2IEC reference](SD2IEC_NATIVE.md) and [SD2IEC walkthrough](READYFS_SD2IEC_TUTORIAL.md).

## Find SoftwareIEC and inspect its mapping

```text
DRIVES
PROBE SOFTIEC
CAPABILITIES s0:/
DIR s0:/
```

Use the logical partition and actual directory names available in your configuration. `s0:` means **SoftwareIEC logical partition 0**, not IEC device 0 or SD2IEC partition 0. `s3:` means logical partition 3; it does not mean device 3. A mapped root may expose a different folder layout from `u:/usb1/`, so inspect it before translating paths by hand.

SoftwareIEC needs the Ultimate Command Interface enabled and a valid discovered IEC bus. The capability report describes the backend model; it does not establish that every folder operation works on every firmware.

## Bookmark a SoftwareIEC folder

With an existing `demo` folder in the selected mapping:

```text
ALIAS SOFT s0:/demo
DIR @soft:/
CD @soft:/
PWD
```

The alias stores this exact location. It does not create a mapping or folder, change firmware settings, or turn the endpoint into UltimateDOS or SD2IEC. Relative paths subsequently use the ReadyFS current directory. Save aliases explicitly with `CONFIG SAVE` if you want to reload them in another session.

## Copy between Ultimate host storage and SoftwareIEC

Assume `u:/usb1/demo/notes.seq` exists, the mapped `demo` destination folder exists, and the destination names are unused:

```text
COPY u:/usb1/demo/notes.seq @soft:/NOTES --WHATIF
COPY u:/usb1/demo/notes.seq @soft:/NOTES
COMPARE u:/usb1/demo/notes.seq @soft:/NOTES
COPY @soft:/NOTES u:/usb1/demo/returned.seq
```

Single-file destinations name the file explicitly. COPY normally verifies the staged destination before committing it. MOVE uses the supported copy/verification route and then removes the source; inspect partial failures before retrying. Host and SoftwareIEC paths can reach overlapping underlying storage, so choose distinct source and destination files rather than assuming different endpoint names imply separate disks.

The same paths can be passed to [batch scripts](READYFS_RUN_GUIDE.md). For example, the compact [TRANSFER.SEQ](examples/TRANSFER.SEQ) can preview and apply a transfer:

```text
RUN u:/usb1/demo/TRANSFER.SEQ u:/usb1/demo/notes.seq @soft:/SAVED PREVIEW
RUN u:/usb1/demo/TRANSFER.SEQ u:/usb1/demo/notes.seq @soft:/SAVED APPLY
```

## Mapping commands and firmware limits

Creating or removing a SoftwareIEC mapping is different from mounting an SD2IEC image or an Ultimate floppy image. ReadyFS exposes the following preview syntax:

```text
MOUNT u:/usb1/demo s3: --NAME DEMO --WHATIF
DISMOUNT s3: --WHATIF
```

The first describes mapping a **host folder** to SoftwareIEC logical partition 3; the second describes removing that mapping. Execution depends on firmware support. The tested Ultimate firmware 3.14 lacks the required map/unmap commands, so use an existing mapping there. A preview is not proof that mapping execution is available.

SoftwareIEC remains firmware-sensitive. Directory enumeration can be incomplete, folder operations can be restricted, and large parent directories can expose firmware limits. Prefer dedicated shallow folders. Verified single-file transfers are not a blanket guarantee of recursive folder-tree support. Native SD2IEC's `IEC 10: CONFIG`, `PARTITIONS`, extension modes and `.1` suffix do not configure SoftwareIEC.

## Interoperability: SoftwareIEC and native SD2IEC

These commands deliberately cross **two distinct backends**. Assume the SoftwareIEC `NOTES` file from the earlier example and an existing SD folder on device 10, partition 1:

```text
ALIAS CARD 10.1:/demo
COPY @soft:/NOTES @card:/fromsoft
COMPARE @soft:/NOTES @card:/fromsoft
COPY @card:/fromsoft @soft:/FROM-SD
```

SoftwareIEC keeps its `s0:` mapping semantics. SD2IEC keeps its native IEC address, partition, filename/type handling and media view. The shared COPY/COMPARE language bridges them; it does not make their configuration or image behavior interchangeable. For SD folder/image transitions and transfers to mounted IEC disks, continue with the [SD2IEC interoperability walkthrough](READYFS_SD2IEC_TUTORIAL.md).

## Further reading

- [ReadyFS overview and path examples](../README.md)
- [Illustrated user guide](READYFS_USER_GUIDE.md)
- [Batch scripting](READYFS_RUN_GUIDE.md)
- [Supported routes and limits](READYFS_ACCEPTANCE.md)
