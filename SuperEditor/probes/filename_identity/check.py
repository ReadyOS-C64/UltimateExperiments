"""Execute exact pinned VICE3.10 CBMDOS parser/name comparison in isolation.

No emulator, disk, production assembly or shared build is touched. The only
substitutions are uint types, disabled logging and libc malloc/calloc aliases.
GPL VICE sources remain unmodified under the caller-supplied isolated directory.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SOURCES={
 'cbmdos.c':'04d188ed716d7b264f231f01e2f47199f885aa45fb037a55dfc577feaf4d51ea',
 'cbmdos.h':'5e29e6486ef91ab2c8f025e91e5b9708ce3ed6c2d8c4c866f041fd60398ca5d8',
 'vdrive-iec.c':'5a13de2d32da96d09d5c499965a796cf9dd8e51648d7531af74cb3bc324d41ba',
 'vdrive-dir.c':'b59da44235bb932e456712e40c5f831b3adf416bf205802631130cfe22e00189',
 'vdrive-command.c':'2f0a9130ccf8d25ab1f4274b70ad657e14633d3033f3ccfc32baec5dcbc27ffe',
}
BASE='https://raw.githubusercontent.com/VICE-Team/svn-mirror/3.10.0/vice/src/'

class Parse(C.Structure):
 _fields_=[('full',C.c_void_p),('fulllength',C.c_uint),('secondary',C.c_uint),
           ('mode',C.c_int),('drive',C.c_int),
           ('command',C.c_void_p),('commandlength',C.c_uint),
           ('abbrv',C.c_void_p),('abbrvlength',C.c_uint),
           ('path',C.c_void_p),('pathlength',C.c_uint),
           ('file',C.c_void_p),('filelength',C.c_uint),
           ('more',C.c_void_p),('morelength',C.c_uint),
           ('readmode',C.c_uint),('filetype',C.c_uint),
           ('recordlength',C.c_uint),('colon',C.c_uint)]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-dir',type=Path,required=True)
 args=ap.parse_args();folder=args.source_dir.resolve()
 for name,sha in SOURCES.items():
  assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==sha,('Unpinned source',name)
 out=folder/'exact-parser';inc=out/'headers';inc.mkdir(parents=True,exist_ok=True)
 (inc/'vice.h').write_text('#include <stdint.h>\n#include <stddef.h>\n')
 (inc/'types.h').write_text('#include <stdint.h>\n')
 (inc/'lib.h').write_text('#include <stdlib.h>\n#define lib_malloc malloc\n#define lib_calloc calloc\n')
 (inc/'log.h').write_text('/* DEBUG_CBMDOS disabled in the unmodified source. */\n')
 library=out/('cbmdos.dylib' if sys.platform=='darwin' else 'cbmdos.so')
 command=['clang','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared',
          '-fPIC','-I'+str(inc),'-I'+str(folder),str(folder/'cbmdos.c'),'-o',str(library)]
 subprocess.run(command,check=True,capture_output=True,text=True)
 lib=C.CDLL(str(library));lib.cbmdos_command_parse_plus.argtypes=[C.POINTER(Parse)]
 lib.cbmdos_command_parse_plus.restype=C.c_uint
 lib.cbmdos_dir_slot_create.argtypes=[C.c_void_p,C.c_uint];lib.cbmdos_dir_slot_create.restype=C.c_void_p
 lib.cbmdos_parse_wildcard_compare.argtypes=[C.c_void_p,C.c_void_p]
 lib.cbmdos_parse_wildcard_compare.restype=C.c_uint
 libc=C.CDLL(None);libc.free.argtypes=[C.c_void_p]
 def parse(data,mode=2):
  raw=C.create_string_buffer(data);p=Parse(full=C.cast(raw,C.c_void_p),fulllength=len(data),secondary=2,mode=mode,drive=-1)
  rc=lib.cbmdos_command_parse_plus(C.byref(p))
  result=dict(rc=rc,drive=p.drive,readmode=p.readmode,filetype=p.filetype)
  for field in ['command','abbrv','path','file','more']:
   ptr=getattr(p,field);length=getattr(p,field+'length')
   result[field]=C.string_at(ptr,length) if ptr else b''
   if ptr:libc.free(ptr)
  return result
 def slot(name):
  raw=C.create_string_buffer(name);ptr=lib.cbmdos_dir_slot_create(raw,len(name))
  data=C.string_at(ptr,16);libc.free(ptr);return data
 def matches(a,b):
  return bool(lib.cbmdos_parse_wildcard_compare(C.create_string_buffer(slot(a)),C.create_string_buffer(slot(b))))
 aliases=[]
 for a,b in [(b'NAME',b'NAME\xA0'),(b'NAME',b'NAME\xA0SUFFIX'),
             (b'NAME\xA0ONE',b'NAME\xA0TWO'),(b'\xA0',b'\xA0HIDDEN')]:
  assert a!=b and matches(a,b) and matches(b,a)
  aliases.append(dict(a=a.hex(),b=b.hex(),same_raw_slot=slot(a)==slot(b),both_directions_match=True))
 accepted=[];checks=0
 forbidden=set(b'"*,/:=?')|set(range(32))|set(range(127,160))|{32,160}
 for byte in range(256):
  if byte in forbidden:continue
  name=bytes([byte]);accepted.append(byte)
  for mode in [b'R',b'W']:
   p=parse(b'0:'+name+b',S,'+mode)
   assert p['rc']==0 and p['file']==name and p['command']==p['path']==b''
   assert p['drive']==0 and p['filetype']==1 and p['readmode']==(mode==b'W')
   checks+=1
 # All16 positions, and all possible companion bytes, prove @ stays literal
 # under the actual forced0: prefix. No replace-command field is produced.
 at_checks=0
 for at in range(16):
  for byte in accepted:
   name=bytes([byte])*at+b'@'+bytes([byte])*(15-at)
   p=parse(b'0:'+name+b',S,W')
   assert p['rc']==0 and p['command']==b'' and p['file']==name and p['readmode']==1
   at_checks+=1
 replace=parse(b'@0:NAME,S,W')
 assert replace['command']==b'@' and replace['file']==b'NAME' and replace['readmode']==1
 # DOS rename/scratch also keep @ literal after their own fixed command
 # prefixes; the second rename parse starts at '=source', exactly as vdrive.
 for name in [b'@',b'@NAME',b'NAME@',b'A$#@B',bytes([0xA1,0xC1,0xFF])]:
  p=parse(b'R0:'+name+b'=SOURCE',1);assert p['command']==b'R' and p['file']==name
  p=parse(b'='+name,1);assert p['command']==b'=' and p['file']==name
  p=parse(b'S0:'+name,1);assert p['command']==b'S' and p['file']==name
 for a,b in [(b'a',b'A'),(b'A',b'\xC1'),(b'\xA1',b'\xA2'),(b'\xFE',b'\xFF')]:assert not matches(a,b)
 result=dict(ok=True,version='VICE3.10/tag3.10.0',sources_sha256=SOURCES,
             official_source_base=BASE,compile_command=command,
             A0_alias_examples=aliases,accepted_single_byte_names=len(accepted),
             read_write_parser_checks=checks,literal_at_position_checks=at_checks,
             unprefixed_replace_control=True,
             recommendation='Reject PETSCII A0 anywhere; preserve @ under forced0: and other unambiguous native bytes',
             scope='Exact matching-release parser and directory-name comparison; no running VICE/native IEC or real-drive claim')
 (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))

if __name__=='__main__':main()
