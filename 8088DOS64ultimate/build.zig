const std = @import("std");

fn addPeddle(module: *std.Build.Module, b: *std.Build) void {
    module.addIncludePath(b.path("tests/host"));
    module.addIncludePath(b.path("third_party/peddle/Peddle"));
    module.addCSourceFiles(.{
        .files = &.{
            "tests/host/peddle_bridge.cpp",
            "third_party/peddle/Peddle/Peddle.cpp",
            "third_party/peddle/Peddle/PeddleDebugger.cpp",
            "third_party/peddle/Peddle/PeddleDisassembler.cpp",
            "third_party/peddle/Peddle/StrWriter.cpp",
        },
        .flags = &.{ "-std=c++20", "-O2", "-Wno-unused-parameter", "-Wno-unused-variable" },
    });
    module.link_libcpp = true;
}

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const tests = b.addTest(.{
        .root_module = b.createModule(.{
            .root_source_file = b.path("tests/host/foundation.zig"),
            .target = target,
            .optimize = b.standardOptimizeOption(.{}),
        }),
    });
    const options = b.addOptions();
    options.addOption(bool, "full_cpu_corpus", b.option(bool, "cpu-corpus", "Run the full pinned CPU corpus") orelse false);
    tests.root_module.addOptions("test_options", options);
    addPeddle(tests.root_module, b);
    const run = b.addRunArtifact(tests);
    b.step("test", "Assert actual 6510 assembly behavior in Peddle").dependOn(&run.step);
    // Profiling is opt-in and retains Debug Zig assertions. It executes the
    // same bridge/Peddle sources as the behavior tests, with the same C++ flags.
    const profile = b.addTest(.{
        .root_module = b.createModule(.{
            .root_source_file = b.path("tests/host/profile.zig"),
            .target = target,
            .optimize = .Debug,
        }),
    });
    addPeddle(profile.root_module, b);
    const run_profile = b.addRunArtifact(profile);
    b.step("profile-cpu", "Measure verified actual-assembly CPU workloads in Peddle").dependOn(&run_profile.step);
}
