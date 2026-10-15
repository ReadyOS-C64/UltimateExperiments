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
    const differential=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/threshold_differential.zig"),.target=target,.optimize=.Debug})});
    addPeddle(differential.root_module,b);b.step("threshold-differential","Compare exact optimized and frozen assembled PIT converters").dependOn(&b.addRunArtifact(differential).step);
    const cg=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/native_cga.zig"),.target=target,.optimize=.Debug})});
    addPeddle(cg.root_module,b);b.step("native-cga","Verify BIOS CGA native presentation").dependOn(&b.addRunArtifact(cg).step);
    const startup = b.addTest(.{ .root_module=b.createModule(.{ .root_source_file=b.path("tests/host/native_timer_startup.zig"), .target=target, .optimize=.Debug }) });
    addPeddle(startup.root_module,b);
    b.step("timer-startup","Private bounded timer activation seams").dependOn(&b.addRunArtifact(startup).step);
    const irq_pit = b.addTest(.{ .root_module=b.createModule(.{ .root_source_file=b.path("tests/host/irq_pit.zig"), .target=target, .optimize=.Debug }) });
    addPeddle(irq_pit.root_module,b);
    b.step("irq-pit","Private leased IRQ/PIT runtime proof").dependOn(&b.addRunArtifact(irq_pit).step);
    const future = b.addTest(.{ .root_module=b.createModule(.{ .root_source_file=b.path("tests/host/future_layout.zig"), .target=target, .optimize=.Debug }) });
    addPeddle(future.root_module,b);
    b.step("future-layout","Private five-overlay lease and phase tests").dependOn(&b.addRunArtifact(future).step);

    const layout = b.addTest(.{ .root_module=b.createModule(.{ .root_source_file=b.path("tests/host/unit_layout.zig"), .target=target, .optimize=.Debug }) });
    addPeddle(layout.root_module,b);
    b.step("unit-layout","Private unit cold lifetime tests").dependOn(&b.addRunArtifact(layout).step);

    const tests = b.addTest(.{
        .root_module = b.createModule(.{
            .root_source_file = b.path("tests/host/foundation.zig"),
            .target = target,
            .optimize = b.standardOptimizeOption(.{}),
        }),
    });
    const options = b.addOptions();
    options.addOption(bool, "long_dos_boot", false);
    options.addOption(bool, "full_cpu_corpus", b.option(bool, "cpu-corpus", "Run the full pinned CPU corpus") orelse false);
    tests.root_module.addOptions("test_options", options);
    addPeddle(tests.root_module, b);
    const run = b.addRunArtifact(tests);
    b.step("test", "Assert actual 6510 assembly behavior in Peddle").dependOn(&run.step);
    // Isolated standalone native clock PRG; explicit VIC script activation
    // tests control flow only. This lane does not use runtime/unit PRG files.
    const clock_probe = b.addTest(.{ .root_module = b.createModule(.{
        .root_source_file = b.path("tests/host/host_clock_probe.zig"),
        .target = target,
        .optimize = .Debug,
    }) });
    addPeddle(clock_probe.root_module, b);
    const run_clock_probe = b.addRunArtifact(clock_probe);
    b.step("clock-probe", "Verify bounded native CIA/VIC calibration fixture").dependOn(&run_clock_probe.step);
    const overlay = b.addTest(.{ .root_module = b.createModule(.{
        .root_source_file = b.path("tests/host/overlay_integration.zig"),
        .target = target,
        .optimize = .Debug,
    }) });
    addPeddle(overlay.root_module, b);
    const run_overlay = b.addRunArtifact(overlay);
    b.step("overlays", "Verify FILE/TEXT/INPUT overlays and bounded startup ownership").dependOn(&run_overlay.step);
    const native_runtime = b.addTest(.{ .root_module = b.createModule(.{
        .root_source_file = b.path("tests/host/native_runtime_integration.zig"),
        .target = target,
        .optimize = .Debug,
    }) });
    addPeddle(native_runtime.root_module, b);
    b.step("native-runtime", "Verify configured native startup, bounded runtime and development commands").dependOn(&b.addRunArtifact(native_runtime).step);
    const native_dos = b.addTest(.{ .root_module=b.createModule(.{
        .root_source_file=b.path("tests/host/native_dos_boot.zig"),.target=target,.optimize=.Debug,
    }) });
    addPeddle(native_dos.root_module,b);
    b.step("native-dos","Opt-in genuine DOS through configured native startup and bounded runtime").dependOn(&b.addRunArtifact(native_dos).step);
    b.step("native-dos-compile","Compile the native DOS long lane without executing it").dependOn(&native_dos.step);
    const display = b.addTest(.{ .root_module = b.createModule(.{
        .root_source_file = b.path("tests/host/native_text_integration.zig"),
        .target = target,
        .optimize = .Debug,
    }) });
    addPeddle(display.root_module, b);
    b.step("native-text", "Verify packed fonts, TEXT overlay and bounded VIC setup").dependOn(&b.addRunArtifact(display).step);
    // Full360KiB source/CRC/failure oracle is deliberately opt-in.
    const image_import = b.addTest(.{ .root_module = b.createModule(.{
        .root_source_file = b.path("tests/host/image_import.zig"),
        .target = target,
        .optimize = .Debug,
    }) });
    addPeddle(image_import.root_module, b);
    const run_image_import = b.addRunArtifact(image_import);
    b.step("image-import", "Verify cold native whole-floppy import and failure ownership").dependOn(&run_image_import.step);
    const boot = b.addTest(.{ .root_module = b.createModule(.{
        .root_source_file = b.path("tests/host/dos_boot.zig"),
        .target = target,
        .optimize = .Debug,
    }) });
    const boot_options = b.addOptions();
    boot_options.addOption(bool, "long_dos_boot", true);
    boot.root_module.addOptions("test_options", boot_options);
    addPeddle(boot.root_module, b);
    const run_boot = b.addRunArtifact(boot);
    b.step("dos-boot", "Continue genuine DOS beyond the verified kernel handoff").dependOn(&run_boot.step);
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
