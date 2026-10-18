# Physical Ultimate screenshots — 2026-10-17

These PNGs are unaltered captures of the physical Ultimate VIC stream, taken through the .NET automation harness at PAL/Manual64. MANIFEST.json records filenames and exact hashes without personal paths. The DOS/BASIC/Turbo frames have independent guest/native memory, font, cursor and full active-pixel checks; detailed development run records are not distributed.

The Turbo test uses an explicitly host-prepared runtime CFG/START and previous native-generated A/B. It proves real DOS3.30 and original Turbo7.01 editor/backspace/save/compile-to-disk/run, actual DOS execution of the saved EXE, and whole-drive persistence. Source66B, EXE2208B and output17B exactly equal independently produced Peddle files. No vendor disk images or application binaries are included here.

The native20MiB installer still has a WRITE_NEW/UCI03 failure; its error screenshot is included as failed-test evidence, not installation success. Native UI Finish, physical human keyboard/readability and full V1 acceptance remain separate. The raw runtime drive was closed through the source-bound development cleanup helper before restart.

Representative images: `restart-source-40.png`, `dir-more-80.png`, `gwbasic-output.png`, `turbo-source-80.png`, `turbo-compile-success.png`, `turbo-program-output.png`, and `dos-compiled-exe-output.png`. Cold restart also passes source/EXE checks in40columns, saved-source reopen in80-column Turbo and exit back to DOS; see `restart-turbo-source-80.png` and `final-dos-prompt.png`. All46 runtime frames pass the independent display checks.
