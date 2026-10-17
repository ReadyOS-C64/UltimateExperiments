const std=@import("std");
const h=@import("machine_future.zig");
const F=h.Fixture;
const c=h.c;
const im=@cImport({@cInclude("host_input_model.h");});
fn p(f:*F,n:[]const u8,v:u8)!void {f.poke(try f.symbol(n),v);}
fn call(f:*F,n:[]const u8,budget:u64,carry:u8)!void {
 const r=try f.call(n,budget);
 try std.testing.expectEqual(carry,r.p&1);
}
test "native failed cold configuration explicitly disables poisoned callback flags before CPU or device takeover" {
 var f=try F.init();defer f.deinit();
 try p(&f,"dos64_irq_callback_enabled",0xa5);
 try p(&f,"dos64_pit_poll_enabled",0xa5);
 try p(&f,"dos64_guest",0x6d);
 // Every hardware model remains default-off: rejected config must not touch it.
 try call(&f,"dos64_native_start",10000,1);
 try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_irq_callback_enabled")));
 try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_pit_poll_enabled")));
 try std.testing.expectEqual(@as(u8,0x6d),f.peek(try f.symbol("dos64_guest")));
 try std.testing.expectEqual(@as(u8,0),c.dos64_model_fault(f.machine));
}
test "bounded native cold timer seam seeds fresh raw epoch before enabling and TEXT activation releases PIT" {
 var f=try F.init();defer f.deinit();
 c.dos64_enable_reu(f.machine);
 c.dos64_cia_clock_enable(f.machine);
 c.dos64_native_display_enable(f.machine);
 im.dos64_host_input_model_enable(@ptrCast(f.machine));
 try call(&f,"dos64_overlay_init",10000,0);
 try p(&f,"dos64_overlay_reu_mib",4);
 try call(&f,"dos64_overlay_bootstrap",300_000,0);
 try call(&f,"dos64_cpu_init",10000,0);
 try p(&f,"dos64_cache_limit",32);
 try call(&f,"dos64_cache_init",100000,0);
 try call(&f,"dos64_bios_init",40000000,0);
 try p(&f,"dos64_host_clock_claim",0xa5);
 try call(&f,"dos64_host_clock_init",10000,0);
 c.dos64_cia_clock_seed(f.machine,0xf000,0xffff);
 try p(&f,"dos64_host_input_claim",0xa5);
 try call(&f,"dos64_overlay_input_init",100000,0);
 const d=try f.symbol("dos64_native_diag");
 for(0..19)|i|f.poke(d+@as(u16,@intCast(i)),0);
 f.poke(d,3);
 // This is the real bounded post-BIOS/input continuation, entered before its
 // first fresh sample. Import completion and source image are preconditions;
 // no DOS image is loaded or executed by this focused test.
 try call(&f,"n_finish_cold",2000000,0);
 try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_irq_callback_enabled")));
 try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_pit_poll_enabled")));
 try std.testing.expectEqual(@as(u8,1),f.peek(try f.symbol("dos64_pit_ready")));
 try std.testing.expectEqual(@as(u16,4095),f.word(try f.symbol("dos64_pit_last")));
 try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_overlay_busy")));
 try std.testing.expectEqual(@as(u8,2),f.peek(try f.symbol("dos64_overlay_current")));
 try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_cold_open")));
 try std.testing.expectEqual(@as(u8,4),f.peek(d));
}
test "cold timer sampling retry remains bounded and never enables PIT on stopped CIA" {
 var f=try F.init();defer f.deinit();
 // Final vector publication now precedes the timer seam; provide its real
 // cold BIOS/cache preconditions, while leaving CIA sampling unseeded.
 c.dos64_enable_reu(f.machine);
 try call(&f,"dos64_overlay_init",10000,0);
 try p(&f,"dos64_overlay_reu_mib",4);
 try call(&f,"dos64_overlay_bootstrap",300000,0);
 try call(&f,"dos64_cpu_init",10000,0);
 try p(&f,"dos64_cache_limit",32);
 try call(&f,"dos64_cache_init",100000,0);
 try call(&f,"dos64_bios_init",40000000,0);
 c.dos64_cia_clock_enable(f.machine);
 try p(&f,"dos64_host_clock_claim",0xa5);
 try call(&f,"dos64_host_clock_init",10000,0);
 try call(&f,"n_finish_cold",2000000,1);
 const d=try f.symbol("dos64_native_diag");
 try std.testing.expectEqual(@as(u8,0xe1),f.peek(d));
 try std.testing.expectEqual(@as(u8,3),f.peek(d+1));
 try std.testing.expectEqual(@as(u8,4),f.peek(d+2));
 try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_irq_callback_enabled")));
 try std.testing.expectEqual(@as(u8,0),f.peek(try f.symbol("dos64_pit_poll_enabled")));
}
