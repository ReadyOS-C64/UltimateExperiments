const std = @import("std");
const c = @cImport({
    @cInclude("directory_bridge.h");
    @cInclude("bulk_model_api.h");
    @cInclude("host_input_model.h");
    @cInclude("cia_clock_model.h");
    @cInclude("graphics_color_model.h");
    @cInclude("native_display_model.h");

});
extern fn native_runtime_control_enable(?*anyopaque) void;
extern fn bulk_model_seed_open(?*anyopaque,u8,[*:0]const u8,u8,u32) void;
const a = std.testing.allocator;
const F = struct {
    m: *c.Dos64Machine,
    labels: []u8,
    s: std.StringHashMapUnmanaged(u16) = .empty,
    tick: u16 = 0,
    fn init() !F {
        const code = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "config.prg", a, .limited(65538));
        defer a.free(code);
        var f = F{ .m = c.dos64_create() orelse return error.Create, .labels = try std.Io.Dir.cwd().readFileAlloc(std.Options.debug_io, "config.labels", a, .limited(200000)) };
        c.dos64_load(f.m, std.mem.readInt(u16, code[0..2], .little), code[2..].ptr, code.len - 2);
        var lines = std.mem.splitScalar(u8, f.labels, '\n');
        while (lines.next()) |line| {
            var t = std.mem.tokenizeAny(u8, line, " \r\t");
            if (!std.mem.eql(u8, t.next() orelse continue, "al")) continue;
            const address = t.next() orelse continue;
            const name = t.next() orelse continue;
            try f.s.put(a, name[1..], try std.fmt.parseInt(u16, address, 16));
        }
        c.dos64_uci_model_enable(f.m, 0xdf1c, 3, 0xc9);
        c.dos64_enable_reu(f.m);
        c.bulk_model_enable(f.m);
        native_runtime_control_enable(f.m);
        c.dos64_graphics_color_enable(f.m);
        c.dos64_cia_clock_enable(f.m);
        c.dos64_native_display_enable(f.m);
        c.dos64_host_input_model_enable(f.m);
        _ = try f.call("runtime_init", 0);
        try std.testing.expectEqual(@as(u8, 1), try f.call("_cg_boot", 0));
        return f;
    }
    fn deinit(f: *F) void {
        c.dos64_destroy(f.m);
        f.s.deinit(a);
        a.free(f.labels);
    }
    fn sym(f: *F, n: []const u8) !u16 {
        return f.s.get(n) orelse error.Symbol;
    }
    fn byte(f: *F, n: []const u8, offset: u16) !u8 {
        return c.dos64_peek(f.m, (try f.sym(n)) + offset);
    }
    fn put(f: *F, n: []const u8, bytes: []const u8) !void {
        c.dos64_load(f.m, try f.sym(n), bytes.ptr, bytes.len);
    }
    fn word(f: *F, n: []const u8, v: u16) !void {
        var bytes: [2]u8 = undefined;
        std.mem.writeInt(u16, &bytes, v, .little);
        try f.put(n, &bytes);
    }
    fn call(f: *F, n: []const u8, arg: u8) !u8 {
        return f.registerCall(n, arg, 0x82);
    }
    fn pointerCall(f: *F, n: []const u8, pointer: u16) !u8 {
        return f.registerCall(n, @truncate(pointer), @truncate(pointer >> 8));
    }
    fn registerCall(f: *F, n: []const u8, arg: u8, x: u8) !u8 {
        const ret = (try f.sym("fixture_return")) -% 1;
        c.dos64_poke(f.m, 0x1ff, @truncate(ret >> 8));
        c.dos64_poke(f.m, 0x1fe, @truncate(ret));
        c.dos64_set_regs(f.m, .{ .pc = try f.sym(n), .sp = 0xfd, .a = arg, .x = x, .y = 0x93, .p = 0x24, .cycles = 0, .instructions = 0 });
        const r = c.dos64_run(f.m, try f.sym("fixture_return"), if (std.mem.eql(u8, n, "_si_poll")) 250000000 else if (std.mem.eql(u8, n, "_so_prepare")) 5000000 else 12000000);
        try std.testing.expectEqual(@as(c_uint, c.DOS64_RUN_RETURNED), r.status);
        try std.testing.expect(r.stack_high_water < 120);
        try std.testing.expectEqual(@as(u8, 0xff), try f.byte("sp", 0));
        try std.testing.expectEqual(@as(u8, 0xcf), try f.byte("sp", 1));
        return r.regs.a;
    }
    fn begin(f:*F)!void {
        var q=[_]u8{0}**7;q[0]=0xa5;
        std.mem.writeInt(u32,q[1..5],0x400000,.little);
        std.mem.writeInt(u16,q[5..7],1000,.little);
        try f.put("_cg_request",&q);
        try std.testing.expectEqual(@as(u8,1),try f.call("_cg_begin",0));
    }
    fn poll(f:*F)!u8 {
        c.dos64_cia_clock_advance(f.m,1024);
        _=try f.call("_cg_poll",0);
        return f.call("_cg_state",0);
    }
    fn ready(f:*F)!u8 {
        for(0..3000)|_| {
            const state=try f.poll();
            if(state!=1 and state!=3 and !(state==2 and try f.byte("_db_result",0)==1)) return state;
        }
        return error.UIBudget;
    }
    fn key(f:*F,row:u3,col:u3,shift:bool)!u8 {
        var keys=[_]u8{0}**8;keys[row]=@as(u8,1)<<col;
        if(shift)keys[1]|=128;
        c.dos64_host_input_model_keys(f.m,&keys);_=try f.poll();
        keys=@splat(0);c.dos64_host_input_model_keys(f.m,&keys);_=try f.poll();
        return f.ready();
    }
    fn seed(f:*F)!void {
        c.dir_model_enable(f.m);
        for([_] [:0]const u8{"/","/Home","/Release","/New"})|p|c.dir_model_path(f.m,p);
        for([_] [:0]const u8{"Home","Release","New"})|n|c.dir_model_row(f.m,"/",16,n.ptr,@intCast(n.len));
        const bytes=@embedFile("valid.cfg");c.bulk_model_seed(f.m,"/Home/DOS64.CFG",bytes.ptr,bytes.len);
    }
};
test "actual CIA selection and native new40 receipt after same-engine startup" {
    var f=try F.init();defer f.deinit();try f.seed();
    const stale="UNCHANGED";c.bulk_model_seed(f.m,"/Stale",stale.ptr,stale.len);
    bulk_model_seed_open(f.m,1,"/Stale",3,7);bulk_model_seed_open(f.m,2,"/Stale",3,7);
    try f.begin();try std.testing.expectEqual(@as(u8,2),try f.ready());
    _=try f.key(0,1,false);try std.testing.expectEqual(@as(u8,4),try f.key(0,4,false));
    _=try f.key(0,7,true);_=try f.key(0,1,false);
    _=try f.key(0,7,false);_=try f.key(0,1,false);_=try f.key(0,4,false);
    _=try f.key(0,7,false);_=try f.key(0,7,false);_=try f.key(0,1,false);
    try std.testing.expectEqual(@as(u8,5),try f.key(0,4,false));
    try std.testing.expectEqual(@as(u8,6),try f.key(0,1,false));
    try std.testing.expectEqual(@as(u8,1),try f.call("_cg_get",0));
    try std.testing.expectEqual(@as(u8,40),try f.byte("_cg_receipt",394));
    for("[emulator]\r\ninitial_columns=40\r\n",0..)|v,i|try std.testing.expectEqual(v,try f.byte("_cg_receipt",@intCast(397+i)));
    try std.testing.expectEqual(@as(u32,9),c.bulk_model_commands(f.m));
    try std.testing.expectEqual(@as(u8,0),c.bulk_model_open(f.m,1));try std.testing.expectEqual(@as(u8,0),c.bulk_model_open(f.m,2));
    try std.testing.expectEqual(@as(u8,1),try f.call("_bc_ui_acquire",0));
    try f.put("_cg_result",&.{6,0,0,0,0,0,80,0xa5});
    try std.testing.expectEqual(@as(u8,0),try f.call("_cg_get",0));
    try std.testing.expectEqual(@as(u8,1),try f.call("_bc_ui_release",0));
    try std.testing.expectEqual(@as(u8,1),try f.call("_cg_get",0));
    const abi=[_]u8{7,0,8,0,0xad,1};for(abi,0..)|v,i|try std.testing.expectEqual(v,try f.byte("_cg_abi_sizes",@intCast(i)));
}
test "actual startup STOP cannot be forged into CONFIG or RI authority" {
    var f=try F.init();defer f.deinit();try f.seed();try f.begin();
    try std.testing.expectEqual(@as(u8,7),try f.key(7,7,false));
    try std.testing.expectEqual(@as(u8,5),try f.call("_cg_error",0));
    try f.put("_cg_result",&.{6,0,0,0,0,0,80,0xa5});
    try std.testing.expectEqual(@as(u8,0),try f.call("_cg_get",0));
    try std.testing.expectEqual(@as(u8,0),try f.call("_ri_attach",0));
    try std.testing.expectEqual(@as(u8,0),try f.call("_ri_boot",0));
    try std.testing.expectEqual(@as(u32,0),c.dir_model_commands(f.m));
}
