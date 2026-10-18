"""Strict local/captured identity for the separately copied F000–FDFF image.

The expected bytes come only from the pinned packaged PRG, never live A000.
No network, target execution, persistence or physical banking proof is implied.
Legacy five/six-byte state stays supported. The matched options format requires
exact eight-byte serialized defaults; capture checks only the live ready guard,
because the other startup fields legitimately change during execution.
"""
import hashlib
import json
from pathlib import Path
import re

SOURCE=0xa000
RUN=0xf000
SIZE=0xe00
END=0xae00
LOAD=0x801


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition,message):
    if not condition:raise ValueError('Invalid copied shadow identity: '+message)


def integer(value):
    return type(value) is int


def shadow_from_map(text):
    block=text.split('Segment list:',1)[1].split('Exports list',1)[0]
    rows={}
    for line in block.splitlines():
        match=re.fullmatch(r'([A-Z]+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+[0-9A-F]+',line)
        if match and match[1] in {'HDBIOS','HDCODE','NATIVESTATE'}:
            require(match[1] not in rows,'duplicate linker segment')
            start,end,size=(int(match[i],16) for i in (2,3,4))
            require(size>0 and start+size-1==end,'linker segment size')
            rows[match[1]]=(start,size)
    if not ({'HDBIOS','HDCODE'} & rows.keys()):return []
    require({'HDBIOS','HDCODE','NATIVESTATE'}<=rows.keys(),'unpaired HD/shadow/state map')
    run,linked=rows['HDBIOS'];hd_run,hd_size=rows['HDCODE'];state,state_size=rows['NATIVESTATE']
    require(run==RUN and 1<=linked<=SIZE,'shadow linker range')
    require(hd_run==0xc900 and 1<=hd_size<=0x700,'HD overlay linker range')
    require(LOAD<=state<state+state_size<=0x4000 and state_size in (5,6,8),'initialized guard state range')
    return [{'name':'HDBIOS','start':RUN,'length':SIZE,'source_start':SOURCE,'linked_length':linked,
             'state_start':state,'state_length':state_size,'hd_linked_length':hd_size}]


def metadata_from_paths(package_path,memory_path,pins):
    require(bool(package_path)==bool(memory_path),'package and memory artifacts must be paired')
    if not package_path:return None
    values={}
    for name,path in [('package',package_path),('memory',memory_path)]:
        raw=Path(path).read_bytes()
        require(sha(raw) in pins,name+' artifact is absent from reviewed build manifest')
        values[name]=json.loads(raw)
    return values


