#!/usr/bin/env python3
"""Create owned DOS/TP disk trees from exact genuine DOS-formatted base and supplied floppies."""
from pathlib import Path
import argparse,json,struct
from dos_disk_inspect import Volume,inspect,sha
from dos_image import Fat12Image
from dos_hd_fixture import EXPECTED
from dos_fat_populate import Populate,short

def verify_tp(tp,tp_manifest):
    actual_files={path.relative_to(tp).as_posix():path for path in tp.rglob('*') if path.is_file()}
    if set(actual_files)!=set(tp_manifest['files']):raise ValueError('verified TP install tree member set')
    for rel,path in actual_files.items():
        meta=tp_manifest['files'][rel];payload=path.read_bytes()
        if len(payload)!=meta['bytes'] or sha(payload)!=meta['sha256']:raise ValueError('verified TP install tree byte identity: '+rel)

def create(inputs,out,tp=None):
    if out.exists():raise ValueError('fresh output required')
    out.mkdir()
    originals=sorted(inputs.glob('*.img'))
    if [sha(p.read_bytes()) for p in originals]!=EXPECTED:raise ValueError('original disk identity')
    base=inputs/'large/disk.raw.img';base_manifest=json.loads((base.parent/'manifest.json').read_text())
    raw=base.read_bytes()
    if sha(raw)!=base_manifest['raw_image']['sha256']:raise ValueError('base manifest identity')
    geometry=(640,4,16);initial=inspect(raw,geometry);start=initial['partition']['start_lba']*512
    v=Volume(raw[start:]);w=Populate(raw[start:]);w.remove('CROSS16.BIN')
    sources=[];resolved={};variants={}
    for index,path in enumerate(originals,1):
        disk=Fat12Image(path.read_bytes());vol=Volume(path.read_bytes())
        for name,payload in vol.payloads.items():
            entry=disk.find(name);template=bytes.fromhex(entry.raw_hex)
            w.put(f'DOS/DISK{index}/{name}',payload,entry.attributes,template=template)
            variants.setdefault(name,[]).append({'disk':index,'bytes':len(payload),'sha256':sha(payload)})
            resolved.setdefault(name,(payload,entry.attributes,template,index))
        sources.append({'disk':index,'sha256':sha(path.read_bytes()),'files':len(vol.files),'payload_bytes':sum(map(len,vol.payloads.values()))})
    for name,(payload,attr,template,index) in sorted(resolved.items()):w.put('DOS/'+name,payload,attr,template=template)
    basic=Volume(originals[2].read_bytes()).payloads['GWBASIC.EXE']
    game=(inputs/'HANGMAN.BAS').read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
    w.put('GAMES/GWBASIC.EXE',basic);w.put('GAMES/HANGMAN.BAS',game)
    w.put('HANGMAN.BAT',b'@ECHO OFF\r\nC:\\GAMES\\GWBASIC.EXE C:\\GAMES\\HANGMAN.BAS\r\n')
    w.put('BASIC.BAT',b'@ECHO OFF\r\nC:\\GAMES\\GWBASIC.EXE %1 %2 %3\r\n')
    smoke=b"program Smoke;\r\nbegin\r\n  WriteLn('DOS64 TP OK');\r\nend.\r\n"
    tp_files=[]
    tp_manifest=None
    if tp:
        tp_manifest=json.loads((inputs/'TP701_INSTALL_TREE.json').read_text())
        verify_tp(tp,tp_manifest)
        for path in sorted(tp.rglob('*')):
            if not path.is_file():continue
            rel=path.relative_to(tp).as_posix().upper()
            for part in rel.split('/'):short(part)
            payload=path.read_bytes();w.put('TP/'+rel,payload);tp_files.append({'path':rel,'bytes':len(payload),'sha256':sha(payload)})
        w.put('TURBO.BAT',b'@ECHO OFF\r\nC:\r\nCD \\TP\\BIN\r\nTURBO %1\r\n')
    auto=b'@ECHO OFF\r\nPATH C:\\DOS;C:\\TP\\BIN;C:\\GAMES;C:\\\r\nPROMPT $N$G\r\nC:\r\nCD \\\r\n'
    w.put('AUTOEXEC.BAT',auto,replace=True)
    volume,report=w.finish();final=raw[:start]+volume
    inspection=inspect(final,geometry)
    if final[:start+512]!=raw[:start+512]:raise AssertionError('MBR/partition/boot bytes changed')
    finalv=Volume(volume)
    for name in ['IO.SYS','MSDOS.SYS','COMMAND.COM']:
        if finalv.payloads[name]!=v.payloads[name]:raise AssertionError('system bytes changed')
    (out/'HD.IMG').write_bytes(final)
    aw=Populate(originals[0].read_bytes());aw.put('AUTOEXEC.BAT',auto,replace='AUTOEXEC.BAT' in aw.expected);aw.put('CONFIG.SYS',b'FILES=25\r\nBUFFERS=25\r\n',replace=True)
    floppy,areport=aw.finish();(out/'BOOT-A.IMG').write_bytes(floppy)
    if [sha(p.read_bytes()) for p in originals]!=EXPECTED:raise AssertionError('source changed')
    m={'schema_version':1,'kind':'dos64-genuine-dos-hd-fixture','complete':True,'original_images_unchanged':True,'source_system_files_identical':True,
       'geometry':{'cylinders':640,'heads':4,'sectors_per_track':16,'bytes_per_sector':512},'inspection':inspection,
       'raw_image':{'path':'HD.IMG','bytes':len(final),'sha256':sha(final)},'derived_floppy':{'path':'BOOT-A.IMG','bytes':len(floppy),'sha256':sha(floppy),'inspection':areport},
       'population':{'source_format_manifest_sha256':sha((base.parent/'manifest.json').read_bytes()),'source_base_sha256':sha(raw),'floppies':sources,'duplicate_policy':'lowest numbered supplied disk wins convenient DOS/name; every original retained byte-for-byte under DOS/DISK1..3','variants':variants,'resolved_sources':{n:x[3] for n,x in resolved.items()},'tp_files':tp_files,'tp_install_manifest_sha256':sha((inputs/'TP701_INSTALL_TREE.json').read_bytes()) if tp else None,'tp_source_download_sha256':tp_manifest['source_download_sha256'] if tp else None,'edits':w.edits,'game_sha256':sha(game),'basic_sha256':sha(basic)},
       'qualification':'Genuine DOS FDISK/FORMAT/SYS base; host FAT population independently inspected; guest execution evidence recorded separately.'}
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');return m

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--inputs',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--tp-tree',type=Path)
    o=a.parse_args();m=create(o.inputs,o.output,o.tp_tree);print(json.dumps({'sha256':m['raw_image']['sha256'],'free_bytes':m['inspection']['free_bytes'],'files':len(m['inspection']['files']),'tp_files':len(m['population']['tp_files'])}))
