const std=@import("std");
pub fn add(b:*std.Build,target:std.Build.ResolvedTarget)void{
 const t=b.addTest(.{.root_module=b.createModule(.{.root_source_file=b.path("tests/iec_standalone/actual_assembly.zig"),.target=target,.optimize=.Debug})});
 t.root_module.addIncludePath(b.path("tests/iec_standalone"));t.root_module.addIncludePath(b.path("tests/host"));t.root_module.addIncludePath(b.path("third_party/peddle/Peddle"));
 t.root_module.addCSourceFiles(.{.files=&.{"tests/iec_standalone/bridge.cpp","third_party/peddle/Peddle/Peddle.cpp","third_party/peddle/Peddle/PeddleDebugger.cpp","third_party/peddle/Peddle/PeddleDisassembler.cpp","third_party/peddle/Peddle/StrWriter.cpp"},.flags=&.{"-std=c++20","-O2","-Wno-unused-parameter","-Wno-unused-variable"}});t.root_module.link_libcpp=true;
 const r=b.addRunArtifact(t);r.setCwd(b.path("."));b.step("iec-standalone","Opt-in actual standalone assembly with explicit mock KERNAL API").dependOn(&r.step);
}
