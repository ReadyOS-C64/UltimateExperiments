const std = @import("std");
const m = @import("machine.zig");
const N = 64;
fn word(v: *[N]u8, at: usize, n: u16) void { std.mem.writeInt(u16, v[at..][0..2], n, .little); }
fn wide(v: *[N]u8, at: usize, n: u32) void { std.mem.writeInt(u32, v[at..][0..4], n, .little); }
fn sign(v: *[N]u8) void { wide(v, 60, std.hash.Crc32.hash(v[0..60])); }
fn source() [N]u8 {
    // Synthetic metadata only; no main image or cold-consumer execution claim.
    var v = [_]u8{0} ** N;
    @memcpy(v[0..6], "D64L\x01\x01"); word(&v,6,64);
    wide(&v,8,0xb801); wide(&v,12,0x12345678); word(&v,16,0x0801); word(&v,18,0xb7ff);
    word(&v,20,0x3000); word(&v,22,0x3003); word(&v,24,0x3006); word(&v,26,0x5882);
    wide(&v,28,0x7000-0x0801+2); wide(&v,32,0x7200-0x0801+2); wide(&v,36,0x3fe0-0x0801+2);
    wide(&v,40,0x3e0000); wide(&v,44,0x3ff000); word(&v,48,576);
    v[50]=32; v[51]=0x40; word(&v,52,142); word(&v,54,140); sign(&v); return v;
}
fn put(f: *m.Fixture, name: []const u8, v: []const u8) !void {
    const at = try f.symbol(name); for(v,0..) |b,i| f.poke(at+@as(u16,@intCast(i)),b);
}
fn get(f: *m.Fixture, name: []const u8) ![N]u8 {
    const at = try f.symbol(name); var out: [N]u8 = undefined;
    for(&out,0..) |*b,i| b.*=f.peek(at+@as(u16,@intCast(i))); return out;
}
fn fixture() !m.Fixture {
    var f=try m.Fixture.initPaths("build/setup-release.prg","build/setup-release.labels");
    _=try f.call("_codec_init",1_000_000); return f;
}
fn check(f: *m.Fixture, v: [N]u8, ok: bool) !void {
    const old=[_]u8{0xa9} ** N; try put(f,"_d64_release_input",&v); try put(f,"_d64_release_output",&old);
    const r=try f.call("_d64_release_validate",2_000_000);
    try std.testing.expectEqual(@as(u8,if(ok) 1 else 0),r.a);
    try std.testing.expectEqualSlices(u8,&v,&try get(f,"_d64_release_input"));
    try std.testing.expectEqualSlices(u8,if(ok) &v else &old,&try get(f,"_d64_release_output"));
    try std.testing.expectEqual(@as(u16,0xc000),f.word(try f.symbol("sp")));
    try std.testing.expect(f.stack_high_water<120);
    const bs=try f.symbol("__BSS_RUN__");const be=bs+try f.symbol("__BSS_SIZE__");
    for(0..65536) |i| {
        const a:u16=@intCast(i);if(m.c.dos64_was_written(f.machine,a)==0)continue;
        if((a>=2 and a<0x1c) or (a>=0x100 and a<0x200) or (a>=0xbf00 and a<0xc000) or (a>=bs and a<be))continue;
        std.debug.print("Forbidden release native write {x}\n",.{a});return error.ForbiddenWrite;
    }
}
test "native release descriptor preserves committed output on every byte corruption" {
    var f=try fixture();defer f.deinit();const v=source();try check(&f,v,true);
    for(0..N) |i| {var b=v;b[i]^=1;try check(&f,b,false);}
}
test "native release refuses signed ABI and reserved fields" {
    var f=try fixture();defer f.deinit();const v=source();
    for([_]usize{4,5,6,16,26,40,44,48,50,51,52,54,56,57,58,59}) |at| {
        var b=v;b[at]^=1;sign(&b);try check(&f,b,false);
    }
}
test "native release rejects wrapped spans overlap and callable flag aliases" {
    var f=try fixture();defer f.deinit();const v=source();
    for([_]usize{28,32,36}) |at| for([_]u32{0,1,0x10000,0xfffffffe,0xffffffff}) |n| {
        var b=v;wide(&b,at,n);sign(&b);try check(&f,b,false);
    };
    var b=v;wide(&b,32,0x7000-0x0801+2);sign(&b);try check(&f,b,false);
    for([_]u32{0x3000,0x3003,0x3006}) |n| {b=v;wide(&b,36,n-0x0801+2);sign(&b);try check(&f,b,false);}
}
test "native release checks exact patch and main bounds" {
    var f=try fixture();defer f.deinit();const v=source();
    for([_]u32{0,1,0x5083,0xb802,0x10000,0xffffffff}) |n| {
        var b=v;wide(&b,8,n);sign(&b);try check(&f,b,false);
    }
    var b=v;wide(&b,32,0x8000-140-0x0801+2);sign(&b);try check(&f,b,true);
    wide(&b,32,0x8000-139-0x0801+2);sign(&b);try check(&f,b,false);
    b=v;wide(&b,36,0x3fff-0x0801+2);sign(&b);try check(&f,b,true);
}
