from pathlib import Path
import subprocess,json,hashlib,zlib,argparse,sys,os
sys.dont_write_bytecode=True
sys.pycache_prefix=str(Path(__file__).resolve().parent/('.absent-gate-build-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
P=Path(__file__).resolve().parent;D=P/'gate';commands=[]
parser=argparse.ArgumentParser()
parser.add_argument('--start-work',type=Path,default=P/'core')
parser.add_argument('--start-sha256')
parser.add_argument('--ino-sha256')
a=parser.parse_args();W=a.start_work.resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if not a.start_sha256 or not a.ino_sha256:
 assert W==P/'core','External START requires explicit wholeSTART andINO SHA256'
 bound=json.loads((P/'CORE_BUILD.json').read_text());a.start_sha256=bound['native'];a.ino_sha256=bound['INO']
assert sha(W/'controller.prg')==a.start_sha256
assert sha(W/'START.INO')==a.ino_sha256
prg=(W/'controller.prg').read_bytes();ino=(W/'START.INO').read_bytes()
assert len(prg)==20480 and prg[:2]==b'\1\10'
L={x.split()[2].lstrip('.'):int(x.split()[1],16)for x in(W/'controller.labels').read_text().splitlines()if x.startswith('al ')}
assert L['__PRELAUNCH_RUN__']==0x6000
assert len(ino)==L['__PRELAUNCH_SIZE__']+L['__PRELAUNCH_RO_SIZE__']<=0x2000
assert L['__BSS_RUN__']+L['__BSS_SIZE__']<=0x9000
assert L['__DEVICESTATE_RUN__']+L['__DEVICESTATE_SIZE__']<=0x9000
spec=L['_so_overlay_spec']-0x801+2
assert prg[spec:spec+6]==b'D64I\1\20'
assert int.from_bytes(prg[spec+6:spec+8],'little')==len(ino)
assert int.from_bytes(prg[spec+8:spec+12],'little')==zlib.crc32(ino)
assert prg[spec+12:spec+16]==b'\0\x60\0\0'
prefix=L['_d64_release_validate']-0x6000
assert 161<prefix<=0x1000 and 0x6000<=L['_d64_config_validate']<0x6000+prefix
for n in ['_br_start','_br_poll','_br_cancel','_br_ui_acquire','_br_ui_release','_sc_ready','_ps_clock_poll','_ps_key_poll','_lc_dma','_c32_update','_d64_path_join','_d64_path_parent']:
 assert 0x0801<=L[n]<0x5800,n
(D/'shared-prefix.bin').write_bytes(ino[:prefix])
(D/'prefix.h').write_text('#define JG_PREFIX_BYTES %du\n#define JG_PREFIX_CRC 0x%08xUL\n'%(prefix,zlib.crc32(ino[:prefix])))
(D/'prefix.inc').write_text('JG_ENTRY = $%04x\n'%(0x6000+prefix))
inputs={n:{'sha256':sha(W/n),'bytes':(W/n).stat().st_size}for n in ['controller.prg','controller.labels','controller.map','START.INO','bulk_reu.h','bulk_uci.h','install_config.h','startup_close.h','platform.h','crc32.h']}

lines=[]
for n,v in L.items():
 if n.startswith('__'):continue
 if n in ('_jg_init','_jg_initialized'):continue
 # ld65 labels include C-local aliases; only public names or C runtime names
 if not(n.startswith('_')or n in ('sp','sreg','regsave','regbank','ptr1','ptr2','ptr3','ptr4','tmp1','tmp2','tmp3','tmp4') or not n.startswith('@')):continue
 lines.extend([('.exportzp 'if v<0x100 else '.export ')+n,n+' = $%04x'%v])
(D/'core_imports.s').write_text('\n'.join(lines)+'\n')
def run(a):
 r=subprocess.run(a,cwd=D,capture_output=True);i=len(commands);(P/f'GATE{i:02}.stdout').write_bytes(r.stdout);(P/f'GATE{i:02}.stderr').write_bytes(r.stderr);commands.append({'argv':a,'exit':r.returncode});(P/'GATE_COMMANDS.json').write_text(json.dumps(commands,indent=2));assert not r.returncode,(a,r.stderr.decode())
run(['cc65','-t','none','-Oirs','--add-source','-D','D64_CONFIG_VALIDATE_ONLY=1','-D','D64_START_OPTIONS=1','-I',str(W),'journal_gate.c','-o','journal_gate.s'])
for n in ('entry','journal_gate','core_imports'):run(['ca65','-g','-I','.',n+'.s','-o',n+'.o'])
run(['ld65','-C','gate.cfg','-o','START.RCV','-Ln','gate.labels','-m','gate.map','entry.o','journal_gate.o','core_imports.o','/opt/homebrew/share/cc65/lib/none.lib'])
print((D/'gate.map').read_text().split('Segment list:')[1].split('Exports list')[0])
print(hashlib.sha256((D/'START.RCV').read_bytes()).hexdigest())

(D/'MATCHED_BINDING.json').write_text(json.dumps({'STARTwork':str(W),'inputs':inputs,'prefixBytes':prefix,'prefixCRC':zlib.crc32(ino[:prefix]),'assetSHA256':sha(D/'START.RCV'),'assetBytes':(D/'START.RCV').stat().st_size,'load':0x6000,'entry':0x6000+prefix,'selectors':{'0':'init','1':'begin','2':'poll returns privateState','3':'state','4':'error','5':'cleanup','6':'class','7':'one-shot boot gate','8':'cancel returns privateState'},'contract':'Coupled builder patches fixed-size capsule count/CRC only after matchedSTART linked; then regenerate descriptor. No START invocation or hardware authority from hostmetadata alone.'},indent=2)+'\n')
