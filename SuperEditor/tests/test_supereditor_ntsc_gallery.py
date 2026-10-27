"""Offline-prepared current62 NTSC five-view native gallery and timing adapter.

Default prepares/compiles only. --run-prepared explicitly executes one isolated
VICE using binary9100/text9200..9239. Real File/Open and IRQ setup; measurements
use disclosed public-entry PC/SP/input seams. No shared build/Git/hardware.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, re, shutil, socket, subprocess, sys, threading, zipfile
import test_cache_rebase_standalone_acceptance as freeze_engine
import test_presentation_vice as presentation
from test_reu_capacity_vice import run_owned_plan
from closed_runtime_copy import run_with_closed_links
from overlay_catalog_policy import catalog_identity, catalog_state
from vice_config import step
from d81_image import D81Image
T = presentation.timing
ROOT = T.ROOT
BASE = ROOT/'build/warm-shift-canonical-working-v2/20261027T001110182649Z/fixture'
PORT = 9100


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dependencies():
    found={}
    for module in list(sys.modules.values()):
        source=getattr(module,'__file__',None)
        if not source:continue
        p=Path(source).resolve()
        if p.suffix=='.py' and p.parent in(ROOT/'tests',ROOT/'tools') and p.name!=Path(__file__).name:
            found[str(p.relative_to(ROOT))]=sha(p)
    return found


def authenticate_verifier(e):
    c=json.loads((e/'adapter.json').read_text());assert c['adapter_sha256']==sha(__file__)
    for name,digest in c['verifier_dependencies'].items():assert sha(ROOT/name)==digest,('use frozen verifier cohort; dependency changed',name)
    return c


class Plan(presentation.Plan):
    def plan(self):
        p = super().plan(); g=p['global_defaults'];g['monitor_port_start']=PORT;g['monitor_port_span']=1
        p['plan_id']='supereditor-current62-ntsc-'+self.e.name
        assert not g.get('kill_stale',False) and not p['steps'][0]['params']['kill_stale']
        return p
    def boot(self):
        super().boot()
        self.raw('actual_ntsc_extra_resources',[f'logname "{self.out}/ntsc-resources.log"','log on',
            'resourceget "MachineVideoStandard"','resourceget "VICIIModel"','resourceget "MachinePowerFrequency"',
            'resourceget "REU"','resourceget "REUsize"','resourceget "Drive8TrueEmulation"','warp','log off'])
    def calibrate(self):
        # Eight real NOPs at the existing free cold probe. Select raster255 in
        # NTSC's lower border so VIC badline stalls do not contaminate16cycles.
        p=T.PROBE; assert p>=self.cold_end and p+8<0x1000
        self.raw('ntsc_16cycle_calibration',['delete',
            f'break exec ${self.idle_pc:04x} if ({self.condition(0)}) && (@cpu:$d012 == $ff)',
            'x','delete',f'> {p:04x} '+bytes([0xea]*8).hex(' '),
            f'logname "{self.out}/calibration.log"','log on','registers',
            f'registers PC=${p:04x}, SP=$ff, FL=$24','stopwatch reset',
            f'until ${p+8:04x}','stopwatch','registers','log off',
            f'registers PC=${self.s["se_idle"]:04x}, SP=$ff, FL=$20','x'])
    def measure(self,ident,data,mode,**kwargs):
        ui=kwargs.get('ui',0);before_ui=2 if kwargs.get('key')==13 else ui
        if mode<3:
            self.memory(ident+'_Full_styles_published','se_st_valid',1)
            self.memory(ident+'_Full_styles_complete','se_st_request',0)
        caps=self.out/'captures';caps.mkdir(exist_ok=True)
        self.raw(ident+'_before_interval_coherent',['delete',
            f'break exec ${self.idle_pc:04x} if {self.condition(before_ui)}','x','delete',
            f'bsave "{caps}/{ident}-interval-before-ram.bin" 0 $0000 $cfff',
            f'bsave "{caps}/{ident}-interval-before-colors.bin" 0 $d800 $dbe7'])
        self.steps.append(step(ident+'_interval_before_reu','dump.reu',mode='full',stage_tag=ident+'-before_reu'))
        super().measure(ident,data,mode,**kwargs)
        self.measurements[-1].update(expected_caps=3,expected_caret=1 if ident.endswith('-right') else 0,
            interval_before_REU=ident+'-before',readonly_source=True)


def scenario(e):
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),2,3)
    n.cost_profile=True;n.measurement_warp=False
    data=T.native.live.grid.fixture();n.boot();n.calibrate();n.open('actual_File_Open_DIVERSE',b'DIVERSE')
    n.memory('actual_default_Full','se_render_caps',3)
    for mode in (0,1,2,3):
        if mode<3:n.mode_to(mode)
        else:n.typed('enter_literal_GE0S','mode hires')
        n.typed('source_top_'+str(mode),'top')
        n.measure('mode'+str(mode)+'-right',data,mode,key=0x1d,category='NTSC-warm-public-caret-right')
        n.measure('mode'+str(mode)+'-left',data,mode,key=0x9d,category='NTSC-warm-public-caret-left')
    n.send('actual_F6_help',b'\x8b',ui=1)
    n.measure('literal-help',data,3,ui=1,full=True,category='NTSC-help-over-literal')
    n.send('close_actual_F6_help',b'\x8b')
    n.send('preview_public_prompt',b'\x88'+T.native.live.grid.native_text('preview'),ui=2)
    n.measure('preview-first',data,3,key=13,ui=4,category='NTSC-formatted-preview-entry')
    # These actual IRQ keys must not edit in the read-only preview. The next
    # independently modeled repaint and full source/history check observe it.
    n.send('preview_readonly_Q_BACK',b'Q\x14',ui=4)
    n.measure('preview-readonly-repaint',data,3,ui=4,full=True,category='NTSC-readonly-preview-repaint')
    n.measure('preview-page',data,3,key=0x87,ui=4,category='NTSC-preview-page-forward')
    n.measure('preview-back',data,3,key=0x86,ui=4,category='NTSC-preview-page-back')
    n.send('preview_Return_to_literal',b'\r')
    return n


def loaded(e):
    n=Plan.__new__(Plan);n.e=e;n.out=e/'timing';n.r=json.loads((e/'editor-report.json').read_text());n.s=n.r['symbols']
    n.standard=2;n.model=3;n.measurement_warp=False;n.cost_profile=True;n.canary=bytes((i*73+29)&255 for i in range(1024))
    n.measurements=json.loads((n.out/'measurements.json').read_text())
    for name,value in json.loads((n.out/'plan-metadata.json').read_text()).items():setattr(n,name,value)
    return n


def prepare(base,out):
    freeze_engine.freeze(base,out);identity=freeze_engine.validate(out)
    n=scenario(out);plan=n.plan();assert len({s['id']for s in plan['steps']})==len(plan['steps'])
    assert len(n.measurements)==13 and {v['mode']for v in n.measurements}=={0,1,2,3}
    text=(n.out/'resources.mon').read_text()
    for token in ('"MachineVideoStandard" "2"','"VICIIModel" "3"','"MachinePowerFrequency" "60"','"REUsize" "16384"'):assert token in text,token
    (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
    (n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
    (n.out/'plan-metadata.json').write_text(json.dumps(dict(cold_end=n.cold_end,service_return=n.service_return,publish_pc=n.publish_pc,cost_points=n.cost_points,guard_start=n.guard_start),indent=2)+'\n')
    with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
        for directory in ('tests','tools'):
            for p in sorted((ROOT/directory).glob('*.py')):z.write(p,p.relative_to(ROOT))
    config=dict(status='PREPARED_NOT_RUN',fixture=str(base),adapter_sha256=sha(__file__),identity=identity,
                binary_port=PORT,text_ports=[9200,9239],standard=2,VICIIModel=3,MachinePowerFrequency=60,
                normal_speed_during_measurements=True,frames=13,whole_REU_intervals=13,verifier_dependencies=dependencies(),
                minimum_distinct_REU_bytes=26*16777216,estimated_peak_bytes=500*1024*1024,
                bootstrap_scope='Natural BASIC SYS idle register witness first; later monitorPC/SP/public-input probe and16cyclemaskedcalibration explicit',scope=__doc__)
    (out/'adapter.json').write_text(json.dumps(config,indent=2)+'\n');compile_plan(out)
    return out


def compile_plan(e):
    project=T.native.live.grid.synchronous_project(e/'timing');T.vice_plan.PROJECT=project
    for label,args in [('dotnet-build',['dotnet','build',str(project),'--nologo']),
                       ('compile-only',['dotnet','run','--no-build','--project',str(project),'--','compile-plan','--plan',str(e/'timing/plan.yaml')])]:
        p=subprocess.run(args,capture_output=True,text=True,timeout=120);(e/'timing'/(label+'.log')).write_text(p.stdout+p.stderr);assert not p.returncode,(label,p.stdout,p.stderr)
    return project


def evaluate(e):
    authenticate_verifier(e);freeze_engine.validate(e);n=loaded(e)
    old_expected,old_catalog=T.semantic.expected,T.FontCatalog
    T.semantic.expected=presentation.expected_geos
    T.FontCatalog=lambda path,native:presentation.preview.pack_catalog((e/'font-pack.bin').read_bytes(),native)
    try:result=T.evaluate(n)
    finally:T.semantic.expected,T.FontCatalog=old_expected,old_catalog
    resources=(n.out/'ntsc-resources.log').read_text(encoding='utf-8-sig')
    for key,value in [('MachineVideoStandard',2),('VICIIModel',3),('MachinePowerFrequency',60),('REU',1),('REUsize',16384),('Drive8TrueEmulation',0)]:
        assert re.search(rf'(?m)^\s*{key}\b[^\r\n]*\b{value}\b',resources),(key,value,resources)
    calibration=(n.out/'calibration.log').read_text(encoding='utf-8-sig')
    assert [int(v)for v in re.findall(r'Stopwatch:\s*(\d+)',calibration,re.I)]==[16]
    assert re.search(r'(?m)^\.;0f08\b',calibration,re.I)
    # Resource/cycle calibration does not turn public-entry timing into a
    # physical IRQ-key-to-photon or worst-case latency claim.
    images=T.native.live.grid.reu_images(n.out/'run');s=n.s;pack=(e/'font-pack.bin').read_bytes();records=[];canonical=None
    for item,measured in zip(n.measurements,result['measurements']):
        ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();before_ram=(n.out/'captures'/(ident+'-interval-before-ram.bin')).read_bytes()
        reu=images[ident];before=images[item['interval_before_REU']];assert len(reu)==len(before)==16777216
        f=presentation.Captured(s,ram,b'',e)
        assert f.get('se_reu_banks',2)==256,'runtime provider must detect all256 configured physical banks'
        if item['mode']<3:assert f.get('se_st_valid',1)==1 and f.get('se_st_request',1)==0,'actual Full styling must be published, not inferred from validity-dependent oracle'
        assert f.get('se_render_caps',1)==3 and f.get('se_hot_caret')==item['expected_caret']
        assert not any(f.get(k,1)for k in('se_hot_pending','se_h_dirty','se_sel_mark'))
        assert f.read(s['se_f_current_name'],f.get('se_f_current_len',1))==b'DIVERSE'
        def history(memory):return memory[s['se_doc_roots']:s['se_doc_roots']+512]+b''.join(memory[s[k]:s[k]+w]for k,w in[('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_clip_token',5),('se_clip_length',3)])
        state=history(ram);assert state==history(before_ram)
        if canonical is None:canonical=state
        assert state==canonical,(ident,'File/view/caret/preview changed canonical history/clipboard')
        assert f.read(s['se_editor_settings'],64)==(e/'editor-defaults.bin').read_bytes()
        current=catalog_identity(f.read(s['se_overlay_ids'],384),s);catalog_state(f.read(s['se_overlay_ids'],384),s)
        assert current==catalog_identity(before_ram[s['se_overlay_ids']:s['se_overlay_ids']+384],s)
        h=f.get('se_gc_handle',1);spans=[];wanted=bytearray(before)
        if h:
            p=ram[s['se_reu_map']+h]
            assert p and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+p]==0xFE
            assert ram[s['se_gc_epoch']:s['se_gc_epoch']+2]==ram[s['se_reu_epoch']:s['se_reu_epoch']+2]
            if item['mode']in(1,2):spans=[(0,22*240),(0x1500,0x1680)]
            elif item['mode']==3:
                spans=[(0,64),(0x200,0xEA88)]
                if item['ui']==4:spans +=[(0xEA88,0xEB69),(0xEB69,0xFBA9)]
            # Mode40 has no blanket cache allowance. Any real writer must be
            # diagnosed from source rather than borrowing another view's span.
            for a,b in spans:wanted[p*65536+a:p*65536+b]=reu[p*65536+a:p*65536+b]
        assert reu==wanted,(ident,'whole16MiB outside exact current-view FE contract; no53 mask')
        assert ram[s['se_gf_state']]==0xA5
        for i,h in enumerate(ram[s['se_gf_state']+1:s['se_gf_state']+3]):
            p=ram[s['se_reu_map']+h];assert h and p and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+p]==0xFD
            raw=pack[i*65536:(i+1)*65536];assert reu[p*65536:p*65536+len(raw)]==raw
        records.append(dict(id=ident,mode=item['mode'],ui=item['ui'],caret=f.get('se_hot_caret'),first_publish_cycles=measured['first_publish_cycles'],settled_cycles=measured['emulated_cycles'],loads=measured['counter_deltas']['se_overlay_loads'],precise_FE_spans=spans,PNG_sha256=sha(n.out/('native-'+ident+'.png'))))
    assert(e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes()
    result.update(status='PASS',frames=records,actual_ntsc_resource_receipt='timing/ntsc-resources.log',calibration_cycles=16,
        exact_whole16MiB_intervals=13,no_analysis53_mask=True,adapter_sha256=sha(__file__),visual_review='pending',scope=__doc__)
    (n.out/'registered-ntsc-result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def free_ports():
    for port in(PORT,*range(9200,9240)):
        with socket.socket()as sock:sock.bind(('127.0.0.1',port))


def run_prepared(e):
    c=authenticate_verifier(e)
    assert not(e/'timing/run').exists(),'preserve completed run; never overwrite'
    free_ports();compile_plan(e);plan=json.loads((e/'timing/plan.yaml').read_text());stop=threading.Event()
    def watch():
        while not stop.wait(.1):
            p=subprocess.run(['ps','-axo','pid=,ppid=,command='],capture_output=True,text=True)
            for line in p.stdout.splitlines():
                if '/x64sc 'in line and '-binarymonitoraddress 127.0.0.1:9100'in line and str(e/'working.d81')in line:
                    x=line.strip().split(None,2);(e/'owned-process.json').write_text(json.dumps(dict(PID=int(x[0]),parent=int(x[1]),command=x[2],binary_port=PORT,text_ports=[9200,9239],match='Both exact ownedworkingdisk andbinarymonitoraddress'),indent=2)+'\n');return
    thread=threading.Thread(target=watch,daemon=True);thread.start()
    try:receipt=run_with_closed_links(run_owned_plan,plan,e/'timing',timeout=2400)
    finally:stop.set();thread.join(timeout=3)
    (e/'owned-manifest.json').write_text(json.dumps(receipt,indent=2)+'\n');owned=json.loads((e/'owned-process.json').read_text())
    p=subprocess.run(['ps','-p',str(owned['PID']),'-o','command='],capture_output=True,text=True);assert str(e/'working.d81')not in p.stdout
    free_ports();(e/'owned-closure.json').write_text(json.dumps(dict(PID=owned['PID'],exact_command_absent=True,owned_ports_released=True),indent=2)+'\n')
    return evaluate(e)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--out',type=Path);p.add_argument('--run-prepared',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args()
    if a.run_prepared:run_prepared(a.run_prepared.resolve())
    elif a.verify:evaluate(a.verify.resolve())
    else:
        out=(a.out or ROOT/'build/ntsc-current-gallery'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
        prepare(a.fixture.resolve(),out);print('PREPARED_NOT_RUN',out,flush=True)
if __name__=='__main__':main()
