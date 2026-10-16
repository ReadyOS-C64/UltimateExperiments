const std = @import("std");

pub fn build(b: *std.Build) void {
    const t = b.addTest(.{ .root_module = b.createModule(.{
        .root_source_file = b.path("tests/host/setup_release.zig"),
        .target = b.standardTargetOptions(.{}), .optimize = .ReleaseFast,
    }) });
    t.root_module.addIncludePath(b.path("tests/host"));
    t.root_module.addIncludePath(b.path("third_party/peddle/Peddle"));
    t.root_module.addCSourceFiles(.{ .files = &.{
        "tests/host/peddle_bridge.cpp",
        "third_party/peddle/Peddle/Peddle.cpp",
        "third_party/peddle/Peddle/PeddleDebugger.cpp",
        "third_party/peddle/Peddle/PeddleDisassembler.cpp",
        "third_party/peddle/Peddle/StrWriter.cpp",
    }, .flags = &.{ "-std=c++20", "-O2", "-Wno-unused-parameter", "-Wno-unused-variable" } });
    t.root_module.link_libcpp = true;
    const run = b.addRunArtifact(t);
    run.has_side_effects = true;
    run.addFileInput(b.path("build/setup-release.prg"));
    run.addFileInput(b.path("build/setup-release.labels"));
    run.setCwd(b.path("."));
    b.step("test", "Actual linked native C START release descriptor").dependOn(&run.step);
    b.step("compile", "Compile native release descriptor assertions for pinned execution")
        .dependOn(&b.addInstallFile(t.getEmittedBin(), "bin/setup-release-tests").step);
}
