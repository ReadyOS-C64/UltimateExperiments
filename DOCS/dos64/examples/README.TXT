DOS64 EXAMPLES

This is a data disk. Boot DOS from A first.

RIPPLE.EXE - run directly from DOS. Eight-colour 40-column text picture.
             Press a key to restore 80 columns and return to DOS.
RIPPLE.PAS - source for Turbo Pascal 7.01, with 8088 code generation.
HANGMAN.BAS - GW-BASIC ASCII hangman, automatically plays itself.

Commands after inserting this disk as B:
  B:\RIPPLE.EXE
  GWBASIC B:\HANGMAN.BAS /F:1
  COPY B:\RIPPLE.EXE C:\RIPPLE.EXE
  COPY B:\RIPPLE.PAS C:\RIPPLE.PAS
  COPY B:\HANGMAN.BAS C:\HANGMAN.BAS

Run GWBASIC from the folder containing GWBASIC.EXE, or put it on PATH.
In BASIC, use LIST to read the game; SYSTEM returns to DOS.

No DOS, GW-BASIC, Turbo Pascal or third-party programs are on this disk.
Obtain DOS/GW-BASIC separately:
https://archive.org/details/
ms-dos-version-3.3-with-gw-basic-3.2-microsoft-1988

RIPPLE.EXE was built from the included source using original TPC 7.01.
The source was independently compiled/run in Turbo on the physical
Ultimate. This host-built EXE has not had a separate hardware identity test.
