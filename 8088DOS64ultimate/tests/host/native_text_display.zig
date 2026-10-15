const std=@import("std");const host=@import("machine.zig");const c=host.c;const F=host.Fixture;
const regs=[_]u16{0xd011,0xd016,0xd018,0xd015,0xd020,0xd021,0xdd00,0xdd02};
fn call(f:*F,name:[]const u8,carry:u8,budget:u64)!void{const r=try f.call(name,budget);try std.testing.expectEqual(carry,r.p&1);try std.testing.expectEqual(f.initial_status&0xce,r.p&0xce);}
fn init(release:bool)!F{var f=try F.init();errdefer f.deinit();c.dos64_enable_reu(f.machine);f.poke(try f.symbol("dos64_native_text_state"),0xb7);try call(&f,"dos64_overlay_init",0,10000);try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_native_text_state")));f.poke(try f.symbol("dos64_overlay_reu_mib"),4);try call(&f,"dos64_overlay_bootstrap",0,300_000);if(release){f.poke(try f.symbol("dos64_cache_limit"),32);try call(&f,"dos64_cache_init",0,50000);try call(&f,"dos64_bios_init",0,40000000);try call(&f,"dos64_cache_flush",0,2000000);try call(&f,"dos64_cold_release",0,10000);}return f;}
fn model(f:*F)void{c.dos64_native_display_enable(f.machine);}
fn seed(f:*F,r:*const [8]u8)void{c.dos64_native_display_seed(f.machine,r);}
fn acquire(f:*F)!void{f.poke(try f.symbol("dos64_overlay_requested"),2);try call(f,"dos64_overlay_acquire",0,10000);}
test "native display I/O model is disabled by default"{var f=try init(true);defer f.deinit();try std.testing.expectError(error.UnsupportedDevice,f.call("dos64_overlay_text_setup",10000));}
test "TEXT phase guard rejects row setup and restore before cold release without entering overlay"{
 var f=try init(false);defer f.deinit();model(&f);const s=[_]u8{0x9b,0xc8,0x14,0xa5,6,14,0x97,0x3f};seed(&f,&s);
 const current=f.peek(try f.symbol("dos64_overlay_current"));var cold:[4096]u8=undefined;for(&cold,0..)|*v,i|v.*=f.peek(@intCast(0x7000+i));
 for([_][]const u8{"dos64_overlay_render_text_row","dos64_overlay_text_setup","dos64_overlay_text_restore"})|name|{
  try call(&f,name,1,10000);try std.testing.expectEqual(@as(u8,8),f.peek(try f.symbol("dos64_overlay_error")));try std.testing.expectEqual(current,f.peek(try f.symbol("dos64_overlay_current")));
  for(0..8)|i|try std.testing.expectEqual(@as(u32,0),c.dos64_native_display_reads(f.machine,@intCast(i))+c.dos64_native_display_writes(f.machine,@intCast(i)));
  for(cold,0..)|v,i|{try std.testing.expectEqual(v,f.peek(@intCast(0x7000+i)));try std.testing.expectEqual(@as(u8,0),c.dos64_was_written(f.machine,@intCast(0x7000+i)));}
  for(0xc900..0xd000)|a|try std.testing.expectEqual(@as(u8,0),c.dos64_was_written(f.machine,@intCast(a)));
 }
 f.poke(try f.symbol("dos64_overlay_busy"),1);try call(&f,"dos64_overlay_text_setup",1,10000);try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_overlay_error")));try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_overlay_busy")));
}
test "loaded TEXT setup restore keeps observable VIC CIA bank and native ABI across64 mappings"{
 var f=try init(true);defer f.deinit();model(&f);for(0x7000..0x8000)|a|f.poke(@intCast(a),0); // All cold code/data are BRK traps.
 for(0..64)|n|{
  const before=[_]u8{0x9b,0xd7,0x14,0xa5,6,14,@intCast(n*3),@intCast(n*4)};seed(&f,&before);try acquire(&f);
  const ddr:u8=0x28|@as(u8,@intCast(n&7));const port:u8=0x30|@as(u8,@intCast(n&7));f.poke(0,ddr);f.poke(1,port);f.initial_status=0xec;
  try call(&f,"dos64_native_text_setup",0,10000);try std.testing.expectEqual(ddr,f.peek(0));try std.testing.expectEqual(port&ddr,f.peek(1)&ddr);
  const after=[_]u8{0x3b,0xc8,8,0,0,0,(before[6]&0xfc)|2,before[7]|3};for(after,0..)|v,i|try std.testing.expectEqual(v,c.dos64_native_display_reg(f.machine,@intCast(i)));
  try call(&f,"dos64_native_text_setup",0,10000);try call(&f,"dos64_native_text_restore",0,10000);
  for(before,0..)|v,i|try std.testing.expectEqual(if(i==0)v&0x7f else if(i==1)v|0xc0 else if(i==2)v|1 else if(i==4 or i==5)v|0xf0 else v,c.dos64_native_display_reg(f.machine,@intCast(i)));
  try call(&f,"dos64_native_text_restore",0,10000);f.poke(0,0x2f);f.poke(1,0x35);try call(&f,"dos64_overlay_release",0,10000);
  for(0xdd04..0xdd10)|a|try std.testing.expectEqual(@as(u8,0),c.dos64_was_written(f.machine,@intCast(a)));
 }
}
test "TEXT wrappers preserve initialized display across FILE INPUT switches without touching elapsed CIA"{
 var f=try init(true);defer f.deinit();model(&f);c.dos64_cia_clock_enable(f.machine);c.dos64_cia_clock_seed(f.machine,0x4567,0x89ab);c.dos64_cia_clock_icr_seed(f.machine,3,2);
 const before=[_]u8{0x1b,0xc8,0x14,0x12,6,14,0x97,0x3f};seed(&f,&before);try call(&f,"dos64_overlay_text_setup",0,10000);
 for([_]u8{1,3,2})|id|{f.poke(try f.symbol("dos64_overlay_requested"),id);try call(&f,"dos64_overlay_acquire",0,10000);try call(&f,"dos64_overlay_release",0,10000);}
 try call(&f,"dos64_overlay_text_restore",0,10000);try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_native_text_state")));try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_overlay_busy")));
 for(4..16)|r|{try std.testing.expectEqual(@as(u32,0),c.dos64_cia_clock_reads(f.machine,@intCast(r)));try std.testing.expectEqual(@as(u32,0),c.dos64_cia_clock_writes(f.machine,@intCast(r)));}
 try std.testing.expectEqual(@as(u16,0x4567),c.dos64_cia_clock_count(f.machine,0));try std.testing.expectEqual(@as(u16,0x89ab),c.dos64_cia_clock_count(f.machine,1));try std.testing.expectEqual(@as(u8,3),c.dos64_cia_clock_mask(f.machine));try std.testing.expectEqual(@as(u8,2),c.dos64_cia_clock_pending(f.machine));
}
fn rw(f:*F,a:u32,v:u16)void{c.dos64_reu_poke(f.machine,a,@truncate(v));c.dos64_reu_poke(f.machine,a+1,@truncate(v>>8));}
fn nibble(p:[]const u8,ci:usize,y:usize)u8{return if(y&1==0)p[ci*4+y/2]>>4 else p[ci*4+y/2]&15;}
test "packaged licensed fonts produce complete bitmap oracle in every text mode"{
 const alloc=std.testing.allocator;const font=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,"assets/native-text/cp437-unscii8.bin",alloc,.limited(2049));defer alloc.free(font);const narrow=try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io,"assets/native-text/cp437-narrow4x8.bin",alloc,.limited(1025));defer alloc.free(narrow);
 var f=try init(true);defer f.deinit();for(font,0..)|v,i|try std.testing.expectEqual(v,f.peek(@intCast(0x4800+i)));for(narrow,0..)|v,i|try std.testing.expectEqual(v,f.peek(@intCast(0x4400+i)));
 for(0..4)|mode|{const cols:u16=if(mode<2)40 else 80;c.dos64_reu_poke(f.machine,0x449,@intCast(mode));rw(&f,0x44a,cols);rw(&f,0x44c,if(cols==40)2048 else 4096);rw(&f,0x44e,0);c.dos64_reu_poke(f.machine,0x462,0);
  for(0..@as(usize,cols)*25)|i|{c.dos64_reu_poke(f.machine,0xb8000+@as(u32,@intCast(i*2)),@truncate(i));c.dos64_reu_poke(f.machine,0xb8001+@as(u32,@intCast(i*2)),7);}try call(&f,"dos64_cache_init",0,50000);
  const req=try f.symbol("dos64_render_text_request");for(0..25)|row|{f.poke(req,@intCast(row));f.poke(req+1,1);try call(&f,"dos64_overlay_render_text_row",0,2000000);for(0..40)|cell|{try std.testing.expectEqual(@as(u8,0xf0),f.peek(@intCast(0x4000+row*40+cell)));for(0..8)|y|{const ci=(row*cols+cell*(if(cols==40)@as(usize,1) else 2))&255;const expected=if(cols==40)font[ci*8+y] else nibble(narrow,ci,y)*16+nibble(narrow,(ci+1)&255,y);try std.testing.expectEqual(expected,f.peek(@intCast(0x6000+row*320+cell*8+y)));}}}
 }
}
