#!/usr/bin/env python3
"""Compile and exercise the four actual cold DOS phases against a faulting DOS."""
from pathlib import Path
import subprocess
import tempfile
root = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix="readyfs-udos-files-") as tmp:
    flags = ["cc", "-std=c99", "-Wall", "-Wextra", "-D__fastcall__=",
             "-I"+str(root/"build_support/readyfs_host_include")]
    objects = []
    for phase in range(1, 5):
        obj = str(Path(tmp)/f"phase{phase}.o")
        subprocess.run(flags+[f"-DRF_UDOS_PHASE={phase}", "-c",
            str(root/"src/apps/readyfs/readyfs_udos_files.c"), "-o", obj], check=True)
        objects.append(obj)
    overlay = (root/"src/apps/readyfs/readyfs_overlay.c").read_text()
    def function(name):
        start = overlay.rfind("\n", 0, overlay.index(name+"(")) + 1
        opening = overlay.index("{", start)
        end = opening + 1
        depth = 1
        while depth:
            depth += (overlay[end] == "{") - (overlay[end] == "}")
            end += 1
        return overlay[start:end]
    gateway = Path(tmp)/"gateway.inc"
    gateway.write_text(function("udos_phase")+"\n"+function("readyfs_overlay_udos"))
    flags += ["-I"+tmp]
    exe = str(Path(tmp)/"test")
    subprocess.run(flags+[str(root/"build_support/readyfs_udos_files_test.c")]+objects+["-o", exe], check=True)
    subprocess.run([exe], check=True)
