const std=@import("std");
const h=@import("machine.zig");
const F=h.Fixture;const c=h.c;
extern fn diagnostic_publish_after_upload(*anyopaque,usize) void;
fn put(f:*F,n:[]const u8,v:u8) !void {f.poke(try f.symbol(n),v);}
fn get(f:*F,n:[]const u8) !u8{return f.peek(try f.symbol(n));}
fn word(f:*F,n:[]const u8,v:u16) !void{const a=try f.symbol(n);f.poke(a,@truncate(v));f.poke(a+1,@truncate(v>>8));}
fn call(f:*F,n:[]const u8) !void{_=try f.call(n,100_000);}
fn setup(shadow:bool) !F {
 var f=try F.init();errdefer f.deinit();
 if(shadow){try put(&f,"dos64_cold_open",0xa5);_=try f.call("hdb_load_extension",250_000);try std.testing.expectEqual(@as(u8,0xa5),try get(&f,"hdb_extension_ready"));try call(&f,"dos64_uci_trace_reset");}
 c.dos64_uci_model_enable(f.machine,0xdf1c,0,0xc9);try call(&f,"dos64_uci_init");
 const cmd=try f.symbol("dos64_uci_command");for(0..61) |i| f.poke(cmd+@as(u16,@intCast(i)),@intCast(i+1));
 try word(&f,"dos64_uci_command_len",61);c.dos64_uci_model_block(f.machine,null,0,"00,OK",5);return f;
}
fn snapshot(f:*F) ![177]u8 {var b:[177]u8=undefined;const a=try f.symbol("dos64_uci_trace_start");for(&b,0..) |*x,i| x.*=f.peek(a+@as(u16,@intCast(i)));return b;}
test "native upload checks stale response before next chunk without PUSH" {
 var f=try setup(true);defer f.deinit();try call(&f,"dos64_uci_start");try call(&f,"dos64_uci_poll");
 c.dos64_uci_model_stale(f.machine,0x20);try call(&f,"dos64_uci_poll");
 try std.testing.expectEqual(@as(u8,6),try get(&f,"dos64_uci_error"));try std.testing.expectEqual(@as(u64,0),c.dos64_uci_model_count(f.machine,0));
 const b=try snapshot(&f);try std.testing.expectEqualSlices(u8,"UCF2",b[0..4]);try std.testing.expectEqual(@as(u8,0xa5),b[5]);
 // snapshot state-relative14=UPLOAD,15=STALE,17=first raw60.
 try std.testing.expectEqual(@as(u8,2),b[6+14]);try std.testing.expectEqual(@as(u8,6),b[6+15]);try std.testing.expectEqual(@as(u8,0x60),b[6+17]);
}
test "native final-byte late response is rejected by pre-PUSH quiet guard" {
 var f=try setup(true);defer f.deinit();diagnostic_publish_after_upload(f.machine,61);
 try call(&f,"dos64_uci_start");for(0..10) |_| {if(try get(&f,"dos64_uci_state")==8) break;try call(&f,"dos64_uci_poll");}
 try std.testing.expectEqual(@as(u8,6),try get(&f,"dos64_uci_error"));try std.testing.expectEqual(@as(u64,0),c.dos64_uci_model_count(f.machine,0));
 try std.testing.expectEqual(@as(u8,0xa5),try get(&f,"dos64_uci_trace_valid"));
}
test "native first record survives recovery and later transaction until explicit ENTRY reset" {
 var f=try setup(true);defer f.deinit();try call(&f,"dos64_uci_start");try call(&f,"dos64_uci_poll");c.dos64_uci_model_error(f.machine);try call(&f,"dos64_uci_poll");
 const first=try snapshot(&f);try std.testing.expectEqual(@as(u8,4),first[6+15]);
 try call(&f,"dos64_uci_poll");try std.testing.expectEqual(@as(u8,10),try get(&f,"dos64_uci_state"));
 try call(&f,"dos64_uci_start");c.dos64_uci_model_error(f.machine);try call(&f,"dos64_uci_poll");try std.testing.expectEqualSlices(u8,&first,&(try snapshot(&f)));
 try call(&f,"dos64_uci_trace_reset");try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_uci_trace_valid"));
}
test "generic unbootstrapped UCI fixture never calls unavailable F000 trace" {
 var f=try setup(false);defer f.deinit();try call(&f,"dos64_uci_start");c.dos64_uci_model_error(f.machine);try call(&f,"dos64_uci_poll");
 try std.testing.expectEqual(@as(u8,4),try get(&f,"dos64_uci_error"));try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_uci_trace_valid"));
}
comptime {_=@import("uci.zig");}

