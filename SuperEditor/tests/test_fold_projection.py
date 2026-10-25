"""Actual root/C11/R1/C16 fold projection, frozen products and host oracles."""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
import argparse,json,sys,shutil,hashlib,zipfile
import test_grid_modes as g
import test_fold_builder as builder
from test_folds import action_model
from test_fold_locator import target_model
from redraw_model import Screen,verify_screen,screen_code,native_text
from supermark_model import blocks,inline,lex
ROOT=g.ROOT

def rows_model(data,top,caret,width,nowrap,folds):
    def hidden(p):return next((f for f in folds if f.flags&1 and f.hidden<=p<f.end),None)
    if top>caret:top=0
    enclosing=hidden(top)
    if enclosing:top=enclosing.start
    starts=[top];ends=[];bits=[];p=top;seen=False
    for _ in range(len(data)+24):
        count=0;cr=False
        while True:
            if p==caret:seen=True
            if p==len(data):
                ends.append(p);bits.append(0)
                while len(starts)<22:starts.append(p);ends.append(p);bits.append(0)
                assert seen,('hiddenunrevealedcaret',caret,folds)
                return tuple(starts)+(p,),tuple(ends),tuple(bits)
            byte=data[p];p+=1;count+=1
            if byte==13:cr=True;break
            if not nowrap and count==width:break
        ends.append(p);mark=0
        if cr:
            enclosing=hidden(p)
            if enclosing:p=enclosing.end;mark=1
        bits.append(mark)
        if len(starts)==22:
            if seen:return tuple(starts)+(p,),tuple(ends),tuple(bits)
            starts.pop(0);ends.pop(0);bits.pop(0)
        starts.append(p)
    raise AssertionError('hostprojectiondidnotconverge')

_style_cache={}
def source_styles(data):
    if data in _style_cache:return _style_cache[data]
    styles=bytearray([1])*len(data)
    for e in blocks(data):
        kind=e['kind'];start,end=e['start'],e['end'];base=0x87 if kind==2 else 14 if kind==5 else 15 if kind in(4,6,7,8) else 1
        styles[start:end]=bytes([base])*(end-start)
        if kind==5:
            palette={7:7,8:13,9:5,10:15,11:7,12:3,13:1}
            for a,b,style in lex(data[e['body']:end],e['language'],start=e['body']):styles[a:b]=bytes([palette[style]])*(b-a)
        if kind in(4,5,6):continue
        origin=e['body']
        for token,style,width,a,b in inline(data[origin:end],origin,body_column=(origin-start) or None):
            if token==1:
                for p in range(a+width,b):
                    mask=(styles[p]&0xF0)|(style<<4);styles[p]=mask|(14 if mask&64 else [1,3,7,10][(mask>>4)&3])
    _style_cache[data]=bytes(styles);return bytes(styles)

