# Physical Ultimate screenshots

These are actual video-stream captures from the C64 Ultimate running at PAL Manual 64 MHz. The overview joins four original frames: DOS prompt, paged DIR, Turbo Pascal source, and the finished RIPPLE effect. Labels and layout are outside the screen contents. The screens are from different points in the demonstration, not one simultaneous session.

![Four physical DOS64 screens](screenshots/overview.png)

## DOS prompt

![40-column DOS prompt](screenshots/physical-20261017/dos-40.png)

## Directory listing

![80-column DIR pipe MORE](screenshots/physical-20261017/dir-more-80.png)

## Turbo Pascal source

![The 18-line RIPPLE source in Turbo Pascal](screenshots/physical-ripple-20261017/editor.png)

## Finished picture

![RIPPLE after drawing finishes](screenshots/physical-ripple-20261017/picture.png)

RIPPLE uses 960 full-block text characters and eight selected colours. The complete 1,000-cell guest buffer matched the expected result; all six captures in that run matched native bitmap/matrix and active VIC pixels. The source editor showed all 18 intended lines. [Example source and data disk](../examples/README.md).

These are development-fixture demonstrations. They are not evidence that the native 20 MiB installer or all disk-management operations pass. [Current status](STATUS.md).
