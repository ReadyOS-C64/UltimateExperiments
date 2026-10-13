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

    # The real resident wrapper distinguishes quiet FIND absence from a READ
    # failure. Missing contained-image STAT previously returned with no output
    # and status OK even though the cold lookup correctly returned MISSING.
    start=resident.index('static unsigned char udos_file(')
    opening=resident.index('{',start);end=opening+1;depth=1
    while depth:
        depth+=(resident[end]=='{')-(resident[end]=='}');end+=1
    required=Path(tmp)/'required_read.c'
    required.write_text(r'''
#include <assert.h>
#include <string.h>
#include "readyfs_udos_files.h"
#include "readyfs_result.h"
#include "readyfs_console.h"
static ReadyFsUdosFilesCall udos_call;
static unsigned char last_result,returned,result_status;
static unsigned int messages;
static void udos_setup(ReadyFsStream *s,unsigned char t,unsigned char op){
udos_call.stream=s;udos_call.target=t;udos_call.operation=op;}
static unsigned char readyfs_overlay_udos(ReadyFsUdosFilesCall *c){
assert(c==&udos_call);last_result=result_status;return returned;}
static void cputs(const char *s){assert(!strcmp(s,RF_ERROR "not found\r\n"));++messages;}
'''+resident[start:end]+r'''
int main(void){ReadyFsStream s={0};
returned=RF_LOOKUP_MISSING;result_status=RF_RESULT_OK;
assert(udos_file(&s,1,RF_UDOS_FIND)==RF_LOOKUP_MISSING && !messages && last_result==RF_RESULT_OK);
assert(udos_file(&s,1,RF_UDOS_READ)==RF_LOOKUP_MISSING && messages==1 && last_result==RF_RESULT_NOT_FOUND);
returned=RF_LOOKUP_ERROR;result_status=RF_RESULT_IO;
assert(udos_file(&s,1,RF_UDOS_READ)==RF_LOOKUP_ERROR && messages==1 && last_result==RF_RESULT_IO);
returned=RF_LOOKUP_FOUND;result_status=RF_RESULT_OK;
assert(udos_file(&s,1,RF_UDOS_READ)==RF_LOOKUP_FOUND && messages==1 && last_result==RF_RESULT_OK);
return 0;}
''')
    required_exe=str(Path(tmp)/'required_read')
    subprocess.run(flags+['-I'+str(root/'src/apps/readyfs'),str(required),'-o',required_exe],check=True)
    subprocess.run([required_exe],check=True)
    print('ReadyFS resident READ: PASS (missing reads report NOT_FOUND; FIND stays quiet)')
