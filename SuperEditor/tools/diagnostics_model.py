"""Independent complete diagnostic popup matrix/color oracle for snapshot ABI1."""
from redraw_model import Screen,native_text,screen_code

def diagnostic_popup(base,descriptor):
    assert descriptor[:8]==b'DGS1\x01\x80\x02\x01'
    number=lambda at,width:int.from_bytes(descriptor[at:at+width],'little')
    matrix=bytearray(base.matrix);colors=bytearray(base.colors)
    for row in range(3,23):
        for col in range(1,39):
            code=32;ink=1
            if row in [3,22]:
                code=0x40;ink=14
                if col==1:code=0x70 if row==3 else 0x6D
                if col==38:code=0x6E if row==3 else 0x7D
            elif col in [1,38]:code=0x5D;ink=14
            matrix[row*40+col]=code;colors[row*40+col]=ink
    def label(row,text):
        code=bytes(map(screen_code,native_text(text)))
        assert len(code)<=35,(row,text)
        matrix[row*40+3:row*40+3+len(code)]=code
    for row,text in [(4,f'Diagnostics ABI ${descriptor[4]:02X}'),
                     (6,f'Length ${number(8,3):06X}  Gen ${number(11,2):04X}'),
                     (7,f'Cursor ${number(13,3):06X}  CRC ${number(22,2):04X}'),
                     (8,f'CRC16/CCITT-FALSE  Type ${descriptor[7]:02X}'),
                     (10,f'Pending ${descriptor[16]:02X}  Dirty ${descriptor[17]:02X}'),
                     (11,f'Epoch ${number(20,2):04X}    Banks ${number(44,2):04X}'),
                     (12,f'Allocated ${number(40,2):04X} Free ${number(42,2):04X}'),
                     (14,'Overlay loads / hits / calls'),
                     (15,f' {number(28,2):04X}      {number(30,2):04X}      {number(32,2):04X}'),
                     (17,f'Map ${number(34,2):04X}    Logical ${number(36,2):04X}'),
                     (18,f'Physical ${number(38,2):04X}'),
                     (19,'Owners: 0 free 1 control 2 assets'),
                     (20,'3 meta 4 source; epoch-borrowed'),
                     (21,'F1/F6/F7 or STOP closes')]:label(row,text)
    colors[4*40+3:4*40+20]=bytes([7])*17
    colors[21*40+3:21*40+34]=bytes([15])*31
    for row,col,width in [(4,20,2),(6,11,6),(6,24,4),(7,11,6),(7,24,4),
                          (8,28,2),(10,12,2),(10,23,2),(11,10,4),(11,25,4),
                          (12,14,4),(12,25,4),(15,4,4),(15,14,4),(15,24,4),
                          (17,8,4),(17,25,4),(18,13,4)]:
        colors[row*40+col:row*40+col+width]=bytes([3])*width
    return Screen(bytes(matrix),bytes(colors),base.anchors,base.caret)
