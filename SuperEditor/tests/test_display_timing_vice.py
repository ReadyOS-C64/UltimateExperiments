"""PAL/NTSC VICE stopwatch measurements of the sealed four-mode editor.

Instruction-entry input is explicit: PC/SP/flags and se_e_key are set by the
monitor, then the REAL foreground scheduler completes all work with IRQs on.
This measures service work, not physical keyboard-to-photon latency. No product
patches, CIA timer changes, shared builds, or fabricated reference screenshots.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,shutil,statistics,subprocess,sys,zipfile
import test_geos_fold_native as native
import test_geos_semantic_editor as semantic
from test_fold_retention_vice import Captured
from geos_preview_model import render,FontCatalog
from png_pixels import read_png
from vice_config import step
import vice_plan
from cache_job_build import editor_pair_index

ROOT=native.ROOT
PROBE=0x0F00
GUARD_START=0x0EB0
GUARD_END=0x1000
DEFAULT=ROOT/'build/geos-semantic-editor/20261025T060655745558Z/fixture'


class Plan(native.Plan):
    def __init__(self,e,report,standard,model):
        super().__init__(e,report,'timing');self.standard=standard;self.model=model;self.measurements=[]
        self.cold_end=max(v['end']+1 for v in report['segments'] if v['name'] in ('COLD','BOOT'))
        self.guard_start=max(GUARD_START,self.cold_end)
        prg=(e/'editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little');service=self.s['se_editor_service']
        needle=bytes((0x20,service&255,service>>8))
        returns=[load+i-2+3 for i in range(2,len(prg)-2) if prg[i:i+3]==needle]
        assert len(returns)==1,('unambiguous actual foreground service caller',returns)
        self.service_return=returns[0]
        sequence=self.s['se_e_draw_sequence'];needle=bytes((0xEE,sequence&255,sequence>>8))
        publishes=[load+i-2 for i in range(2,len(prg)-2) if prg[i:i+3]==needle]
        assert len(publishes)==1,('unambiguous resident publication',publishes)
        self.publish_pc=publishes[0]
        def after_calls(name):
            a=self.s[name];pattern=bytes((0x20,a&255,a>>8))
            return [load+i-2+3 for i in range(2,len(prg)-2) if prg[i:i+3]==pattern]
        self.cost_points={k:self.s[k] for k in ('se_overlay_call','jump_overlay','crc_stage','se_ef_prepare','se_geos_navigate','se_editor_render_ui','se_editor_reload')}
        returns=after_calls('jump_overlay');assert len(returns)==1
        self.cost_points['overlay_payload_return']=returns[0]
        result=self.s['call_result'];busy=self.s['se_overlay_busy']
        suffix=bytes((0x8d,result&255,result>>8,0x68,0xaa,0xa9,0,0x9d,busy&255,busy>>8,0xad,result&255,result>>8,0x60))
        at=returns[0]-load+2;assert prg[at:at+len(suffix)]==suffix
        self.cost_points['overlay_complete_rts']=returns[0]+len(suffix)-1
        self.cost_points['crc_returns']=after_calls('crc_stage')
        self.cost_points['fold_prepare_returns']=after_calls('se_ef_prepare')
        self.cost_profile=False
        self.measurement_warp=True
    def plan(self):
        p=super().plan();p['global_defaults']['monitor_port_start']=7900
        p['global_defaults']['monitor_port_span']=1
        p['global_defaults']['timeouts']['step_s']=120
        return p
    def boot(self):
        super().boot()
        path=self.out/'resources.mon';text=path.read_text()
        text=text.replace('"MachineVideoStandard" "1"',f'"MachineVideoStandard" "{self.standard}"')
        text=text.replace('"VICIIModel" "0"',f'"VICIIModel" "{self.model}"')
        text+=f'resourceset "MachinePowerFrequency" "{50 if self.standard==1 else 60}"\n'
        path.write_text(text)
        self.raw('timing_resources',['logname "'+str(self.out/'resources.log')+'"','log on',
            'resourceget "MachineVideoStandard"','resourceget "VICIIModel"',
            'resourceget "MachinePowerFrequency"','resourceget "Drive8TrueEmulation"','warp','log off'])
        self.raw('monitor_help',['logname "'+str(self.out/'monitor-help.log')+'"','log on',
            'help command','help trace','help stopwatch','log off'])
        # Keep the natural BASIC SYS stack witness before any stopwatch
        # measurement explicitly changes PC/SP. Read-only breakpoint/logging.
        # Historical profile subclasses also record their own named witness;
        # keep the common step ID distinct so those plans remain replayable.
        self.raw('timing_natural_startup_idle',['delete',
            f'break exec ${self.idle_pc:04x} if {self.condition(0)}','x','delete',
            f'logname "{self.out / "natural-startup-idle.log"}"','log on','registers','log off'])
    def condition(self,ui):
        pairs=[('se_e_ui',ui),('se_e_job',0),('se_e_redraw',0),('se_e_draw_busy',0),
               ('se_doc_read_locks',0),('se_f_owner',0),('se_input_nmi_pending',0),('se_st_request',0),
               ('se_overlay_busy',0)]
        c=' && '.join(f'(@cpu:${self.s[n]:04x} == ${v:02x})' for n,v in pairs)
        c+=f' && (@cpu:${self.s["se_overlay_busy"]+1:04x} == $00)'
        return c+f' && (@cpu:${self.s["se_input_head"]:04x} == @cpu:${self.s["se_input_tail"]:04x}) && (@cpu:$00c6 == $00)'
    def measure(self,ident,data,mode,*,key=None,full=False,ui=0,category=None):
        # JSR input/render returns to our cold probe, then the real scheduler.
        # Stack lower64B is captured before/after; unused cold neighbors guarded.
        target=self.s['se_editor_input' if key is not None else 'se_editor_render']
        code=bytes((0x20,target&255,target>>8,0x4C,self.s['se_idle']&255,self.s['se_idle']>>8))
        assert PROBE>=self.cold_end and PROBE+len(code)<0x1000
        guard=bytes((i*53+17)&255 for i in range(GUARD_END-self.guard_start))
        log=self.out/('stopwatch-'+ident+'.log')
        captures=self.out/'captures';captures.mkdir(exist_ok=True)
        commands=['delete',f'break exec ${self.idle_pc:04x} if {self.condition(ui if key!=13 else 2)}',
            'x','delete',f'bsave "{captures}/{ident}-stack-before.bin" 0 $0100 $013f',
            f'bsave "{captures}/{ident}-before-ram.bin" 0 $0000 $cfff']
        commands += [f'> {self.guard_start+i:04x} '+guard[i:i+128].hex(' ') for i in range(0,len(guard),128)]
        commands += [f'> {PROBE:04x} '+code.hex(' ')]
        if key is not None:commands += [f'> {self.s["se_e_key"]:04x} {key:02x}',f'> {self.s["se_e_mods"]:04x} 00']
        if full:
            commands += [f'> {self.s["se_r_valid"]:04x} 00',f'> {self.s["se_gc_valid"]:04x} 00 00 00']
            if mode==3 and ui==0:
                # Source GEOS has a separate retained bitmap/caret witness.
                # Clearing only grid-valid flags measures a cache hit, not a
                # full page. Authenticate the addresses from this frozen ABI.
                with zipfile.ZipFile(self.e/'product-sources.zip') as z:
                    gcc=z.read('src/render/geos/caret-cache.inc')
                    gec=z.read('src/render/geos/edit-certificate.inc')
                assert b'GCC_STATE=$CF90' in gcc and b'GCC_VALID=GCC_STATE' in gcc
                assert b'GEC_RECORD=$CFE8' in gec and b'GEC_VALID=GEC_RECORD' in gec
                commands += ['> cf90 00','> cfe8 00',f'> {self.s["se_gc_width"]:04x} 00']
        commands += [f'logname "{log}"','log on',f'registers PC=${PROBE:04x}, SP=$ff, FL=$20',
            'registers',f'trace exec ${self.s["se_editor_service"]:04x}',f'trace exec ${self.service_return:04x}',
            f'trace exec ${self.publish_pc:04x}']
        if self.cost_profile:
            points=[]
            for value in self.cost_points.values():points+=value if isinstance(value,list) else [value]
            commands += [f'trace exec ${pc:04x}' for pc in sorted(set(points))]
        commands += [
            f'break exec ${self.idle_pc:04x} if {self.condition(ui)}',
            'warp on' if self.measurement_warp else 'warp off','warp',
            'stopwatch reset','x','stopwatch','registers','delete','warp','log off','warp on',
            f'bsave "{captures}/{ident}-stack-after.bin" 0 $0100 $013f',
            f'bsave "{captures}/{ident}-probe.bin" 0 ${self.guard_start:04x} $0fff',
            f'bsave "{captures}/{ident}-finished-ram.bin" 0 $0000 $cfff',
            f'bsave "{captures}/{ident}-finished-colors.bin" 0 $d800 $dbe7']
        # The unique final colors file is the existing .NET capture sentinel.
        self.raw(ident+'_timed_coherent',commands)
        self.measurements.append(dict(id=ident,category=category or ident,mode=mode,key=key,full=full,
            source=data.hex(),ui=ui,probe_hex=code.hex(),boundary='JSR public input/render through actual scheduler to quiescent foreground idle',
            probe_guard_hex=guard.hex(),probe_guard_start=self.guard_start))
        self.snapshot(ident,data,mode,ui)


def freeze(source,standard):
    e=native.freeze(source)
    target=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-display-timing-'+standard)
    target.parent.mkdir(parents=True,exist_ok=True);shutil.move(e,target)
    shutil.copytree(ROOT/'build/geos-font-catalog',target/'genuine')
    return target


def scenario(e,standard,model,probe=False,focus='all',cost_profile=False,normal_speed=False):
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),standard,model);data=native.live.grid.fixture()
    n.cost_profile=cost_profile
    n.measurement_warp=not normal_speed
    n.boot();n.open('open_diverse',b'DIVERSE')
    if focus=='geos-full':
        n.typed('enter_geos','mode hires');n.typed('top_mode3','top')
        n.measure('m3-full',data,3,full=True,category='forced-full-repaint')
        return n
    for mode in ([0] if probe else [3] if focus in ('geos','geos-right','geos-warm') else [0,1,2,3]):
        if mode<3:n.mode_to(mode)
        else:n.typed('enter_geos','mode hires')
        n.typed('top_mode'+str(mode),'top')
        n.measure('m'+str(mode)+'-right',data,mode,key=0x1D,category='warm-right')
        if focus=='geos-right':break
        n.measure('m'+str(mode)+'-left',data,mode,key=0x9D,category='warm-left')
        if focus=='geos-warm':
            n.measure('m3-right-again',data,mode,key=0x1D,category='sustained-warm-right')
            break
        if probe:
            n.measure('m0-down',data,mode,key=0x11,category='service-trace-calibration')
            continue
        inserted=native.live.grid.native_text('Q')+data
        n.measure('m'+str(mode)+'-typing',inserted,mode,key=native.live.grid.native_text('Q')[0],category='pending-typing')
        n.send('undo_type'+str(mode),b'\x1a')
        if focus=='geos':continue
        n.measure('m'+str(mode)+'-down',data,mode,key=0x11,category='vertical-down')
        n.measure('m'+str(mode)+'-page',data,mode,key=0x87,category='page-down')
        n.measure('m'+str(mode)+'-scroll',data,mode,key=0x11,category='down-after-page')
        n.measure('m'+str(mode)+'-full',data,mode,full=True,category='forced-full-repaint')
    if not probe and focus not in ('geos-right','geos-warm'):
        n.typed('preview_top','top')
        # Populate F7 normally, time final RETURN including command parse/page.
        n.send('preview_prompt',bytes((0x88,))+native.live.grid.native_text('preview'),ui=2)
        n.measure('preview-first',data,3,key=13,ui=4,category='preview-font-admission')
        n.measure('preview-page',data,3,key=0x87,ui=4,category='preview-page-forward')
        n.measure('preview-back',data,3,key=0x86,ui=4,category='preview-page-back')
        n.measure('preview-repaint',data,3,full=True,ui=4,category='preview-font-hit-repaint')
    return n


def cost_summary(n,text,ident,calls):
    """Pair nested real overlay boundaries; no per-byte trace traffic."""
    c=n.cost_points;stack=[];done=[];crc=None;crcs=[];fold=None;folds=[];other=[]
    for line in text.splitlines():
        m=re.match(r'\.C:([0-9a-f]{4}).*?A:([0-9a-f]{2}) X:([0-9a-f]{2}).*?\s(\d+)\s*$',line,re.I)
        if not m:continue
        pc,a,x=(int(v,16) for v in m.groups()[:3]);t=int(m[4])
        if pc==c['se_overlay_call']:stack.append(dict(id=a,slot=x,entry=t,children=0))
        elif pc==c['jump_overlay']:assert stack;stack[-1]['payload']=t
        elif pc==c['overlay_payload_return']:assert stack;stack[-1]['payload_end']=t
        elif pc==c['overlay_complete_rts']:
            q=stack.pop();q.update(end=t,total=t-q['entry'],admission=q['payload']-q['entry'],payload_inclusive=q['payload_end']-q['payload'])
            q['payload_self']=q['payload_inclusive']-q['children'];done.append(q)
            if stack:stack[-1]['children']+=q['total']
        elif pc==c['crc_stage']:assert crc is None;crc=t
        elif pc in c['crc_returns']:
            assert crc is not None;crcs.append(dict(start=crc,end=t,cycles=t-crc,id=stack[-1]['id'],slot=stack[-1]['slot']));crc=None
        elif pc==c['se_ef_prepare']:fold=t
        elif pc in c['fold_prepare_returns']:
            assert fold is not None;folds.append(t-fold);fold=None
        elif pc in [c[k] for k in ('se_geos_navigate','se_editor_render_ui','se_editor_reload')]:other.append(dict(pc=hex(pc),a=a,x=x,t=t))
    assert not stack and crc is None and len(done)==calls,(ident,'complete overlay trace',len(done),calls)
    names={(b[5],b[6]):p.stem for p in n.e.glob('*.seo') if (b:=p.read_bytes())}
    groups=[]
    for slot,identity in sorted({(q['slot'],q['id']) for q in done}):
        rows=[q for q in done if(q['slot'],q['id'])==(slot,identity)]
        groups.append(dict(slot=slot,id=identity,name=names.get((slot,identity)),calls=len(rows),**{k:sum(q[k] for q in rows) for k in ('admission','payload_self','payload_inclusive','total')}))
    result=dict(status='passed',overlay_calls=len(done),groups=groups,crc=crcs,crc_cycles=sum(q['cycles'] for q in crcs),fold_prepare_cycles=folds,other_entry_events=other,overlay_intervals=done,
        scope='Exact instruction-entry timestamps. Overlay intervals end at final RTS entry, omit final return instruction; nestedself retains small childreturn overhead. CRC ends at actual caller return. Group inclusive intervals nest. No per-byte tracing.')
    (n.out/('cost-profile-'+ident+'.json')).write_text(json.dumps(result,indent=2)+'\n');return result


def evaluate(n):
    out=n.out;s=n.s;fonts={name:(n.e/name).read_bytes() for name in native.live.geos.GEOS_FONTS+('native8.bin',)}
    catalog=FontCatalog(n.e/'genuine/catalog.json',native=fonts['native8.bin'])
    reus=native.live.grid.reu_images(out/'run');palette={};observations=[];viewport=None;catalog_bytes=None
    resources=(out/'resources.log').read_text(encoding='utf-8-sig')
    for name,value in [('MachineVideoStandard',n.standard),('VICIIModel',n.model),('MachinePowerFrequency',50 if n.standard==1 else 60)]:
        assert re.search(rf'{name}[^\r\n]*\b{value}\b',resources),(name,resources)
    for item in n.measurements:
        ident=item['id'];text=(out/('stopwatch-'+ident+'.log')).read_text(encoding='utf-8-sig')
        warp_states=re.findall(r'Warp mode is (on|off)\.',text,re.I)
        assert warp_states==['on' if n.measurement_warp else 'off']*2,(ident,'warp state at both timing boundaries',warp_states)
        cycles=[int(x) for x in re.findall(r'Stopwatch:\s*(\d+)',text,re.I)]
        assert len(cycles)==1 and cycles[0]>0,(ident,'one measured interval',cycles,text)
        service=[];entered=None;published=[]
        for pc,clock in re.findall(r'(?m)^\.C:([0-9a-f]{4})\s+[^\r\n]*?\s+(\d+)\s*$',text,re.I):
            pc=int(pc,16);clock=int(clock)
            if pc==s['se_editor_service']:
                assert entered is None,(ident,'nested or truncated service timestamp')
                entered=clock
            elif pc==n.service_return:
                assert entered is not None and clock>entered,(ident,'unpaired service return')
                service.append(clock-entered);entered=None
            elif pc==n.publish_pc:published.append(clock)
        assert entered is None,(ident,'unfinished service trace')
        cap=out/'captures';ram=(cap/(ident+'-ram.bin')).read_bytes();colors=(cap/(ident+'-colors.bin')).read_bytes();f=Captured(s,ram,colors,n.e);f.colored=True
        before=(cap/(ident+'-before-ram.bin')).read_bytes()
        finished=(cap/(ident+'-finished-ram.bin')).read_bytes()
        def counter(raw,name,width):return int.from_bytes(raw[s[name]:s[name]+width],'little')
        counters={name:(counter(finished,name,width)-counter(before,name,width))%(1<<(8*width))
            for name,width in [('se_overlay_loads',2),('se_overlay_hits',2),('se_overlay_calls',2),
                ('se_reu_dma_calls',2),('se_reu_dma_bytes',3),('se_e_draw_sequence',2)]}
        assert len(published)==counters['se_e_draw_sequence'],(ident,'all resident publication timestamps',published,counters)
        assert published and published[0]<=cycles[0],(ident,'first visible publication')
        data=bytes.fromhex(item['source']);assert native.live.merged(f,reus[ident])==data,(ident,'canonical pending source')
        current_catalog=f.read(s['se_overlay_ids'],6*s['se_overlay_capacity'])
        if 'se_overlay_managed_verification' in s:
            from overlay_catalog_policy import catalog_identity
            current_catalog=catalog_identity(current_catalog,s)
        if catalog_bytes is None:catalog_bytes=current_catalog
        assert current_catalog==catalog_bytes,(ident,'complete catalog changed')
        for order,name in enumerate(json.loads((n.e/'freeze.json').read_text())['catalog']):
            image=(n.e/(name+'.seo')).read_bytes();index=editor_pair_index(image[5],image[6]) if 'catalog_index' in s else order
            handle=f.read(s['se_overlay_asset']+(index>>4),1)[0];bank=ram[s['se_reu_map']+handle]
            assert handle and bank and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==2
            payload=image[36:];at=bank*65536+(index&15)*4096
            assert reus[ident][at:at+len(payload)]==payload,(ident,'full sealed catalog payload',name)
        assert f.read(0xC600,1024)==n.canary
        assert all(f.get(k,1)==0 for k in ('se_e_job','se_e_draw_busy','se_e_redraw','se_doc_read_locks','se_f_owner','se_e_error'))
        assert (cap/(ident+'-stack-before.bin')).read_bytes()==(cap/(ident+'-stack-after.bin')).read_bytes(),(ident,'lower64Bstack')
        guard=bytearray.fromhex(item['probe_guard_hex']);code=bytes.fromhex(item['probe_hex']);lo=item['probe_guard_start'];guard[PROBE-lo:PROBE-lo+len(code)]=code
        assert (cap/(ident+'-probe.bin')).read_bytes()==guard,(ident,'cold probe neighbors')
        if item['ui']==4:
            expected=render(data,f.read(s['se_editor_settings'],64),catalog=catalog,top=f.get('se_v_top'))
            matrix,roles,popup=native.live.geos.grid.logical_ui(f,data);assert popup is None
            bits,attrs=native.live.geos.with_chrome(expected.bitmap,expected.attrs,matrix,roles,fonts['native8.bin'])
        elif item['mode']==3:bits,attrs,_,_=semantic.expected(f,data,fonts)
        else:
            (a,b),_,_,_=native.live.geos.grid.expected(f,data)
            if item['mode']==0:
                assert f.read(0x4000,1000)==a and bytes(v&15 for v in colors)==b
                font=(n.e/'chargen.bin').read_bytes()[0x800:0x1000]
                bits=bytearray(8000);attrs=bytearray(1000)
                for i in range(1000):bits[(i//40)*320+(i%40)*8:(i//40)*320+(i%40)*8+8]=font[a[i]*8:a[i]*8+8];attrs[i]=(b[i]<<4)|6
            else:bits,attrs=a,b
        if item['mode']:
            assert ram[0x6000:0x7F40]==bits and ram[0x4000:0x43E8]==attrs,(ident,'independent bitmap/attrs')
        w,h,pixels=read_png(out/('native-'+ident+'.png'));assert w>=320 and h>=200
        def role_at(x,y):
            attr=attrs[(y//8)*40+x//8];ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8))
            return attr>>4 if ink else attr&15
        if viewport is None:
            candidates=[]
            for yy in range(h-200+1):
                for xx in range(w-320+1):
                    seen={};valid=True
                    for y in range(0,16,2):
                        for x in range(0,320,5):
                            role=role_at(x,y);value=pixels[(yy+y)*w+xx+x]
                            if value!=seen.setdefault(role,value):valid=False;break
                        if not valid:break
                    if valid and len(set(seen.values()))==len(seen):candidates.append((xx,yy))
            matches=[]
            for xx,yy in candidates:
                seen={};valid=True
                for y in range(200):
                    for x in range(320):
                        role=role_at(x,y);value=pixels[(yy+y)*w+xx+x]
                        if value!=seen.setdefault(role,value):valid=False;break
                    if not valid:break
                if valid and len(set(seen.values()))==len(seen):matches.append((xx,yy))
            assert len(matches)==1,(ident,'unique independent PAL/NTSC viewport',matches)
            viewport=matches[0]
        for y in range(200):
            for x in range(320):
                role=role_at(x,y);value=pixels[(viewport[1]+y)*w+viewport[0]+x]
                assert value==palette.setdefault(role,value),(ident,'nativeVICpixels',x,y)
        observations.append(dict(item,emulated_cycles=cycles[0],service_cycles=service,
            service_calls=len(service),service_peak_cycles=max(service) if service else None,
            first_publish_cycles=published[0],publication_cycles=published,counter_deltas=counters,
            cost_profile=cost_summary(n,text,ident,counters['se_overlay_calls']) if n.cost_profile else None,
            caret=f.get('se_hot_caret'),top=f.get('se_v_top'),pending=f.get('se_hot_pending',1)))
    result=dict(status='passed',identity=json.loads((n.e/'freeze.json').read_text()),standard=n.standard,vicii_model=n.model,
        measurements=observations,probe_address=PROBE,cold_end_exclusive=n.cold_end,irq_enabled=True,measurement_warp=n.measurement_warp,
        cost_trace_points=n.cost_points if n.cost_profile else None,
        native_pixels=len(observations)*64000,native_viewport=viewport,scope='Instruction-entry to actual foreground-quiescence cycles; PC/SP/inputfield intervention, not physical keyboard latency. No worst-case bound.',
        service_peak_status='Every actual foreground service entry/return traced on the same non-resetting VICE CPU cycle counter as whole interaction; includes IRQ/VIC/REU stalls, excludes caller JSR6cycles.',
        service_peak_cycles=max((x['service_peak_cycles'] or 0) for x in observations),
        publication_boundary='Exact instruction-entry timestamp of unique resident INC draw_sequence; bitmap/text memory/chrome complete before publication, not physical VIC beam completion. No assumed instruction-completion cycles during IRQ/VIC stalls. Optional styling may publish more frames before quiescence.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,len(observations));return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--prepare',action='store_true');p.add_argument('--probe',action='store_true');p.add_argument('--focus',choices=['all','geos','geos-right','geos-warm','geos-full'],default='all');p.add_argument('--cost-profile',action='store_true');p.add_argument('--normal-speed',action='store_true',help='Disable warp only during measured interactions; boot/setup remain in warp.');p.add_argument('--fixture',type=Path,default=DEFAULT);p.add_argument('--standard',choices=['pal','ntsc','both'],default='both');a=p.parse_args()
    if not a.run and not a.prepare:print('Prepared. --prepare/--run --fixture IMMUTABLE --probe --standard pal');return
    for standard,model,label in [(1,0,'pal'),(2,3,'ntsc')]:
        if a.standard not in (label,'both'):continue
        e=freeze(a.fixture, label);n=scenario(e,standard,model,a.probe,a.focus,a.cost_profile,a.normal_speed);plan=n.plan()
        assert len({x['id'] for x in plan['steps']})==len(plan['steps']),'duplicate plan step'
        (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
        with zipfile.ZipFile(e/'timing-verifier.zip','w',zipfile.ZIP_DEFLATED) as z:
            for module in [Path(__file__),ROOT/'tools/geos_preview_model.py',ROOT/'tests/test_geos_semantic_editor.py']:z.write(module,module.relative_to(ROOT))
        print('PREPARED',n.out,len(n.steps),flush=True)
        if a.run:
            project=native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
            build=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(build.stdout+build.stderr);assert not build.returncode
            vice_plan.run_plan(plan,n.out);evaluate(n)


if __name__=='__main__':main()
