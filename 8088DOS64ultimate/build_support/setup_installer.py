#!/usr/bin/env python3
"""Build native SETUP and its FAT/PUB overlays without running the hardware."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    data=path.read_bytes()
    return {'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}

def toolchain():
    result={name:shutil.which(os.environ.get('DOS64_'+name.upper(),name))for name in ['cc65','ca65','ld65']}
    if not all(result.values()):raise RuntimeError('cc65, ca65 and ld65 are required')
    result={name:str(Path(value).resolve())for name,value in result.items()}
    override=os.environ.get('DOS64_CC65_LIB')
    choices=[Path(override)]if override else[Path(result['cc65']).parent.parent/'share/cc65/lib/none.lib',Path('/opt/homebrew/share/cc65/lib/none.lib'),Path('/usr/share/cc65/lib/none.lib')]
    library=next((p for p in choices if p.is_file()),None)
    if library is None:raise RuntimeError('Set DOS64_CC65_LIB to the cc65 none.lib path')
    result['library']=str(library.resolve())
    return result

def verify(record):
    for name,want in record.items():
        if digest(Path(name))!=want:raise RuntimeError('Build input changed: '+name)

def run(command,work,commands):
    commands.append([str(x)for x in command])
    subprocess.run(commands[-1],cwd=work,check=True,stdin=subprocess.DEVNULL,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))

def stage(work,record):
    for name,relative in SOURCES.items():
        source=ROOT/relative;target=work/name;target.parent.mkdir(parents=True,exist_ok=True)
        record[str(source)]=digest(source);shutil.copyfile(source,target)
        if digest(target)!=record[str(source)]:raise RuntimeError('Source staging mismatch: '+name)
        record[str(target)]=digest(target) # pin the bytes the compiler actually reads

def read_labels(path):
    return {s.split()[2].lstrip('.'):int(s.split()[1],16)for s in path.read_text().splitlines()if s.startswith('al ')}

def label_rows(path):
    return sorted((s.split()[2],int(s.split()[1],16))for s in path.read_text().splitlines()if s.startswith('al '))

def memory_check(build):
    l=read_labels(build/'setup.labels')
    def end(name):return l['__'+name+'_RUN__']+l['__'+name+'_SIZE__']
    checks={
        'real_SYS_bootstrap':l['setup_boot']==0x080d,
        'UI_at6000':l['__UI_CODE_RUN__']==0x6000,
        'UI_RO_contiguous':l['__UI_RO_RUN__']==end('UI_CODE'),
        'HIGH_serialized_after_UI':l['__HIGH_CODE_LOAD__']==end('UI_RO'),
        'AUX_serialized_after_HIGH':l['__AUX_CODE_LOAD__']==l['__HIGH_CODE_LOAD__']+l['__HIGH_CODE_SIZE__'],
        'AUX_RO_serialized':l['__AUX_RO_LOAD__']==l['__AUX_CODE_LOAD__']+l['__AUX_CODE_SIZE__'],
        'UI_BSS_after_serialized_code':l['__UIBSS_RUN__']>=l['__AUX_RO_LOAD__']+l['__AUX_RO_SIZE__'],
        'UI_fits':end('UIBSS')<=0xb000,
        'FAT_fits':end('FAT_RO')<=0xb000,
        'PUB_fits':end('PUBBSS')<=0xb000,
        'STATE_fits':l['__BSS_RUN__']==0xb000 and end('BSS')<=0xc000,
        'HIGH_state_fits':l['__HIGHBSS_RUN__']==0xe000 and end('HIGHBSS')<=0xf700,
        'HIGH_code_vectors_disjoint':l['__HIGH_CODE_RUN__']==0xf700 and end('HIGH_CODE')<=0xfffa,
        'AUX_run_bounds':l['__AUX_CODE_RUN__']==0xc3a0 and end('AUX_RO')<=0xc800,
    }
    if not all(checks.values()):raise RuntimeError('SETUP memory contract failed: '+json.dumps(checks))
    segments={}
    for line in (build/'setup.map').read_text().splitlines():
        m=re.fullmatch(r'([A-Z][A-Z0-9_]*)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+[0-9A-F]+',line.strip())
        if m:segments[m[1]]={'start':int(m[2],16),'end':int(m[3],16),'bytes':int(m[4],16)}
    if segments['UCIBUFFER']!={'start':0xc000,'end':0xc39f,'bytes':928}:raise RuntimeError('Compact UCI buffer layout changed')
    if segments['DATA']['end']>=0x6000:raise RuntimeError('Resident SETUP exceeds6000')
    return {'checks':checks,'segments':segments,'free':{'resident':0x6000-segments['DATA']['end']-1,'FAT':0xb000-end('FAT_RO'),'UI_stage':0xb000-end('UIBSS'),'PUB':0xb000-end('PUBBSS'),'HIGH_code':0xfffa-end('HIGH_CODE'),'HIGH_state':0xf700-end('HIGHBSS'),'AUX':0xc800-end('AUX_RO')}}

SOURCES={'bindings.s': 'tools/setup/app/bindings.s', 'bulk_context.c': 'tools/setup/app/bulk_context.c', 'bulk_context.h': 'tools/setup/app/bulk_context.h', 'bulk_reu.c': 'tools/setup/app/bulk_reu.c', 'bulk_reu.h': 'tools/setup/app/bulk_reu.h', 'bulk_uci.h': 'tools/native/bulk_uci.h', 'compact.cfg': 'tools/setup/app/compact.cfg', 'context_bindings.s': 'tools/setup/app/context_bindings.s', 'coordinator.s': 'tools/setup/app/coordinator.s', 'coordinator_capture.c': 'tools/setup/app/coordinator_capture.c', 'coordinator_capture.h': 'tools/setup/app/coordinator_capture.h', 'coordinator_internal.h': 'tools/setup/app/coordinator_internal.h', 'coordinator_internal.inc': 'tools/setup/app/coordinator_internal.inc', 'crc32.h': 'tools/native/crc32.h', 'crc32.s': 'tools/native/crc32.s', 'directory_browser.c': 'tools/setup/app/directory_browser.c', 'directory_browser.h': 'tools/setup/app/directory_browser.h', 'existing_c.inc': 'tools/setup/app/existing_c.inc', 'fat_prepare.c': 'tools/setup/app/fat_prepare.c', 'fat_prepare.h': 'tools/setup/app/fat_prepare.h', 'fat_worker.s': 'tools/setup/app/fat_worker.s', 'files.inc': 'include/files.inc', 'files.s': 'tools/setup/app/files.s', 'install_config.c': 'tools/setup/app/install_config.c', 'install_config.h': 'tools/setup/app/install_config.h', 'install_writer.c': 'tools/setup/app/install_writer.c', 'install_writer.h': 'tools/setup/app/install_writer.h', 'lease_context.c': 'tools/setup/app/lease_context.c', 'native_fat.c': 'tools/setup/app/native_fat.c', 'native_fat.h': 'tools/setup/app/native_fat.h', 'overlay_bindings.s': 'tools/setup/app/overlay_bindings.s', 'overlay_manifest.s': 'tools/setup/app/overlay_manifest.s', 'platform.c': 'tools/native/platform.c', 'platform.h': 'tools/native/platform.h', 'platform.s': 'tools/native/platform.s', 'pub_codec.c': 'tools/setup/app/pub_codec.c', 'pub_config.c': 'tools/setup/app/pub_config.c', 'pub_config_original.h': 'tools/setup/app/pub_config_original.h', 'pub_config_prefix.h': 'tools/setup/app/pub_config_prefix.h', 'pub_crc_adapter.c': 'tools/setup/app/pub_crc_adapter.c', 'publish_assets.c': 'tools/setup/app/publish_assets.c', 'publish_assets.h': 'tools/setup/app/publish_assets.h', 'publish_scratch.c': 'tools/setup/app/publish_scratch.c', 'publish_scratch.h': 'tools/setup/app/publish_scratch.h', 'publish_worker.c': 'tools/setup/app/publish_worker.c', 'publish_worker.h': 'tools/setup/app/publish_worker.h', 'publish_worker_asm.s': 'tools/setup/app/publish_worker_asm.s', 'raw_output.c': 'tools/setup/app/raw_output.c', 'raw_output.h': 'tools/setup/app/raw_output.h', 'selection_capsule.c': 'tools/setup/app/selection_capsule.c', 'selection_capsule.h': 'tools/setup/app/selection_capsule.h', 'setup_cooperate.c': 'tools/setup/app/setup_cooperate.c', 'setup_cooperate.h': 'tools/setup/app/setup_cooperate.h', 'setup_copy.s': 'tools/setup/app/setup_copy.s', 'setup_dma.s': 'tools/setup/app/setup_dma.s', 'setup_io.c': 'tools/setup/app/setup_io.c', 'setup_io.h': 'tools/setup/app/setup_io.h', 'setup_overlay.c': 'tools/setup/app/setup_overlay.c', 'setup_overlay.h': 'tools/setup/app/setup_overlay.h', 'setup_select.c': 'tools/setup/app/setup_select.c', 'setup_select.h': 'tools/setup/app/setup_select.h', 'setup_ui_run.c': 'tools/setup/app/setup_ui_run.c', 'setup_ui_run.h': 'tools/setup/app/setup_ui_run.h', 'shared/abi.inc': 'include/abi.inc', 'shared/reu.inc': 'include/reu.inc', 'shared/reu.s': 'tools/setup/app/shared/reu.s', 'source_load.c': 'tools/setup/app/source_load.c', 'source_load.h': 'tools/setup/app/source_load.h', 'start_template.c': 'tools/setup/start_template.c', 'start_template.h': 'tools/setup/start_template.h', 'startup.s': 'tools/setup/app/startup.s', 'startup_close.s': 'tools/native/startup_close.s', 'startup_glue.s': 'tools/setup/app/startup_glue.s', 'uci.inc': 'include/uci.inc', 'uci.s': 'tools/setup/app/uci.s', 'ui_fixture.c': 'tools/setup/app/selection_abi.c', 'validator_crc.c': 'tools/native/validator_crc.c', 'validator_crc.h': 'tools/native/validator_crc.h'}
C_NAMES=['native_fat', 'bulk_context', 'install_config', 'directory_browser', 'lease_context', 'platform', 'setup_io', 'install_writer', 'setup_overlay', 'setup_select', 'ui_fixture', 'selection_capsule', 'raw_output', 'source_load', 'fat_prepare', 'pub_codec', 'pub_crc_adapter', 'start_template', 'publish_assets', 'publish_worker', 'publish_scratch', 'setup_ui_run', 'coordinator_capture', 'setup_cooperate']
ASM_NAMES=['startup', 'bindings', 'context_bindings', 'uci', 'files', 'setup_dma', 'crc32', 'overlay_manifest', 'startup_close', 'startup_glue', 'overlay_bindings', 'coordinator', 'fat_worker', 'publish_worker_asm', 'setup_copy', 'platform_asm', 'reu']
PUB_NAMES=['raw_output','pub_codec','pub_crc_adapter','start_template','publish_assets','publish_worker','publish_scratch']
FAT_NAMES=['native_fat','fat_prepare']
UI_NAMES=['install_config','directory_browser','lease_context','setup_select','ui_fixture','source_load','setup_ui_run','coordinator_capture']
HIGH_BSS_NAMES=['directory_browser','platform','setup_io','install_writer','selection_capsule','source_load']
UI_BSS_NAMES=['install_config','setup_select','ui_fixture','selection_capsule','raw_output','setup_ui_run']
DEFINES={'source_load':['DOS64_SETUP_SMALL_UCI=1'],'bulk_context':['DOS64_SETUP_WRITER_CLEANUP=1'],'install_writer':['DOS64_SETUP_WRITER_CLEANUP=1'],'raw_output':['DOS64_SETUP_PUBLICATION=1'],'publish_assets':['DOS64_SETUP_PUBLICATION=1'],'setup_io':['DOS64_SETUP_COOPERATIVE=1'],'install_config':['D64_CONFIG_PATH_ONLY=1']}

def metadata(B,ui,fat,pub,pub_length):
 h=bytearray(64);h[:4]=b'D64F';h[4:8]=bytes([1,2,64,0]);struct.pack_into('<IHHIII',h,8,len(fat),0x6000,0x5000,zlib.crc32(fat),zlib.crc32(ui),zlib.crc32(ui.ljust(0x5000,b'\0')));h[28:60]=hashlib.sha256(fat).digest();struct.pack_into('<I',h,60,zlib.crc32(h[:60]))
 text='_so_asset_header:\n.byte '+','.join(str(x)for x in h)+'\n'
 for name,value,size in [('ui_bytes',len(ui),2),('fat_bytes',len(fat),2),('asset_bytes',len(fat)+64,2),('ui_crc',zlib.crc32(ui),4),('ui_full_crc',zlib.crc32(ui.ljust(0x5000,b'\0')),4),('fat_crc',zlib.crc32(fat),4)]:text+='_so_'+name+':\n.'+('word'if size==2 else'dword')+' '+str(value)+'\n'
 pub_header=bytearray(h);pub_header[5]=3;struct.pack_into('<I',pub_header,8,len(pub));struct.pack_into('<I',pub_header,16,zlib.crc32(pub));pub_header[28:60]=hashlib.sha256(pub).digest();struct.pack_into('<I',pub_header,60,zlib.crc32(pub_header[:60]))
 text+='_so_publish_header:\n.byte '+','.join(str(x)for x in pub_header)+'\n'
 for name,value,size in [('publish_bytes',pub_length,2),('publish_asset_bytes',len(pub)+64,2),('publish_crc',zlib.crc32(pub[:pub_length]),4),('publish_full_crc',zlib.crc32(pub),4)]:text+='_so_'+name+':\n.'+('word'if size==2 else'dword')+' '+str(value)+'\n'
 (B/'overlay_metadata.inc').write_text(text);return bytes(h),bytes(pub_header)

def build_native(work,t):
    commands=[];B=work/'build';B.mkdir()
    # Fixed-size placeholders do not affect placement. Actual phase bytes are
    # measured below and replace these fields before the second link.
    metadata(B,bytes(6630),bytes(18587),bytes(0x5000),16)
    for n in C_NAMES:
        output=n+'_c'if n=='platform'else n
        phase='PUB'if n in PUB_NAMES else'FAT'if n in FAT_NAMES else'UI'if n in UI_NAMES else None
        opts=['--code-name',phase+'_CODE','--rodata-name',phase+'_RO']if phase else[]
        opts += [item for flag in DEFINES.get(n,[])for item in ['-D',flag]]
        bss='PUBBSS'if n in PUB_NAMES else'HIGHBSS'if n in HIGH_BSS_NAMES else'UIBSS'if n in UI_BSS_NAMES else None
        run([t['cc65'],'-O','-t','none','--cpu','6502',*opts,*(['--bss-name',bss]if bss else[]),'-I',work,'-o',B/(output+'.s'),work/(n+'.c')],work,commands)
        run([t['ca65'],'-g','-D','DOS64_FILES_INFO=1','-I',work,'-I',work/'shared','-o',B/(output+'.o'),B/(output+'.s')],work,commands)
    for n in ASM_NAMES:
        source=work/'platform.s'if n=='platform_asm'else work/'shared/reu.s'if n=='reu'else work/(n+'.s')
        run([t['ca65'],'-g','-D','DOS64_FILES_INFO=1',*(['-D','DOS64_SETUP_SMALL_UCI=1']if n in ['uci','files']else[]),'-I',work,'-I',work/'shared','-o',B/(n+'.o'),source],work,commands)
    objects=[B/(n+'.o')for n in ASM_NAMES+[n+'_c'if n=='platform'else n for n in C_NAMES]]
    link=[t['ld65'],'-C',work/'compact.cfg','-o',B/'setup.prg','-Ln',B/'setup.labels','-m',B/'setup.map',*objects,t['library']]
    run(link,work,commands);layout=memory_check(B);l=read_labels(B/'setup.labels')
    ui_length=sum(l.get('__'+n+'_SIZE__',0)for n in ['UI_CODE','UI_RO','HIGH_CODE','AUX_CODE','AUX_RO'])
    ui=(B/'setup.prg').read_bytes()[0x6000-0x801+2:0x6000-0x801+2+ui_length]
    fat=(B/'fat-overlay.bin').read_bytes();pub_length=l['__PUB_CODE_SIZE__']+l.get('__PUB_RO_SIZE__',0);pub=(B/'publish-overlay.bin').read_bytes().ljust(0x5000,b'\0')
    if len(ui)!=ui_length or ui_length>0x5000 or len(fat)>0x5000 or len(pub)!=0x5000 or any(pub[pub_length:]):raise RuntimeError('Invalid measured phase payload')
    header,pub_header=metadata(B,ui,fat,pub,pub_length)
    run([t['ca65'],'-g','-I',work,'-o',B/'overlay_manifest.o',work/'overlay_manifest.s'],work,commands);run(link,work,commands)
    if (B/'setup.prg').read_bytes()[0x6000-0x801+2:0x6000-0x801+2+ui_length]!=ui or(B/'fat-overlay.bin').read_bytes()!=fat or(B/'publish-overlay.bin').read_bytes()!=pub[:pub_length]:raise RuntimeError('Metadata relink changed phase bytes')
    data=(B/'setup.prg').read_bytes()
    if data[:2]!=b'\x01\x08' or len(data)!=0x6000-0x801+2+ui_length:raise RuntimeError('Native PRG load/length changed')
    (B/'SETUP.FAT').write_bytes(header+fat);(B/'SETUP.PUB').write_bytes(pub_header+pub)
    return commands,layout

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=ROOT/'build/setup-installer',help='Output folder; each build uses a fresh work directory')
    p.add_argument('--verify-against',type=Path,help='Development-only comparison with a qualified native build folder')
    args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    t=toolchain();record={str(Path(x).resolve()):digest(Path(x).resolve())for x in [*t.values(),sys.executable,__file__]}
    work=Path(tempfile.mkdtemp(prefix='source-',dir=out));phase='source';published=[]
    try:
        (out/'RESULT.json').write_text(json.dumps({'status':'building','work':str(work)},indent=2)+'\n')
        stage(work,record)
        if args.verify_against:
            reference=args.verify_against.resolve()
            for name in ['setup.prg','SETUP.FAT','SETUP.PUB','fat-overlay.bin','publish-overlay.bin','overlay_metadata.inc','setup.labels']:
                record[str(reference/name)]=digest(reference/name)
        (work/'SOURCE_BEFORE.json').write_text(json.dumps(record,indent=2)+'\n')
        phase='compile';commands,layout=build_native(work,t);verify(record)
        built=work/'build';comparisons={}
        if args.verify_against:
            phase='reference comparison'
            for name in ['setup.prg','SETUP.FAT','SETUP.PUB','fat-overlay.bin','publish-overlay.bin','overlay_metadata.inc']:
                comparisons[name]=digest(built/name)==digest(reference/name)
            comparisons['label_addresses']=label_rows(built/'setup.labels')==label_rows(reference/'setup.labels')
            if not all(comparisons.values()):raise RuntimeError('Qualified build comparison failed: '+json.dumps(comparisons))
        products={str(f.relative_to(built)):digest(f)for f in sorted(built.rglob('*'))if f.is_file()}
        result={'status':'passed','physical':False,'DOS_cold_boot_qualified':False,'complete_install_UI_scope_qualified':False,'work':str(work),'source_inputs':record,'commands':commands,'products':products,'memory':layout,'reference_comparison':comparisons}
        phase='prepare bundle';bundle=work/'bundle';bundle.mkdir()
        names=[('SETUP.PRG','setup.prg'),('SETUP.FAT','SETUP.FAT'),('SETUP.PUB','SETUP.PUB'),('SETUP.labels','setup.labels'),('SETUP.map','setup.map')]
        for name,source in names:
            shutil.copyfile(built/source,bundle/name)
            if digest(bundle/name)!=products[source]:raise RuntimeError('Bundle copy mismatch: '+name)
        verify(record)
        phase='publish bundle'
        for name,_ in names:
            os.replace(bundle/name,out/name);published.append(name)
        # Completion is the last publication. An interrupted replacement stays
        # failed/building and never claims a complete mixed-generation bundle.
        (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(str(out))
    except BaseException as first:
        failure={'status':'failed','first_type':type(first).__name__,'first_message':str(first),'phase':phase,'work':str(work),'published_products':published}
        # Reporting must not replace the exact original failure object.
        for path in [work/'FAILED.json',out/'RESULT.json']:
            try:path.write_text(json.dumps(failure,indent=2)+'\n')
            except BaseException:pass
        raise

if __name__=='__main__':main()
