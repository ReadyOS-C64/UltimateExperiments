# Actual C64U DOS framebuffer comparisons

Genuine MS-DOS3.3 ran `MODE CO40`, `VER`, `DIR /W`, then the same commands in80columns. Each pair shows the emulated PC text/attributes on the left using the pinned8pixel CP437Unscii presentation font, and exact captured C64bitmap/matrix pixels on the right. RGB is illustrative; these are RAM framebuffer reconstructions, not HDMI photographs. All35files,9216freebytes and returnedA> were checked inbothmodes. DOS wide output naturally wraps in40columns.

[40columns](dos33-dir-wide-40.png) · [80columns](dos33-dir-wide-80.png) · Evidence (local development record, not distributed).

Fullfirst4MiB REU and originalmachine/media settings were restored and independently compared. NativeBIOS keys were injected; physicalkeyboardmatrix/readability acceptance remains separate. `DIR | MORE` captures are the next requested workflow.

## DIR | MORE

Actual first MORE pages: [40 columns](dos33-dir-more-40.png) · [80 columns](dos33-dir-more-80.png) · Evidence (local development record, not distributed).

Real SPACE inputs continue both listings to DOS. The running pipe has two temporary files (37 files/7168 free); final cleanup independently preserves all35 originals/9216 free, exact metadata/chains/allocated data and slack/FAT/boot. Only2066 bytes of deleted temporary slots/free-cluster residue differ in the disposable REU copy. Full4MiB restoration and readonly remote source/PRG readback pass.