test "native all256 raw ID values preserve rejected identifier before any command" {
 for(0..256)|id|{var f=try setup(true);defer f.deinit();c.dos64_uci_model_enable(f.machine,0xdf1c,0,@intCast(id));const r=try f.call("dos64_uci_start",100_000);const accepted=(id&0x7f)==0x49;try std.testing.expectEqual(@as(u8,if(accepted)0 else 1),r.p&1);try std.testing.expectEqual(@as(u8,@intCast(id)),try get(&f,"dos64_uci_trace_last_id"));try std.testing.expectEqual(@as(u64,0),c.dos64_uci_model_count(f.machine,0));try std.testing.expectEqual(@as(u64,0),c.dos64_uci_model_count(f.machine,3));
 if(accepted){try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_uci_trace_valid"));try std.testing.expectEqual(@as(u8,1),try get(&f,"dos64_uci_state"));}else{const b=try snapshot(&f);try std.testing.expectEqualSlices(u8,"UCF2",b[0..4]);try std.testing.expectEqual(@as(u8,2),b[4]);try std.testing.expectEqual(@as(u8,0xa5),b[5]);try std.testing.expectEqual(@as(u8,0),b[6+14]);try std.testing.expectEqual(@as(u8,2),b[6+15]);try std.testing.expectEqual(@as(u8,0),b[6+17]);try std.testing.expectEqual(@as(u8,@intCast(id)),b[176]);try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_uci_last_status"));}
 }
}
test "native rejected INPUT marks ID unobserved and preserves prior first ID through retry" {
 var f=try setup(true);defer f.deinit();try word(&f,"dos64_uci_command_len",0);try put(&f,"dos64_uci_trace_last_id",0x81);_=try f.call("dos64_uci_start",100_000);const b=try snapshot(&f);try std.testing.expectEqual(@as(u8,1),b[6+15]);try std.testing.expectEqual(@as(u8,0),b[176]);try call(&f,"dos64_uci_trace_reset");try word(&f,"dos64_uci_command_len",61);c.dos64_uci_model_enable(f.machine,0xdf1c,0,0x81);_=try f.call("dos64_uci_start",100_000);const first=try snapshot(&f);try std.testing.expectEqual(@as(u8,0x81),first[176]);c.dos64_uci_model_enable(f.machine,0xdf1c,0,0xc9);try call(&f,"dos64_uci_start");try std.testing.expectEqual(@as(u8,0xc9),try get(&f,"dos64_uci_trace_last_id"));try std.testing.expectEqualSlices(u8,&first,&(try snapshot(&f)));try call(&f,"dos64_uci_trace_reset");try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_uci_trace_first_id"));try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_uci_trace_last_id"));
}
test "generic unbootstrapped rejected ID never jumps into absent shadow" {
 var f=try setup(false);defer f.deinit();c.dos64_uci_model_enable(f.machine,0xdf1c,0,0x81);_=try f.call("dos64_uci_start",100_000);try std.testing.expectEqual(@as(u8,2),try get(&f,"dos64_uci_error"));try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_uci_trace_valid"));try std.testing.expectEqual(@as(u8,0x81),try get(&f,"dos64_uci_trace_last_id"));
}
test "native rejectedID retained original unit model RAM for offline decoder" {
 var f=try setup(true);defer f.deinit();c.dos64_uci_model_enable(f.machine,0xdf1c,0,0x81);_=try f.call("dos64_uci_start",100_000);var ram:[65536]u8=undefined;for(&ram,0..)|*v,i|v.*=f.peek(@intCast(i));try std.Io.Dir.cwd().writeFile(std.Options.debug_io,.{.sub_path="build/uci2-rejected-id-unit-model-64k.bin",.data=&ram});
}

