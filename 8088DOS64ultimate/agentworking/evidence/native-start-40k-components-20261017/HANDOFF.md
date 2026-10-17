# 40KiB modal asset capacity and cold lifetime

Private successor of actual START journal gate b5f36c82. Native change is only modalcount upperbound8000→A000; packer produces40KiB. The additional16KiB maps3F0000..3F3FFF, after first24KiB3DA000..3DFFFF, keeping3F4000..3F7FFF reserved and all368640 bytes of the third floppy intact. Both additional8KiB slots contain deterministic data in these tests, not executing controller/BIND assets.

Fresh coupled build START09e12ff0/INO9f9e164f with unchanged rawRCVa0ba9fb0. Actual5 tests pass6.486s: full40/80 nojournal startup and byte-exact asset handoff, RCVcache retired before40KiB staging overwrites3E8000, wholethirdfloppy/remaining16KiB guards, actualfirstBINDslotSTORE failure, final3F3FFF targetbyteCRC corruption. Two fresh defaultprofiles preserve public79bb/eebb.182 source+products are before/after exact during actualtests, with previous source-built model bytes explicitly reused unchanged.

FIRST_FAILURES preserves overlay-breakpoint ambiguity: a numeric PC is not phase identity. Tests now require actualresidentphase12 and exact normalINO before treating a PC as modal_copy. Previous apparent firstSTORE success duringRCV is explicitly rejected. No native timeout changed and no unchanged36s fullpending suite repeated.

This is loader allocation/lifetime evidence only. Finalcombined native header, realworker bytes/roles, full controller dispatch, livebinding/CLEAN/Swap/Finish and explicit recovery actions still need integration. No publicpromotion or physicalproductclaim.