def prepare(prg,labels,segments,metadata):
    shadows=[s for s in segments if s.get('name')=='HDBIOS']
    advertised=len(prg)>0x9800-LOAD+2 or any(name in labels for name in ('__HDBIOS_RUN__','__HDEXT_START__','__HDCODE_RUN__','hdb_extension_ready'))
    if not shadows and not advertised:
        require(metadata is None,'shadow metadata supplied for a layout without a shadow')
        return None
    require(len(shadows)==1 and metadata is not None,'HD map/labels require pinned package and memory metadata')
    segment=shadows[0]
    require(set(segment)=={'name','start','length','source_start','linked_length','state_start','state_length','hd_linked_length'},'map descriptor schema')
    require(all(integer(segment[k]) for k in segment if k!='name'),'map descriptor integer fields')
    linked=segment['linked_length'];state=segment['state_start'];hd_size=segment['hd_linked_length']
    require((segment['start'],segment['length'],segment['source_start'])==(RUN,SIZE,SOURCE),'source/run/window ranges')
    state_size=segment['state_length']
    require(1<=linked<=SIZE and state_size in (5,6,8) and LOAD<=state<state+state_size<=0x4000,'linked image/state size')
    require(1<=hd_size<=0x700,'HD payload size')
    saver_size=labels.get("__SAVERCODE_SIZE__",0)
    require(type(saver_size)is int and 0<=saver_size<=0x7f0,"SAVER linked size")
    disk_size=labels.get("__DISKCODE_SIZE__",0)
    require(type(disk_size)is int and 0<=disk_size<=0x700 and (not disk_size or saver_size),"DISK linked size/paired SAVER")
    packaged_end=0xc000 if disk_size else 0xb800 if saver_size else END
    require(prg[:2]==LOAD.to_bytes(2,'little') and len(prg)==packaged_end-LOAD+2,'PRG load address/complete packaged length')
    options_state=any(k in labels for k in ('dos64_bios_initial_mode','dos64_options_required'))
    require((state_size==8)==options_state,'matched options symbols require exact eight-byte initialized schema')
    cold_offset=1 if state_size==8 else 0
    expected_labels={'__HDEXT_START__':RUN,'__HDEXT_SIZE__':SIZE,'__HDEXT_FILEOFFS__':0,
                     '__HDEXT_LAST__':RUN+linked,'__HDBIOS_LOAD__':RUN,'__HDBIOS_RUN__':RUN,'__HDBIOS_SIZE__':linked,
                     '__NATIVESTATE_LOAD__':state,'__NATIVESTATE_RUN__':state,'__NATIVESTATE_SIZE__':state_size,
                     'hdb_boot_drive':state+3+cold_offset,'hdb_extension_ready':state+4+cold_offset,
                     '__HDCODE_LOAD__':0xc900,'__HDCODE_RUN__':0xc900,'__HDCODE_SIZE__':hd_size}
    require(all(type(labels.get(k)) is int and labels[k]==v for k,v in expected_labels.items()),'linked source/run/guard symbols')
    guard=state+4+cold_offset
    require(prg[guard-LOAD+2]==0,'packaged guard must start clear')
    if state_size==8:
        state_labels={'dos64_bios_initial_mode':state,'dos64_cold_open':state+1,
                      'dos64_cold_error':state+2,'n_started':state+3,
                      'dos64_native_started':state+3,'hdb_boot_drive':state+4,
                      'hdb_extension_ready':state+5,'dos64_loader_required':state+6,
                      'dos64_options_required':state+7}
        require(all(type(labels.get(k))is int and labels[k]==v for k,v in state_labels.items()),'exact mode/cold/native/HD/loader/options symbols')
        require(type(labels.get('dos64_native_entry'))is int and LOAD<=labels['dos64_native_entry']<0x4000,'eight-byte schema requires resident native entry')
        require(prg[state-LOAD+2:state-LOAD+2+8]==b'\x03\xa5\0\0\0\0\0\0','exact eight-byte initialized defaults')
    elif state_size==6:

        require(labels.get('dos64_loader_required')==state+5 and prg[state+5-LOAD+2]==0,'packaged loader flag must be explicit legacy0')
    else:
        require('dos64_loader_required' not in labels,'loader flag needs its initialized resident byte')
    require(type(metadata) is dict and set(metadata)=={'package','memory'},'metadata schema')
    package=metadata['package'];memory=metadata['memory']
    require(type(package) is dict and type(package.get('version')) is int and package['version']==1,'package schema version')
    require(type(memory) is dict and memory.get('passed') is True and memory.get('errors')==[],'verified memory report')
    load=memory.get('load',{})
    require(type(load) is dict,'memory load schema')
    require(load.get('payload_checked') is True and load.get('layout') in ('runtime','unit') and
            load.get('start')==LOAD and load.get('end_exclusive')==packaged_end and load.get('prg_bytes')==len(prg),'verified load extent')
    require(package.get('sha256',{}).get('packaged_prg')==sha(prg),'package/base PRG hash')
    p=package.get('shadow',{});m=load.get('shadow',{})
    for item in (p,m):
        require(type(item) is dict and all(type(item.get(k)) is int and item[k]==v for k,v in
                {'source':SOURCE,'run':RUN,'window_bytes':SIZE,'linked_bytes':linked}.items()),'package/memory shadow range')
    require(p.get('ownership')=='verified copy before cache; permanent RAM+IO, no KERNAL, excludes FE00-FFFF' and
            m.get('ownership')=='verified cold copy before guest cache; permanent RAM+IO/no KERNAL' and
            m.get('excludes')=='FE00-FFFF hardware vectors','reviewed permanent RAM/I/O bank and vector ownership contract')
    require(type(p.get('tail_zero_bytes')) is int and p['tail_zero_bytes']==SIZE-linked and m.get('payload_checked') is True,'verified zero tail contract')
    offset=SOURCE-LOAD+2;expected=bytes(prg[offset:offset+SIZE])
    require(len(expected)==SIZE and not any(expected[linked:]),'complete zero-padded immutable source')
    require(p.get('sha256')==sha(expected[:linked]),'linked shadow payload hash')
    rows=memory.get('segments',[])
    require(type(rows) is list and all(type(r) is dict for r in rows),'memory segment schema')
    for name,start,size in [('HDBIOS',RUN,linked),('HDCODE',0xc900,hd_size),('NATIVESTATE',state,state_size)]:
        found=[r for r in rows if r.get('name')==name]
        require(len(found)==1 and found[0].get('start')==start and found[0].get('end')==start+size-1 and found[0].get('bytes')==size,'memory/map segment disagreement')
    require(package.get('startup_sources')==[0x6000,0x6800,0x8000,0x8800,0x9000,0x9800]+([0xb000]if saver_size else [])+([0xb800]if disk_size else []) and
            package.get('slot_size')==2048 and package.get('window')==0xc900 and package.get('window_size')==0x700,'six overlay package contract')
    lengths=package.get('payload_lengths',[])
    require(type(lengths) is list and len(lengths)==(8 if disk_size else 7 if saver_size else 6) and all(type(v) is int and 1<=v<=0x700 for v in lengths[:6]) and lengths[5]==hd_size and (not saver_size or lengths[6]==saver_size) and (not disk_size or lengths[7]==disk_size),'six overlay lengths')
    for identity,(source,size) in enumerate(zip(package['startup_sources'],lengths),1):
        slot=prg[source-LOAD+2:source-LOAD+2+2048]
        tag={1:b'FILE',2:b'TEXT',3:b'KEYS',4:b'TIME',5:b'CGA ',6:b'HD  ',7:b'SAVE',8:b'DSK '}[identity]
        header=b'D64O'+bytes([1,7 if identity==8 else identity])+size.to_bytes(2,'little')+(0xb010 if identity==7 else 0xc900).to_bytes(2,'little')+b'\0\0'+tag
        require(slot[:16]==header and not any(slot[16+size:]),'complete overlay slot/header/tail')
    for phase in (package.get('startup_cache_phase',{}),load.get('startup_cache_phase',{})):
        require(type(phase) is dict and all(type(phase.get(k)) is int and phase[k]==v for k,v in
                {'start':0x8000,'end_exclusive':packaged_end,'cache_frames':31 if disk_size else 27 if saver_size else 23,'overlay_frames':16,'shadow_frames':7}.items()),'startup cache ownership metadata')
    if saver_size:
        for item in (package.get('saver'),load.get('saver')):
            require(type(item)is dict and all(type(item.get(k))is int and item[k]==v for k,v in {'source':0xb000,'run':0xb010,'reu':0x343000,'slot_bytes':2048,'linked_bytes':saver_size,'compare_stage':0xb800}.items()),'SAVER exact package/memory modal ranges')
        require(package['saver'].get('modal_cache_frames')==[24,32] and load['saver'].get('cache_frames')==[24,32],'SAVER eight-frame modal borrow')
        payload=prg[0xb010-LOAD+2:0xb010-LOAD+2+saver_size]
        require(package['saver'].get('sha256')==sha(payload),'SAVER payload immutable source hash')
        require(not any(prg[END-LOAD+2:0xb000-LOAD+2]),'SAVER source gap must remain zero')
        require(labels.get('__SAVERCODE_LOAD__')==0xb010 and labels.get('__SAVERCODE_RUN__')==0xb010,'SAVER source/run metadata')
        row=[r for r in rows if r.get('name')=='SAVERCODE']
        require(len(row)==1 and row[0].get('start')==0xb010 and row[0].get('bytes')==saver_size and row[0].get('end')==0xb010+saver_size-1,'SAVER map segment')
        for phase in (package['startup_cache_phase'],load['startup_cache_phase']):
            require(phase.get('span_cache_frames')==(32 if disk_size else 28) and phase.get('saver_frames')==4 and phase.get('gap_cache_frames')==[23],'SAVER actual27frames versus28span with frame23gap')
    else:
        require(package.get('saver')is None and load.get('saver')is None,'SAVER metadata without linked payload')
    if disk_size:
        require(labels.get('__DISKCODE_LOAD__')==0xc900 and labels.get('__DISKCODE_RUN__')==0xc900,'DISK source/run metadata')
        row=[r for r in rows if r.get('name')=='DISKCODE']
        require(len(row)==1 and row[0].get('start')==0xc900 and row[0].get('bytes')==disk_size and row[0].get('end')==0xc900+disk_size-1,'DISK map segment')
        for item in (package.get('disk'),load.get('disk')):
            require(type(item)is dict and all(type(item.get(k))is int and item[k]==v for k,v in {'source':0xb800,'run':0xc900,'reu':0x343800,'slot_bytes':2048,'linked_bytes':disk_size}.items()),'DISK exact source/run/REU ranges')
        for phase in (package['startup_cache_phase'],load['startup_cache_phase']):
            require(phase.get('disk_frames')==4,'DISK four startup frames')
        payload=prg[0xb810-LOAD+2:0xb810-LOAD+2+disk_size]
        require(package['disk'].get('sha256')==sha(payload),'DISK immutable payload hash')
    else:
        require(package.get('disk')is None and load.get('disk')is None,'DISK metadata without linked payload')
    return {'expected':expected,'source_start':SOURCE,'start':RUN,'length':SIZE,'linked_length':linked,
            'zero_tail_bytes':SIZE-linked,'loaded_guard_address':guard,'loaded_guard_required':0xa5,
            'expected_window_sha256':sha(expected),'base_prg_sha256':sha(prg)}


