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
    # Exercise the actual resident cleanup gate. A failed target2 CLOSE must
    # not cause target1 to delete a stage which may still have an open handle.
    resident=(root/'src/apps/readyfs/readyfs.c').read_text()
    start=resident.index('static unsigned char delete_stream(')
    opening=resident.index('{',start);end=opening+1;depth=1
    while depth:
        depth+=(resident[end]=='{')-(resident[end]=='}');end+=1
    cleanup=Path(tmp)/'cleanup.c'
    cleanup.write_text(r'''
#include <assert.h>
#include "readyfs_files.h"
#include "readyfs_result.h"
#define READYFS_OVERLAY_RUNTIME
#define RF_FOUND(x) ((x)==RF_LOOKUP_FOUND)
#define RF_MISSING(x) ((x)==RF_LOOKUP_MISSING)
static unsigned char udos_open_targets,last_result;
static unsigned int lookups,deletes;
static unsigned char stream_uses_iec(ReadyFsStream *s){return s->path.endpoint==RF_EP_IEC;}
static unsigned char softiec_enter_parent(ReadyFsStream *s){(void)s;return 1;}
static unsigned char native_file(ReadyFsStream *s,void *other,unsigned char op){(void)s;(void)other;(void)op;return 1;}
static unsigned char stream_find_type(ReadyFsStream *s){(void)s;return 0;}
static const char *udos_find_leaf(ReadyFsStream *s,unsigned char target){(void)s;assert(target==1);++lookups;return "stage";}
static unsigned char uci_call(unsigned char target,unsigned char op,const char *name){assert(target==1 && op==9 && name);++deletes;return 1;}
static unsigned char uci_status_ok(unsigned char target){assert(target==1);return 1;}
'''+resident[start:end]+r'''
int main(void){ReadyFsStream s={0};s.path.endpoint=RF_EP_ULTIMATE;
for(udos_open_targets=1;udos_open_targets<=3;++udos_open_targets){
last_result=0;assert(!delete_stream(&s) && last_result==RF_RESULT_IO);assert(!lookups && !deletes);}
udos_open_targets=0;assert(delete_stream(&s) && lookups==1 && deletes==1);return 0;}
''')
    cleanup_exe=str(Path(tmp)/'cleanup')
    subprocess.run(flags+['-I'+str(root/'src/apps/readyfs'),str(cleanup),'-o',cleanup_exe],check=True)
    subprocess.run([cleanup_exe],check=True)
    print('ReadyFS resident cleanup: PASS (uncertain DOS handles preserve stage)')
