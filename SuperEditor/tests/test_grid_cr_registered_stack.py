"""Actual60 CFG; same registered59 analysis plus explicit extra R29 leaf."""
from pathlib import Path
import argparse,importlib.util,inspect,json
ROOT=Path(__file__).resolve().parents[1]
def run(out,fixture,project):
 context=out.with_name(out.name+'-context');context.mkdir(parents=True)
 source=ROOT/'src/cache/lexical-registration-probe/stack-run.py';spec=importlib.util.spec_from_file_location('cr60_registered',source);r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
 # Only catalogue shape admission changes. The extra leaf is still traversed
 # by the original actual-instruction analyzer with every unknown edge refused.
 text=inspect.getsource(r.m.stage_proof);needle="59:['code','clex','type','grid','hotcold','fold','sema','inln','page','line','edit','tail','lex','ical','ctrl']"
 assert text.count(needle)==1;text=text.replace(needle,needle+",60:['code','clex','type','grid','hotcold','fold','sema','inln','page','line','edit','tail','lex','ical','ctrl','row']")
 p=context/'stage60.py';p.write_text(text);ns=dict(r.m.__dict__);exec(compile(text,str(p),'exec'),ns);r.m.stage_proof=ns['stage_proof']
 original=r.m.original.foreground_proof;text=inspect.getsource(original);old="[(0xb000,image[36:])],Ccall)";new="[(0xb000,image[36:])]+([(0xa000,images['geostail'][36:])]if name=='grid'else[]),Ccall)";assert text.count(old)==1
 p=context/'foreground60.py';p.write_text(text.replace(old,new));ns=dict(r.m.original.__dict__);exec(compile(p.read_text(),str(p),'exec'),ns);r.m.original.foreground_proof=ns['foreground_proof']
 result=r.run(out,fixture,project);assert any(x['name']=='R:row'for x in result['foreground']['results']);result.pop('scope59',None);result['scope60']='All60 actual assets decoded, including R29; relative foreground52 plus IRQ/NMI16, under declared frame/vector contracts.';(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.out.resolve(),a.fixture.resolve(),a.project.resolve())
