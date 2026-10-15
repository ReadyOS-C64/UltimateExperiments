# Genuine DOS continuation audit: shared interrupt rearm

This is the retained audit of an earlier intermediate stop. The subsequent
clock/keyboard/UCI slice accepts genuine COMMAND.COM, VER and DIR; see
[the later evidence](../evidence/dos-command-builtins-20261015.json).

On 2026-10-15 the long DOS continuation stopped at `9DFD:0A53`, opcode
`EE` (`OUT DX,AL`), with `DX=02F2`, `AL=FF`, after 53,861 completed guest
instructions. This is genuine DOS SYSINIT code executing normally. The
port number is intentional; the evidence does not support corrupt control
flow or a fetch error.

The inspected report explicitly accepts IO.SYS entry and **does not accept a
COMMAND.COM prompt**. This audit does not change that milestone.

## Captured evidence

Owned scratch directory: `agentworking/scratch/dos-trace-audit/`.
Copies of the report, coherent 640 KiB RAM and 16 KiB CGA dump preserve this
particular stop independently of later runs. `audit.json` records comparison
spans and source identity. These generated captures remain scratch artifacts.

| Artifact | SHA-256 |
| --- | --- |
| Coherent guest RAM | `de8c9826dc017005a932dafa83ffc88a90925d39d588974efeac2c8a916b3d0a` |
| Coherent CGA RAM | `e2f9259ca1e5d6999fe1ba98826b7f1f2a256d65c1157531b9d61046da5aa15d` |
| Original IO.SYS, 22,398 bytes | `b0bbdb145bd201c025b7921542cc3ee5244b47cdbc06be849f0d9ce8ba46a9c4` |
| Original MSDOS.SYS, 30,128 bytes | `312f79cbc91f8aeb497e70f73be29cf2fb209c73f661350ee51259247037d65f` |
| Original COMMAND.COM, 25,308 bytes | `1619d4e38e14ca649818a7be9c15d181964ff8d59693cb5a7d98ffde9a1811a7` |
| Original CONFIG.SYS, 50 bytes | `25923f876c309f5db74b6ce834ff1a65614cdbe5e868e9fdeae0d2088de33896` |

Original files were extracted read-only using `build_support/dos_image.py`.
Original images and shared source/build files were not edited by this audit.
`ndisasm -b16` and direct byte comparisons were used for instruction analysis.

## Relocation is consistent with the original file

The SYSINIT extent begins at IO.SYS file offset `374Fh`, length `202Fh`.
Its live physical base is `9DFD0h`. Comparing this full extent gives
8,174 matching bytes out of 8,239; differences lie only among mutable
variables and the active stack in `07F4h..0969h`. In particular, the full
`096Ah..202Eh` tail, 5,829 bytes, is unchanged from the original file.
Thus the stopping routine and its surrounding code are exact original bytes.

The original relocation routine at SYSINIT `091Dh..0941h` obtains the top
paragraph from its memory-size field (`A000h`, also consistent with BDA
`0413h=0280h`, 640 KiB). It rounds `202Fh` bytes to `0203h` paragraphs,
subtracts this from `A000h`, and gets **9DFDh**. It copies `2030h` bytes
using `REP MOVSW`, then enters the relocated segment using `RETF` with
IP `0942h`. This derivation uses the original code and captured mutable
field. It is a reconstruction, not a newly recorded dynamic trace of the
initial relocation instruction.

## The final control flow is legitimate

The captured final trace contains an ordinary DOS INT 21h return sequence:

| Completed guest instructions | CS:IP before next instruction | Meaning |
| --- | --- | --- |
| 53,850 | `022F:157B` | DOS indirect near jump to its return stub |
| 53,851 | `022F:156C` | `IRET` |
| 53,852 | `9DFD:1C51` | `TEST DL,80h`, checking device IOCTL result |
| 53,853 | `9DFD:1C54` | `JNZ 1C48h` |
| 53,854 | `9DFD:1C48` | `RET` from the open-device helper |
| 53,855 | `9DFD:0A4A` | `PUSH AX` |
| 53,856–53,858 | `0A4B..0A4D` | save BX, DX and ES |
| 53,859 | `9DFD:0A4E` | `MOV AL,FFh` |
| 53,860 | `9DFD:0A50` | `MOV DX,02F2h` |
| 53,861 | `9DFD:0A53` | `OUT DX,AL`, currently unsupported |

The preceding calls open/duplicate DOS devices CON, AUX and PRN. The
following code writes six consecutive byte ports `02F2h..02F7h`, restores
registers and continues toward opening `\COMMAND.COM`.

The captured screen reads `Unrecognized command in CONFIG.SYS`. The actual
immutable CONFIG.SYS starts with the line `c:` and also refers to
`c:\dos\ansi.sys`. The first line accounts for an expected configuration
parser complaint on this image. It is not evidence of corrupt screen output.
No AUTOEXEC.BAT root entry exists in this image.

## Primary source identifies the port sequence

Microsoft's published MS-DOS v4 source contains the inherited DOS 3.30
shared-interrupt rearm routine in
[SYSINIT1.ASM, lines 1539–1629](https://github.com/microsoft/MS-DOS/blob/2d04cacc5322951f187bb17e017c12920ac8ebe2/v4.0/src/BIOS/SYSINIT1.ASM#L1539).
The comments identify a global rearm broadcast for shared interrupt devices,
with one port for each IRQ level 2 through 7, after driver loading. They
explicitly describe the write value as arbitrary. The code is marked as a
3.30 change. This v4 source establishes the documented purpose; it is not
claimed to be the exact source build of the supplied 3.3 binary.

Pinned repository tree: `2d04cacc5322951f187bb17e017c12920ac8ebe2`.
Downloaded SYSINIT1.ASM SHA-256:
`e2e9033d69611aeb6822d79a1cd798ab089fd2121e4c9c8382fe4aab2b5c4c86`.

The actual supplied binary uses the same six-port sequence unconditionally
at this point. Its subsequent machine-type check skips the secondary
`06F2h` family for our XT model byte `FEh`. The details of that conditional
flow differ from the published v4 source, so the binary remains authoritative
for this run.

## Narrow next implementation and verification

Treat byte writes to `02F2h..02F7h` as recognized shared-interrupt rearm
broadcasts. With no shared-interrupt adapter attached, they have no device
state to alter. Preserve guest registers and FLAGS, keep unsupported reads
and unrelated ports explicit, and avoid claiming a complete new controller
or asynchronous IRQ delivery. The primary source does not justify a blanket
unknown-port success policy or a required `FFh` value restriction.

Tests should exercise all six ports, arbitrary byte values, FLAGS/register
preservation and unchanged PIC state; reject adjacent ports and unsupported
word forms according to the emulator's stated port policy. Then continue
unchanged DOS to the next bounded first failure. A COMMAND.COM prompt still
requires separate evidence.

An independent agent's native dual-fixture differential subsequently matched
fast fetch against the retained original slow fetch for all 55,583 scheduling
calls, every 14-word guest state and the full flushed 640 KiB RAM plus 16 KiB
CGA. It stopped at this same instruction. Its separate evidence is
`agentworking/scratch/dos-fetch-compare/result.json`. This rules out a
fetch-optimization regression relative to the original slow path; it does
not independently prove every other CPU instruction correct.
