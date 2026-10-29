"""Independent source40 screen oracle and actual renderer submission trace.

Run without flags to diagnose the pre-incremental baseline; use
--require-incremental for the production gate. CPU cycles here exclude VIC
steals, IRQ and REU wait states and are never reported as PAL/NTSC latency.
"""
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from editor_fixture import EditorFixture
from redraw_model import BODY_ROWS, changed_body_rows, screen_code, source40, verify_screen

RESULT = ROOT / 'build/redraw-test-result.json'
REQUIRED = ['se_r_valid', 'se_r_revision', 'se_r_saved_revision',
            'se_r_damage_valid', 'se_r_damage_from', 'se_r_damage_to',
            'se_r_path', 'se_r_rows', 'se_r_cells']


def main():
    RESULT.unlink(missing_ok=True)
    f = EditorFixture()
    missing = [name for name in REQUIRED if name not in f.s]
    incremental = not missing
    rows_checked = cells_checked = reu_checks = 0
    traces = []
    harness_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    oracle_sha256 = hashlib.sha256((ROOT / 'tools/redraw_model.py').read_bytes()).hexdigest()
    source = b''
    previous = None
    render_snapshot = None

    def capture_frame():
        widths = {
            'se_hot_caret': 3, 'se_hot_base': 3, 'se_hot_left': 2, 'se_hot_right': 2,
            'se_hot_old_length': 2, 'se_hot_pending': 1,
            'se_doc_length': 3, 'se_doc_generation': 2,
            'se_v_top': 3, 'se_v_bottom': 3, 'se_v_length': 3,
            'se_v_seen': 1, 'se_v_caret_row': 1, 'se_v_caret_col': 1,
            'se_sel_mark': 1, 'se_sel_anchor': 3,
            'se_r_valid': 1, 'se_r_revision': 4, 'se_r_saved_revision': 4,
            'se_r_damage_valid': 1, 'se_r_damage_from': 3, 'se_r_damage_to': 3,
            'se_r_path': 1, 'se_r_rows': 1, 'se_r_cells': 2, 'se_r_length': 3,
            'se_r_top': 3, 'se_r_caret': 3, 'se_r_caret_row': 1, 'se_r_caret_col': 1,
            'se_r_under_glyph': 1, 'se_r_under_color': 1,
            'se_r_first': 3, 'se_r_last': 3, 'se_r_delta': 3, 'se_r_next': 3,
            'se_r_mode': 1, 'se_r_mark': 1, 'se_r_anchor': 3,
        }
        out = {name: f.get(name, width) for name, width in widths.items() if name in f.s}
        out['row_starts'] = [int.from_bytes(f.read(f.s['se_v_rows'] + i*3, 3), 'little')
                             for i in range(BODY_ROWS)]
        return out

    def reu_digest():
        return hashlib.sha256(bytes(f.m.lib.zeropage_peddle_read_reu(f.m.handle, i)
                                    for i in range(8 * 65536))).hexdigest()

    def merged():
        committed = f.document()
        base = f.get('se_hot_base')
        span = (f.read(0x9200, f.get('se_hot_left', 2)) +
                f.read(0x9200 + f.get('se_hot_right', 2),
                       2048 - f.get('se_hot_right', 2)))
        return committed[:base] + span + committed[base + f.get('se_hot_old_length', 2):]

    def render(tag, *, expected_path=None, max_cells=None, max_rows=None,
               plain=True):
        nonlocal previous, rows_checked, cells_checked, reu_checks, render_snapshot
        assert merged() == source, (tag, 'merged source differs from host edit model')
        render_snapshot = dict(tag=tag, source_hex=source.hex(), before=capture_frame(),
                               before_matrix=f.read(0x4000, 1000).hex(),
                               before_colors=f.read(0xD800, 1000).hex())
        assert f.read(0xC600, 1024) == f.shim, (tag, 'shim before render')
        source_state = {name: f.read(f.s[name], width) for name, width in
                        [('se_doc_length', 3), ('se_doc_generation', 2),
                         ('se_hot_caret', 3), ('se_hot_pending', 1),
                         ('se_h_current', 4), ('se_h_saved', 4)]
                        if name in f.s}
        before_reu = reu_digest()
        m = f.m
        for name, value in [('a', 0), ('x', 0), ('y', 0), ('p', 0x24),
                            ('sp', 0xFD), ('pc', f.s['se_editor_render'])]:
            getattr(m.lib, 'zeropage_peddle_set_' + name)(m.handle, value)
        m.write(0x1FE, 0xFE)
        m.write(0x1FF, 0x02)
        initial = m.regs()
        submissions = []
        for _ in range(2_000_000):
            r = m.regs()
            if r.pc == 0x02FF:
                assert not r.p & 1, (tag, 'render failed', r.a)
                if f.get('se_e_job', 1) != 7:
                    break
                f.settle() # C11 reads pending source in bounded128-byte jobs
                for name, value in [('a', 0), ('x', 0), ('y', 0), ('p', 0x24),
                                    ('sp', 0xFD), ('pc', f.s['se_editor_render'])]:
                    getattr(m.lib, 'zeropage_peddle_set_' + name)(m.handle, value)
                m.write(0x1FE, 0xFE); m.write(0x1FF, 0x02)
                continue
            if r.pc == f.s['tui_putc40'] and 2 <= r.y < 24 and r.x < 40:
                submissions.append((r.y - 2, r.x))
            m.lib.zeropage_peddle_step_instruction(m.handle)
        else:
            raise AssertionError((tag, 'render instruction limit', hex(m.regs().pc)))
        final = m.regs()
        render_snapshot.update(after=capture_frame(),
                               actual_matrix=f.read(0x4000, 1000).hex(),
                               actual_colors=f.read(0xD800, 1000).hex(),
                               submissions=submissions)
        assert not final.p & 1, (tag, 'render failed', final.a)
        assert reu_digest() == before_reu, (tag, 'render wrote REU')
        reu_checks += 1
        assert f.read(0xC600, 1024) == f.shim, (tag, 'render wrote shim')
        for name, old in source_state.items():
            assert f.read(f.s[name], len(old)) == old, (tag, 'render mutated', name)
        expected = None
        changed_rows = None
        if plain:
            assert f.get('se_e_ui', 1) == 0, (tag, 'unexpected popup/command UI')
            expected = source40(source, f.get('se_v_top'), f.get('se_hot_caret'),
                marked=bool(f.get('se_sel_mark', 1)), anchor=f.get('se_sel_anchor'),
                pending=bool(f.get('se_hot_pending', 1)), dirty=bool(f.get('se_h_dirty', 1)),
                error=f.get('se_e_error', 1), history_fault=bool(f.get('se_h_fault', 1)),
                trimmed=bool(f.get('se_h_trimmed', 2)))
            render_snapshot.update(expected_matrix=expected.matrix.hex(),
                                   expected_colors=expected.colors.hex(),
                                   expected_anchors=expected.anchors,
                                   expected_caret=expected.caret)
            verify_screen(f.read(0x4000, 1000), f.read(0xD800, 1000), expected, tag=tag)
            anchors = tuple(int.from_bytes(f.read(f.s['se_v_rows'] + i * 3, 3), 'little')
                            for i in range(BODY_ROWS)) + (f.get('se_v_bottom'),)
            assert anchors == expected.anchors, (tag, 'source row anchors', anchors, expected.anchors)
            assert expected.caret is not None, (tag, 'caret is not visible')
            assert (f.get('se_v_caret_row', 1), f.get('se_v_caret_col', 1)) == expected.caret
            if previous is not None:
                changed_rows = sorted(changed_body_rows(previous, expected))
            previous = expected
            rows_checked += 25
            cells_checked += 1000
        else:
            previous = None
        item = dict(tag=tag, instructions=final.instructions - initial.instructions,
                    cpu_cycles_without_vic_irq_dma=(final.cycles - initial.cycles) or None,
                    traced_body_cells=len(submissions),
                    traced_body_rows=len({row for row, col in submissions}),
                    visible_changed_body_rows=changed_rows,
                    top=f.get('se_v_top'), caret=f.get('se_hot_caret'))
        if incremental:
            item.update(path=f.get('se_r_path', 1),
                        reported_cells=f.get('se_r_cells', 2),
                        reported_rows=f.get('se_r_rows', 1))
            # Popup labels may call the same primitive from the separate UI
            # service. Its submissions are outside source-renderer metrics.
            if plain:
                assert item['reported_cells'] == item['traced_body_cells'], (tag, item)
            # rows counts complete row compositions; cursor cell patches do not
            # count as composed rows. Each composition submits exactly40 cells.
            if plain:
                composed = sum(n // 40 for n in Counter(row for row, col in submissions).values())
                assert item['reported_rows'] == composed, (tag, item, 'traced full rows', composed)
            assert item['reported_rows'] * 40 <= len(submissions), (tag, item)
            if item['path'] == 1:
                assert item['reported_rows'] == 0, (tag, item)
            if expected_path is not None:
                assert item['path'] == expected_path, (tag, item)
            if max_cells is not None:
                assert len(submissions) <= max_cells, (tag, item)
            if max_rows is not None:
                assert item['reported_rows'] <= max_rows, (tag, item)
        traces.append(item)
        print(f"{tag}: {item['traced_body_cells']} cells, {item['traced_body_rows']} rows, "
              f"{item['instructions']} instructions", flush=True)

    def new_source(data):
        nonlocal source, previous
        source = data
        previous = None
        f.source(source, physical=8)

    def insert(value):
        nonlocal source
        p = f.get('se_hot_caret')
        f.key(value)
        source = source[:p] + bytes([value]) + source[p:]

    def position(target):
        # Fixture's direct hot LOAD requires a clean window. Use the actual
        # command pipeline to publish pending edits before moving that window.
        if f.get('se_hot_pending', 1):
            f.command(32)
        f.position(target)

    def back():
        nonlocal source
        p = f.get('se_hot_caret')
        f.key(0x14)
        if p:
            source = source[:p-1] + source[p:]

    def delete():
        nonlocal source
        p = f.get('se_hot_caret')
        f.command(4)
        source = source[:p] + source[p+1:]

    try:
        if missing:
            print('Incremental renderer not implemented in this build: ' + ', '.join(missing), flush=True)
            assert '--require-incremental' not in sys.argv, missing
        # Exhaustive expected native mapping; rendered source exercises all bytes.
        assert [screen_code(n) for n in [0, 31, 32, 63, 64, 95, 96, 127,
                                         128, 159, 160, 191, 192, 223, 224, 254, 255]] == [
            63, 63, 32, 63, 0, 31, 64, 95, 63, 63, 96, 127, 64, 95, 96, 126, 94]
        diverse = (b'# ' + bytes([0xD3]) + b'uper' + bytes([0xC5]) + b'ditor\r'
                   b'plain **bold** /italics/ 1234\r\r' + b'W' * 40 + b'\r' +
                   bytes(range(256)) + b'\r' +
                   b''.join(f'row {i:02d}: '.encode() + bytes([0xC1 + i % 26]) * (i % 31 + 1) + b'\r'
                            for i in range(40)))
        new_source(diverse)
        if incremental:
            f.put('se_r_valid', 0, 1)
        render('full-diverse', expected_path=0)
        render('unchanged', expected_path=1, max_cells=2, max_rows=2)
        for tag, command in [('right', 2), ('left', 1), ('down', 37), ('up', 36)]:
            f.command(command)
            render(tag, expected_path=1, max_cells=2, max_rows=2)
        position(6)
        render('position-before-typing')
        insert(0xD8)
        render('typing-one-row', expected_path=2, max_rows=2)
        # Publishing already-painted hot bytes changes committed generation,
        # but must preserve their visible revision and avoid a full repaint.
        f.command(1)
        render('pending-flush-left', expected_path=1, max_cells=2, max_rows=0)
        f.command(2)
        render('right-after-known-flush', expected_path=1, max_cells=2, max_rows=0)
        back()
        render('backspace-one-row', expected_path=2, max_rows=2)
        delete()
        render('forward-delete-one-row', expected_path=2, max_rows=2)
        for value in [0xD9, 0x5A, 0xC1]:
            insert(value)
        render('batched-three-characters', expected_path=2, max_rows=2)
        position(3)
        f.command(68)
        position(160)
        render('marked-forward')
        f.command(1)
        render('marked-one-character-step', expected_path=2, max_rows=1)
        render('marked-unchanged', expected_path=1, max_cells=2, max_rows=0)
        position(1)
        render('marked-reversed')
        f.command(50)
        render('unmarked')
        f.key(0x85)
        f.key(ord('B'))
        render('block-popup', plain=False)
        f.key(3)
        render('popup-restored', expected_path=0)
        f.command(66)
        render('help-popup', plain=False)
        f.key(3)
        render('help-restored', expected_path=0)
        f.key(0x88)
        f.key(ord('Q'))
        render('command-line', plain=False)
        f.key(3)
        render('command-restored')
        f.command(39)
        render('page-down')
        f.command(38)
        render('page-up')
        # The reclaimed former status row is now the22nd source body row.
        # Its start remains in the66-byte original map; the exclusive bottom
        # anchor is a separate suffix field, preserving all previous addresses.
        reclaimed = [bytes([0xC1 + i % 26]) + f' row {i:02d}'.encode() + b'\r'
                     for i in range(BODY_ROWS)]
        new_source(b''.join(reclaimed) + b'BELOW VIEWPORT\r')
        row21 = sum(map(len, reclaimed[:21]))
        position(row21 + 3)
        render('reclaimed-last-body-row')
        assert f.get('se_v_top') == 0 and f.get('se_v_caret_row', 1) == 21
        assert f.read(0x4000 + 23*40, 1) == bytes([screen_code(reclaimed[21][0])])
        bottom_before = f.get('se_v_bottom')
        insert(0xD8)
        render('typing-in-last-body-row', expected_path=2, max_rows=1)
        assert f.get('se_v_bottom') == bottom_before + 1
        back()
        render('backspace-in-last-body-row', expected_path=2, max_rows=1)
        assert f.get('se_v_bottom') == bottom_before
        position(sum(map(len, reclaimed[:20])) + 2)
        f.command(68)
        position(row21 + len(reclaimed[21])-1)
        render('selection-on-last-body-row')
        assert f.get('se_v_caret_row', 1) == 21
        assert f.read(0xD800 + 23*40, 1)[0] & 15 == 3
        assert f.read(0xD800 + 23*40 + len(reclaimed[21])-1, 1)[0] & 15 == 7
        caret_before, top_before = f.get('se_hot_caret'), f.get('se_v_top')
        f.key(0x8B)
        assert f.get('se_e_ui', 1) == 1 and f.get('se_e_menu', 1) == 6
        render('f6-global-help', plain=False)
        f.key(0x8B)
        render('f6-help-toggle-restored', expected_path=0)
        assert f.get('se_hot_caret') == caret_before and f.get('se_v_top') == top_before
        assert f.get('se_sel_mark', 1) == 1
        f.command(50)
        f.command(2)
        render('last-body-row-boundary-reveal')
        assert f.get('se_v_top') > 0 and f.get('se_v_seen', 1) == 1
        # A partial row contains its EOF blank cell. Its repeated end anchor
        # must not make an unpainted BOTTOM+Return edit start one row too low.
        new_source(b'A' * 65)
        f.command(35)
        insert(13)
        render('eof65-bottom-return-without-paint', expected_path=2, max_rows=1)
        eof_vectors = [
            ('empty', b''), ('one', b'A'), ('partial39', b'A'*39),
            ('full40', b'A'*40), ('partial41', b'A'*41), ('partial65', b'A'*65),
            ('spaces65', b' '*65), ('controls65', bytes([1])*65),
            ('graphics65', bytes([255])*65), ('trailing-cr', b'A'*65+b'\r'),
            ('full40-cr', b'A'*40+b'\r'), ('two-trailing-cr', b'A'*65+b'\r\r'),
        ]
        for name, fixture in eof_vectors:
            new_source(fixture)
            f.command(35)
            render('eof-locate-' + name, expected_path=1, max_cells=2, max_rows=0)
            f.command(34)
            f.command(35)
            insert(13)
            render('eof-return-' + name, expected_path=2, max_rows=1)
        # Full-width line then CR: separately selectable empty row; deletion
        # changes wrap/CR topology and must repaint all affected successors.
        new_source(b'A' * 40 + b'\r\rTAIL\r' + b'B' * 90)
        render('exact-wrap-cr')
        position(40)
        f.command(68)
        position(42)
        render('selected-two-cr-cells')
        f.command(50)
        position(40)
        delete()
        render('delete-wrap-cr')
        insert(13)
        render('insert-wrap-cr')
        # Edits at separated offsets accumulated before a paint, including a
        # pending->committed transition, may not forget earlier damaged rows.
        position(3)
        insert(0xDA)
        position(75)
        insert(0xC2)
        render('batched-separated-edits')
        f.command(16)
        source = source[:75] + source[76:]
        render('undo-separated-edit')
        f.command(17)
        source = source[:75] + bytes([0xC2]) + source[75:]
        render('redo-separated-edit')
        new_source(b'')
        render('empty-document')
        f.command(68)
        render('empty-marked-caret')
        f.command(50)
        insert(13)
        render('empty-insert-cr')
        f.command(35)
        render('eof-after-cr')
        # 24-bit row positions and EOF context, not a short fixture only.
        new_source(b'L' * 65537 + b'\r' + b'END\r')
        position(65536)
        render('above-64k')
        f.command(35)
        render('large-eof')
        # Replay carets are deliberately more than64KiB apart. Replaying a
        # transaction must reveal its own before/after caret and may not keep
        # the viewport at the unrelated position from which Undo was invoked.
        original = b''.join(f'Line {i:03d}: '.encode() + b'context' * 5 + b'\r'
                            for i in range(1600))
        new_source(original)
        insert(0xD8)
        f.command(35)
        insert(0xD9)
        f.command(34)
        render('replay-at-unrelated-top')
        f.command(16)
        source = bytes([0xD8]) + original
        assert f.get('se_hot_caret') == len(source), 'undo before caret at distant EOF'
        render('undo-reveals-distant-eof')
        f.command(17)
        source += bytes([0xD9])
        assert f.get('se_hot_caret') == len(source), 'redo after caret at distant EOF'
        render('redo-reveals-distant-eof')
        f.command(16)
        source = bytes([0xD8]) + original
        f.command(16)
        source = original
        assert f.get('se_hot_caret') == 0
        render('undo-reveals-distant-top')
        f.command(17)
        source = bytes([0xD8]) + original
        assert f.get('se_hot_caret') == 1
        render('redo-near-top')
        # A changed row can be unrelated to the caret currently painted on
        # screen. Clearing that old caret must not require repainting its row.
        new_source(b'abcdefghij\r' * 40)
        position(120)
        insert(0xDA)
        render('old-caret-outside-dirty-row', expected_path=2, max_rows=2)
        # Deterministic randomized transitions use host edit semantics only;
        # no damage bounds, cached rows or renderer paths drive the oracle.
        rng = random.Random(0x52454452)
        new_source(b'R' * 40 + b'\r\r' + b''.join(
            f'line {i:02d}: '.encode() + bytes([0xC1 + i % 26]) * rng.randrange(1, 35) + b'\r'
            for i in range(40)))
        for case in range(40):
            action = case % 8
            f.command(50)
            if action == 0:
                position(rng.randrange(len(source) + 1))
                for _ in range(rng.randrange(2, 5)):
                    insert(rng.choice([13, 32, 65, 0xC2, 0xFF]))
                tag = 'batch-insert'
            elif action == 1:
                position(rng.randrange(len(source) + 1))
                back()
                delete()
                tag = 'back-delete-union'
            elif action in (2, 3):
                a, b = sorted((rng.randrange(len(source) + 1), rng.randrange(len(source) + 1)))
                if action == 3:
                    a, b = b, a
                position(a)
                f.command(68)
                position(b)
                tag = 'reverse-mark' if action == 3 else 'forward-mark'
            elif action == 4:
                a, b = sorted((rng.randrange(len(source) + 1), rng.randrange(len(source) + 1)))
                position(b)
                f.command(68)
                position(a)
                value = rng.choice([13, 0xD8, 0xFF])
                f.key(value)
                source = source[:a] + bytes([value]) + source[b:]
                tag = 'selected-replacement'
            elif action == 5:
                position(rng.randrange(len(source) + 1))
                insert(0xC3)
                position(rng.randrange(len(source) + 1))
                insert(0xC4)
                tag = 'disjoint-mutation-union'
            elif action == 6:
                f.key(0x88)
                f.key(ord('Q'))
                f.key(13, error=0x76)
                render(f'fuzz-{case:02d}-editable-command-error', plain=False)
                assert f.get('se_e_ui', 1) == 2
                f.key(3)
                tag = 'ui-error-restored'
            else:
                f.command(35)
                if rng.randrange(2):
                    insert(13)
                else:
                    back()
                tag = 'eof-cr-boundary'
            render(f'fuzz-{case:02d}-{tag}')
        assert f.read(0xC600, 1024) == f.shim
        result = dict(status='passed' if incremental else 'not_implemented',
            source_oracle='passed', missing_renderer_metrics=missing,
            harness_sha256=harness_sha256, oracle_sha256=oracle_sha256,
            prg_sha256=f.report['sha256'], resident_binding=f.report['resident_binding']['digest'],
            overlay_sha256={n: hashlib.sha256(v).hexdigest() for n, v in f.assets.items()},
            screen_cells_checked=cells_checked, screen_rows_checked=rows_checked,
            complete_512k_reu_before_after_render_checks=reu_checks,
            reserved_shim_bytes=1024, independent_tui_body_submission_trace=True,
            body_rows=BODY_ROWS, single_bottom_status_row=24,
            body_anchor_count=22, separate_bottom_anchor=True,
            reclaimed_last_row_selection_and_f6_help=True,
            eof_partial_row_vectors=len(eof_vectors),
            eof65_unpainted_bottom_then_return=True,
            deterministic_randomized_render_cases=40, randomized_seed='0x52454452',
            traces=traces,
            limitations='Peddle CPU/storage proof only; cycle totals exclude VIC/IRQ/DMA stalls. Native screenshots and PAL/NTSC measurements require separate VICE runs.')
        RESULT.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k != 'traces'}, indent=2))
    except Exception as error:
        (ROOT/'build/redraw-failure-state.json').write_text(
            json.dumps(render_snapshot, indent=2) + '\n')
        (ROOT/'build/redraw-failure-cpu.bin').write_bytes(f.read(0, 65536))
        (ROOT/'build/redraw-failure-reu.bin').write_bytes(bytes(
            f.m.lib.zeropage_peddle_read_reu(f.m.handle, i) for i in range(8*65536)))
        RESULT.write_text(json.dumps(dict(status='failed', error=repr(error),
            harness_sha256=harness_sha256, oracle_sha256=oracle_sha256,
            prg_sha256=f.report['sha256'],
            resident_binding=f.report['resident_binding']['digest'],
            overlay_sha256={n: hashlib.sha256(v).hexdigest() for n, v in f.assets.items()},
            missing_renderer_metrics=missing, completed_traces=traces), indent=2) + '\n')
        raise
    finally:
        f.close()


if __name__ == '__main__':
    main()
