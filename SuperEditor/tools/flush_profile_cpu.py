"""Supplementary instruction/CRC/call attribution for a real hot flush.

Peddle supplies instruction counts only. Native stopwatch timings are separate.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

from editor_fixture import EditorFixture

ROOT = Path(__file__).resolve().parents[1]
WIDTHS = {'se_e_job':1, 'se_e_error':1, 'se_hot_phase':1, 'se_h_phase':1,
          'se_doc_busy':1, 'se_hot_pending':1, 'se_hot_caret':3,
          'se_hot_feed_left':2, 'se_doc_generation':2, 'se_doc_length':3,
          'se_h_end':2, 'se_h_current':4, 'se_r_revision':4,
          'se_overlay_calls':2, 'se_overlay_loads':2, 'se_overlay_hits':2,
          'se_reu_dma_calls':2, 'se_reu_dma_bytes':3}


def profile():
    f = EditorFixture()
    def state():
        out = {n:f.get(n,w) for n,w in WIDTHS.items()}
        out['active_catalog_indices'] = list(f.read(f.s['se_overlay_active'],2))
        return out
    catalog = {(image[5],image[6]):dict(name=n,index=i+1,payload=len(image)-36)
               for i,(n,image) in enumerate(f.assets.items())}
    inline_crc={f.s[n]:kind for n,kind in
                [('se_overlay_crc_page_byte','overlay_admission_page'),
                 ('se_overlay_crc_tail_byte','overlay_admission_tail')]
                if n in f.s}
    def call(name):
        before = state()
        m,s = f.m,f.s
        for field,value in [('a',0),('x',0),('y',0),('p',0x24),('sp',0xFD),('pc',s[name])]:
            getattr(m.lib,'zeropage_peddle_set_'+field)(m.handle,value)
        m.write(0x1FE,0xFE);m.write(0x1FF,0x02)
        initial=m.regs().instructions;calls=[];crc=Counter()
        for _ in range(3_000_000):
            r=m.regs()
            if r.pc==0x02FF:break
            if r.pc==s['se_overlay_call']:
                item=dict(slot=r.x,identity=r.a,operation=f.get('se_overlay_frame',1))
                cat=catalog.get((r.x,r.a))
                if cat:
                    item.update(cat);item['cold']=m.read(s['se_overlay_active']+r.x)!=cat['index']
                calls.append(item)
            if r.pc==s['se_crc_byte']:
                ret=m.read(0x100+((r.sp+1)&255)) | m.read(0x100+((r.sp+2)&255))<<8
                crc['overlay_admission' if s['crc_stage'] <= ret < s['crc_stage']+160
                    else 'journal_or_other']+=1
            if r.pc in inline_crc:
                crc['overlay_admission']+=1
                crc[inline_crc[r.pc]]+=1
            m.lib.zeropage_peddle_step_instruction(m.handle)
        else:raise AssertionError(('CPU profile limit',name,hex(m.regs().pc)))
        assert not m.regs().p&1,(name,m.regs().a)
        payload_bytes=sum(c['payload'] for c in calls if c.get('cold'))
        assert crc['overlay_admission']==payload_bytes,(name,dict(crc),payload_bytes)
        return dict(function=name,before=before,after=state(),
                    instructions=m.regs().instructions-initial,
                    overlay_calls=calls,crc_byte_calls=dict(crc),
                    admission_payload_bytes=payload_bytes)
    try:
        prg=(ROOT/'build/editor.prg').read_bytes();s=f.s
        source=prg[2+s['sample']-0x801:2+s['sample_end']-0x801]
        f.source(source,banks=1,physical=8)
        for _ in range(5):f.key(0xD8);f.call('se_editor_render')
        f.put('se_e_key',0x9D,1);f.put('se_e_mods',0,1)
        stages=[call('se_editor_input')]
        while f.get('se_e_job',1):
            assert len(stages)<80
            stages.append(call('se_editor_service'))
        stages.append(call('se_editor_render'))
        assert f.document()==bytes([0xD8])*5+source and f.get('se_hot_caret')==4
        assert f.read(0xC600,1024)==f.shim
        return dict(status='passed',prg_sha256=f.report['sha256'],
            resident_binding=f.report['resident_binding']['digest'],
            overlay_sha256={n:hashlib.sha256(v).hexdigest() for n,v in f.assets.items()},
            service_calls=len(stages)-2,stages=stages,
            total_instructions=sum(x['instructions'] for x in stages),
            crc_byte_calls=dict(sum((Counter(x['crc_byte_calls']) for x in stages),Counter())),
            admission_crc_counting='exported inline page/tail entries' if inline_crc
                else 'se_crc_byte calls from crc_stage',
            limitations='CPU instructions/call attribution only; no VIC, IRQ, REU wait-state timing.')
    finally:f.close()


if __name__=='__main__':
    result=profile();(ROOT/'build/flush-profile-cpu.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
