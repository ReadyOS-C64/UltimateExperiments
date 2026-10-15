const std = @import("std");
const host = @import("machine.zig");
const Fixture = host.Fixture;
const c = host.c;

fn configure(f: *Fixture, address: u16, far: u32, length: u16, direction: u8) !u16 {
    const request = try f.symbol("dos64_reu_request");
    const bytes = [_]u8{ @truncate(address), @truncate(address>>8), @truncate(far), @truncate(far>>8), @truncate(far>>16), @truncate(length), @truncate(length>>8), direction, 0xee, 0xee };
    for (bytes, 0..) |value,index| f.poke(request+@as(u16,@intCast(index)),value);
    return request;
}
fn setupRaw(f: *Fixture, address: u16, far: u32, length: u16, control: u8) void {
    const bytes = [_]u8{ @truncate(address), @truncate(address>>8), @truncate(far), @truncate(far>>8), @truncate(far>>16), @truncate(length), @truncate(length>>8) };
    for (bytes, 0..) |value,index| c.dos64_bus_write(f.machine, 0xdf02+@as(u16,@intCast(index)), value);
    c.dos64_bus_write(f.machine, 0xdf09, 0);
    c.dos64_bus_write(f.machine, 0xdf0a, control);
}

test "actual DMA assembly roundtrips unaligned buffers at multiple sizes and far banks" {
    var f = try Fixture.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(0,0x2f);
    f.poke(1,0x37);
    const sizes = [_]u16{ 1,16,64,256,512,1024,2048,4096 };
    const banks = [_]u32{0, 0x070000, 0x080000, 0x3f0000};
    for (banks) |bank| {
        for (sizes) |size| {
            for (0..size) |index| {
                const value: u8 = @truncate(index*37+11);
                f.poke(0x6003+@as(u16,@intCast(index)),value);
            }
            const req = try configure(&f,0x6003,bank+3,size,0);
            var regs = try f.call("dos64_reu_transfer",2000);
            try std.testing.expectEqual(@as(u8,0), regs.p & 1);
            try std.testing.expectEqual(@as(u8,0), f.peek(req+9));
            try std.testing.expectEqual(@as(u8,0x40), f.peek(req+8)&0xe0);
            for (0..size) |index| {
                try std.testing.expectEqual(@as(u8,@truncate(index*37+11)), c.dos64_reu_peek(f.machine,bank+3+@as(u32,@intCast(index))));
                f.poke(0x6003+@as(u16,@intCast(index)),0);
            }
            _ = try configure(&f,0x6003,bank+3,size,1);
            regs = try f.call("dos64_reu_transfer",2000);
            try std.testing.expectEqual(@as(u8,0), regs.p&1);
            for (0..size) |index| try std.testing.expectEqual(@as(u8,@truncate(index*37+11)),f.peek(0x6003+@as(u16,@intCast(index))));
            try std.testing.expectEqual(@as(u8,0x2f), f.peek(0));
            try std.testing.expectEqual(@as(u8,0x37 & 0x2f), f.peek(1)&0x2f);
            try std.testing.expectEqual(@as(u8,0x93),regs.y);
        }
    }
    try std.testing.expectEqual(@as(u64,64),c.dos64_dma_transfers(f.machine));
}

test "DMA assembly preserves decimal and interrupt state while returning carry" {
    var f = try Fixture.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.initial_status = 0x28;
    f.poke(0,0x2f); f.poke(1,0x35);
    _ = try configure(&f,0x6000,0x100000,1,0);
    const regs = try f.call("dos64_reu_transfer",2000);
    try std.testing.expectEqual(@as(u8,0x28),regs.p&0xfe);
    try std.testing.expectEqual(@as(u8,0x2f),f.peek(0));
}

test "DMA assembly rejects unsafe host and cross-bank ranges before issuing commands" {
    const Case = struct{ address:u16, far:u32, length:u16, mode:u8, err:u8 };
    const cases = [_]Case{
        .{.address=0x100,.far=0,.length=1,.mode=0,.err=1},
        .{.address=0xd000,.far=0,.length=1,.mode=0,.err=1},
        .{.address=0xcfff,.far=0,.length=2,.mode=0,.err=1},
        .{.address=0xffff,.far=0,.length=2,.mode=0,.err=1},
        .{.address=0x6000,.far=0x07ffff,.length=2,.mode=0,.err=1},
        .{.address=0x6000,.far=0,.length=0,.mode=0,.err=3},
        .{.address=0x6000,.far=0,.length=1,.mode=2,.err=2},
    };
    var f = try Fixture.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    for (cases) |item| {
        const req = try configure(&f,item.address,item.far,item.length,item.mode);
        const regs = try f.call("dos64_reu_transfer",2000);
        try std.testing.expectEqual(@as(u8,1),regs.p&1);
        try std.testing.expectEqual(item.err,f.peek(req+9));
        try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(f.machine));
    }
}

