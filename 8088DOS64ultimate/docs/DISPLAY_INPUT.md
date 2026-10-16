# Text, CGA, and keyboard

## Rendering contract

Keep PC VRAM, text characters/attributes, cursor, mode, active page, and palette exact in the guest model. Rendering is a lossy view of that state; reading guest memory or BIOS pixels must never return the lossy C64 picture. CP437 byte values remain CP437, not PETSCII. Asset provenance/license and font hashes belong in the build manifest.

| PC mode | C64 presentation | Explicit tradeoff |
|---|---|---|
| 00h/01h, 40×25 text | 8×8 glyphs in 320×200 hires bitmap | Per-cell two-color foreground/background fits; map IBM palette to nearest chosen C64 colors |
| 02h/03h, 80×25 text | 4×8 glyphs, two characters per 8×8 bitmap cell | Arbitrary adjacent attributes can require four colors; VIC cell provides two |
| 04h/05h, 320×200×4 CGA | Initial 160×200 multicolor conversion by combining horizontal pairs | Horizontal detail is reduced; preserve CGA palette selection/intensity in conversion |
| 06h, 640×200×2 CGA | 320×200 hires with deterministic two-pixel reduction | Thin alternating pixels/lines can merge; no true 640-pixel VIC output |

40-column bitmap output is the default because PC backgrounds vary by cell. A native text-mode fast path is optional when the screen attributes fit its global-background constraints. Do not assume ordinary C64 text preserves every PC attribute.

For 80 columns, first deliver a stable readable monochrome mode and a deterministic color approximation. Choose each 8×8 pair's palette from both guest cells, favoring readable contrast; redraw both halves when either changes. Reverse video, blink, cursor overlay, and blanks must be handled explicitly. Keep original attributes so subsequent edits restore their intended colors. Offer an optional 40-column inspection view/pan later if useful, but the required default still displays all 80 columns. Temporal flicker/raster tricks and undocumented HDMI-specific video extensions are not dependencies.

