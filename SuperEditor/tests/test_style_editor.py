"""Actual editor/style idle integration, independent full source40 color oracle.

Default is preparation only. --run freezes the current editor/sidecars first,
then executes actual resident idle/input/render/C14/R14 code on Peddle. ROM
startup SEQ imports are the existing fixture substitution; no VICE/IRQ claim.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, shutil, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import cpu_editor, editor_fixture
from redraw_model import Screen, native_text, screen_code, source40, verify_screen
from overlay_catalog_policy import catalog_identity
from supermark_model import blocks, inline, lex
from supermark_probe import petscii

ROLE_COLORS = [1,3,7,10,14,1,1,7,13,5,15,7,3,1]

REQUIRED = ['se_style_idle', 'se_style_input', 'se_fs_end', 'se_f_owner',
            'se_st_busy', 'se_st_valid', 'se_st_request', 'se_st_descriptor',
            'se_st_generation', 'se_st_cache_generation', 'se_st_cache_valid',
            'se_fs_owned', 'se_fs_active', 'se_st_key', 'se_st_rows', 'st_phase',
            'st_pos', 'se_v_bottom', 'se_idle', 'image_slot', 'se_overlay_capacity']


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze_current(out):
    names = list(cpu_editor.NAMES)
    assert {'styler', 'viewsource', 'lexical'} <= set(names), ('style assets absent', names)
    assert len(names) == len(set(names)), ('duplicate actual catalog names', names)
    frozen = out / 'fixture'
    (frozen / 'build/overlays').mkdir(parents=True)
    for name in ['editor.prg', 'editor-report.json', 'editor.lbl', 'editor.map',
                 'editor-bindings.json', 'disk-manifest.json']:
        shutil.copy2(ROOT / 'build' / name, frozen / 'build' / name)
    for name in names:
        shutil.copy2(ROOT / f'build/overlays/{name}.seo',
                     frozen / f'build/overlays/{name}.seo')
    report = json.loads((frozen / 'build/editor-report.json').read_text())
    assert not (missing := set(REQUIRED+['st_lex_phase']) - report['symbols'].keys()), sorted(missing)
    identity = dict(names=names, prg_sha256=sha(frozen / 'build/editor.prg'),
        assets={n:sha(frozen / f'build/overlays/{n}.seo') for n in names})
    # Detect mutation while taking the freeze; a build is never invoked here.
    assert identity['prg_sha256'] == sha(ROOT / 'build/editor.prg')
    for name, digest in identity['assets'].items():
        assert digest == sha(ROOT / f'build/overlays/{name}.seo'), name
    (frozen / 'freeze.json').write_text(json.dumps(identity, indent=2)+'\n')
    return frozen, identity


def rows_for(source, top, nowrap):
    """Derive23 anchors from canonical bytes, independently of renderer maps."""
    rows = [top]
    for _ in range(22):
        p = rows[-1]
        if nowrap:
            end = source.find(b'\r', p)
            p = len(source) if end < 0 else end + 1
        else:
            for _ in range(40):
                if p == len(source): break
                value = source[p]
                p += 1
                if value == 13: break
        rows.append(p)
    return rows


def semantic_plan(source, rows, nowrap, pan, lexical=False):
    """Independent parser-model spans projected onto source positions,880cells."""
    styles = bytearray(len(source))
    for event in blocks(source):
        kind = event['kind']
        base = 0x82 if kind == 2 else 4 if kind == 5 else 10 if kind in (4, 6, 7, 8) else 0
        start, end = event['start'], event['end']
        styles[start:end] = bytes([base]) * (end-start)
        if kind == 5 and lexical:
            origin=event['body']
            # The independent stream lexer emits exact canonical source spans.
            # These are full-word PETSCII BASIC/assembler, never PRG decoding.
            palette={7:7,8:8,9:9,10:10,11:7,12:12,13:0}
            for a,b,style in lex(source[origin:end],event['language'],start=origin):
                styles[a:b]=bytes([palette[style]])*(b-a)
        if kind in (4, 5, 6): continue
        origin = event['body']
        for token, style, width, a, b in inline(source[origin:end], origin,
                                body_column=(origin-start) or None):
            if token != 1: continue
            for p in range(a+width, b):
                mask = (styles[p] & 0xF0) | (style << 4)
                styles[p] = mask | (4 if mask & 64 else [0, 1, 2, 3][(mask >> 4) & 3])
    plan = bytearray(880)
    for row, (start, stop) in enumerate(zip(rows, rows[1:])):
        for col in range(40):
            p = start + (pan if nowrap else 0) + col
            if p < min(stop, len(source)) and source[p] != 13:
                plan[row*40+col] = styles[p]
    return bytes(plan)


class Fixture(editor_fixture.EditorFixture):
    evidence = None
    frames = []
    with_lexical = False

    def __init__(self):
        self.idle_steps = 0
        self.idle_peak = 0
        super().__init__()

    def close(self):
        if sys.exc_info()[0] is not None and self.evidence is not None:
            # Preserve the first actual failed state before releasing its CPU.
            target = self.evidence / 'failed-state'
            if not target.exists():
                target.mkdir()
                (target/'state.json').write_text(json.dumps(dict(
                    fields=self.debug(),symbols=self.s,
                    expected_source_hex=getattr(self,'last_expected',b'').hex()),indent=2)+'\n')
                (target/'c64.bin').write_bytes(self.read(0,65536))
                (target/'reu.bin').write_bytes(self.reu_image())
        super().close()

    def tick(self):
        """One real foreground loop iteration, including its input priority."""
        m = self.m
        for name, value in [('a', 0), ('x', 0), ('y', 0), ('p', 0x24),
                            ('sp', 0xFF), ('pc', self.s['se_idle'])]:
            getattr(m.lib, 'zeropage_peddle_set_'+name)(m.handle, value)
        for count in range(250000):
            m.lib.zeropage_peddle_step_instruction(m.handle)
            if m.regs().pc == self.s['se_idle']:
                self.idle_steps += 1
                self.idle_peak = max(self.idle_peak, count+1)
                assert self.get('se_e_job', 1) != 10, 'style must not claim editor job10'
                assert self.read(0xC600, 1024) == self.shim
                return
        raise AssertionError(('idle iteration did not return', hex(m.regs().pc)))

    def queued(self, byte, mods=0):
        head = self.get('se_input_head', 1)
        assert (head+1)&63 != self.get('se_input_tail', 1)
        for name, value in [('se_input_chars', byte), ('se_input_mods', mods),
                            ('se_input_matrix', 0x40)]:
            self.m.write(self.s[name]+head, value)
        self.put('se_input_head', (head+1)&63, 1)

    def finish_style(self, valid=True):
        for _ in range(100000):
            if (not self.get('se_e_job', 1) and not self.get('se_e_redraw', 1)
                and self.get('se_f_owner', 1) != 2
                and self.get('se_st_request', 1) != 1):
                assert bool(self.get('se_st_valid', 1)) == valid
                return
            self.tick()
        raise AssertionError(('style idle did not converge', self.debug()))

    def begin_style(self):
        # A real render schedules the derived request; stop at actual acquisition.
        self.render()
        for _ in range(100):
            if self.get('se_f_owner', 1) == 2:
                assert self.get('se_st_busy', 1) and self.get('se_fs_owned', 1)
                return
            self.tick()
        raise AssertionError(('style did not acquire phase', self.debug()))

    def until_lexical(self,phase):
        assert self.with_lexical
        for _ in range(100000):
            assert self.get('se_f_owner',1)==2 and self.get('se_st_busy',1)
            if self.get('st_lex_phase',1)==phase:return
            self.tick()
        raise AssertionError(('lexical phase did not arrive',phase,self.debug()))

    def debug(self):
        fields=[('se_e_job',1),('se_e_redraw',1),
            ('se_e_ui',1),('se_e_error',1),('se_f_owner',1),('se_st_busy',1),
            ('se_st_valid',1),('se_st_request',1),('se_doc_read_locks',1),
            ('se_fs_owned',1),('st_phase',1),('st_pos',3)]
        if self.with_lexical:fields.append(('st_lex_phase',1))
        return {n:self.get(n,w) for n,w in fields}

    def merged(self):
        data = self.document()
        if not self.get('se_hot_ready',1): return data
        base = self.get('se_hot_base')
        gap = (self.read(0x9200, self.get('se_hot_left',2)) +
               self.read(0x9200+self.get('se_hot_right',2),
                         2048-self.get('se_hot_right',2)))
        return data[:base]+gap+data[base+self.get('se_hot_old_length'):]

    def canonical(self):
        return self.read(self.s['se_doc_roots'],512)+b''.join(
            self.read(self.s[n],w) for n,w in [('se_doc_meta',15),
            ('se_doc_generation',2),('se_doc_length',3),('se_hot_ready',1),
            ('se_hot_pending',1),('se_hot_base',3),('se_hot_caret',3),
            ('se_hot_left',2),('se_hot_right',2),('se_sel_mark',13),
            ('se_h_current',4),('se_h_saved',4),('se_h_end',2),
            ('se_h_cursor',2),('se_h_counter',4)])+self.read(0x9200,2048)

    def reu_image(self):
        return bytes(self.m.lib.zeropage_peddle_read_reu(self.m.handle,i)
                     for i in range(32*65536))

    def catalog(self):
        # The six fixed-entry arrays are immutable identity except for the
        # declared managed-verification bit on published slot bytes.
        raw=self.read(self.s['se_overlay_ids'],6*self.s['se_overlay_capacity'])
        return catalog_identity(raw,self.s)

    def expected(self, data, styled=True):
        top, caret = self.get('se_v_top'), self.get('se_hot_caret')
        mode, pan = self.get('se_l_mode',1), self.get('se_l_pan')
        mark, anchor = bool(self.get('se_sel_mark',1)), self.get('se_sel_anchor')
        base = source40(data, top, caret, marked=mark, anchor=anchor,
            pending=bool(self.get('se_hot_pending',1)), dirty=bool(self.get('se_h_dirty',1)),
            error=self.get('se_e_error',1),history_fault=bool(self.get('se_h_fault',1)),
            trimmed=bool(self.get('se_h_trimmed',2)))
        rows = rows_for(data,top,mode)
        plan = semantic_plan(data,rows,mode,pan,self.with_lexical) if styled else bytes(880)
        matrix, colors = bytearray(base.matrix), bytearray(base.colors)
        matrix[80:960], colors[80:960] = bytes([32])*880, bytes([1])*880
        lo, hi = sorted((anchor,caret)) if mark else (caret,caret)
        seen = None
        for row,(start,stop) in enumerate(zip(rows,rows[1:])):
            end = stop
            if mode and end>start and data[end-1]==13: end-=1
            for col in range(40):
                p = start+(pan if mode else 0)+col
                if mode:
                    if p>end: continue
                elif p>len(data) or (p>=stop and p!=len(data)): break
                eof, cr = p==len(data), p<len(data) and data[p]==13
                glyph = 32 if eof or cr else screen_code(data[p])
                cell = row*40+col
                # CR/EOF/filler are ordinary plan cells, even beneath headings.
                style = plan[cell] if not eof and not cr else 0
                glyph ^= style&128
                ink = ROLE_COLORS[style&15]
                under = glyph
                if lo<=p<hi: glyph^=128; ink=3
                if p==caret and seen is None:
                    glyph=under^128; ink=7 if mark else 3; seen=(row,col)
                matrix[80+cell],colors[80+cell]=glyph,ink
                if not mode and (eof or cr):break
        return Screen(bytes(matrix),bytes(colors),tuple(rows),seen),plan

    def check(self, data, tag, styled=True):
        self.last_expected=data
        assert self.merged()==data,(tag,'canonical merged source')
        expected, plan = self.expected(data,styled)
        verify_screen(self.read(0x4000,1000),self.read(0xD800,1000),expected,tag=tag)
        anchors=tuple(int.from_bytes(self.read(self.s['se_v_rows']+i*3,3),'little')
                      for i in range(22))+(self.get('se_v_bottom'),)
        assert anchors==expected.anchors,(tag,'source anchors')
        if styled:
            actual=self.read(0x4400,880)
            mode=self.get('se_l_mode',1)
            pan=self.get('se_l_pan') if mode else 0
            for row,(start,stop) in enumerate(zip(anchors,anchors[1:])):
                end=stop
                if mode and end>start and end<=len(data) and data[end-1]==13:end-=1
                for col in range(40):
                    position=start+pan+col
                    if position<min(end,len(data)) and data[position]!=13:
                        cell=row*40+col
                        assert actual[cell]==plan[cell],(tag,'live plan cell',cell)
        assert self.get('se_f_owner',1)==0 and not self.get('se_fs_owned',1)
        assert self.read(0xC600,1024)==self.shim
        self.frames.append(dict(tag=tag,source_bytes=len(data),styled=styled,
            top=self.get('se_v_top'),pan=self.get('se_l_pan'),
            mode=self.get('se_l_mode',1),caret=self.get('se_hot_caret')))

    def remove_asset(self, slot, identity=14):
        capacity=self.s['se_overlay_capacity']
        index=next(i for i in range(capacity)
            if self.m.read(self.s['se_overlay_ids']+i)==identity and
               self.m.read(self.s['image_slot']+i)&0x7f==slot)
        self.m.write(self.s['se_overlay_ids']+index,0)
        self.m.write(self.s['se_overlay_active']+slot,0)
        return index


def run(out, previous=None):
    if previous is None:
        frozen, identity = freeze_current(out)
    else:
        frozen=out/'fixture';shutil.copytree(previous,frozen)
        identity=json.loads((frozen/'freeze.json').read_text())
        assert sha(frozen/'build/editor.prg')==identity['prg_sha256']
        for name,digest in identity['assets'].items():
            assert sha(frozen/f'build/overlays/{name}.seo')==digest
    editor_fixture.ROOT = cpu_editor.ROOT = frozen
    editor_fixture.NAMES = cpu_editor.NAMES = identity['names']
    Fixture.evidence=out
    Fixture.frames=[]
    Fixture.with_lexical='lexical' in identity['names']
    cases=[];allfixtures=[];immutable_passes=0;catalog_checks=0
    def fixture(data):
        f=Fixture();f.source(data,banks=2,physical=32)
        # source() deliberately resets BSS. This CPU fixture explicitly enters
        # the running foreground state that native startup publishes.
        f.put('se_status',1,1)
        allfixtures.append(f)
        return f
    def finish_stable(f,data,tag):
        nonlocal immutable_passes,catalog_checks
        # Source paint has priority; derived selection bounds settle before the
        # read-only style interval. Keep the exact entire selection state guard.
        f.render()
        canonical,reu,diag=f.canonical(),f.reu_image(),f.read(0x8800,128)
        catalog=f.catalog()
        f.finish_style();f.check(data,tag)
        assert f.canonical()==canonical,(tag,'style changed canonical state')
        assert f.reu_image()==reu,(tag,'style changed REU')
        assert f.read(0x8800,128)==diag,(tag,'style changed diagnostics prefix')
        assert f.catalog()==catalog,(tag,'style changed admitted catalog metadata')
        assert f.get('se_doc_read_locks',1)==0
        immutable_passes+=1
        catalog_checks+=1
    texts=['', '# Mixed *heading* **strong** @@code@@\nplain *emphasis*\n',
        '**outer *inner* outer** *outer **inner** outer*\n- list\n12. ordered\n',
        ':::basic\n10 PRINT "*literal*"\n20 GOTO 10\n:::\n:::asm\nloop: lda #$ff\n sta $d020\n:::\n',
        ':::region Title\n## Inside\n£*literal£* *unclosed\n:::end\n',
        'x'*40+'\n# Exact boundary\n'+'line\n'*25]
    if Fixture.with_lexical:
        texts += [
            ':::basic\n10PRINT"HELLO":GOTO10\n20IFA1=1THENPRINTLEFT$("X",1)\n30REM PRINT:DATA"GOTO"\n40DATA"X:Y",PRINT:PRINT.5,3.14E-2,5.\n:::\n',
            ':::basic\n10print"lower spelling":goto10\n20 PRINT"unterminated\n30 REM "PRINT" + 123\n40 DATA 12,"A:B",PRINT:PRINT 42\n:::\n',
            ':::asm\nlabel: lda #$0f\n@local: .byte %1010,123\n .segment "CODE" ; comment lda #1\n .word label+1\n .asciiz \'Text\'\n unknown: UNKNOWN $G %2\n:::\n',
            ':::text\n10PRINT"not a BASIC fence"\nlabel: lda #$12 ; still plain code\n:::\n',
            ':::asm\nlabel: '+(' '*120)+'lda #$1234 ; cross128 packet\n .byte "unterminated\n:::\n']
    for index,text in enumerate(texts):
        data=petscii(text);f=fixture(data)
        try:
            finish_stable(f,data,f'fixture{index}')
        finally:f.close()
    cases.append('independent live-cell plan/full screen plus23 source anchors')

    if Fixture.with_lexical:
        # Native high/unsupported bytes stay canonical raw text, never tokenized
        # PRG BASIC; wrap/control display follows the established source oracle.
        data=petscii(':::basic\n10PRINT"')+bytes([0,10,0x80,0x93,0xCB,0xFF])+petscii('"\n20 REM native bytes\n:::\n')
        f=fixture(data)
        try:finish_stable(f,data,'lexical-native-highbytes')
        finally:f.close()
        cases.append('BASIC REM/DATA/string/number/operator and assembler token palettes; rawhighbytes preserved')

        # A real document offset beyond64KiB and a token across the worker's
        #128-byte packet boundary, independently projected in both layouts.
        prefix=petscii('prefix\n')*9400
        opener=petscii(':::asm\n')
        line=petscii('label: '+(' '*120)+'lda #$1234 ; crosspacket token\n')
        data=prefix+opener+line+petscii(' .word label+1\n:::\n# After\n')
        body=len(prefix)+len(opener)
        assert body>65536 and line[127:130]==petscii('lda')
        f=fixture(data)
        try:
            f.position(body+127);finish_stable(f,data,'lexical-offset24-wrap')
            f.command(77);finish_stable(f,data,'lexical-offset24-nowrap')
            before=f.get('se_l_pan');f.command(75)
            assert f.get('se_l_pan')==before+20
            finish_stable(f,data,'lexical-offset24-manualpan')
            cases.append('actual24bit code anchors / wrapped line / logicalpan / cross128 keyword')
        finally:f.close()

        # Changes inside an assembler string retain their raw bytes even when
        # quotes become malformed; actual undo/redo must repaint derived colors.
        original=petscii(':::asm\nlabel: lda #$20 ; comment\n.byte "Text",1\n:::\n')
        f=fixture(original)
        try:
            f.finish_style();position=original.index(petscii('Text'))+2
            f.position(position);f.key(34)
            edited=original[:position]+b'"'+original[position:]
            assert f.get('se_hot_pending',1)
            finish_stable(f,edited,'lexical-quote-edit')
            f.command(16);finish_stable(f,original,'lexical-quote-undo')
            f.command(17);finish_stable(f,edited,'lexical-quote-redo')
            cases.append('actual code-line edit/undo/redo with malformed quote remains sourceeditable')
        finally:f.close()

        # Cancellation while the C15 scan is live must release only its own
        # lease before the queued ordinary byte reaches the actual hot editor.
        original=petscii(':::basic\n10 PRINT "')+b'A'*300+petscii('"\n20 GOTO 10\n:::\n')
        position=len(petscii(':::basic\n'))
        f=fixture(original)
        try:
            f.position(position);f.begin_style();f.until_lexical(2)
            assert not f.call('se_doc_read_acquire').p&1
            f.queued(ord('Q'));f.tick()
            assert f.get('se_f_owner',1)==0 and not f.get('se_fs_owned',1)
            assert not f.get('se_st_busy',1) and not f.get('st_lex_phase',1)
            assert f.get('se_doc_read_locks',1)==1
            edited=original[:position]+b'Q'+original[position:]
            assert f.merged()==edited
            assert not f.call('se_doc_read_release').p&1
            f.settle();finish_stable(f,edited,'lexical-active-input-cancel')
            cases.append('actual input priority cancels activeC15 scan, foreignlease retained')
        finally:f.close()

        for phase,label in [(None,'missing-C15-initial'),(3,'missing-C15-duringpaint')]:
            data=petscii(':::asm\nlabel: lda #$1234 ; comment\n:::\n');f=fixture(data)
            try:
                f.begin_style()
                if phase is not None:f.until_lexical(phase)
                assert not f.call('se_doc_read_acquire').p&1
                f.remove_asset(1,15)
                canonical,reu=f.canonical(),f.reu_image()
                catalog=f.catalog()
                f.finish_style(valid=False)
                assert f.get('se_st_request',1)==0x80
                assert f.get('se_f_owner',1)==0 and not f.get('st_lex_phase',1)
                assert not f.get('se_fs_owned',1) and f.get('se_doc_read_locks',1)==1
                assert f.canonical()==canonical and f.reu_image()==reu
                assert f.catalog()==catalog,(label,'changed admitted catalog metadata')
                catalog_checks+=1
                f.render();f.check(data,label,styled=False)
                calls=f.get('se_overlay_calls',2)
                for _ in range(4):f.tick()
                assert f.get('se_overlay_calls',2)==calls,'failed exactcontext must not retry'
                assert not f.call('se_doc_read_release').p&1
                cases.append(label+' plainfallback/request80/foreignlease cleanup')
            finally:f.close()

    data=petscii('# H\nplain **strong** *body*\n:::asm\nlda #$20\n:::\n')
    f=fixture(data)
    try:
        f.finish_style();f.position(12)
        inserted=petscii('**Pending**')
        for byte in inserted:f.key(byte)
        data=data[:12]+inserted+data[12:]
        assert f.get('se_hot_pending',1)
        finish_stable(f,data,'pending')
        # Actual reverse mark and cursor-only paints must restore styled underlay.
        f.command(68);f.command(1);finish_stable(f,data,'reverse-mark')
        f.command(50);finish_stable(f,data,'unmark')
        f.command(77);finish_stable(f,data,'logical-no-wrap')
        f.command(75);finish_stable(f,data,'logical-pan')
        cases.append('pending noflush / reversed selection / caret underlay / nowrap pan')
    finally:f.close()

    data=petscii('*'+('a'*66000)+'* closing\n# After\n')
    f=fixture(data)
    try:
        finish_stable(f,data,'closer-beyond64KiB')
        cases.append('actual long-line closer beyond64KiB styles visible source')
    finally:f.close()

    # Every normal input cancels derived work before executing the queued byte.
    f=fixture(petscii('# Before\ntext\n'))
    try:
        f.begin_style();assert not f.call('se_doc_read_acquire').p&1
        assert f.get('se_doc_read_locks',1)==2
        f.queued(ord('Q'));f.tick()
        assert f.get('se_input_head',1)==f.get('se_input_tail',1)
        assert f.get('se_f_owner',1)==0 and not f.get('se_fs_owned',1)
        assert not f.get('se_st_busy',1) and not f.get('se_st_valid',1)
        assert f.get('se_doc_read_locks',1)==1
        assert f.merged()==b'Q'+petscii('# Before\ntext\n')
        assert not f.call('se_doc_read_release').p&1
        f.settle()
        finish_stable(f,b'Q'+petscii('# Before\ntext\n'),'queued-input-cancellation')
        cases.append('actual root queued input cancels own stylelease preserves foreignlease')
    finally:f.close()

    for slot,label in [(1,'missing-C14'),(0,'missing-R14')]:
        data=petscii('# Failure\nplain *source*\n');f=fixture(data)
        try:
            f.begin_style();assert not f.call('se_doc_read_acquire').p&1
            f.remove_asset(slot)
            canonical,reu=f.canonical(),f.reu_image()
            catalog=f.catalog()
            f.tick()
            assert f.get('se_f_owner',1)==0 and not f.get('se_fs_owned',1)
            assert not f.get('se_st_busy',1) and not f.get('se_st_valid',1)
            assert f.get('se_doc_read_locks',1)==1
            assert f.canonical()==canonical and f.reu_image()==reu
            assert f.catalog()==catalog,(label,'changed admitted catalog metadata')
            catalog_checks+=1
            assert f.get('se_e_error',1)==0
            f.render();f.check(data,label,styled=False)
            assert not f.call('se_doc_read_release').p&1
            cases.append(label+' actual admission fallback resident cleanup')
        finally:f.close()

    # A real File OPEN initializer owns the union; no host DOS provider is
    # substituted. Exercise only painting/help before its queued DOS service.
    data=petscii('# File modal\n**body**\n');f=fixture(data)
    try:
        f.finish_style()
        f.put('se_e_key',15,1);f.put('se_e_mods',4,1);f.call('se_editor_input')
        assert f.get('se_e_ui',1)==3 and f.get('se_f_owner',1)==1
        if Fixture.with_lexical:
            # Explicit phase-union ownership probe: this byte belongs to the
            # File frame now, so its value cannot trigger a lexical dispatch.
            f.m.write(f.s['st_lex_phase'],3)
        phase=f.read(0x8D00,1152);canonical=f.canonical();catalog=f.catalog()
        f.call('se_style_input')
        assert f.get('se_f_owner',1)==1 and f.read(0x8D00,1152)==phase
        if Fixture.with_lexical:
            f.call('se_style_idle')
            assert f.get('se_f_owner',1)==1 and f.read(0x8D00,1152)==phase
        for _ in range(2):
            assert not f.call('se_editor_render').p&1
            assert f.read(0x8D00,1152)==phase and f.canonical()==canonical
        assert f.catalog()==catalog,'modal paint changed admitted catalog metadata'
        catalog_checks+=1
        assert f.read(0xC600,1024)==f.shim
        cases.append('actual File modal owner1 paint keeps FILESTATE; style input leaves owner1')
    finally:f.close()
    result=dict(status='passed',identity=identity,cases=cases,frames=Fixture.frames,
        lexical_palette_enabled=Fixture.with_lexical,
        root_idle_iterations=sum(f.idle_steps for f in allfixtures),
        peak_idle_instructions=max(f.idle_peak for f in allfixtures),
        compared_source_cells=880*len(Fixture.frames),
        immutable_style_intervals=immutable_passes,whole_reu_bytes=32*65536,
        catalog_metadata_bytes=6*allfixtures[0].s['se_overlay_capacity'],
        catalog_metadata_start=allfixtures[0].s['se_overlay_ids'],
        immutable_catalog_intervals=catalog_checks,
        shim_bytes=1024,source_sha256={str(p.relative_to(ROOT)):sha(p) for p in
            [Path(__file__),ROOT/'tools/redraw_model.py',ROOT/'tools/supermark_model.py',
             ROOT/'tools/editor_fixture.py',ROOT/'tools/cpu_editor.py']},
        limits=['CPU integrated root/C14/R14/R1 proof, no native/VIC/physical keyboard claim.',
                'Fixture source initialization is explicit; normal input events use actual root queue.',
                'File modal paint only; no ROM DOS operation is faked by this test.'])
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true')
    parser.add_argument('--fixture',type=Path,help='Reuse an already frozen editor fixture')
    args=parser.parse_args()
    if not args.run:
        print('Prepared only. Wait for stable production gate, then --run; no CPU/build/native launched.')
        return
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=ROOT/'build/style-editor'/stamp;out.mkdir(parents=True)
    try:run(out,args.fixture)
    except Exception as error:
        (out/'failure.json').write_text(json.dumps(dict(error=repr(error)),indent=2)+'\n')
        raise


if __name__=='__main__':main()
