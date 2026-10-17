const std = @import("std");
pub fn build(b: *std.Build) void {
    const t = b.addTest(.{ .root_module = b.createModule(.{ .root_source_file = b.path("tests/host/ini_sidecar.zig"), .target = b.standardTargetOptions(.{}), .optimize = .Debug }) });
    t.root_module.addIncludePath(b.path("tests/host"));
    t.root_module.addIncludePath(b.path("third_party/peddle/Peddle"));
    t.root_module.addCSourceFiles(.{ .files = &.{ "tests/host/peddle_bridge.cpp", "third_party/peddle/Peddle/Peddle.cpp", "third_party/peddle/Peddle/PeddleDebugger.cpp", "third_party/peddle/Peddle/PeddleDisassembler.cpp", "third_party/peddle/Peddle/StrWriter.cpp" }, .flags = &.{ "-std=c++20", "-O2", "-Wno-unused-parameter", "-Wno-unused-variable" } });
    t.root_module.link_libcpp = true;
    const r = b.addRunArtifact(t);
    r.has_side_effects = true;
    r.setCwd(b.path("."));
    for ([_][]const u8{ "build/dos64-tests.prg", "build/dos64-tests.labels", "build/dos64-tests.prg.unit-extra.bin" }) |n| r.addFileInput(b.path(n));
    b.step("test", "Actual test-only sidecar ownership").dependOn(&r.step);
}
