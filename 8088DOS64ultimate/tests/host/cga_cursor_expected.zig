// Independent snapshot expectation for existing opt-in native workflow oracles.
// Captured field cache, not host time or port read count, controls the cursor.
const std=@import("std");const F=@import("machine.zig").Fixture;
pub const Cursor=struct{
 base:usize,address:usize,start:u8,end:u8,visible:bool,
 pub fn capture(f:*F,bda:*const [256]u8)!Cursor{
  try std.testing.expectEqual(@as(u8,0xa5),f.peek(try f.symbol("dos64_cursor_phase_valid")));
  const cols=std.mem.readInt(u16,bda[0x4a..0x4c],.little);try std.testing.expect(cols==40 or cols==80);
  const base=std.mem.readInt(u16,bda[0x4e..0x50],.little)/2;const r=try f.symbol("dos64_cga_registers");
  try std.testing.expectEqual(base,(@as(u16,f.peek(r+12))<<8)|f.peek(r+13));
  const shape=f.peek(r+10);const start=shape&31;const end=f.peek(r+11)&31;const mode=(shape>>5)&3;
  try std.testing.expect(mode==1 or start<=end);const phase=f.peek(try f.symbol("dos64_cursor_field_phase"));
  return .{.base=base,.address=(@as(u16,f.peek(r+14))<<8)|f.peek(r+15),.start=start,.end=end,.visible=mode!=1 and phase&8==0 and (mode!=2 or phase&16==0) and (mode!=3 or phase&32==0)};
 }
 pub fn mask(self:Cursor,cols:usize,row:usize,cell:usize,y:usize)u8{
  if(!self.visible or y<self.start or y>self.end)return 0;
  const first=self.base+row*cols+cell*(cols/40);
  if(self.address==first)return if(cols==40)255 else 240;
  return if(cols==80 and self.address==first+1)15 else 0;
 }
};