def expected(f,data,folds,requested_top):
    mode=f.get('se_mode',1);width=[40,60,80][mode];nowrap=f.get('se_l_mode',1);pan=f.get('se_l_pan') if nowrap else 0;caret=f.get('se_hot_caret');mark=f.get('se_sel_mark',1)
    anchors,ends,foldbits=rows_model(data,requested_top,caret,width,nowrap,folds)
    matrix,colors,rect=g.logical_ui(f,data);seen=None;styles=source_styles(data) if f.get('se_st_valid',1) else bytes([1])*len(data)
    lo,hi=sorted((caret,f.get('se_sel_anchor'))) if mark else(0,0);bitmap=bytearray(8000);attrs=bytearray([0x16])*1000
    for row,(start,end) in enumerate(zip(anchors,ends)):
        realend=end-1 if end>start and data[end-1]==13 else end;chars=[];flags=[];roles=[]
        for col in range(width):
            p=start+pan+col;visible=p<=realend;raw=data[p] if p<realend else 32;style=styles[p] if p<realend else 1
            marker=visible and p==realend and foldbits[row]
            flag=(1 if style&128 else 0);role=g.semantic_role(style)
            if marker:raw=0x2B;flag=1;role=2
            under=screen_code(raw)^(128 if flag&1 else 0);glyph=under;ink=1 if marker else style&15
            # The CR marker summarizes [CR,next canonical row anchor), so a
            # nonempty hidden-only selection highlights this same visible cell.
            selected=visible and (lo<=p<hi or (marker and lo<hi and lo<anchors[row+1] and p<hi))
            if selected:flag|=2;glyph^=128;ink=3
            if visible and p==caret and seen is None:flag|=4;glyph=under^128;ink=7 if mark else 3;seen=(row,col)
            chars.append(raw);flags.append(flag if visible else 0);roles.append(role if p<realend or marker else 0)
            if not mode:
                at=(row+2)*40+col
                if not rect or not(rect[1]<=row+2<rect[1]+rect[3] and rect[0]<=col<rect[0]+rect[2]):
                    matrix[at]=glyph if visible else 32;colors[at]=ink if visible else 1
        if mode:
            bits,ink=g.narrow_row(chars,flags,width,f.fonts['narrow5.bin' if mode==1 else 'narrow4.bin'],roles,True);bitmap[(row+2)*320:(row+3)*320]=bits;attrs[(row+2)*40:(row+3)*40]=ink
    if not mode:return(bytes(matrix),bytes(colors)),anchors,ends,foldbits,seen
    ui={(r,c) for r in [0,1,24] for c in range(40)}
    if rect:
        x,y,w,h=rect;ui.update((r,c) for r in range(y,y+h) for c in range(x,x+w))
    for row,col in ui:
        at=row*40+col;code=matrix[at];glyph=f.fonts['native8.bin'][(code&127)*8:(code&127)*8+8];bitmap[row*320+col*8:row*320+col*8+8]=bytes(v^(255 if code&128 else 0) for v in glyph);attrs[at]=((colors[at]&15)<<4)|6
    return(bytes(bitmap),bytes(attrs)),anchors,ends,foldbits,seen

class Fixture(g.Fixture):
    def render(self):
        for _ in range(16):
            r=self.call('se_editor_render');assert not r.p&1,('render',hex(r.a),self.get('se_e_job',1),self.get('se_l_index',1))
            if self.get('se_e_job',1):assert self.get('se_e_job',1) in(7,10);self.settle()
            else:return r
        raise AssertionError('foldrenderdidnotconverge')
    def metadata(self):
        token=self.read(self.s['se_ef_token'],5);count=self.get('se_ef_count',2);data=bytearray()
        for offset in range(0,count*32,1024):
            self.m.load(self.s['se_object_id'],token);self.put('se_object_offset',offset);length=min(1024,count*32-offset);self.put('se_object_length',length,2);self.put('se_object_c64',0x8000,2);assert not self.call('se_object_copy',1).p&1;data+=self.read(0x8000,length)
        return bytes(data)

