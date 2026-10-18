const std = @import("std");
const host = @import("machine.zig");
const F = host.Fixture;
const m = @cImport({
    @cInclude("uci_model.h");
});
fn p(f: *F, n: []const u8, v: u8) !void {
    f.poke(try f.symbol(n), v);
}
fn g(f: *F, n: []const u8) !u8 {
    return f.peek(try f.symbol(n));
}
fn w(f: *F, n: []const u8, v: u16) !void {
    const a = try f.symbol(n);
    f.poke(a, @truncate(v));
    f.poke(a + 1, @truncate(v >> 8));
}
fn call(f: *F, n: []const u8, c: u8) !void {
    const port = f.peek(1);
    const direction = f.peek(0);
    const wrapper = if (std.mem.eql(u8, n, "dos64_files_init")) "dos64_overlay_files_init" else if (std.mem.eql(u8, n, "dos64_files_start")) "dos64_overlay_files_start" else if (std.mem.eql(u8, n, "dos64_files_poll")) "dos64_overlay_files_poll" else n;
    const r = try f.call(wrapper, 100_000);
    try std.testing.expectEqual(port & direction, f.peek(1) & direction);
    try std.testing.expectEqual(direction, f.peek(0));
    try std.testing.expectEqual(c, r.p & 1);
    try std.testing.expectEqual(f.initial_status & 0xce, r.p & 0xce);
    if (std.mem.eql(u8, wrapper, n)) {
        try std.testing.expectEqual(@as(u8, 0x71), r.a);
        try std.testing.expectEqual(@as(u8, 0x82), r.x);
        try std.testing.expectEqual(@as(u8, 0x93), r.y);
    } else {
        try std.testing.expectEqual(@as(u8, 0), try g(f, "dos64_overlay_busy"));
        try std.testing.expectEqual(@as(u8, 1), try g(f, "dos64_overlay_current"));
    }
}
fn setup() !F {
    var f = try F.init();
    errdefer f.deinit();
    host.c.dos64_enable_reu(f.machine);
    _ = try f.call("dos64_overlay_init", 10_000);
    try p(&f, "dos64_overlay_reu_mib", 4);
    _ = try f.call("dos64_overlay_bootstrap", 300_000);
    m.dos64_uci_model_enable(f.machine, 0xdf1c, 7, 0xc9);
    try call(&f, "dos64_uci_init", 0);
    try call(&f, "dos64_files_init", 0);
    try w(&f, "dos64_uci_timeout", 4000);
    f.poke((try f.symbol("dos64_uci_command")) - 1, 0xa5);
    return f;
}
fn reply(f: *F, d: []const u8, s: []const u8) void {
    m.dos64_uci_model_block(f.machine, d.ptr, d.len, s.ptr, s.len);
}
fn tick(f: *F, now: *u16) !void {
    now.* +%= 1;
    try w(f, "dos64_files_now", now.*);
    try call(f, "dos64_files_poll", 0);
}
fn path(f: *F, op: u8, s: []const u8) !void {
    try p(f, "dos64_files_op", op);
    try p(f, "dos64_files_path_len", @intCast(s.len + 1));
    const a = (try f.symbol("dos64_uci_command")) + @as(u16, if (op == 2) 3 else 2);
    for (s, 0..) |b, i| f.poke(a + @as(u16, @intCast(i)), b);
    f.poke(a + @as(u16, @intCast(s.len)), 0);
}
fn run(f: *F, cmd: []const u8, d: []const u8, s: []const u8) !void {
    m.dos64_uci_model_enable(f.machine, 0xdf1c, 7, 0xc9);
    reply(f, d, s);
    try call(f, "dos64_files_start", 0);
    var now = f.word(try f.symbol("dos64_files_now"));
    var seen = false;
    for (0..4000) |_| {
        if (try g(f, "dos64_uci_state") == 3 and !seen) {
            for (cmd, 0..) |b, i| try std.testing.expectEqual(b, m.dos64_uci_model_command(f.machine, @intCast(i)));
            seen = true;
        }
        if (try g(f, "dos64_files_state") != 1) break;
        try tick(f, &now);
    }
    try std.testing.expect(seen);
    try std.testing.expect(try g(f, "dos64_files_state") != 1);
    try std.testing.expectEqual(now, f.word(try f.symbol("dos64_uci_now")));
    try std.testing.expectEqual(@as(u8, 0xa5), f.peek((try f.symbol("dos64_uci_command")) - 1));
    try std.testing.expectEqual(@as(u8, 0xad), f.peek(try f.symbol("dos64_uci_buffer_end")));
}
fn open(f: *F) !void {
    try path(f, 2, "disk.img");
    try p(f, "dos64_files_mode", 1);
    try run(f, &.{ 1, 2, 1, 'd', 'i', 's', 'k', '.', 'i', 'm', 'g', 0 }, "", "00,OK");
    try std.testing.expectEqual(@as(u8, 1), try g(f, "dos64_files_handle"));
}

