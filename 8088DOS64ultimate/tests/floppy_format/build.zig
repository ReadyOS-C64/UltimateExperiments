const std=@import("std");pub fn build(b:*std.Build)void{
 const t=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("actual.zig"),.target=b.standardTargetOptions(.{}),.optimize=.ReleaseFast})});
 t.root_module.addIncludePath(b.path("model/tests/floppy_export"));t.root_module.addIncludePath(b.path("model/tests/host"));t.root_module.addIncludePath(b.path("work/third_party/peddle/Peddle"));
 t.root_module.addCSourceFiles(.{.files=&.{"model/tests/floppy_export/bridge.cpp","work/third_party/peddle/Peddle/Peddle.cpp","work/third_party/peddle/Peddle/PeddleDebugger.cpp","work/third_party/peddle/Peddle/PeddleDisassembler.cpp","work/third_party/peddle/Peddle/StrWriter.cpp"},.flags=&.{"-std=c++20","-O2","-Wno-unused-parameter","-Wno-unused-variable"}});t.root_module.link_libcpp=true;
 const run=b.addRunArtifact(t);run.setCwd(b.path("."));run.has_side_effects=true;run.addFileInput(b.path("work/build/dos64.prg"));run.addFileInput(b.path("work/build/dos64.labels"));b.step("test","Actual FORMAT1 runtime").dependOn(&run.step);b.step("compile","Compile FORMAT assertions").dependOn(&b.addInstallFile(t.getEmittedBin(),"bin/format-tests").step);
}