def main():
    a=argparse.ArgumentParser();a.add_argument('--fixture',type=Path,required=True);args=a.parse_args();out=ROOT/'build/fold-projection'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);frozen=out/'fixture';shutil.copytree(args.fixture,frozen)
    identity=json.loads((frozen/'freeze.json').read_text());assert {'foldcore','foldctl','rangeio'}<=set(identity['names'])
    for n,h in identity['assets'].items():assert hashlib.sha256((frozen/f'build/overlays/{n}.seo').read_bytes()).hexdigest()==h
    g.editor_fixture.ROOT=g.cpu_editor.ROOT=frozen;g.editor_fixture.NAMES=g.cpu_editor.NAMES=identity['names'];dll=g.runner(out);frames=[]
    def check(f,data,folds,tag,allow_fold_writes=False):
        top=f.get('se_v_top');canonical,reu,catalog=f.canonical(),f.reu(),f.catalog();f.render();wanted,anchors,ends,foldbits,seen=expected(f,data,folds,top)
        actual=tuple(int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little') for i in range(22))+(f.get('se_v_bottom'),)
        assert actual==anchors,(tag,'anchors',actual,anchors)
        actualends=tuple(int.from_bytes(f.read(f.s['se_ef_paint_ends']+i*3,3),'little') for i in range(22));actualbits=f.get('se_ef_fold_rows')
        # Paintends are a derived fold projection, consumed only while the
        # checked map is valid. Plain incremental text rendering may leave the
        # inactive table unchanged; canonical anchors/pixels remain exact.
        if f.get('se_ef_valid',1):assert actualends==ends,(tag,'paintends',actualends,ends)
        assert actualbits==sum(v<<i for i,v in enumerate(foldbits)),(tag,'foldbits',hex(actualbits),foldbits)
        mode=f.get('se_mode',1)
        if mode:
            assert f.read(0x6000,8000)==wanted[0],(tag,'bitmap',next((i,a,b) for i,(a,b) in enumerate(zip(f.read(0x6000,8000),wanted[0])) if a!=b))
            assert f.read(0x4000,1000)==wanted[1],(tag,'attributes')
        else:verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),Screen(*wanted,anchors,seen),tag=tag)
        assert f.canonical()==canonical and f.merged()==data and f.catalog()==catalog
        if allow_fold_writes:
            after=f.reu();want=bytearray(reu);handle=f.get('se_gc_handle',1)
            if handle:
                assert f.m.read(f.s['se_reu_logical_owner']+handle)==0xFE
                physical=f.m.read(f.s['se_reu_map']+handle);assert f.m.read(f.s['se_reu_physical_owner']+physical)==0xFE
                at=physical*65536;want[at:at+5280]=after[at:at+5280]
            token=f.read(f.s['se_ef_token'],5);assert f.m.read(f.s['object_owner']+token[0])==0x46
            length=len(folds)*32
            for i in range((length+65535)//65536):
                logical=f.m.read(f.s['object_extents']+token[0]*16+i);physical=f.m.read(f.s['se_reu_map']+logical)
                assert f.m.read(f.s['se_reu_logical_owner']+logical)==0x46 and f.m.read(f.s['se_reu_physical_owner']+physical)==0x46
                at=physical*65536;n=min(65536,length-i*65536);want[at:at+n]=after[at:at+n]
            assert after==want,(tag,'outsideFE/actualfoldrecordsREUchanged')
            assert f.metadata()==b''.join(x.bytes() for x in folds)
        else:assert f.reu_safe(reu,tag)
        assert f.get('se_f_owner',1)==0 and f.get('se_doc_read_locks',1)==0 and f.read(0xC600,1024)==f.shim
        frames.append(dict(tag=tag,mode=mode,top=anchors[0],caret=f.get('se_hot_caret'),foldbits=actualbits));(out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
    data=native_text('# First\rOne hidden line.\rAnother hidden line.\r# Second\rVisible last line.\r');tree,_,_,err=builder.oracle(data);assert not err
    f=Fixture(out,frozen,dll,True)
    try:
        f.source(data);folds=[replace(x) for x in tree];f.typed(native_text('fold'));folds,_=action_model(folds,0,0,0,f.get('se_ef_motion',4),0)
        assert f.get('se_ef_valid',1) and f.metadata()==b''.join(x.bytes() for x in folds)
        check(f,data,folds,'first-actual40-collapsed')
        for mode in [1,2,0]:f.command(96+mode);check(f,data,folds,f'first-mode{mode}-collapsed')
        f.command(114);folds,_=action_model(folds,2,0,0,f.get('se_ef_motion',4),0);check(f,data,folds,'first-expanded')
        f.command(113);folds,_=action_model(folds,1,0,0,f.get('se_ef_motion',4),0);check(f,data,folds,'first-recollapsed')
        f.command(37)
        folds,_=action_model(folds,5,0,f.get('se_hot_caret'),f.get('se_ef_motion',4),f.get('se_hot_caret'))
        check(f,data,folds,'first-DOWN-hidden-auto-reveal',allow_fold_writes=True)
        assert f.metadata()==b''.join(x.bytes() for x in folds)
        f.close();f=None
        # The persistent navigation index shares the phase union with folds.
        # Exercise the actual public GOTO path both before and after C19/C11
        # claims, then cut a canonical selection spanning invisible body text.
        for mode in range(3):
            data=native_text('# First\rOne hidden line.\rAnother hidden line.\r# Second\rVisible last line.\r')
            tree,_,_,error=builder.oracle(data);assert not error
            f=Fixture(out,frozen,dll,True);f.source(data)
            if mode:f.command(96+mode)
            f.typed(native_text('goto 4'));assert f.get('se_hot_caret')==46
            assert f.get('se_i_ready',1), 'actual GOTO must warm the index'
            f.typed(native_text('goto 2'));assert f.get('se_hot_caret')==8
            f.typed(native_text('fold'));folds,_=action_model(tree,0,0,8,f.get('se_ef_motion',4),8)
            check(f,data,folds,f'index-{mode}-collapse')
            f.typed(native_text('fold'));folds,_=action_model(folds,0,0,0,f.get('se_ef_motion',4),0)
            assert f.get('se_hot_caret')==8
            check(f,data,folds,f'index-{mode}-restore-inner-caret')
            f.typed(native_text('fold'));folds,_=action_model(folds,0,0,8,f.get('se_ef_motion',4),8)
            check(f,data,folds,f'index-{mode}-recollapse')
            f.command(68);f.typed(native_text('goto 4'));assert f.get('se_hot_caret')==46
            check(f,data,folds,f'index-{mode}-selected-hidden-source')
            f.typed(native_text('copy'));assert f.get('se_clip_length')==46
            check(f,data,folds,f'index-{mode}-copy-hidden-source')
            f.typed(native_text('cut'));assert f.merged()==data[46:]
            check(f,data[46:],[],f'index-{mode}-cut-hidden-source')
            assert not f.get('se_ef_valid',1) #read-only key guard invalidates before publication
            f.typed(native_text('undo'));assert f.merged()==data
            check(f,data,[],f'index-{mode}-undo-byteexact')
            f.close();f=None
        geometry=[('empty',b''),('plain',native_text('plain source\r')*30),
            ('nested',native_text('# Outer\rintro\r## Inner\rbody\r:::region Detail\rinside\r:::asm\rloop: lda #$20 ; comment\r:::\r:::end\r# Tail\rtext\r')),
            ('cross',native_text(':::region Region\r# Heading\rbody\r:::end\rheading tail\r# Last\rvisible\r')),
            ('lastrow',native_text('prefix\r')*21+native_text(':::region Last\rhidden\r:::end\rafter\r'))]
        for mode,width in [(0,40),(1,60),(2,80)]:
            fixtures=geometry+[(f'exact{n}',native_text('# ')+b'A'*(n-2)+native_text('\rhidden body\r# Tail\rvisible\r')) for n in [width-1,width,width+1,width*2+3]]
            for label,data in fixtures:
                tree,_,_,error=builder.oracle(data);assert not error
                f=Fixture(out,frozen,dll,True);f.source(data)
                if mode:f.command(96+mode)
                motion=f.get('se_ef_motion',4);f.command(115);folds,_=action_model(tree,3,0,0,motion,0)
                assert f.metadata()==b''.join(x.bytes() for x in folds)
                check(f,data,folds,f'geometry-{mode}-{label}-collapsed')
                f.command(116);folds,_=action_model(folds,4,0,0,f.get('se_ef_motion',4),0)
                check(f,data,folds,f'geometry-{mode}-{label}-expanded')
                f.close();f=None
        result=dict(status='passed',identity=identity,frames=frames,limits=['ActualrootC11/R18projection andR1/C16pixels; CPUROMreadseam documentedbygridfixture, nonativeclaim.'])
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e)),indent=2)+'\n');raise
    finally:
        if f is not None:f.close()
if __name__=='__main__':main()
