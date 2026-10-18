# Genuine GW-BASIC ASCII hangman

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


HANGMAN.BAS runs the supplied GW-BASIC3.20 through genuine DOS3.30's normal EXE loader. It plays ten guesses: three misses(ZXQ), then ULTIMAE, revealing both Ts and winning ULTIMATE. ASCII gallows, word, misses and history fit40 columns. TIMER pacing is bounded to200 iterations; rendering/interpreter speed also affects the visible pace. No host BASIC, INT21 replacement or native EXE loader is involved.

The disposable disk1 copy removes only FDISK.COM,4201.CPI,GRAPHICS.COM. It preserves the exact boot sector and all34 retained payloads, including IO.SYS,MSDOS.SYS,COMMAND.COM,MODE.COM,MORE.COM and CONFIG.SYS. It adds byte-exact80,608-byte GWBASIC.EXE from supplied disk3 and1,329-byte ASCII/CRLF BAS. Independent strict FAT12 inspection checks both mirrors, allocation chains, complete payload set and every retained file. Free space is7,168 bytes. All original images remain unchanged.

The genuine command sequence is MODE CO40; GWBASIC HANGMAN /F:1; autoplay/WIN/Ok; LIST10-130; LIST140-240; LIST300-350; LIST360-420; SYSTEM; DIR (type a space after LIST). Four LIST pages cover every source line. The observer waits for actual prompts and refills the15-key BIOS queue using its real head/tail. GW-BASIC prints Ok followed byCP437FFh, a blank glyph; prompt recognition normalizes that glyph while rawCGA bytes remain unmodified. DIR presence is accumulated across scrolling observations.

## Compatibility slice

Actual execution exposed IN61h, OUT40h and IN201h. Port61h byte input/output now uses the XT8255 mode0 output latch, initially48h. It is distinct from ATport61 timer/status inputs. Fixed BIOS PITcounter0 mode3/binary/divisor65536/RWlohi accepts zero byte writes40h and tracks the LSB/MSB sequence; rewriting the same divisor retains timing phase, fraction, counters and PIC state. Nonzero data, reads, words, control43h and other channels remain unsupported. The configured absent game adapter201h has byte inputFFh; writes, words, neighboring/high-alias addresses remain rejected. No generic unknown-port fallback exists.

Speaker waveform, parity faults, keyboard wire/reset effects and programmable PIT divisors/modes remain outside this slice. The output latch provides a basis for future device wiring. FFh is the configured absent-device bus profile, not a measurement of every XT clone's floating bus.

Primary IBM April1984 Technical Reference map1-26 labels all portB bits as outputs; Intel8255A-5 describes portB's latch. Original XT BIOS source sets counter0 with36h/00h/00h and finishes keyboard enable with48h. Intel8253 mode3 continues its waveform when the same count is rewritten. Exact primary-reference hashes and inspected pages are retained in the private package. Implementation is independent.

## Evidence and limits

Clean native proof passes all ten observed guesses, WIN, four LIST pages, SYSTEM and DOS DIR/A>. Coherent BDA,16KiB CGA and64KiB nativeRAM captures are retained at WIN, each LIST page and final DIR. Full40-column bitmap/matrix oracles pass WIN and DIR. All368,640 image bytes remain unchanged in REU.

Exact private target: runtimeed7462bad54947a32092cf7cd3f6ac4e6f962cea98757555e104c0ebffdcedd8, unitd530c37556d148e0972766b5f9a7bbdc7bba39d83d06792ce22661163a8e03ea;42,497 bytes0801–ADFF. CODE grows95 bytes, DEVICESTATE2; MAINfree20/19bytes. HDBIOS stays2,361code+1,223zero-tail. Default actual-assembly suite passes425 tests including597 quick8088 cases; focused port10/10 and FAT fixture4/4 pass.

Native workflow:3,949,737 guest instructions;11,575,240,395 modeled6510 CPU cycles. Those exclude DMA stalls and do not establish physical elapsed time, an XT ratio, physical BASIC compatibility or video acceptance. Independent review, hardware staging/media verification/recording and complete first4MiB restoration remain separate gates. Physical chapters should start at first visible game frame, after WIN/Ok before LIST, and after SYSTEM/A> before DIR. Hold WIN and each LIST page about2s, final DIR3s.
