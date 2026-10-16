#!/usr/bin/env python3
"""Assemble current generic/native REU code and run actual Peddle fault controls.

Synthetic delayed assertion and stale-read models are separate from physical
C64U timing. No fixed-delay repair, reissued command, or implicit CIA ownership.
"""
import argparse,hashlib,json,subprocess,shutil
from pathlib import Path

def run(project,output):
    project=Path(project).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    cfg=output/'link.cfg';cfg.write_text('MEMORY {ZP: start=$20,size=$E0;RAM: start=$0800,size=$7800,file=%O;BSS: start=$E000,size=$0100;} SEGMENTS {ZEROPAGE: load=ZP,type=zp;CODE: load=RAM,type=ro;BSS: load=BSS,type=bss;}\n')
    sources=[project/'src/reu.s',project/'include/abi.inc',project/'include/reu.inc',project/'tests/host/reu_observer_model.cpp']
    vendor=project/'third_party/peddle/Peddle';core=[vendor/(name+'.cpp') for name in ('Peddle','PeddleDebugger','PeddleDisassembler','StrWriter')]
    def call(args):subprocess.run(list(map(str,args)),check=True,cwd=project)
    for name,flags in [('generic',[]),('native',['-D','DOS64_NATIVE_REU_OBSERVER=1'])]:
        call(['ca65',*flags,'-I',project/'include',project/'src/reu.s','-o',output/(name+'.o')])
        call(['ld65','-C',cfg,output/(name+'.o'),'-o',output/(name+'.bin'),'-Ln',output/(name+'.labels')])
    binary=output/'model-test'
    call(['clang++','-std=c++20','-O2','-I',vendor,'-I',project/'tests/host',project/'tests/host/reu_observer_model.cpp',*core,'-o',binary])
    result=subprocess.run([str(binary),str(output/'generic.bin'),str(output/'native.bin')],cwd=project,check=True,capture_output=True,text=True)
    (output/'actual-tests.log').write_text(result.stdout+result.stderr)
    files=[*sources,*vendor.glob('*.h'),*vendor.glob('*.cpp'),project/'tests/host/reu_model.h',Path(__file__).resolve(),cfg,binary,output/'generic.bin',output/'native.bin']
    proof={'status':'passed','hardware_executed':False,'model':'actual6510 with synthetic delayed DMA assertion and stale/readclear responses','finite_attempt_bound':256,'native_timer_deadline':False,'groups':{'delayed_stale_original_candidate_comparisons':16,'all_first_status_masks':256,'all_initial_P_success_error_differentials':512},'files':{str(p):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files}}
    (output/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(result.stdout,end='');return proof
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(Path(__file__).resolve().parents[1],a.output)