def verify(contract,ram,cpu_port_snapshot=None):
    actual=bytes(ram[RUN:RUN+SIZE]);guard=ram[contract['loaded_guard_address']]
    # REST readmem returns underlying RAM: an accepted physical capture has
    # 00/01 at addresses0/1, not the live6510 port. Never infer banking from it.
    bank={'required_effective_low_bits':5,'contract':'permanent RAM+IO/no KERNAL',
          'captured_raw_ram_bytes':bytes(ram[:2]).hex(),'live_cpu_port_verified':False,
          'limitation':'Underlying RAM identity does not establish live CPU-port banking'}
    bank_match=True
    if cpu_port_snapshot is not None:
        require(isinstance(cpu_port_snapshot,bytes) and len(cpu_port_snapshot)==2,'explicit trusted CPU-port snapshot requires DDR/data bytes')
        ddr,data=cpu_port_snapshot
        effective=(data|(~ddr&0xff))&7
        bank.update(ddr=ddr,data=data,effective_low_bits=effective,live_cpu_port_verified=True,
                    source='caller-supplied model CPU-port snapshot; no physical port claim')
        bank_match=effective==5
    proof={k:v for k,v in contract.items() if k!='expected'}
    proof.update(name='HDBIOS',source_kind='immutable packaged PRG',captured_sha256=sha(actual),
                 raw_matches=actual==contract['expected'],mutable_operands=[],normalizations=[],
                 loaded_guard_value=guard,bank=bank,
                 excluded_vectors={'start':0xfe00,'length':512})
    proof['matches']=proof['raw_matches'] and guard==0xa5 and bank_match
    if not proof['raw_matches']:
        proof['first_difference_address']=RUN+next(i for i,(a,b) in enumerate(zip(actual,contract['expected'])) if a!=b)
    return proof
