const std=@import("std");pub fn build(b:*std.Build)void{
 const t=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("coordinator_actual.zig"),.target=b.standardTargetOptions(.{}),.optimize=.ReleaseFast})});
 t.root_module.addIncludePath(b.path("tests/floppy_export"));t.root_module.addIncludePath(b.path("tests/host"));t.root_module.addIncludePath(b.path("third_party/peddle/Peddle"));
 t.root_module.addCSourceFiles(.{.files=&.{"tests/floppy_export/bridge.cpp","third_party/peddle/Peddle/Peddle.cpp","third_party/peddle/Peddle/PeddleDebugger.cpp","third_party/peddle/Peddle/PeddleDisassembler.cpp","third_party/peddle/Peddle/StrWriter.cpp"},.flags=&.{"-std=c++20","-O2","-Wno-unused-parameter","-Wno-unused-variable"}});t.root_module.link_libcpp=true;
 const run=b.addRunArtifact(t);run.setCwd(b.path("."));run.has_side_effects=true;run.addFileInput(b.path("build/setup.prg"));run.addFileInput(b.path("build/setup.labels"));run.addFileInput(b.path("build/SETUP.FAT"));b.step("test","Actual native directorybrowser").dependOn(&run.step);b.step("compile","Compile pinned nativeassertions").dependOn(&b.addInstallFile(t.getEmittedBin(),"bin/coordinator-tests").step);
}