test "DMA exact bank end and exact safe host end are valid" {
    var f = try Fixture.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(0xcfff,0x96);
    _ = try configure(&f,0xcfff,0x3fffff,1,0);
    const regs = try f.call("dos64_reu_transfer",2000);
    try std.testing.expectEqual(@as(u8,0),regs.p&1);
    try std.testing.expectEqual(@as(u8,0x96),c.dos64_reu_peek(f.machine,0x3fffff));
}

test "REU model postconditions include address increments count one and clear-on-read status" {
    var f = try Fixture.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    setupRaw(&f,0x6000,0x12fffe,2,0);
    c.dos64_bus_write(f.machine,0xdf01,0x90);
    try std.testing.expectEqual(@as(u8,2),c.dos64_bus_read(f.machine,0xdf02));
    try std.testing.expectEqual(@as(u8,0),c.dos64_bus_read(f.machine,0xdf04));
    try std.testing.expectEqual(@as(u8,0x13),c.dos64_bus_read(f.machine,0xdf06));
    try std.testing.expectEqual(@as(u8,1),c.dos64_bus_read(f.machine,0xdf07));
    try std.testing.expectEqual(@as(u8,0x10),c.dos64_bus_read(f.machine,0xdf01));
    try std.testing.expectEqual(@as(u8,0x50),c.dos64_bus_read(f.machine,0xdf00));
    try std.testing.expectEqual(@as(u8,0x10),c.dos64_bus_read(f.machine,0xdf00));
}

test "REU model autoload restores addresses and count" {
    var f = try Fixture.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    setupRaw(&f,0x60a0,0x127bcd,7,0);
    c.dos64_bus_write(f.machine,0xdf01,0xb0);
    try std.testing.expectEqual(@as(u8,0xa0),c.dos64_bus_read(f.machine,0xdf02));
    try std.testing.expectEqual(@as(u8,0xcd),c.dos64_bus_read(f.machine,0xdf04));
    try std.testing.expectEqual(@as(u8,7),c.dos64_bus_read(f.machine,0xdf07));
    try std.testing.expectEqual(@as(u8,0x30),c.dos64_bus_read(f.machine,0xdf01));
}

test "REU model zero hardware count means 65536 with fixed host address" {
    var f = try Fixture.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(0x6000,0x5a);
    setupRaw(&f,0x6000,0x100000,0,0x80);
    c.dos64_bus_write(f.machine,0xdf01,0x90);
    for (0..65536) |index| try std.testing.expectEqual(@as(u8,0x5a),c.dos64_reu_peek(f.machine,0x100000+@as(u32,@intCast(index))));
    try std.testing.expectEqual(@as(u64,65536),c.dos64_dma_bytes(f.machine));
    try std.testing.expectEqual(@as(u8,0),c.dos64_bus_read(f.machine,0xdf02));
}

test "expanded REU REC counter wraps within 512 KiB without carrying upper bank latch" {
    var f = try Fixture.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    f.poke(0x6000,0x11); f.poke(0x6001,0x22);
    setupRaw(&f,0x6000,0x0fffff,2,0);
    c.dos64_bus_write(f.machine,0xdf01,0x90);
    try std.testing.expectEqual(@as(u8,0x11),c.dos64_reu_peek(f.machine,0x0fffff));
    try std.testing.expectEqual(@as(u8,0x22),c.dos64_reu_peek(f.machine,0x080000));
    try std.testing.expectEqual(@as(u8,0),c.dos64_reu_peek(f.machine,0x100000));
}

test "unmodeled REU compare deferred trigger and interrupts fail explicitly" {
    for ([_]u8{0x93,0x80}) |command| {
        var f = try Fixture.init();
        defer f.deinit();
        c.dos64_enable_reu(f.machine);
        setupRaw(&f,0x6000,0,1,0);
        c.dos64_bus_write(f.machine,0xdf01,command);
        try std.testing.expectEqual(@as(u8,1),c.dos64_model_fault(f.machine));
        try std.testing.expectEqual(@as(u64,0),c.dos64_dma_transfers(f.machine));
    }
}

