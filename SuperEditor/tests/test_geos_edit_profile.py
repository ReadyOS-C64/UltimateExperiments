"""Measured GEOS edit matrix on one immutable editor, no product edits.

PublicGOTO/key input performs setup. Measurement uses the established explicit
monitorPC/SP public-input seam withIRQs, exactfirst-publication/idle timestamps,
nestedoverlay/CRCtrace, and full independent nativepixel/source/catalog guards.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,shutil,subprocess,zipfile
import test_display_timing_vice as timing
import vice_plan
ROOT=timing.ROOT
DEFAULT=ROOT/'build/geos-semantic-editor/20261025T071324227584Z/fixture'


class Plan(timing.Plan):
    literal_return=False
    def condition(self,ui):
        # RETURN edits a normal document here; it isnot a previewcommand
        # acceptance from theF7 prompt (the parent harness's specialcase).
        return super().condition(0 if self.literal_return and ui==2 else ui)


def scenario(e,standard,model):
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),standard,model);n.cost_profile=True
    data=timing.native.live.grid.fixture();q=timing.native.live.grid.native_text('Q')[0]
    prose=data.index(timing.native.live.grid.native_text('Mixed Case'))
    heading=2+len(timing.native.live.grid.native_text('Super'))
    basic=data.index(timing.native.live.grid.native_text('10 PRINT'))
    strong=data.index(timing.native.live.grid.native_text('Strong words'))
    cases=[('front-changes-heading',0,q,'insert'),('prose-interior-insert',prose+8,q,'insert'),
           ('prose-interior-backspace',prose+9,0x14,'backspace'),('heading-text-insert',heading,q,'insert'),
           ('BASIC-keyword-letter',basic+5,q,'insert'),('prose-linebreak',prose+15,13,'insert'),
           ('inline-strong-interior',strong+5,q,'insert')]
    n.boot();n.open('open_diverse',b'DIVERSE');n.typed('enter_geos','mode hires')
    for serial,(tag,at,key,operation) in enumerate(cases):
        line=data[:at].count(b'\r')+1;column=at-(data.rfind(b'\r',0,at)+1)
        n.typed(tag+'_top','top');n.typed(tag+'_goto',f'goto {line}')
        if column:n.send(tag+'_column',bytes([0x1D])*column)
        n.memory(tag+'_before_caret','se_hot_caret',at,3)
        after=data[:at-1]+data[at:] if operation=='backspace' else data[:at]+bytes([key])+data[at:]
        n.literal_return=key==13;n.measure(tag,after,3,key=key,category=operation);n.literal_return=False
        n.send(tag+'_undo',b'\x1a');n.memory(tag+'_undo_length','se_v_length',len(data),3)
    return n


def summary(n,result,standard_name):
    groups=[]
    for item in result['measurements']:
        cost=item['cost_profile'];by={(v['slot'],v['id']):v for v in cost['groups']}
        def own(*ids):return sum(v['payload_self']for k,v in by.items()if k in ids)
        groups.append(dict(id=item['id'],first=item['first_publish_cycles'],idle=item['emulated_cycles'],
            crc=cost['crc_cycles'],overlay_admission=sum(v['admission']for v in by.values()),
            layout_source=own((1,20)),source_provider=own((0,14)),semantic_query=own((1,24)),lexer=own((1,25)),inline=own((1,26)),
            page_coordinator=own((1,21)),paint_coordinator=own((1,22)),raster=own((0,21)),caret=own((0,27)),
            window=own((1,6)),chrome=own((1,16),(0,16)),counters=item['counter_deltas'],
            service_peak=item['service_peak_cycles']))
    r=dict(status='passed',identity=result['identity'],cases=groups,
        scope=f'Actual{standard_name.upper()} CPUcycles inclIRQ/VIC/REU stalls. Payloadself excludesmeasuredchildoverlays, retainsreturnoverhead. Firstpaintis memorypublication notVICbeam/physicalkeylatency. Allnativepixels/source/catalog/shim guards mustpass first.')
    (n.out/'edit-profile.json').write_text(json.dumps(r,indent=2)+'\n');return r


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path,default=DEFAULT);p.add_argument('--standard',choices=('pal','ntsc'),default='pal');a=p.parse_args()
    if not a.run:print('Use --run --fixture IMMUTABLE [--standard pal|ntsc]. Oneowned VICE7900/text8000; no sharedbuild.');return
    standard,model=(1,0) if a.standard=='pal' else (2,3)
    e=timing.freeze(a.fixture,a.standard);n=scenario(e,standard,model);plan=n.plan()
    (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
    with zipfile.ZipFile(e/'edit-profile-verifier.zip','w',zipfile.ZIP_DEFLATED)as z:
        for path in [Path(__file__),ROOT/'tests/test_display_timing_vice.py']:z.write(path,path.relative_to(ROOT))
    print('PREPARED',n.out,len(n.steps),flush=True)
    project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    proc=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(proc.stdout+proc.stderr);assert not proc.returncode
    vice_plan.run_plan(plan,n.out);r=timing.evaluate(n);s=summary(n,r,a.standard);print('EDITPROFILEPASS',n.out,flush=True)
    for item in s['cases']:print(json.dumps(item),flush=True)

if __name__=='__main__':main()
