"""Seeded public-command data/history soak on an immutable editor fixture.

CPU transport seams only; native capacity/pixels/timing are separate gates.
Canonical GOTO/movement are checked before mutations. This gate does not infer
vertical layout or use emitted geometry as a source/reference model.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,random,subprocess,sys,zipfile
import test_geos_fold_editor as fold

ROOT=fold.ROOT
MUTABLE={3,4,5,6,0x46,0xFE}


def runner(out):
    reference=fold.retention.runner(out)
    p=out/'runner.cpp';source=p.read_text()
    old='(lo!=0x46 && lo!=0xfe)'
    assert source.count(old)==1
    source=source.replace(old,'(lo!=3 && lo!=4 && lo!=5 && lo!=6 && lo!=0x46 && lo!=0xfe)')
    p.write_text(source)
    suffix='.dylib' if sys.platform=='darwin' else '.so';path=out/('soak-runner'+suffix)
    subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC',
        '-I'+str(fold.geos.grid.VENDOR),str(p),str(ROOT/('build/libse_peddle'+suffix)),'-o',str(path)],check=True)
    dll=C.CDLL(str(path))
    for name in ('gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu',
                 'fr_begin','fr_mask','fr_bad','fr_writes','fr_end'):
        getattr(dll,name).argtypes=getattr(reference,name).argtypes
        getattr(dll,name).restype=getattr(reference,name).restype
    return dll


def run(out,previous,rounds,seed):
    frozen,identity=fold.geos.freeze(out,previous)
    fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen
    fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=identity['names']
    dll=runner(out);f=fold.Fixture(out,frozen,dll,True)
    rng=random.Random(seed);events=[];checks=[];high_banks=high_objects=0
    source=fold.geos.native_text('# Soak\rIntro **bold** and *italic*.\r:::region Work\rEditable line here.\r:::end\r'
        ':::basic\r10 PRINT "Hello":REM note\r:::\r:::asm\rstart: lda #$2A\r rts\r:::\rTail **end**.\r')
    data=source

    def owners():return f.read(f.s['se_reu_physical_owner'],256)

    def foreign(before,oldowners,tag):
        nonlocal high_banks,high_objects
        # Authenticate owner/type at the actual DMA, including temporary
        # allocations freed before a checkpoint. Checkpoint owner unions alone
        # would falsely classify those writes as writes to an unowned bank.
        f.audit_end(before,tag);newowners=owners()
        assert f.m.read(f.s['se_reu_logical_owner']+250)==0xA5
        assert f.m.read(f.s['se_reu_map']+250)==249 and newowners[249]==0xA5
        high_banks=max(high_banks,sum(v not in (0,255) for v in newowners))
        high_objects=max(high_objects,sum(v!=0 for v in f.read(f.s['object_owner'],8)))

    def check(tag):
        assert f.merged()==data,(tag,'canonical source',len(data),len(f.merged()))
        assert f.get('se_hot_caret')<=len(data),(tag,'caret outside source')
        assert not any(f.get(n,1) for n in ('se_e_error','se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned','se_b_phase','se_clip_busy')),(tag,'owned job/lease')
        assert f.read(0xC600,1024)==f.shim and f.catalog()==catalog,(tag,'shim/catalog')
        checks.append(dict(tag=tag,length=len(data),caret=f.get('se_hot_caret'),mode=f.get('se_mode',1),pending=f.get('se_hot_pending',1),sha256=hashlib.sha256(data).hexdigest()))
        (out/'progress.json').write_text(json.dumps(dict(checks=checks,events=events),indent=2)+'\n')

    def goto(at):
        assert 0<=at<=len(data)
        line=data[:at].count(b'\r')+1;column=at-(data.rfind(b'\r',0,at)+1)
        f.typed(fold.geos.native_text(f'goto {line}'))
        for _ in range(column):f.command(2)
        assert f.get('se_hot_caret')==at,('public canonical GOTO',line,column,at,f.get('se_hot_caret'))

    def seed_foreign():
        regs,_=f.fast_call(f.s['se_reu_bind'],a=0xA5,x=250,y=249)
        assert not regs.p&1
        pattern=bytes((i*73+29)&255 for i in range(256));f.m.load(0x5000,pattern)
        for offset in (0,0xFF00):
            for n,v,w in [('se_reu_logical',250,1),('se_reu_offset',offset,2),('se_reu_c64',0x5000,2),('se_reu_length',256,2)]:f.put(n,v,w)
            assert not f.call('se_reu_copy',0).p&1

    def clip_bytes():
        token=f.read(f.s['se_clip_token'],5);length=f.get('se_clip_length');result=bytearray()
        for offset in range(0,length,256):
            n=min(256,length-offset);f.m.load(f.s['se_object_id'],token)
            f.put('se_object_offset',offset);f.put('se_object_length',n,2);f.put('se_object_c64',0x8000,2)
            assert not f.call('se_object_copy',1).p&1
            result+=f.read(0x8000,n)
        return bytes(result)

    try:
        f.source(data);seed_foreign();catalog=f.catalog()
        for turn in range(rounds):
            before,oldowners=f.reu(),owners()
            f.audit_begin()
            mode=turn%4;f.command(96+mode)
            f.command(50)
            # Select short native spans at independently chosen line/columns.
            starts=[0]+[i+1 for i,b in enumerate(data) if b==13]
            start=rng.choice(starts)
            end=data.find(b'\r',start);end=len(data) if end<0 else end
            at=start+rng.randrange(min(end-start,12)+1);goto(at)
            op=turn%4;old=data
            if op==0:
                raw=fold.geos.native_text(rng.choice(('aB3','**Q**','\rNext',' *i* ')))
                for byte in raw:f.key(byte)
                data=data[:at]+raw+data[at:];f.command(1)
                assert f.get('se_hot_caret')==at+len(raw)-1
                f.command(16);assert f.merged()==old,('insert group undo',turn)
                f.command(17);assert f.merged()==data,('insert group redo',turn)
            elif op==1:
                count=min(rng.randrange(1,7),len(data)-at)
                if count:
                    f.command(68)
                    for _ in range(count):f.command(2)
                    f.command(69);clip=old[at:at+count]
                    assert clip_bytes()==clip,('canonical clipboard',turn)
                    f.command(50);target=rng.choice(starts);goto(target)
                    f.command(71);data=old[:target]+clip+old[target:]
                    f.command(16);assert f.merged()==old,('paste undo',turn)
                    f.command(17);assert f.merged()==data,('paste redo',turn)
            elif op==2:
                if at<len(data):
                    f.command(4);data=data[:at]+data[at+1:]
                    f.command(1);f.command(16);assert f.merged()==old,('delete undo',turn)
                    f.command(17);assert f.merged()==data,('delete redo',turn)
            else:
                if at:
                    f.command(3);data=data[:at-1]+data[at:]
                    f.command(2);f.command(16);assert f.merged()==old,('backspace undo',turn)
                    f.command(17);assert f.merged()==data,('backspace redo',turn)
            check('transaction-'+str(turn))
            if turn%8==0:
                # Random edits can leave an explicit fence/region incomplete.
                # The independent grammar predicts its documented B5 refusal;
                # the edit itself and all original bytes must still survive.
                _,_,_,error=fold.builder.oracle(data)
                assert error in (0,0xB5),('unexpected host grammar status',error)
                f.command(115,error=error)
                if error:
                    assert f.merged()==data
                    f.key(0x8B);f.key(0x8B)
                    f.render();check('incomplete-fold-refused-'+str(turn))
                else:
                    f.render();check('fold-all-'+str(turn))
                    f.command(116);f.render();check('unfold-all-'+str(turn))
                # Actual read-only preview and exit preserve all canonical data.
                f.command(99);f.command(102);f.render();check('preview-'+str(turn))
                f.key(13);f.render();check('preview-exit-'+str(turn))
            foreign(before,oldowners,'transaction-'+str(turn))
            events.append(dict(turn=turn,operation=op,mode=mode,start=at,delta=len(data)-len(old)))
        check('small-final')
        # A real canonical offset above65535, with bounded logical lines. This
        # is a fresh fixture, not a host patch of object/page/viewport metadata.
        prefix=fold.geos.native_text(''.join('Padding '+str(i)+' '+('X'*140)+'\r' for i in range(440)))
        data=prefix+source
        f.source(data);seed_foreign();catalog=f.catalog();assert len(data)>65536
        for mode in range(4):
            before,oldowners=f.reu(),owners();f.audit_begin();f.command(96+mode)
            target=len(prefix)+len(fold.geos.native_text('# Soak\r'))
            goto(target);raw=fold.geos.native_text('High')
            old=data
            for byte in raw:f.key(byte)
            data=old[:target]+raw+old[target:];f.command(1)
            f.command(16);assert f.merged()==old
            f.command(17);assert f.merged()==data
            check('above64KiB-mode'+str(mode));foreign(before,oldowners,'high-mode'+str(mode))
        result=dict(status='passed',identity=identity,seed=seed,rounds=rounds,events=events,checks=checks,
            final_sha256=hashlib.sha256(data).hexdigest(),checkpoint_max_allocated_banks=high_banks,
            checkpoint_max_objects=high_objects,peak_instructions=f.peak,
            scope='Actual public all-mode seeded canonical/history/clipboard/fold/preview soak + >64KiB edits; byte source model and whole16MiB exact observed typed3/4/5/6/46/FE DMA guards. CPU transport seams; no pixel/native/latency claim. Allocation maxima are checkpoint observations, not transient peaks.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    except BaseException as error:
        (out/'failure.json').write_text(json.dumps(dict(error=repr(error),events=events,checks=checks),indent=2)+'\n')
        (out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
    finally:dll.fr_end();f.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--rounds',type=int,default=128);p.add_argument('--seed',type=lambda s:int(s,0),default=0x53454F53);a=p.parse_args()
    out=ROOT/'build/editor-soak'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for folder in ('tests','tools'):
            for path in sorted((ROOT/folder).glob('*.py')):z.write(path,path.relative_to(ROOT))
    print('RUN',out,flush=True);run(out,a.fixture,a.rounds,a.seed)
