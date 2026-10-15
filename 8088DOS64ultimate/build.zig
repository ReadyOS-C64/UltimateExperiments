const std = @import("std");

pub fn build(b: *std.Build) void {
    const tests = b.addTest(.{
        .root_module = b.createModule(.{
            .root_source_file = b.path("tests/host/foundation.zig"),
            .target = b.standardTargetOptions(.{}),
            .optimize = b.standardOptimizeOption(.{}),
        }),
    });
    tests.root_module.addIncludePath(b.path("tests/host"));
    tests.root_module.addIncludePath(b.path("third_party/peddle/Peddle"));
    tests.root_module.addCSourceFiles(.{
        .files = &.{
            "tests/host/peddle_bridge.cpp",
            "third_party/peddle/Peddle/Peddle.cpp",
            "third_party/peddle/Peddle/PeddleDebugger.cpp",
            "third_party/peddle/Peddle/PeddleDisassembler.cpp",
            "third_party/peddle/Peddle/StrWriter.cpp",
        },
        .flags = &.{ "-std=c++20", "-Wno-unused-parameter", "-Wno-unused-variable" },
    });
    tests.root_module.link_libcpp = true;
    const run = b.addRunArtifact(tests);
    b.step("test", "Assert actual 6510 assembly behavior in Peddle").dependOn(&run.step);
}
