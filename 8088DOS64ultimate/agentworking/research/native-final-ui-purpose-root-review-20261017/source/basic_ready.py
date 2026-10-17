"""Exact prior conservative paused BASIC readiness observation, no activation."""
def basic_ready(ram):
 """Conservative actual KERNAL/BASIC screen+cursor+empty-buffer observation."""
 if not isinstance(ram,bytes) or len(ram)!=65536:raise ValueError('Full paused original RAM required')
 row=ram[0xd6];column=ram[0xd3];pointer=int.from_bytes(ram[0xd1:0xd3],'little')
 if ram[0x288]!=4 or ram[0x289]!=10 or not 1<=row<=24 or column!=0 or pointer!=0x400+40*row:return None
 if ram[0xc6]!=0:return None
 previous=bytes(v&0x7f for v in ram[pointer-40:pointer]);current=bytes(v&0x7f for v in ram[pointer:pointer+40])
 if previous[:6]!=bytes([18,5,1,4,25,46]) or previous[6:]!=b' '*34 or current!=b' '*40:return None
 return {'cursor_row':row,'cursor_column':column,'screen_row_pointer':pointer,'keyboard_count':0,'jiffy':int.from_bytes(ram[0xa0:0xa3],'big'),'ready_row_screen_codes':previous.hex(),'current_row_screen_codes':current.hex()}
