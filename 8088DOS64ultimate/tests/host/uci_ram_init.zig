const std=@import("std");
const h=@import("machine.zig");const c=h.c;
test "native RAM initializer is register flag state equivalent to original before and after cold release" {
 const a=std.testing.allocator;const original=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,"build/original-init-reference.bin",a,.limited(2048));defer a.free(original);
 var f=try h.Fixture.init();defer f.deinit();const first=try f.symbol("dos64_uci_state_start");const end=try f.symbol("dos64_uci_state_end");const sentinel=try f.symbol("fixture_return");
 c.dos64_load(f.machine,0x8000,original.ptr,original.len);
 for([_]u8{0,0xa5,0xff})|ready|for(0..256)|flags|for([_]u8{0x30,0x31,0x32,0x33,0x34,0x35,0x36,0x37})|bank| {
  f.poke(try f.symbol("hdb_extension_ready"),ready);f.poke(try f.symbol("dos64_cold_open"),if(ready==0xa5)0 else 0xa5);f.poke(try f.symbol("dos64_overlay_ready"),if(ready==0xa5)0xa5 else 0);
  for(0xf000..0xfe00)|i|f.poke(@intCast(i),0);
  var reference:[64]u8=undefined;var expected:c.Dos64Regs=undefined;
  for(0..2)|lane|{
   var at=first;while(at<end):(at+=1)f.poke(at,0xa7);f.poke(first-1,0x6b);f.poke(end,0xd7);f.poke(0,0x2f);f.poke(1,bank);
   const ret=sentinel-%1;f.poke(0x1ff,@truncate(ret>>8));f.poke(0x1fe,@truncate(ret));c.dos64_clear_writes(f.machine);
   c.dos64_set_regs(f.machine,.{.pc=if(lane==0)0x8000 else try f.symbol("dos64_uci_init"),.sp=0xfd,.a=0x79,.x=0xa6,.y=0xd3,.p=@intCast(flags),.cycles=0,.instructions=0});
   const r=c.dos64_run(f.machine,sentinel,10000);try std.testing.expectEqual(@as(c_uint,c.DOS64_RUN_RETURNED),r.status);try std.testing.expectEqual(@as(u8,0xff),r.regs.sp);
   try std.testing.expectEqual(@as(u8,0x79),r.regs.a);try std.testing.expectEqual(@as(u8,0xa6),r.regs.x);try std.testing.expectEqual(@as(u8,0xd3),r.regs.y);try std.testing.expectEqual(@as(u8,0x2f),f.peek(0));try std.testing.expectEqual(bank&0x2f,f.peek(1)&0x2f);
   try std.testing.expectEqual(@as(u8,0x6b),f.peek(first-1));try std.testing.expectEqual(@as(u8,0xd7),f.peek(end));
   if(lane==0){expected=r.regs;for(0..end-first)|i|reference[i]=f.peek(first+@as(u16,@intCast(i)));}else{
    try std.testing.expectEqual(expected.p,r.regs.p);for(0..end-first)|i|try std.testing.expectEqual(reference[i],f.peek(first+@as(u16,@intCast(i))));
    try std.testing.expectEqual(@as(c_int,0),c.dos64_was_written(f.machine,0));try std.testing.expectEqual(@as(c_int,0),c.dos64_was_written(f.machine,1));
    for(0..65536)|i|{if(c.dos64_was_written(f.machine,@intCast(i))==0)continue;try std.testing.expect((i>=0x100 and i<0x200) or (i>=first and i<end));}
   }
  }
 };
 std.debug.print("native_RAM_init_equivalence_cases=6144 original_bytes={d}\n",.{original.len});
}
