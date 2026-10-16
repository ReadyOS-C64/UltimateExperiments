# User floppy media, save and swap — proposal2026-10-16

A conventional raw360KiB IMG is the persistent PC floppy representation. It contains the DOS boot/FAT/root/data sectors and needs no D81, otherCBM container, or sidecar to interpret its sectors. Config/optionalrecovery journals are separate application metadata. Arbitrary compressed/flux formats and largergeometries are outside the initial supported profile. The complete mounted image resides in its assigned REUslot; REU is working storage, not persistence.

## Current actual behavior

src/disk.s services only BIOS DL0 and writes the mounted image in REU. There is no independentB implementation or user disk browser/dirty-state UI. The reserved512KiB Bslot does not change that. DOS may expose single-drive logical behavior; it is not an independent second mountedimage.

Native development SAVE command7, from coherentpaused state, exports all720sectors to a fresh create-new path, closes/reopens, checks exact368640-byte size, compares everybyte, checks EOF and finalCLOSE. The earlier d883c678 build passed this on physicalUltimate with independent wholefile retrieval; evidence/c64u-complete-split-save-20261015.json. No automaticwriteback or final userSave/Discard/Exit interface is implemented. Current src/native_save.s explicitly rejects hdb_online/hd_uncertain/conflictinghandles; floppy saving with C mounted needs new reviewed context integration and physical acceptance. Do not transfer the old physical result to a new composed binary automatically.

## Recommended first user workflow

Keep originalsupplied DOS images readonly. SETUP creates writableworkingcopies where requested. HostDiskMenu shows A/B selectedname, readonly/writable, modified/saved/uncertain/empty and actions Insert/Change,Eject,Save,SaveAs,WriteProtect,Resume,Exit. Use a testedhost-only shortcut that does not steal DOS/editor keys; do not invent an untested matrix chord. Native UI runs while guest is paused at a safe boundary, using explicit overlay/REUownership; it is not a separate setup app overwriting a liveemulator without context preservation.

Save freezes the exactdrive/mount/content generation, makes guest-to-REU caches coherent, writes a fresh temporaryIMG, closes/reopens and verifies it completely, then publishes the backingpath via checkedbackup/rename/finalreadback. Clear modifiedstate only for the frozen generation after allcommitchecks. SaveAs creates another normal rawIMG and changes its backingbinding only after verification. Failure leaves REUauthoritative and dirty/uncertain, with recoverableold/newfiles; never ejectonfailedsave. This is not a provenpower-loss-atomic replace.

Changing/ejecting a modifiedimage offers SaveAndContinue,DiscardChanges,Cancel. Cancel preserves the mounteddrive. Discard is explicit and affects only the currentworkingversion. Saving failure cancels the change and keeps oldmedia authoritative. Validate an incomingIMG fully, stage it separately and switch its descriptor only after successfulload. A spare512KiB swapbuffer can be budgeted from the HDcachearena (currently onlytwo32KiBextents used), with explicit allocator/ownership/layout changes; never overwrite liveguest/otherfloppy/activeHDcache to make room implicitly. The4MiBminimum remainsbinding.

Each drive needs a realdescriptor: backingpath, geometry/length, REUbase, readonly, mountgeneration, contentgeneration, dirty/uncertain and savedidentity/CRC. Mark dirty before/through a potentiallypartial mutation, not only after a wholeBIOSwrite reports success. A/B must never silentlyalias. Configuration CRC/bindings must refresh after legitimateSave; originals remain unchanged.

## DOS boundaries and persistence policy

A nativeSave exports bytes DOS has actually submitted to BIOS; it cannot force an application to close files or flush data still held in guestDOS buffers. Prefer swapping at the DOSprompt or application's normal disk-change prompt, after files are closed. Native cache coherence is not DOS filesystem cache invalidation. Test originalXT/DOS3.3 swap/revalidation behavior explicitly, including identical labels/volumeIDs, directorybuffers and openfiles; do not graft laterATchange-line semantics by assumption. A small genuineDOS helper using normalDOS calls to coordinate buffer flushing and the native menu is an option, not implemented behavior or an INT21h replacement.

Recommend explicitSave plus promptedSave on swap/eject/exit for the firstrelease, with whole360KiB images and completeverification. Autosave can follow at coherentDOSidle/checkpoints with visiblepending/saved/errorstate; per-sectorwrite-through makes commonwrites slower and still does not make a multi-sector FATupdate atomic. Dirty-sector maps (720bits=90B/drive) may optimize later saves, but do not replace drive/generation binding or verification. CurrentonlineC restriction must be fixed while preserving/reopening its own handle/cachecontext before normalA+B+C persistence is advertised. Hardware tests must prove that floppySave neithercloses norcorruptsC unexpectedly.

## Acceptance

Actualassembly/Peddle: independentA/B routing/geometry/readonly, partial-write dirtytracking, save-generationbinding, malformed/short/extra/changedsource, swaploadfailure retainingoldmedia, everySave/Discard/Cancel branch, HDonlinecontext/leases, configCRCrefresh and coherentpause/resume. FullFAT/payload/originalpreservation checks use independenthostoracles. OnUltimate: createfileonA andB, Save, reset/relaunch and verifyeach; swapseveralimages with DOSDIR/COPY/applicationprompts; diskfull/failedsave/cancel; Cactive duringallsaves; readonlyoriginal unchanged. UIclock/IRQ behavior and testedkeyboardshortcut need explicitacceptance. No new implementation or hardwaretest was performed for this proposal.
