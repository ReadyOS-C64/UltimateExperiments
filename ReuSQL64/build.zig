const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const runner = b.addExecutable(.{
        .name = "rsql64_emu_tests",
        .root_module = b.createModule(.{
            .root_source_file = b.path("tests/host/runner.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });
    runner.root_module.addIncludePath(b.path("third_party/peddle"));
    runner.root_module.addIncludePath(b.path("../../zig64/third_party/peddle/Peddle"));
    runner.root_module.addCSourceFiles(.{
        .files = &.{
            "third_party/peddle/rsql64_peddle.cpp",
            "../../zig64/third_party/peddle/Peddle/Peddle.cpp",
            "../../zig64/third_party/peddle/Peddle/PeddleDebugger.cpp",
            "../../zig64/third_party/peddle/Peddle/PeddleDisassembler.cpp",
            "../../zig64/third_party/peddle/Peddle/StrWriter.cpp",
        },
        .flags = &.{ "-std=c++20", "-Wno-unused-parameter", "-Wno-unused-variable" },
    });
    runner.root_module.link_libcpp = true;

    const run = b.addRunArtifact(runner);
    if (b.args) |args| run.addArgs(args);
    const emu = b.step("emu-test", "Run the target foundation in Peddle");
    emu.dependOn(&run.step);
}
