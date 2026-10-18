# Example applications

[Download EXAMPLES.IMG](EXAMPLES.IMG), a reproducible 360 KiB FAT12 **data** disk containing only these four files:

| File | Use |
|---|---|
| RIPPLE.EXE | Run directly from DOS; press a key to return to 80-column DOS |
| RIPPLE.PAS | The 18-line 8088-compatible Turbo Pascal source |
| HANGMAN.BAS | ASCII GW-BASIC hangman with autoplay |
| README.TXT | Commands and dependencies |

Boot your own DOS disk first, then insert this image as B. Run `B:\RIPPLE.EXE`. From a folder containing GWBASIC.EXE, run `GWBASIC B:\HANGMAN.BAS /F:1`; `LIST` shows the program and `SYSTEM` returns to DOS. To keep a copy, use DOS COPY from B to C. Floppy writes require explicit native Save. [Installation and disk controls](../docs/INSTALL.md).

DOS, GW-BASIC and Turbo Pascal binaries are not on this image. Get the three original DOS/GW-BASIC images from [Internet Archive](https://archive.org/details/ms-dos-version-3.3-with-gw-basic-3.2-microsoft-1988). Obtain Turbo Pascal separately if you want to recompile the source. The supplied RIPPLE.EXE was built from this source with original TPC 7.01 in a host reference environment; that exact EXE has not had a separate physical identity test. The same source was independently compiled and run in Turbo on the physical Ultimate, as shown in the screenshots.

RIPPLE selects BIOS mode 1, draws 960 full-block characters in eight selected RGBI colours using integer arithmetic and standard System/Dos units, then waits in BIOS for a key before restoring mode 3. `{$G-}` keeps code generation compatible with the 8088. Each 40-column character has its own C64 colour pair; 80-column neighbours share one. This is colour text art, not 16-colour CGA graphics.

[Source and finished-picture screenshots](../docs/SCREENSHOTS.md). `build_support/example_disk.py` recreates the image without vendor media, and `tests/tooling/test_example_disk.py` checks its exact allowlist, payloads, reproducibility and FAT corruption rejection. `ripple_picture_check.py` compares every captured guest cell; `physical_gallery.py` separately checks the native bitmap/matrix and VIC stream pixels.

## RIPPLE source

```pascal
program Ripple;
{$G-}
uses Dos;
const p:array[0..7] of byte=(1,5,4,12,14,15,11,9);
var x,y,d,e:integer; r:Registers;
begin
  r.ax:=1; Intr($10,r);
  for y:=1 to 24 do
    for x:=0 to 39 do begin
      d:=((x-11)*(x-11)+(y-12)*(y-12)) div 6;
      e:=((x-28)*(x-28)+(y-12)*(y-12)) div 6;
      Mem[$B800:2*(y*40+x)]:=219;
      Mem[$B800:2*(y*40+x)+1]:=p[(d xor e) mod 8];
    end;
  Write('RIPPLE - press a key');
  r.ax:=0; Intr($16,r);
  r.ax:=3; Intr($10,r)
end.
```
