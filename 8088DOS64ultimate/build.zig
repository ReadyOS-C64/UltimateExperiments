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

// These executables read linked target bytes at runtime. Always execute them,
// and include the native inputs in the build graph rather than treating a
// cached host test executable as evidence for a newly assembled PRG.
fn nativeInputs(run: *std.Build.Step.Run, b: *std.Build) void {
    run.has_side_effects = true;
    run.addFileInput(b.path("build/dos64-tests.prg"));
    run.addFileInput(b.path("build/dos64-tests.labels"));
    run.addFileInput(b.path("build/dos64-tests.prg.unit-extra.bin"));
}

fn nativeRun(b: *std.Build, artifact: *std.Build.Step.Compile) *std.Build.Step.Run {
    const run = b.addRunArtifact(artifact);
    nativeInputs(run, b);
    return run;
}

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const trap=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/trap.zig"),.target=target,.optimize=.Debug})});addPeddle(trap.root_module,b);b.step("cpu-trap","Original8088 TF type1 actual assembly").dependOn(&nativeRun(b,trap).step);b.step("cpu-trap-compile","Compile original8088 trap assertions").dependOn(&b.addInstallFile(trap.getEmittedBin(),"bin/cpu-trap-tests").step);
    const loader=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/loader_handoff.zig"),.target=target,.optimize=.Debug})});addPeddle(loader.root_module,b);loader.filters=b.option([]const []const u8,"loader-filter","Focused cold handoff cases") orelse &.{};const run_loader=nativeRun(b,loader);nativeInputs(run_loader,b);b.step("loader-handoff","Actual cold REU handoff and preloaded floppy adoption").dependOn(&run_loader.step);
    const loader_dos=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/loader_dos_boot.zig"),.target=target,.optimize=.Debug})});addPeddle(loader_dos.root_module,b);const run_loader_dos=nativeRun(b,loader_dos);nativeInputs(run_loader_dos,b);b.step("loader-dos","Genuine DOS VER DIR through required preloaded main handoff").dependOn(&run_loader_dos.step);
    const fl=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/dual_floppy.zig"),.target=target,.optimize=.Debug})});fl.filters=b.option([]const []const u8,"dual-floppy-filter","Focused dual media controls") orelse &.{};addPeddle(fl.root_module,b);const run_fl=nativeRun(b,fl);nativeInputs(run_fl,b);b.step("dual-floppy","Actual independent floppy drives and native mount lifecycle").dependOn(&run_fl.step);b.step("dual-floppy-compile","Compile independent media regressions").dependOn(&b.addInstallFile(fl.getEmittedBin(),"bin/dual-floppy-tests").step);
    const cursor=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/cga_cursor.zig"),.target=target,.optimize=.Debug})});cursor.filters=b.option([]const []const u8,"cga-cursor-filter","Focused hardware cursor controls") orelse &.{};addPeddle(cursor.root_module,b);b.step("cga-cursor","Actual hardware cursor presentation").dependOn(&nativeRun(b,cursor).step);b.step("cga-cursor-compile","Compile cursor controls").dependOn(&b.addInstallFile(cursor.getEmittedBin(),"bin/cursor-tests").step);
    const status=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/cga_status.zig"),.target=target,.optimize=.Debug})});addPeddle(status.root_module,b);b.step("cga-status","OriginalCGA clock-derived status and leases").dependOn(&nativeRun(b,status).step);
    const crtc=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/cga_crtc.zig"),.target=target,.optimize=.Debug})});addPeddle(crtc.root_module,b);b.step("cga-crtc","OriginalCGA MC6845 actualregisterporttests").dependOn(&nativeRun(b,crtc).step);b.step("cga-crtc-compile","Compile CRTCrepro").dependOn(&b.addInstallFile(crtc.getEmittedBin(),"bin/crtc-tests").step);
    const escape=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/escape.zig"),.target=target,.optimize=.Debug})});addPeddle(escape.root_module,b);
    b.step("escape","Original8088 absent8087 ESC and WAIT actual assembly").dependOn(&nativeRun(b,escape).step);
    b.step("escape-compile","Compile absent8087 tests without execution").dependOn(&b.addInstallFile(escape.getEmittedBin(),"bin/escape-tests").step);
    const palette=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/video_xt_integration.zig"),.target=target,.optimize=.Debug}),.filters=&.{"XT palette", "INT10 query"}});addPeddle(palette.root_module,b);b.step("video-palette","XT color register semantics").dependOn(&nativeRun(b,palette).step);

    const ui=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/uci_ram_init.zig"),.target=target,.optimize=.Debug})});addPeddle(ui.root_module,b);const ui_ref=b.addSystemCommand(&.{"python3","build_support/build_uci_ram_init_reference.py"});const ui_run=nativeRun(b,ui);ui_run.step.dependOn(&ui_ref.step);b.step("uci-ram-init","Actual native initializer original equivalence").dependOn(&ui_run.step);
    const fi=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/files_info.zig"),.target=target,.optimize=.Debug})});addPeddle(fi.root_module,b);b.step("files-info","Strict actual native FILE_INFO record/status/owner").dependOn(&nativeRun(b,fi).step);

    const fx=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/files.zig"),.target=target,.optimize=.Debug})});addPeddle(fx.root_module,b);b.step("files-existing","Existing actual native FILE operations").dependOn(&nativeRun(b,fx).step);

    @import("tests/floppy_export/build.zig").add(b,target);
    const sav=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/native_save.zig"),.target=target,.optimize=.Debug})});
    sav.filters=b.option([]const []const u8,"native-save-filter","Focused SAVE tests") orelse &.{};
    sav.root_module.addIncludePath(b.path("tests/floppy_export"));sav.root_module.addIncludePath(b.path("tests/host"));sav.root_module.addIncludePath(b.path("third_party/peddle/Peddle"));
    sav.root_module.addCSourceFiles(.{.files=&.{"tests/floppy_export/bridge.cpp","third_party/peddle/Peddle/Peddle.cpp","third_party/peddle/Peddle/PeddleDebugger.cpp","third_party/peddle/Peddle/PeddleDisassembler.cpp","third_party/peddle/Peddle/StrWriter.cpp"},.flags=&.{"-std=c++20","-O2","-Wno-unused-parameter","-Wno-unused-variable"}});sav.root_module.link_libcpp=true;
    b.step("native-save","Modal native paused whole floppy export").dependOn(&nativeRun(b,sav).step);
    const save_dos=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/native_save_workflow.zig"),.target=target,.optimize=.Debug})});save_dos.root_module.addIncludePath(b.path("tests/floppy_export"));save_dos.root_module.addIncludePath(b.path("tests/host"));save_dos.root_module.addIncludePath(b.path("third_party/peddle/Peddle"));save_dos.root_module.addCSourceFiles(.{.files=&.{"tests/floppy_export/bridge.cpp","third_party/peddle/Peddle/Peddle.cpp","third_party/peddle/Peddle/PeddleDebugger.cpp","third_party/peddle/Peddle/PeddleDisassembler.cpp","third_party/peddle/Peddle/StrWriter.cpp"},.flags=&.{"-std=c++20","-O2","-Wno-unused-parameter","-Wno-unused-variable"}});save_dos.root_module.link_libcpp=true;b.step("native-save-dos","Genuine DOS COPY whole native save and continued guest workflow").dependOn(&nativeRun(b,save_dos).step);


    @import("build_support/iec_standalone_tests.zig").add(b, target);
    const cgaw=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/native_cga_workflow.zig"),.target=target,.optimize=.Debug})});
    addPeddle(cgaw.root_module,b);
    b.step("native-cga-workflow","Genuine DOS loads guest CGA COM").dependOn(&nativeRun(b,cgaw).step);
    const gw=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/native_gwbasic_workflow.zig"),.target=target,.optimize=.Debug})});
    addPeddle(gw.root_module,b);
    b.step("native-gwbasic","Genuine supplied GW-BASIC ASCII hangman").dependOn(&nativeRun(b,gw).step);
    const ud=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/uci_diagnostic.zig"),.target=target,.optimize=.Debug})});
    addPeddle(ud.root_module,b);b.step("uci-diagnostic","Private persistent native transport failure evidence").dependOn(&nativeRun(b,ud).step);
    // Explicit slow native recovery proof; no dependency from default test.
    const reu_file=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/native_file_recovery/actual_assembly.zig"),.target=target,.optimize=.Debug})});
    reu_file.root_module.addIncludePath(b.path("tests/native_file_recovery/fixture"));
    reu_file.root_module.addIncludePath(b.path("third_party/peddle/Peddle"));
    reu_file.root_module.addCSourceFiles(.{.files=&.{"tests/native_file_recovery/fixture/peddle_bridge.cpp","third_party/peddle/Peddle/Peddle.cpp","third_party/peddle/Peddle/PeddleDebugger.cpp","third_party/peddle/Peddle/PeddleDisassembler.cpp","third_party/peddle/Peddle/StrWriter.cpp"},.flags=&.{"-std=c++20","-O2","-Wno-unused-parameter","-Wno-unused-variable"}});
    reu_file.root_module.link_libcpp=true;
    const run_reu_file=nativeRun(b,reu_file);run_reu_file.setCwd(b.path("."));
    b.step("native-file-recovery","Opt-in actual6502 full4MiB recovery and failure proof").dependOn(&run_reu_file.step);
    b.step("native-file-recovery-compile","Compile opt-in recovery fixture without executing full4MiB tests").dependOn(&reu_file.step);
    const hd_options = b.addOptions();
    hd_options.addOption(bool, "long_hd", b.option(bool, "long-hd", "Run opt-in genuine HD boot using explicit pinned manifests") orelse false);
    hd_options.addOption(?[]const u8, "small_manifest", b.option([]const u8, "hd-small-manifest", "Path to pinned small HD fixture manifest"));
    hd_options.addOption(?[]const u8, "large_manifest", b.option([]const u8, "hd-large-manifest", "Path to pinned large HD fixture manifest"));
    for ([_]struct { name: []const u8, file: []const u8 }{ .{ .name = "hd-fixtures", .file = "tests/host/hd_fixtures.zig" }, .{ .name = "hd-backend", .file = "tests/host/hd_backend.zig" }, .{ .name = "hd-bios", .file = "tests/host/hd_integration.zig" }, .{ .name = "hd-cold", .file = "tests/host/hd_cold_start.zig" } }) |entry| {
        const t = b.addTest(.{ .root_module = b.createModule(.{ .root_source_file = b.path(entry.file), .target = target, .optimize = .Debug }) });
        t.root_module.addOptions("hd_options", hd_options);
        addPeddle(t.root_module, b);
        b.step(entry.name, "Opt-in actual HD assembly integration").dependOn(&nativeRun(b,t).step);
        if(std.mem.eql(u8,entry.name,"hd-backend")) {
            b.step("hd-backend-compile","Compile exact backend test executable").dependOn(&b.addInstallFile(t.getEmittedBin(),"bin/hd-backend-tests").step);
            const regression=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path(entry.file),.target=target,.optimize=.Debug}),.filters=&.{"HD split256 avoids"}});
            regression.root_module.addOptions("hd_options",hd_options);addPeddle(regression.root_module,b);
            b.step("hd-write-regression-compile","Compile targeted native write regression").dependOn(&b.addInstallFile(regression.getEmittedBin(),"bin/hd-write-regression-tests").step);
        }
    }
    const workflows=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/native_builtin_workflows.zig"),.target=target,.optimize=.Debug}),.filters=&.{"internal disposable", "ASCII mapping"}});
    addPeddle(workflows.root_module,b);b.step("native-builtins","Opt-in genuine native DOS disposable workflows").dependOn(&nativeRun(b,workflows).step);
    const oracle_compile=b.step("native-cursor-oracle-compile","Compile cursor-aware native workflow oracles without running vendor programs");oracle_compile.dependOn(&workflows.step);oracle_compile.dependOn(&gw.step);oracle_compile.dependOn(&cgaw.step);
    const modes=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/native_builtin_workflows.zig"),.target=target,.optimize=.Debug}),.filters=&.{"MODE COM"}});
    addPeddle(modes.root_module,b);b.step("native-mode","Opt-in genuine MODE CO40/CO80").dependOn(&nativeRun(b,modes).step);
    const compat=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/video_xt_integration.zig"),.target=target,.optimize=.Debug})});
    addPeddle(compat.root_module,b);b.step("video-xt-compat","Original XT ignored INT10 functions").dependOn(&nativeRun(b,compat).step);
    const differential=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/threshold_differential.zig"),.target=target,.optimize=.Debug})});
    addPeddle(differential.root_module,b);b.step("threshold-differential","Compare exact optimized and frozen assembled PIT converters").dependOn(&nativeRun(b,differential).step);
    const cg=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/host/native_cga.zig"),.target=target,.optimize=.Debug})});
    addPeddle(cg.root_module,b);b.step("native-cga","Verify BIOS CGA native presentation").dependOn(&nativeRun(b,cg).step);
    const startup = b.addTest(.{ .root_module=b.createModule(.{ .root_source_file=b.path("tests/host/native_timer_startup.zig"), .target=target, .optimize=.Debug }) });
    addPeddle(startup.root_module,b);
    b.step("timer-startup","Private bounded timer activation seams").dependOn(&nativeRun(b,startup).step);
    const irq_pit = b.addTest(.{ .root_module=b.createModule(.{ .root_source_file=b.path("tests/host/irq_pit.zig"), .target=target, .optimize=.Debug }) });
    addPeddle(irq_pit.root_module,b);
    b.step("irq-pit","Private leased IRQ/PIT runtime proof").dependOn(&nativeRun(b,irq_pit).step);
    const future = b.addTest(.{ .root_module=b.createModule(.{ .root_source_file=b.path("tests/host/future_layout.zig"), .target=target, .optimize=.Debug }) });
    addPeddle(future.root_module,b);
    b.step("future-layout","Private five-overlay lease and phase tests").dependOn(&nativeRun(b,future).step);

    const layout = b.addTest(.{ .root_module=b.createModule(.{ .root_source_file=b.path("tests/host/unit_layout.zig"), .target=target, .optimize=.Debug }) });
    addPeddle(layout.root_module,b);
    b.step("unit-layout","Private unit cold lifetime tests").dependOn(&nativeRun(b,layout).step);

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
    b.step("base-full-compile","Compile all base/corpus assertions without executing").dependOn(&b.addInstallFile(tests.getEmittedBin(),"bin/base-full-tests").step);
    const run = nativeRun(b,tests);
    nativeInputs(run, b);
    b.step("test", "Assert actual 6510 assembly behavior in Peddle").dependOn(&run.step);
    // Isolated standalone native clock PRG; explicit VIC script activation
    // tests control flow only. This lane does not use runtime/unit PRG files.
    const clock_probe = b.addTest(.{ .root_module = b.createModule(.{
        .root_source_file = b.path("tests/host/host_clock_probe.zig"),
        .target = target,
        .optimize = .Debug,
    }) });
    addPeddle(clock_probe.root_module, b);
    const run_clock_probe = nativeRun(b,clock_probe);
    b.step("clock-probe", "Verify bounded native CIA/VIC calibration fixture").dependOn(&run_clock_probe.step);
    const overlay = b.addTest(.{ .root_module = b.createModule(.{
        .root_source_file = b.path("tests/host/overlay_integration.zig"),
        .target = target,
        .optimize = .Debug,
    }) });
    addPeddle(overlay.root_module, b);
    const run_overlay = nativeRun(b,overlay);
    b.step("overlays", "Verify FILE/TEXT/INPUT overlays and bounded startup ownership").dependOn(&run_overlay.step);
    const native_runtime = b.addTest(.{ .root_module = b.createModule(.{
        .root_source_file = b.path("tests/host/native_runtime_integration.zig"),
        .target = target,
        .optimize = .Debug,
    }) });
    addPeddle(native_runtime.root_module, b);
    const run_native_runtime=nativeRun(b,native_runtime);nativeInputs(run_native_runtime,b);b.step("native-runtime", "Verify configured native startup, bounded runtime and development commands").dependOn(&run_native_runtime.step);
    const native_dos = b.addTest(.{ .root_module=b.createModule(.{
        .root_source_file=b.path("tests/host/native_dos_boot.zig"),.target=target,.optimize=.Debug,
    }) });
    addPeddle(native_dos.root_module,b);
    b.step("native-dos","Opt-in genuine DOS through configured native startup and bounded runtime").dependOn(&nativeRun(b,native_dos).step);
    b.step("native-dos-compile","Compile the native DOS long lane without executing it").dependOn(&native_dos.step);
    const display = b.addTest(.{ .root_module = b.createModule(.{
        .root_source_file = b.path("tests/host/native_text_integration.zig"),
        .target = target,
        .optimize = .Debug,
    }) });
    addPeddle(display.root_module, b);
    b.step("native-text", "Verify packed fonts, TEXT overlay and bounded VIC setup").dependOn(&nativeRun(b,display).step);
    // Full360KiB source/CRC/failure oracle is deliberately opt-in.
    const image_import = b.addTest(.{ .root_module = b.createModule(.{
        .root_source_file = b.path("tests/host/image_import.zig"),
        .target = target,
        .optimize = .Debug,
    }) });
    addPeddle(image_import.root_module, b);
    const run_image_import = nativeRun(b,image_import);
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
    const run_boot = nativeRun(b,boot);
    nativeInputs(run_boot, b);
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
    const run_profile = nativeRun(b,profile);
    b.step("profile-cpu", "Measure verified actual-assembly CPU workloads in Peddle").dependOn(&run_profile.step);
}