The cc65 Soft-80 implementation demonstrates packed half-cell drawing and explicitly handles two adjacent glyphs competing for cell colors. Study its drawing and color restoration, not its PETSCII conio interface as a drop-in PC display. [Drawing source](https://github.com/cc65/cc65/blob/a6530f46914232c085c281c4bf84e87bd136596f/libsrc/c64/soft80_cputc.s), [color source](https://github.com/cc65/cc65/blob/a6530f46914232c085c281c4bf84e87bd136596f/libsrc/c64/soft80_color.s).

## CGA state and dirty work

Implement even/odd graphics scanlines in separate 8 KiB halves: row offset `(y & 1) * 0x2000 + (y >> 1) * 80`; choose bit extraction by mode. Support active text pages (2 KiB stride at 40 columns, 4 KiB at 80), BIOS scroll/window operations, cursor positions per page, CRTC start address, palette registers, mode reset/clear rules, and direct VRAM writes. No composite artifact-color or snow fidelity is promised.

A 40/80 text dirty map tracks 1,000 **host cells** (125 bytes) or a measured finer alternative. Each host cell represents one 40-column character or a pair of 80-column characters. VRAM cache writes mark dirty state. The presenter copies a bounded number of dirty rows/cells per service period and merges dirty host frames with backing state. A full redraw reads the same authoritative memory API as BIOS; do not flush all guest RAM merely to draw a screen.

Use a measured presentation cadence, provisionally 20–30 Hz for changing text, while accepting keyboard events at least every frame. Burst scrolling can coalesce work; the guest must never wait for every character to be painted. Test lost-dirty-bit races, updates during redraw, mode switches, and palette-only changes. Physical PAL/NTSC/display behavior determines the final budget.

## Keyboard

Create a canonical PC key event (make/break scancode, ASCII where applicable, modifier state) from a host keyboard scanner. The BIOS IRQ1 path populates the PC BDA ring buffer and shift flags; INT 16h reads/checks it with correct blocking and ZF behavior. Do not feed a PETSCII byte stream directly to DOS. A blocking BIOS read must yield host service time and allow timer/keyboard delivery.

Proposed mapping for review in M7: letters/digits/punctuation map by intended PC character, RETURN→Enter, DEL→Backspace, RUN/STOP→Esc, CTRL+C→Ctrl-C, cursor keys→PC arrows, HOME→Home, shifted HOME→End, C64 F keys/shifted F keys→F1–F8. Assign F9/F10, Insert/Delete, PgUp/PgDn, Alt and Ctrl-Break through a documented Commodore-key chord or emulator menu. Reserve one distinct chord for host pause/save/eject so it cannot accidentally reset the guest. Physical C64U USB keyboard forwarding may expose more keys; verify rather than assume.

Test key press/release, modifier combinations, typematic, buffer full, extended keys (ASCII zero plus scan), Ctrl-C, DOS editing, EDLIN and DEBUG. Hardware acceptance includes legible text on the user's actual display and useful key mappings, not merely a framebuffer checksum.


# C64 physical keys for the XT and Turbo Pascal

This private successor implements £ as a deferred printable key and the F9/F10 layer switch. Commodore continues to supply PC Alt; CTRL supplies PC Ctrl. Either Shift selects F2/F4/F6/F8 on the four physical F1/F3/F5/F7 keys.

| PC action | Physical C64 keys | BIOS word |
|---|---|---|
| F9 | Hold £, press F5 | 4300h |
| F10 / Turbo Pascal menu | Hold £, press F7 | 4400h |
| Ctrl-F9 / Turbo Pascal run | CTRL + £ + F5 | 6600h |
| Alt-F9 / Turbo Pascal compile | Commodore + £ + F5 | 7000h |
| Shift-F9 / Shift-F10 | Either Shift + £ + F5/F7 | 5C00h / 5D00h |
| Alt-X / Turbo Pascal exit | Commodore + X | 2D00h |
| Alt-F5 / Turbo Pascal output | Commodore + F5 | 6C00h |
| Esc | RUN/STOP | 011Bh |
| Tab | Left-arrow legend key | 0F09h |
| Backspace / Delete | DEL / Shift + DEL | 0E08h / 5300h |
| Right / Left | Cursor right / Shift + cursor right | 4D00h / 4B00h |
| Down / Up | Cursor down / Shift + cursor down | 5000h / 4800h |
| Home / End | HOME / Shift + HOME | 4700h / 4F00h |
| Backslash / pipe | £ / Shift + £, then release | 2B5Ch / 2B7Ch |

Press £ first or together with F5/F7. A function key already delivered before £ is pressed keeps its original identity. Hold £ while releasing and pressing F5/F7 again to send another F9/F10. Releasing a consumed £ sends no printable prefix. If an ordinary key is pressed while £ remains held, backslash or pipe is delivered first, followed by that key; the layer then stays disabled until £ is released. Deferred printable words retain the modifiers observed when £ was pressed, including through a full BIOS queue. No timed chord window or artificial pacing is used. Ctrl+£ and Ctrl+Shift+£ both supply XT Ctrl-backslash (2B1Ch); this corrects the old shifted printable path, which left Ctrl+Shift+£ as pipe.

Function combinations use the original XT BIOS modifier scan tables: Ctrl-F1–F10 are 5E00h–6700h and Alt-F1–F10 are 6800h–7100h. Alt takes priority over Ctrl, then Shift. For ordinary physical function keys, Shift selects the even logical function before Ctrl/Alt translation. For the £ layer, Shift modifies F9/F10. Values and priority follow IBM's original XT BIOS K9/K12/K13 tables and K28/K38 branches in the [IBM PC XT Technical Reference](https://erikarn.github.io/pcxt/PC-XT.pdf). A local source listing is pinned as IBM-XT-BIOS.ASM; this is research/reference material only, no source copied into the emulator.

C64 keys have no isolation diodes. Three corners of a matrix rectangle are ambiguous and are rejected before changing the BIOS queue or modifier flags. For example, ordinary Ctrl + Commodore + physical F3/F4 is ambiguous. £+F5/F7 avoids the modifier-column collisions of the first attempted £+F1/F3 layout: both Shift keys and combined Ctrl/Alt remain distinguishable for the new F9/F10 chords. The first failed test receipt is preserved. Joysticks must be released or disconnected; USB forwarding is unverified.

Each observed key press produces one word; holding does not repeat. Typematic, Insert, PgUp/PgDn, Ctrl-Break, the host pause/save/eject chord and complete modified navigation semantics remain unfinished. Actual linked 6510 code and the independent C64 switch-network model verify this mapping. Physical keyboard and original Turbo Pascal human acceptance remain separate requirements.


ROOT2026-10-16 accepted lifecycle: fullBIOSqueue retainsonecapturedword/modifiers. Ifheldwhenaccepted itcoalesceswiththatpress untilobservedrelease; ifreleasedwhenaccepted itdoesnotpoisonthenextfreshpress. ConsumedPoundcannotrearmprintableorFn untilrelease. Thisboundedpolicydoesnotretainunlimitedsecondaryedgehistory. Independentold/new regressions and96modifier/keycombinationspass; ROOT484/308 and503pre/postpins/copies. Physicalkeyboardacceptanceremainsseparate.
