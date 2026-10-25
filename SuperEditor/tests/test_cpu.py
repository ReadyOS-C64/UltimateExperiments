"""Instruction-level tests of emitted editor routines, using the real PRG."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from peddle import Machine

report = json.loads((ROOT/'build/build-report.json').read_text())
symbols = report['symbols']
image = (ROOT/'build/supereditor.prg').read_bytes()
m = Machine()
try:
    m.load(int.from_bytes(image[:2], 'little'), image[2:])
    # Verify the native mixed-case contract by classes, including PETSCII aliases.
    expected = {0x41: 1, 0x5A: 26, 0xC1: 65, 0xDA: 90,
                0x5C: 28, 0x5E: 30, 0x5F: 31, 0x40: 0,
                0x20: 32, 0x3F: 63, 0xA0: 96, 0x60: 64, 0xFF: 94}
    for key, screen in expected.items():
        regs, _ = m.call(symbols['se_petscii_screen'], a=key)
        assert regs.a == screen, (hex(key), regs.a, screen)
    for control in list(range(32))+list(range(0x80, 0xA0)):
        regs, _ = m.call(symbols['se_petscii_screen'], a=control)
        assert regs.a == 63
    sentinel = bytes((i*73+29) & 255 for i in range(1024))
    m.load(0xC600, sentinel)
    m.load(0xC000, bytes([0xA6])*0x600)
    m.call(symbols['se_clear_state'])
    assert all(m.read(symbols['__BSS_RUN__']+i) == 0 for i in range(symbols['__BSS_SIZE__']))
    assert bytes(m.read(0xC600+i) for i in range(1024)) == sentinel
    _, probe_instructions = m.call(symbols['se_reu_probe'])
    banks = m.read(symbols['se_reu_banks'])+256*m.read(symbols['se_reu_banks']+1)
    assert banks == 256
    assert all(m.lib.zeropage_peddle_read_reu(m.handle, (b<<16)+0xFFFD) == 0 for b in range(256))
    assert bytes(m.read(0xC600+i) for i in range(1024)) == sentinel
    # Execute IRQ event-publication logic with deliberately tiny KERNAL stubs.
    # Actual interrupt entry/exit, CIA scan and key chords are VICE checks.
    for address in [0xFFEA, 0xFF9F, 0xEA81]:
        m.write(address, 0x60)
    m.write(0xC6, 1)
    m.write(0x277, 19)  # HOME and CTRL-S share this byte
    m.write(0x28D, 4)
    m.write(0xCB, 13)
    m.call(symbols['se_input_irq'])
    assert m.read(0xC6)==0
    m.write(0x28D,0)  # release before main gets to consume it
    regs,_=m.call(symbols['se_input_get'])
    assert (regs.a,regs.x,regs.y)==(19,4,13)
    regs,_=m.call(symbols['se_input_get'])
    assert regs.a==0
    # Queue wrap and publication ordering retain both events and modifiers.
    m.write(symbols['se_input_tail'],63)
    m.write(symbols['se_input_head'],1)
    for slot,char,mods,matrix in [(63,0x41,0,10),(0,0xC1,1,10)]:
        m.write(symbols['se_input_chars']+slot,char)
        m.write(symbols['se_input_mods']+slot,mods)
        m.write(symbols['se_input_matrix']+slot,matrix)
    for expected_event in [(0x41,0,10),(0xC1,1,10)]:
        regs,_=m.call(symbols['se_input_get'])
        assert (regs.a,regs.x,regs.y)==expected_event
    m.write(symbols['se_input_nmi_pending'],1)
    regs,_=m.call(symbols['se_input_get'])
    assert regs.a==3 and m.read(symbols['se_input_nmi_pending'])==0
    # Execute production TUI micromodules from the separately linked probe.
    probe = json.loads((ROOT/'build/display-probe-report.json').read_text())['symbols']
    raw = (ROOT/'build/display-probe.prg').read_bytes()
    m.load(int.from_bytes(raw[:2],'little'),raw[2:])
    m.load(0x4000, bytes([1])*1024)
    for name,value in [('tui_box_x',3),('tui_box_y',4),('tui_box_w',29),('tui_box_h',12)]:
        m.write(probe[name],value)
    m.call(probe['tui_box40'])
    for x,y,char in [(3,4,0x70),(31,4,0x6E),(3,15,0x6D),(31,15,0x7D)]:
        assert m.read(0x4000+y*40+x)==char
        assert m.read(0xD800+y*40+x)==14
    assert m.read(0x4000+5*40+4)==32
    assert m.read(0xD800+5*40+4)==1
    assert m.read(0x4000+4*40+2)==1
    m.write(probe['tui_color'],7)
    m.call(probe['tui_putc40'],a=65,x=39,y=24)
    assert m.read(0x43E7)==65 and m.read(0xDBE7)==7
    m.call(probe['tui_putc40'],a=99,x=40,y=24)
    assert m.read(0x43E8)==1
    for name,value in [('tui_box_x',40),('tui_box_y',25),('tui_box_w',0)]:
        original=m.read(probe[name])
        before=bytes(m.read(0x4000+i) for i in range(1024))
        m.write(probe[name],value)
        regs,_=m.call(probe['tui_box40'])
        assert regs.p&1
        assert bytes(m.read(0x4000+i) for i in range(1024))==before
        m.write(probe[name],original)
    result = dict(status='passed', engine='Peddle MOS_6510 / ZeroPage wrapper',
                  native_mapping_cases=len(expected)+64,
                  input_cases=5,
                  tui_cases=6,
                  main_prg_sha256=report['sha256'],
                  probe_prg_sha256=json.loads((ROOT/'build/display-probe-report.json').read_text())['sha256'],
                  shim_bytes_verified=1024, reu_banks=banks,
                  probe_instructions=probe_instructions,
                  timing='Wrapper does not advance Peddle clock; cycles are not measured',
                  limitations='No VIC, physical keyboard or real REU timing proof')
    (ROOT/'build/cpu-test-result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
finally:
    m.close()
