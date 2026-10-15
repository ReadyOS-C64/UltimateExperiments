const std=@import("std");
// Included by root build.zig, reuses its already resolved target.
pub fn add(b:*std.Build,target:std.Build.ResolvedTarget) void {
 const t=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/floppy_export/actual_assembly.zig"),.target=target,.optimize=.Debug})});
 t.root_module.addIncludePath(b.path("tests/floppy_export"));
 t.root_module.addIncludePath(b.path("tests/host"));
 t.root_module.addIncludePath(b.path("third_party/peddle/Peddle"));
 t.root_module.addCSourceFiles(.{.files=&.{"tests/floppy_export/bridge.cpp","third_party/peddle/Peddle/Peddle.cpp","third_party/peddle/Peddle/PeddleDebugger.cpp","third_party/peddle/Peddle/PeddleDisassembler.cpp","third_party/peddle/Peddle/StrWriter.cpp"},.flags=&.{"-std=c++20","-O2","-Wno-unused-parameter","-Wno-unused-variable"}});
 t.root_module.link_libcpp=true;
 const run=b.addRunArtifact(t);run.setCwd(b.path("."));
 b.step("floppy-export","Opt-in standalone actual6502 native floppy export/reopen verification").dependOn(&run.step);
}
