DOS64 Ultimate runtime-media development candidate

This source-built candidate is not a qualified V1 or physical release.
Keep backups. It includes twelve matched native files, no DOS images or
configured user disks. Copy all twelve into one NEW folder on the Ultimate.
Keep the three SETUP files, CONFIG.PRG and all eight runtime/START assets
together. Do not mix assets from another build or replace an existing home.

Supply your own three DOS 3.3 360 KiB raw images. Enable Ultimate DOS/UCI
and at least 4 MiB REU. The modeled profile is PAL, Turbo Control Manual,
CPU Speed 64. Record your usual settings; a speed labelled 64 alone does
not prove Manual turbo is active. Build success is not hardware acceptance.

Run SETUP.PRG, choose this home and your three DOS images, then choose
2 or 20 MiB C, or the supported existing-C import. SETUP creates C, A/B,
a configured START.PRG and DOS64.CFG, and copies the matched runtime assets.
Existing destinations are refused. After interruption, retain all files
and choose a fresh home; do not overwrite an uncertain installation.
No blank HD download, dummy D81 or guest FORMAT/COPY is required.

Run the generated START.PRG. It verifies the matching runtime, menu and
startup recovery assets. A pending save journal is not silently ignored:
follow its explicit recovery screen, retaining the original and new files.
CONFIG.PRG can prepare a new launch folder using existing absolute media
paths. It asks for the release folder, new folder and supported 40/80 startup
preference. A missing same-home DOS64.INI defaults to 80; the included ASCII
example documents that option. Do not move launch folders without rebuilding
the launcher/configuration through the supported tools.

During DOS, Ctrl + Commodore + Run/Stop opens native floppy controls.
A/B selects the drive; S saves to a new managed image version; N is Save as;
I inserts/changes an image; E ejects; W changes session write protection.
Follow Save/Discard/Cancel prompts for modified media. Eject/protect are
session-only. R resumes DOS when ownership and closure checks permit it.
Before ending a session, exit guest applications to DOS, then use F Finish.
Restart only after the native screen reports that it is safe. Finish ends
the guest session; it does not resume DOS. Errors or unknown file ownership
must not be treated as a completed save or permission to restart normally.

Model workflows and source builds do not establish physical keyboard,
display, power-loss or Turbo Pascal acceptance for this exact package.
No performance target is claimed. See docs/V1_ENDPOINT.md in the project.
SHA256SUMS checks copy integrity, not authenticity or release qualification.
