const std=@import("std");
const host=@import("machine.zig");const F=host.Fixture;const c=host.c;
fn setup() !F {var f=try F.init();errdefer f.deinit();c.dos64_cia_clock_enable(f.machine);f.poke(try f.symbol("dos64_host_clock_claim"),0xa5);const r=try f.call("dos64_host_clock_init",5000);try std.testing.expectEqual(@as(u8,0),r.p&1);return f;}
fn seed(f:*F,t:u32) void {c.dos64_cia_clock_seed(f.machine,@truncate(~t),@truncate(~(t>>16)));}
fn check(f:*F,t:u32,carry:u8,ddr:u8,port:u8) !void {
 const out=try f.symbol("dos64_elapsed_now");f.poke(out,0x6d);f.poke(out+1,0xb2);seed(f,t);f.poke(0,ddr);f.poke(1,port);
 const r=try f.call("dos64_elapsed_poll",10000);try std.testing.expectEqual(carry,r.p&1);try std.testing.expectEqual(f.initial_status&0xce,r.p&0xce);try std.testing.expectEqual(@as(u8,0x82),r.x);try std.testing.expectEqual(@as(u8,0x93),r.y);try std.testing.expectEqual(ddr,f.peek(0));try std.testing.expectEqual(port&ddr,f.peek(1)&ddr);
 try std.testing.expectEqual(if(carry==0) @as(u16,@truncate(t>>12)) else @as(u16,0xb26d),f.word(out));
}
test "actual CIA publication converts exact 4096-tick units at boundaries and both wraps" {
 var f=try setup();defer f.deinit();
 for([_]u32{0x100,0xfff,0x1000,0x1fff,0x12345100,0x0fffff00,0x10000100,0xffffef00,0xffffff00,0x100}) |t| try check(&f,t,0,0x2f,0x35);
 var s:u32=0x808864;for(0..2048) |_| {s=s*%1664525+%1013904223;const t=s|0x100;try check(&f,t,0,0x2f,0x35);}
}
test "clock faults and reload sample rejection preserve old elapsed publication" {
 var f=try setup();defer f.deinit();
 try check(&f,0,1,0x2f,0x35);try check(&f,0xff,1,0x2f,0x35);
 f.poke(try f.symbol("dos64_host_clock_claim"),0);try check(&f,0x12345100,1,0x2f,0x35);
 f.poke(try f.symbol("dos64_host_clock_claim"),0xa5);f.poke(try f.symbol("dos64_host_clock_ready"),0);try check(&f,0x12345100,1,0x2f,0x35);
}
test "elapsed reader banks resident state and preserves every native flag and driven bank bit" {
 var f=try setup();defer f.deinit();
 for(0..256) |status| {f.initial_status=@intCast(status);for([_]u8{0,7,0x2f,0xff}) |ddr| for([_]u8{0x30,0x35,0x37,0xff}) |port| try check(&f,0x31415926,0,ddr,port);}
}
