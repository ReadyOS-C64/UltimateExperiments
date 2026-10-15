# User requirement coverage

| ID | Requirement | Design / milestone | Evidence required |
|---|---|---|---|
| R01 | Planning now; review before implementation with 6.1 Sol | README, PLAN, NEXT_SLICE | User authorized implementation2026-10-14; local verified commits, no pushes |
| R02 | Project isolated under 8088DOS64ultimate | AGENTS, local ignore rules | All new files/records in this directory |
| R03 | 8086 emulator, real DOS 3.3 supplied images | ARCHITECTURE M3–M5 | Actual image boot and DOS-owned INT 21h/process/file logic |
| R04 | 64 MHz C64U, 640 KiB guest RAM via REU | MEMORY, PERFORMANCE M1–M4 | Real hardware timing, INT 12h and memory/paging tests |
| R05 | Target 6502 assembly (user clarification) | AGENTS, architecture, D03 | Assembler output is the runtime under test |
| R06 | ZeroPage-style Peddle and Zig assertions | TESTING M0 onward | Zig runs linked assembly and asserts guest/host/device outcomes |
| R07 | Unit, integration, end-user tests | TESTING all lanes | Machine assertions plus DOS scripts and physical UI evidence |
| R08 | Mock REU and Ultimate DOS load/save | TESTING M2/M6 | Register-level transfer/protocol tests and injected failures |
| R09 | Whole floppy image in REU, load/save as file | STORAGE M5/M6 | Complete image hash/length and restart persistence |
| R10 | HD parts cached in REU; around 2 MiB then up to 20 MiB | STORAGE M8/M9 | Forced eviction, guest FDISK/FORMAT/SYS, offsets beyond 16 MiB |
| R11 | Real C64U testing, slower cadence | TESTING/PERFORMANCE M1/M6+ | Firmware/configured physical runs and saved-image verification |
| R12 | Optional real IEC/D81 with VICE traps/warp | STORAGE/TESTING M6 | Binary IMG in SEQ, trap lane, smaller true-drive lane, extraction |
| R13 | Keyboard and text/graphics; no extra peripheral scope | DISPLAY_INPUT, architecture | Keyboard/editor use; absence behavior for unsupported devices |
| R14 | Both 40 and 80 characters with custom rendering | DISPLAY_INPUT M7 | Mode switches, CP437, readable font, documented color compromise |
| R15 | Only manageable CGA graphics | DISPLAY_INPUT M10 | Modes 4/5/6 guest pixel tests and C64 conversion evidence |
| R16 | Strategy aiming near original 8088 performance | PERFORMANCE M1/M11 | Disclosed baseline, per-workload ratios, cache/CPU/render breakdown |
| R17 | DOS included commands before third-party apps | TESTING M5–M10 | Explicit required/conditional/excluded utility manifest |
| R18 | Long-horizon context, decisions, lessons | agentworking records | Updated STATUS/NEXT_SLICE/DECISIONS/LESSONS/TEST_LOG each slice |
| R19 | Deep research, consider DOSBox comparisons | RESEARCH, TESTING M0 | Source register; installed DOSBox-X recorded; actual DOSBox-X reference boot recorded |

Planning coverage means each request has an implementation/test destination. It does not mean those implementation tests have passed.


2026-10-15 accepted scope: R03/R11 now have realC64U Manual64MHz native UCIboot/COMMAND.COM/VER/DIR proof, with exact35entries/9216free/returnedprompt and complete4MiB/configuration recovery. R09 native wholefloppy loading is physically accepted; save/reopen remains pending. R14 physical80column bitmap/matrix bytes match independent oracle, but human readability/keyboard/40column remain pending. R10/12/15/16 persistence/HD/IEC/nativephysicalCGA/XTperformance are not complete. [Physical evidence](../agentworking/evidence/c64u-native-dos-20261015.json).
