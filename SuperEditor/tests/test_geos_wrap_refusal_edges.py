"""Actual C6/R28 pre-output refusal with all alnum advances and inline hazards."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_row_backup_candidate as backup
from test_geos_heading_body_candidate import geos,semantic

def run(out,fixture):
 frozen,identity=geos.freeze(out,fixture);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out)
 f=backup.PoisonFixture(out,frozen,dll,True);fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};w=fonts['bsw9-widths.bin'];cases=[]
 def width(raw):
  styles=semantic.classify(raw+b'\r').styles
  return sum(w[geos.native(v)]+(styles[i]&1)+(styles[i]&2)for i,v in enumerate(raw))
 def fill(prefix,target):
  raw=geos.native_text(prefix)
  while width(raw)+w[geos.native(46)]<=target:raw+=b'.'
  if width(raw)<target:
   assert target-width(raw)==1 and raw.endswith(b'.');raw=raw[:-1]+geos.native_text('f');assert width(raw)==target
  return raw
 def invoke(op):f.put('se_overlay_frame',op,1);return f.fast_call(f.s['se_overlay_call'],a=28,x=0)
 def mutate(row,offset,data):
  f.call('se_doc_invalidate');f.m.load(0x8000,data)
  for n,v,z in [('se_reu_logical',f.get('se_gc_handle',1),1),('se_reu_offset',0x200+row*2048+offset,2),('se_reu_length',len(data),2),('se_reu_c64',0x8000,2)]:f.put(n,v,z)
  assert not f.call('se_reu_copy',0).p&1
 def case(tag,line,byte,at,expected,mutation=None):
  raw=line+geos.native_text('\rTail.');f.source(raw);f.command(99);f.position(at);f.render();cache,bank=f.raw_cache();row=cache[42];packet=cache[0x200+row*2048:0x220+row*2048]
  assert int.from_bytes(packet[28:30],'little')==width(line) and packet[17]==1,(tag,'realcompletewidth',packet.hex())
  if mutation:mutate(row,*mutation)
  f.key(byte);changed=raw[:at]+bytes([byte])+raw[at:];canonical=f.canonical();assert f.merged()==changed and f.m.read(0xcfe8)==1
  f.put('se_f_owner',4,1);before=f.reu();screen=f.read(0x4000,1000)+f.read(0x6000,8000);r,n=invoke(0)
  assert not r.p&1 and r.a==expected,(tag,'actualADMIT',r.a,r.p)
  assert f.canonical()==canonical and f.merged()==changed and f.read(0x4000,1000)+f.read(0x6000,8000)==screen,(tag,'preoutput/canonical')
  after=f.reu()
  if expected==2:assert after==before,(tag,'earlyrefusal must write zeroREUbytes')
  else:
   wanted=bytearray(before)
   for lo,hi in [(0,64),(0xd528,0xd568)]:wanted[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
   assert after==wanted,(tag,'admittedwrites only current/oldheader')
   c,_=invoke(3);assert not c.p&1 and c.a==0
  assert f.m.read(0x9149)==0 and not f.m.read(0xcfe8)
  f.put('se_f_owner',0,1);f.render();assert f.merged()==changed and f.canonical()==canonical
  eb,ea,_,_=semantic.expected(f,changed,fonts);assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea,(tag,'normalfullfallbackpixels')
  assert not any(f.get(k,1)for k in ['se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned','se_e_error'])and f.read(0xc600,1024)==f.shim
  geos.png(eb,ea,out/(tag+'.png'));cases.append(dict(tag=tag,source_bytes=len(raw),insert_byte=byte,oldwidth=width(line),advance=w[geos.native(byte)],ADMIT=expected,instructions=n,old_inline=packet[23]));print('PASS',cases[-1],flush=True)
 try:
  for byte in [*range(0x41,0x5b),*range(0xc1,0xdb),*range(0x30,0x3a)]:
   case('overflow-'+hex(byte),fill('# ',319),byte,2,2)
   case('exact320-'+hex(byte),fill('# ',320-w[geos.native(byte)]),byte,2,1)
  # These insertedalnums can split unmatched delimiter runs into closedpairs.
  # INLINE1 must keep the actual parser/VERIFY path even if oldSTYLES arezero.
  for tag,prefix,at in [('split-emph','# **',3),('split-strong','# ****',4),('split-both','# ******',5),('unmatched-code','# @@@@',4),('escaped-star','# '+chr(0x5c)+'**',4),('closed-bold','# **B**',5),('closed-italic','# *I*',4)]:
   case(tag,fill(prefix,319),geos.native_text('Q')[0],at,1)
  # CorruptINLINE0 alone cannot turn a nonzero-style row into a plain proof.
  case('style-array-guard',fill('# **B**',319),geos.native_text('Q')[0],5,1,(23,b'\0'))
  case('malformed-style-noinline',fill('# ',319),geos.native_text('Q')[0],2,1,(194,b'\1'))
  case('palette-role-refuses',fill('# ',319),geos.native_text('Q')[0],2,2,(356,b'\7'))
  # HighPETSCIIdigit-lookinggraphics pass the oldalnum filter but are not one
  # of the62 compressedfont entries; they safely retain originalVERIFY.
  for byte in [0xb0,0xb9]:case('unsupported-'+hex(byte),fill('# ',319),byte,2,1)
  result=dict(status='passed',identity=identity,cases=cases,frames=len(cases),pixels=len(cases)*64000,attributes=len(cases)*1000,all_refusals_zeroREUandVRAM_writes=True,wholeREU_bytes=16777216,scope='ActualC6edit+sealedR28publicADMIT; nohostpositivecertificate or glyphsubstitution. Independentactualsource/fontfullfallback.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n');raise
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();out=ROOT/'build/geos-wrap-refusal-edges'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture.resolve())