fn metadata(length:usize) [75]u8 {
 var data:[75]u8=@splat('Q');data[0..4].*=.{0x00,0xa0,0x05,0x01};@memset(data[4..8],0);data[8..11].*=.{ 'I','M','G' };data[11]=0x20;_ = length;return data;
}
test "FILE_INFO known target owner accepts valid13and75byte records and retains LE32 size" {
 for([_]usize{13,20,75}) |length| {var f=try setup();defer f.deinit();try open(&f);try p(&f,"dos64_files_op",7);const data=metadata(length);try run(&f,&.{1,7},data[0..length],"00,OK");try std.testing.expectEqual(@as(u8,2),try g(&f,"dos64_files_state"));try std.testing.expectEqual(@as(u8,1),try g(&f,"dos64_files_handle"));try std.testing.expectEqual(@as(u16,@intCast(length)),f.word(try f.symbol("dos64_files_actual")));try std.testing.expectEqual(@as(u8,1),try g(&f,"dos64_files_count_known"));for(data[0..length],0..) |v,i|try std.testing.expectEqual(v,f.peek((try f.symbol("dos64_uci_data"))+@as(u16,@intCast(i))));}
}
test "FILE_INFO rejects closed unknown and wrong target before PUSH" {
 for([_]u8{0,1,2}) |which| {var f=try setup();defer f.deinit();if(which!=0)try open(&f);m.dos64_uci_model_enable(f.machine,0xdf1c,7,0xc9);if(which==1)try p(&f,"dos64_files_handle",2);if(which==2)try p(&f,"dos64_files_target",2);try p(&f,"dos64_files_op",7);try call(&f,"dos64_files_start",1);try std.testing.expectEqual(@as(u64,0),m.dos64_uci_model_count(f.machine,0));}
}
test "FILE_INFO rejects empty short oversized metadata and invalid file records" {
 for([_]usize{0,1,11,12,76,895}) |length| {var f=try setup();defer f.deinit();try open(&f);try p(&f,"dos64_files_op",7);var data:[895]u8=@splat('Q');const valid=metadata(75);@memcpy(data[0..75],&valid);try run(&f,&.{1,7},data[0..length],"00,OK");try std.testing.expectEqual(@as(u8,3),try g(&f,"dos64_files_state"));}
 for([_]u8{0x10,0x08,0x18}) |attributes| {var f=try setup();defer f.deinit();try open(&f);try p(&f,"dos64_files_op",7);var data=metadata(20);data[11]=attributes;try run(&f,&.{1,7},data[0..20],"00,OK");try std.testing.expectEqual(@as(u8,3),try g(&f,"dos64_files_state"));}
 var f=try setup();defer f.deinit();try open(&f);try p(&f,"dos64_files_op",7);var data=metadata(20);data[15]=0;try run(&f,&.{1,7},data[0..20],"00,OK");try std.testing.expectEqual(@as(u8,3),try g(&f,"dos64_files_state"));
}
test "FILE_INFO fresh data needs exact success status and target2 owner works" {
 for([_][]const u8{"","0","85,ERR","00,OK\x00","00,ok"}) |status| {var f=try setup();defer f.deinit();try open(&f);try p(&f,"dos64_files_op",7);const data=metadata(20);try run(&f,&.{1,7},data[0..20],status);try std.testing.expectEqual(@as(u8,3),try g(&f,"dos64_files_state"));}
 var f=try setup();defer f.deinit();try p(&f,"dos64_files_target",2);try path(&f,2,"disk.img");try p(&f,"dos64_files_mode",1);try run(&f,&.{2,2,1,'d','i','s','k','.','i','m','g',0},"","00,OK");try p(&f,"dos64_files_op",7);const data=metadata(20);try run(&f,&.{2,7},data[0..20],"00,OK");try std.testing.expectEqual(@as(u8,2),try g(&f,"dos64_files_state"));
}
