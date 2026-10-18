// Explicit guest type1 fixture for preexisting tests which retain TF=1.
// It executes the real IVT entry and a real IRET, never clears native state.
const std=@import("std");const h=@import("machine.zig");const F=h.Fixture;const c=h.c;
pub fn enabled(f:*F)bool{return f.symbols.contains("dos64_trap_state");}
pub fn install(f:*F)!void{
 if(!enabled(f))return;
 // Seed through the actual coherent write API: BIOS fixtures may already
 // have page0 cached, so changing backing REU alone would be an invalid setup.
 const addresses=[_]u32{4,5,6,7,0x50200};const values=[_]u8{0,2,0,0x50,0xcf};
 const pointer=try f.symbol("dos64_address");
 for(addresses,values)|address,value|{
  f.poke(pointer,@truncate(address));f.poke(pointer+1,@truncate(address>>8));f.poke(pointer+2,@truncate(address>>16));f.poke(try f.symbol("dos64_mem_value"),value);
  const r=try f.call("dos64_mem_write",100000);try std.testing.expectEqual(@as(u8,0),r.p&1);
 }
 // These legacy fixtures seed later code/IVT entries in backing REU. Finish
 // the coherent setup, then discard clean cached pages before those writes.
 const mode=f.peek(try f.symbol("dos64_memory_mode"));
 const flushed=try f.call("dos64_cache_flush",100000);try std.testing.expectEqual(@as(u8,0),flushed.p&1);
 _=try f.call("dos64_cache_init",100000);f.poke(try f.symbol("dos64_memory_mode"),mode);
}
pub fn enterAndReturn(f:*F)!void{
 if(!enabled(f))return;
 try std.testing.expectEqual(@as(u8,2),f.peek(try f.symbol("dos64_trap_state")));
 const g=try f.symbol("dos64_guest");const ip=f.word(g+24);const cs=f.word(g+18);const sp=f.word(g+8);const flags=f.word(g+26);const count=f.word(try f.symbol("dos64_cpu_instructions"));
 const t=try f.call("dos64_cpu_step",200000);try std.testing.expectEqual(@as(u8,0),t.p&1);try std.testing.expectEqual(sp-%6,f.word(g+8));try std.testing.expectEqual(@as(u16,0),f.word(g+26)&0x300);try std.testing.expectEqual(count,f.word(try f.symbol("dos64_cpu_instructions")));
 const r=try f.call("dos64_cpu_step",200000);try std.testing.expectEqual(@as(u8,0),r.p&1);try std.testing.expectEqual(ip,f.word(g+24));try std.testing.expectEqual(cs,f.word(g+18));try std.testing.expectEqual(sp,f.word(g+8));try std.testing.expectEqual((flags&0x0fd5)|0xf002,f.word(g+26));try std.testing.expectEqual(count+%1,f.word(try f.symbol("dos64_cpu_instructions")));
}
