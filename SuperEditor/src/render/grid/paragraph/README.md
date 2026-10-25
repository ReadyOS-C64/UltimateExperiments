# Wrapped source-grid prose transaction

These are production assembler micromodules, not dependencies on a probe build.
C14's real complete logical-paragraph scan supplies SP2 authority; the R14
producer stores its source/epoch/width/anchor/CRC record at FE1600..167F.
C33 validates every affected source/cache/font row before any pixel mutation;
R25 updates packets and CRCs after the bounded pixel carry. Unsupported markup,
selection, folds, pan and geometry changes retain the normal renderer.

`producer.s` implements the optional R14 BEGIN3/EVENT4/FINISH5 hooks; normal
source-reader operations0..2 are unchanged. `controller.inc` coordinates the
C33 transaction, `packet.inc` supplies R25's packet update, and `shift-row.s`
implements a strict bounded4/5-pixel VIC-row shift in R14 op7 (owner4 checked before frame access). Pixels are carried in one R14 batch, followed by R25 packet commits; the untouched horizontal prefix is preserved. `long.inc` and `prose2.inc` document
borrowed phase memory and the source-derived record. No resident/BSS/ZP or REU
allocation is added. Owner2 producer and owner4 consumer phases are separate.

The ordinary Make targets build C14/R14 and native R16/R17 first, then
`../caret/build.py` generates exact publisher/font witnesses, links R25, and
uses its linked checksum when building C33. The original native charset stays
complete; only the dynamic status renderer uses its26-code subset.

Current evidence and limitations are in agentsworking/STATUS.md and
`docs/PERFORMANCE.md`. This transaction improves eligible long prose but does
not close general typing performance; rejected paragraph checks have a measured
cost that remains active optimization work. The owner2 live latch at89C3 skips record work for absent/rejected candidates; clean scans and final publication keep the full authenticated source checks.