test "C64 bus hides RAM under each ROM and routes writes to underlying RAM" {
    var f = try Fixture.init();
    defer f.deinit();
    f.poke(0,0x2f); f.poke(1,0x37);
    f.poke(0xa000,0x11); f.poke(0xe000,0x22); f.poke(0xd000,0x33);
    try std.testing.expectEqual(@as(u8,0xba),c.dos64_bus_read(f.machine,0xa000));
    try std.testing.expectEqual(@as(u8,0xea),c.dos64_bus_read(f.machine,0xe000));
    c.dos64_bus_write(f.machine,0xe000,0x77);
    f.poke(1,0x35);
    try std.testing.expectEqual(@as(u8,0x11),c.dos64_bus_read(f.machine,0xa000));
    try std.testing.expectEqual(@as(u8,0x77),c.dos64_bus_read(f.machine,0xe000));
    f.poke(1,0x33);
    try std.testing.expectEqual(@as(u8,0xcc),c.dos64_bus_read(f.machine,0xd000));
    f.poke(1,0x30);
    try std.testing.expectEqual(@as(u8,0x33),c.dos64_bus_read(f.machine,0xd000));
}

test "fixed REU address fills host buffer without incrementing REU pointer" {
    var f = try Fixture.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    c.dos64_reu_poke(f.machine,0x123456,0x87);
    setupRaw(&f,0x6000,0x123456,32,0x40);
    c.dos64_bus_write(f.machine,0xdf01,0x91);
    for (0..32) |index| try std.testing.expectEqual(@as(u8,0x87),f.peek(0x6000+@as(u16,@intCast(index))));
    try std.testing.expectEqual(@as(u8,0x56),c.dos64_bus_read(f.machine,0xdf04));
}

test "unmodeled REU interrupt request is rejected" {
    var f = try Fixture.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    c.dos64_bus_write(f.machine,0xdf09,0xc0);
    try std.testing.expectEqual(@as(u8,1),c.dos64_model_fault(f.machine));
}

test "shared integrity probe runs the actual assembly and checks 4096 restored bytes" {
    var f = try Fixture.init();
    defer f.deinit();
    c.dos64_enable_reu(f.machine);
    _ = try f.call("dos64_reu_probe",200_000);
    try f.expectStatus(0xa5);
    const mailbox = try f.symbol("dos64_mailbox");
    try std.testing.expectEqual(@as(u8,0),f.peek(mailbox+4));
    try std.testing.expectEqual(@as(u64,2),c.dos64_dma_transfers(f.machine));
    try std.testing.expectEqual(@as(u64,8192),c.dos64_dma_bytes(f.machine));
    for (0..4096) |index| {
        const expected = @as(u8,@truncate(index)) ^ 0xa7;
        try std.testing.expectEqual(expected,f.peek(0x6000+@as(u16,@intCast(index))));
        try std.testing.expectEqual(expected,c.dos64_reu_peek(f.machine,0x180003+@as(u32,@intCast(index))));
    }
}

test "unimplemented CIA or VIC registers cannot silently act as RAM" {
    var f = try Fixture.init();
    defer f.deinit();
    _ = c.dos64_bus_read(f.machine,0xdc04);
    try std.testing.expectEqual(@as(u8,1),c.dos64_model_fault(f.machine));
}

test "4 8 and 16 MiB capacity models reach their last bank with actual DMA assembly" {
    var f = try Fixture.init();
    defer f.deinit();
    for ([_]u32{4096,8192,16384}) |size_kib| {
        try std.testing.expectEqual(@as(u8,1),c.dos64_enable_reu_sized(f.machine,size_kib));
        const last = size_kib*1024-1;
        f.poke(0x6000,0xbc);
        _ = try configure(&f,0x6000,last,1,0);
        const regs = try f.call("dos64_reu_transfer",2000);
        try std.testing.expectEqual(@as(u8,0),regs.p&1);
        try std.testing.expectEqual(@as(u8,0xbc),c.dos64_reu_peek(f.machine,last));
    }
    try std.testing.expectEqual(@as(u8,0),c.dos64_enable_reu_sized(f.machine,512));
}