// Independent union review additions; assembly remains byte-exact authored UCF2/PIT.
test "review rejected start captures preFAILED states and preserves nativeflags at every base" {
 for([_]u16{0xdf1c,0xde1c,0xdffc})|base|for([_]u8{0,9,10})|prior|for(0..16)|bits|{
  var f=try setup(true);defer f.deinit();const status:u8=0x22|@as(u8,@intCast(bits&1))|@as(u8,@intCast((bits&2)<<1))|@as(u8,@intCast((bits&4)<<1))|@as(u8,@intCast((bits&8)<<3));f.initial_status=status;
  try word(&f,"dos64_uci_base",base);try put(&f,"dos64_uci_state",prior);try put(&f,"dos64_uci_last_status",0xab);c.dos64_uci_model_enable(f.machine,base,0,0x81);
  const r=try f.call("dos64_uci_start",100000);try std.testing.expectEqual(@as(u8,1),r.p&1);try std.testing.expectEqual(status&0xce,r.p&0xce);const b=try snapshot(&f);try std.testing.expectEqual(prior,b[6+14]);try std.testing.expectEqual(@as(u8,2),b[6+15]);try std.testing.expectEqual(@as(u8,0xab),b[6+17]);try std.testing.expectEqual(@as(u8,0x81),b[176]);try std.testing.expectEqual(@as(u8,10),try get(&f,"dos64_uci_state"));try std.testing.expectEqual(@as(u64,0),c.dos64_uci_model_count(f.machine,0));try std.testing.expectEqual(@as(u64,0),c.dos64_uci_model_count(f.machine,3));
 };
}
test "review unbootstrapped rejected start all255 readiness bytes avoid poisoned shadow" {
 for(0..256)|ready|{if(ready==0xa5)continue;var f=try setup(false);defer f.deinit();for(0xf000..0xfe00)|at|f.poke(@intCast(at),0);try put(&f,"hdb_extension_ready",@intCast(ready));c.dos64_uci_model_enable(f.machine,0xdf1c,0,0x80);const r=try f.call("dos64_uci_start",100000);try std.testing.expectEqual(@as(u8,1),r.p&1);try std.testing.expectEqual(@as(u8,2),try get(&f,"dos64_uci_error"));try std.testing.expectEqual(@as(u8,0),try get(&f,"dos64_uci_trace_valid"));try std.testing.expectEqual(@as(u8,0x80),try get(&f,"dos64_uci_trace_last_id"));}
}
test "review UCF2 exact42plus128plusID publication A5 is last with no neighbor overwrite" {
 var f=try setup(true);defer f.deinit();const source=try f.symbol("dos64_uci_state_start");const cmd=try f.symbol("dos64_uci_command");for(0..42)|i|f.poke(source+@as(u16,@intCast(i)),@intCast(i^0x5a));for(0..128)|i|f.poke(cmd+@as(u16,@intCast(i)),@intCast(i^0xa7));try put(&f,"dos64_uci_error",2);try put(&f,"dos64_uci_trace_last_id",0x81);
 const first=try f.symbol("dos64_uci_trace_start");const end=try f.symbol("dos64_uci_trace_end");const valid=try f.symbol("dos64_uci_trace_valid");var publish:u16=0;const entry=try f.symbol("dos64_uci_trace_first");for(0..128)|i|{const at=entry+@as(u16,@intCast(i));if(f.peek(at)==0xa9 and f.peek(at+1)==0xa5 and f.peek(at+2)==0x8d and f.word(at+3)==valid and f.peek(at+5)==0x60)publish=at+2;}try std.testing.expect(publish!=0);const done=publish+3;
 try std.testing.expectEqual(@as(u8,0x8d),f.peek(publish));try std.testing.expectEqual(valid,f.word(publish+1));f.poke(first-1,0x6b);f.poke(end+1,0xd7);
 c.dos64_set_regs(f.machine,.{.pc=try f.symbol("dos64_uci_trace_first"),.sp=0xff,.a=0,.x=0,.y=0,.p=0x24,.cycles=0,.instructions=0});const r=c.dos64_run(f.machine,publish,100000);try std.testing.expectEqual(@as(c_uint,c.DOS64_RUN_RETURNED),r.status);try std.testing.expectEqual(@as(u8,0),f.peek(valid));
 const b=try snapshot(&f);try std.testing.expectEqualSlices(u8,"UCF2\x02",b[0..5]);for(0..42)|i|try std.testing.expectEqual(f.peek(source+@as(u16,@intCast(i))),b[6+i]);for(0..128)|i|try std.testing.expectEqual(f.peek(cmd+@as(u16,@intCast(i))),b[48+i]);try std.testing.expectEqual(@as(u8,0x81),b[176]);
 c.dos64_step(f.machine);try std.testing.expectEqual(@as(u8,0xa5),f.peek(valid));try std.testing.expectEqual(done,c.dos64_get_regs(f.machine).pc);try std.testing.expectEqual(@as(u8,0x6b),f.peek(first-1));try std.testing.expectEqual(@as(u8,0xd7),f.peek(end+1));try std.testing.expectEqual(@as(u8,0x81),try get(&f,"dos64_uci_trace_last_id"));
}
