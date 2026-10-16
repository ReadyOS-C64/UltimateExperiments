"""Pure independent oracle for a captured canonical CGA text frame.

No device imports and no current-time access. Caller must bind the capture to
its exact expected native pair and installed font identities. Graphics keeps
its separate graphics oracle: this function rejects graphics captures.
"""
COLORS = (0, 6, 5, 3, 2, 4, 9, 15, 12, 14, 13, 3, 10, 4, 7, 1)

def render_text_capture(bda, cga, narrow, wide, *, registers, control,
                        control_valid, phase_valid, field_phase, blink_visible,
                        native_sha256, expected_native_sha256):
    if len(native_sha256) != 64 or native_sha256 != expected_native_sha256:
        raise ValueError('Capture native identity does not match this oracle cohort')
    if tuple(map(len, (bda,cga,narrow,wide,registers))) != (256,16384,1024,2048,18):
        raise ValueError('Exact BDA/CGA/font/hardware-latch capture sizes required')
    if control_valid != 0xA5 or phase_valid != 0xA5:
        raise ValueError('Current owned control and same-frame cursor sample required')
    if blink_visible not in (0,1) or not 0 <= field_phase <= 255 or not 0 <= control <= 63:
        raise ValueError('Invalid captured display phase/control')
    mode=bda[0x49]; cols=int.from_bytes(bda[0x4a:0x4c],'little')
    if (mode,cols) not in ((0,40),(1,40),(2,80),(3,80)):
        raise ValueError('Canonical text capture required; graphics has no cursor overlay')
    size=2048 if cols==40 else 4096; page=bda[0x62]
    offset=int.from_bytes(bda[0x4e:0x50],'little')
    if page >= 16384//size or int.from_bytes(bda[0x4c:0x4e],'little') != size or offset != page*size:
        raise ValueError('Inconsistent captured BDA active page')
    start_address=(registers[12]<<8)|registers[13]
    if start_address != offset//2:
        raise ValueError('Hardware start/BDA source mismatch is unsupported')
    start=registers[10]&31; end=registers[11]&31
    if end < start and (registers[10]>>5)&3 != 1:
        raise ValueError('Inverted cursor scanline shape is unsupported')
    cursor_address=(registers[14]<<8)|registers[15]
    display_mode=(registers[10]>>5)&3
    visible=(display_mode!=1 and not field_phase&8 and
             (display_mode!=2 or not field_phase&16) and
             (display_mode!=3 or not field_phase&32))
    bitmap=bytearray(8000); matrix=bytearray(1000)
    intensity=not control&32
    for row in range(25):
        for cell in range(40):
            first=row*cols+cell*(cols//40)
            ch=cga[offset+first*2]; attr=cga[offset+first*2+1]
            matrix[row*40+cell]=((COLORS[attr&15]<<4)|COLORS[(attr>>4)&(15 if intensity else 7)]) if control&8 else 0
            for scan in range(8):
                bits=0
                for half in range(cols//40):
                    word=first+half; char=cga[offset+word*2]; attribute=cga[offset+word*2+1]
                    dots=wide[char*8+scan] if cols==40 else (narrow[char*4+scan//2]>>(4 if scan%2==0 else 0))&15
                    if not intensity and attribute&128 and not blink_visible: dots=0
                    if visible and start<=scan<=end and start_address+word==cursor_address:
                        dots |= 255 if cols==40 else 15
                    bits |= dots if cols==40 else dots<<(4 if half==0 else 0)
                bitmap[row*320+cell*8+scan]=bits
    return {'bitmap':bytes(bitmap),'matrix':bytes(matrix),
            'metadata':{'mode':mode,'columns':cols,'active_page':page,
                        'start_address':start_address,'cursor_address':cursor_address,
                        'field_phase':field_phase,'blink_visible':blink_visible,
                        'native_sha256':native_sha256,'cursor_gate':visible,
                        'profile':'canonical-CGA-captured-cursor-v1'}}
