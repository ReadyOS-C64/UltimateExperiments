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
fn snapshot(f:*F) ![176]u8 {var b:[176]u8=undefined;const a=try f.symbol("dos64_uci_trace_start");for(&b,0..) |*x,i| x.*=f.peek(a+@as(u16,@intCast(i)));return b;}
test "native upload checks stale response before next chunk without PUSH" {
 var f=try setup(true);defer f.deinit();try call(&f,"dos64_uci_start");try call(&f,"dos64_uci_poll");
 c.dos64_uci_model_stale(f.machine,0x20);try call(&f,"dos64_uci_poll");
 try std.testing.expectEqual(@as(u8,6),try get(&f,"dos64_uci_error"));try std.testing.expectEqual(@as(u64,0),c.dos64_uci_model_count(f.machine,0));
 const b=try snapshot(&f);try std.testing.expectEqualSlices(u8,"UCF1",b[0..4]);try std.testing.expectEqual(@as(u8,0xa5),b[5]);
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
