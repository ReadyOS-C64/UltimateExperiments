"""Cold fixed-grid style-plan proof with every plan byte poisoned first.

This gate freezes the actual packaged editor, invalidates only derived style
state, and runs the normal background planner and renderer.  It covers Full
and Markdown at 40/60/80 columns.  A read-only instruction observer records
every CPU load/store in the selected plan window and rejects any load of a
byte that the current cold job has not written.  Independent grid oracles
check the complete screen/bitmap and all attributes, including EOF filler.

No product source, overlay, RAM result, or parser output is substituted.
"""

from datetime import datetime, timezone
from pathlib import Path
import ctypes as C
import hashlib
import json
import re
import subprocess
import sys

import test_cache_hotpath_profile as profile
import test_styled_grid_convergence_profile_vice as styled


ROOT = profile.ROOT
OUT_ROOT = ROOT / "build" / "style-plan-no-preclear"
ORIGINAL_RUNNER = profile.observer.runner
MODES = ((0, 40, 0x4400, 880), (1, 60, 0x4800, 1320),
         (2, 80, 0x4800, 1760))
CAPABILITIES = (("markdown", 1), ("full", 3))
POISONS = (0x26, 0xD9)


def petscii(text):
    return profile.observer.geos.native_text(text)


def documents(width):
    return (
        ("empty", b""),
        ("short-eof", petscii("# Head\rTail *italic* and **bold**")),
        ("cr-terminators", petscii("# Head\r\r- item\r12. numbered\r")),
        ("wrapped", petscii("# Wrapped\r") + b"A" * (width * 2 + 7)
         + petscii(" *tail*\rAfter.\r")),
        ("code", petscii(
            ":::basic\r10 PRINT \"HELLO\":GOTO 10\r:::\r"
            ":::asm\rloop: lda #$20 ; comment\r bne loop\r:::\r"
            "After **code**.")),
    )


def runner(out):
    """Add plan read-before-write observation to the existing CPU runner."""
    original = ORIGINAL_RUNNER(out)
    cpp = out / "runner.cpp"
    source = cpp.read_text()
    marker = "static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);"
    assert source.count(marker) == 1
    extra = r'''
static bool pn_on=false;static uint16_t pn_base=0,pn_size=0;
static uint8_t pn_written[2048],pn_read[2048];static uint16_t pn_pc[2048];
static uint32_t pn_reads=0,pn_writes=0,pn_stale=0;
static uint8_t pn_b(ZeroPagePeddle*m,uint16_t a){return zeropage_peddle_read(m,a);}
static uint16_t pn_w(ZeroPagePeddle*m,uint16_t a){return pn_b(m,a)|(pn_b(m,uint16_t(a+1))<<8);}
extern "C" void pn_begin(uint16_t base,uint16_t size){pn_base=base;pn_size=size;
 memset(pn_written,0,sizeof(pn_written));memset(pn_read,0,sizeof(pn_read));
 memset(pn_pc,0,sizeof(pn_pc));pn_reads=pn_writes=pn_stale=0;pn_on=true;}
extern "C" void pn_end(){pn_on=false;}
extern "C" uint32_t pn_get(unsigned n){return n==0?pn_reads:n==1?pn_writes:pn_stale;}
extern "C" void pn_copy(uint8_t*w,uint8_t*r,uint16_t*p){memcpy(w,pn_written,2048);memcpy(r,pn_read,2048);memcpy(p,pn_pc,4096);}
static void pn_before(ZeroPagePeddle*m){if(!pn_on)return;auto r=zeropage_peddle_regs(m);
 uint8_t op=pn_b(m,r.pc),lo=pn_b(m,r.pc+1);uint16_t abs=pn_w(m,r.pc+1),a=0;bool mem=true;
 switch(op){
 /* zero page */
 case 0x05:case 0x06:case 0x24:case 0x25:case 0x26:case 0x45:case 0x46:
 case 0x65:case 0x66:case 0x84:case 0x85:case 0x86:case 0xa4:case 0xa5:
 case 0xa6:case 0xc4:case 0xc5:case 0xc6:case 0xe4:case 0xe5:case 0xe6:a=lo;break;
 /* zero page,X */
 case 0x15:case 0x16:case 0x35:case 0x36:case 0x55:case 0x56:case 0x75:
 case 0x76:case 0x94:case 0x95:case 0xb4:case 0xb5:case 0xd5:case 0xd6:
 case 0xf5:case 0xf6:a=uint8_t(lo+r.x);break;
 /* zero page,Y */
 case 0x96:case 0xb6:a=uint8_t(lo+r.y);break;
 /* absolute */
 case 0x0d:case 0x0e:case 0x2c:case 0x2d:case 0x2e:case 0x4d:case 0x4e:
 case 0x6d:case 0x6e:case 0x8c:case 0x8d:case 0x8e:case 0xac:case 0xad:
 case 0xae:case 0xcc:case 0xcd:case 0xce:case 0xec:case 0xed:case 0xee:a=abs;break;
 /* absolute,X */
 case 0x1d:case 0x1e:case 0x3d:case 0x3e:case 0x5d:case 0x5e:case 0x7d:
 case 0x7e:case 0x9d:case 0xbc:case 0xbd:case 0xdd:case 0xde:case 0xfd:
 case 0xfe:a=uint16_t(abs+r.x);break;
 /* absolute,Y */
 case 0x19:case 0x39:case 0x59:case 0x79:case 0x99:case 0xb9:case 0xbe:
 case 0xd9:case 0xf9:a=uint16_t(abs+r.y);break;
 /* (zero page,X) */
 case 0x01:case 0x21:case 0x41:case 0x61:case 0x81:case 0xa1:case 0xc1:
 case 0xe1:{uint8_t z=uint8_t(lo+r.x);a=pn_b(m,z)|(pn_b(m,uint8_t(z+1))<<8);break;}
 /* (zero page),Y */
 case 0x11:case 0x31:case 0x51:case 0x71:case 0x91:case 0xb1:case 0xd1:
 case 0xf1:a=uint16_t((pn_b(m,lo)|(pn_b(m,uint8_t(lo+1))<<8))+r.y);break;
 default:mem=false;}
 if(!mem||a<pn_base||a>=uint16_t(pn_base+pn_size))return;unsigned i=a-pn_base;
 bool write=false,read=true;switch(op){case 0x81:case 0x84:case 0x85:case 0x86:
 case 0x8c:case 0x8d:case 0x8e:case 0x91:case 0x94:case 0x95:case 0x96:
 case 0x99:case 0x9d:write=true;read=false;break;
 case 0x06:case 0x0e:case 0x16:case 0x1e:case 0x26:case 0x2e:case 0x36:
 case 0x3e:case 0x46:case 0x4e:case 0x56:case 0x5e:case 0x66:case 0x6e:
 case 0x76:case 0x7e:case 0xc6:case 0xce:case 0xd6:case 0xde:case 0xe6:
 case 0xee:case 0xf6:case 0xfe:write=true;break;}
 if(read){pn_reads++;pn_read[i]=1;if(!pn_written[i]){pn_stale++;if(!pn_pc[i])pn_pc[i]=r.pc;}}
 if(write){pn_writes++;pn_written[i]=1;}}
'''
    source = source.replace(marker, extra + marker + "pn_before(m);")
    cpp.write_text(source)
    suffix = ".dylib" if sys.platform == "darwin" else ".so"
    target = out / ("plan-poison-runner" + suffix)
    subprocess.run([
        "clang++", "-std=c++20", "-O2",
        "-dynamiclib" if sys.platform == "darwin" else "-shared", "-fPIC",
        "-I" + str(profile.observer.geos.grid.VENDOR), cpp,
        ROOT / ("build/libse_peddle" + suffix), "-o", target,
    ], check=True)
    dll = C.CDLL(str(target))
    for name in (
        "gm_rom", "gm_rom_count", "gm_profile", "gm_metric", "gm_run",
        "gm_idle", "gm_read", "gm_reu", "fr_begin", "fr_end", "fr_mask",
        "fr_bad", "fr_writes", "pb_config", "pb_begin", "pb_end", "pb_get",
        "pb_fault_get", "ob_ring", "ob_ring_get",
    ):
        old, new = getattr(original, name), getattr(dll, name)
        new.argtypes, new.restype = old.argtypes, old.restype
    dll.pn_begin.argtypes = [C.c_uint16, C.c_uint16]
    dll.pn_get.argtypes = [C.c_uint]
    dll.pn_get.restype = C.c_uint32
    dll.pn_copy.argtypes = [C.c_void_p, C.c_void_p, C.c_void_p]
    return dll


def pixel_oracle(f, source, caps, tag):
    (primary, attributes), wanted_anchors, seen, _ = \
        profile.observer.geos.grid.expected(f, source)
    if caps == 1:
        primary, attributes = styled.markdown_expected(
            f, source, primary, attributes)
    mode = f.get("se_mode", 1)
    actual_primary = f.read(0x4000 if mode == 0 else 0x6000,
                            1000 if mode == 0 else 8000)
    actual_attributes = f.read(0xD800 if mode == 0 else 0x4000, 1000)
    assert actual_primary == primary, (tag, "primary")
    assert actual_attributes == attributes, (tag, "attributes")
    actual_anchors = tuple(int.from_bytes(
        f.read(f.s["se_v_rows"] + i * 3, 3), "little") for i in range(22)) \
        + (f.get("se_v_bottom"),)
    assert actual_anchors == wanted_anchors, (tag, "anchors")
    assert seen == (f.get("se_v_caret_row", 1), f.get("se_v_caret_col", 1)), \
        (tag, "caret")
    return hashlib.sha256(primary + attributes).hexdigest()


def plan_observation(dll, size):
    written = C.create_string_buffer(2048)
    read = C.create_string_buffer(2048)
    pcs = (C.c_uint16 * 2048)()
    dll.pn_copy(written, read, pcs)
    return {
        "reads": int(dll.pn_get(0)),
        "writes": int(dll.pn_get(1)),
        "stale_reads": int(dll.pn_get(2)),
        "written_unique": sum(bool(v) for v in written.raw[:size]),
        "read_unique": sum(bool(v) for v in read.raw[:size]),
        "stale_addresses": [
            {"offset": i, "pc": int(pcs[i])}
            for i in range(size) if pcs[i]
        ],
    }


def measure_linked_savings(out):
    """Link an otherwise identical counterfactual with the old preclear."""
    source = (ROOT / "src/style/plan.s").read_text()
    replacements = (
        (".import st_columns,st_plan_page\n", ".import st_columns,st_plan_page,st_cells\n"),
        (".ifdef SE_STYLE_GRID\n"
         "    lda #1                  ;every live cell is overwritten by its base span\n"
         ".else\n"
         "    lda #0                  ;isolated fixed-size planner retains full fill ABI\n"
         ".endif\n"
         "    sta st_phase\n",
         ".ifdef SE_STYLE_GRID\n"
         "    lda #0                  ;counterfactual fixed-grid preclear phase\n"
         ".else\n"
         "    lda #0                  ;isolated fixed-size planner retains full fill ABI\n"
         ".endif\n"
         "    sta st_phase\n"),
        ("    lda st_phase\n.ifndef SE_STYLE_GRID\n    jeq clear_step\n.endif\n",
         "    lda st_phase\n    jeq clear_step\n"),
        (".ifndef SE_STYLE_GRID\nclear_step:\n", "clear_step:\n"),
        ("    jmp pending\n.endif\n\nblock_step:\n",
         "    jmp pending\n\nblock_step:\n"),
        ("    lda grid_pages,x\n    sta st_plan_page\n.endif\n"
         "    jsr se_fs_begin\n",
         "    lda grid_pages,x\n    sta st_plan_page\n"
         "    lda grid_cells_low,x\n    sta st_cells\n"
         "    lda grid_cells_high,x\n    sta st_cells+1\n"
         ".endif\n    jsr se_fs_begin\n"),
        ("grid_columns:.byte 40,60,80\ngrid_pages:.byte >STYLE_PLAN,$48,$48\n",
         "grid_columns:.byte 40,60,80\ngrid_pages:.byte >STYLE_PLAN,$48,$48\n"
         "grid_cells_low:.byte <880,<1320,<1760\n"
         "grid_cells_high:.byte >880,>1320,>1760\n"),
    )
    for old, new in replacements:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    control = out / "control-plan.s"
    control.write_text(source)
    dummy = out / "control-state.s"
    dummy.write_text(".export st_cells\nst_cells=$02fe\n")
    subprocess.run(["ca65", "-g", "-D", "SE_STYLE_LEXICAL=1", "-D",
                    "SE_STYLE_GRID=1", "-I", "src", "-I", "build", "-o",
                    out / "control-plan.o", control],
                   cwd=ROOT, check=True)
    subprocess.run(["ca65", "-o", out / "control-state.o", dummy],
                   cwd=ROOT, check=True)
    objects = [
        ROOT / "build/style-prod/entry.o", out / "control-plan.o",
        ROOT / "build/style-prod/editor-control.o",
        ROOT / "build/style-prod/reader-grid-dispatch.o",
        ROOT / "build/style-prod/inline-code.o",
        ROOT / "build/style-prod/bindings.o", out / "control-state.o",
    ]
    subprocess.run(["ld65", "-C", "cfg/style-c.cfg", "-o",
                    out / "control-styler.bin", "-m", out / "control-styler.map",
                    *objects], cwd=ROOT, check=True)
    production = ROOT / "build/overlays/styler.bin"
    current = len(production.read_bytes())
    control_bytes = len((out / "control-styler.bin").read_bytes())
    assert control_bytes > current
    return {
        "production_C14_bytes": current,
        "counterfactual_preclear_C14_bytes": control_bytes,
        "C14_bytes_saved": control_bytes - current,
        "linked_BSS_bytes_saved": 0,
        "logical_counter_bytes_retired": 2,
        "reserved_padding_bytes": 2,
        "removed_resident_fields": ["st_cells", "st_cells+1"],
    }


def run(out):
    out.mkdir(parents=True)
    saved = profile.observer.runner
    profile.observer.runner = runner
    try:
        gate = profile.observer.Gate(out, None)
    finally:
        profile.observer.runner = saved
    f, dll = gate.f, gate.dll
    rows = []
    try:
        for mode, width, base, size in MODES:
            for syntax, caps in CAPABILITIES:
                for document, source in documents(width):
                    for poison in POISONS:
                        tag = f"{syntax}-{width}-{document}-{poison:02x}"
                        f.source(source, physical=256)
                        f.typed(petscii("syntax " + syntax))
                        f.command(96 + mode)
                        profile.drain(f)
                        assert f.merged() == source, (tag, "setup source")
                        canonical = f.canonical()
                        catalog = f.catalog()
                        f.m.load(base, bytes((poison,)) * size)
                        f.put("se_st_valid", 0, 1)
                        f.put("se_st_cp_valid", 0, 1)
                        f.put("se_st_request", 1, 1)
                        dll.pn_begin(base, size)
                        try:
                            profile.drain(f)
                        finally:
                            dll.pn_end()
                        observed = plan_observation(dll, size)
                        assert observed["stale_reads"] == 0, (tag, observed)
                        assert f.merged() == source, (tag, "source")
                        assert f.canonical() == canonical, (tag, "canonical")
                        assert f.catalog() == catalog, (tag, "catalog")
                        assert not any(f.get(name, 1) for name in (
                            "se_e_job", "se_e_draw_busy", "se_e_redraw",
                            "se_f_owner", "se_doc_read_locks", "se_e_error",
                        )), (tag, f.debug())
                        assert f.get("se_st_valid", 1) == 1, (tag, "style valid")
                        plan = f.read(base, size)
                        remaining = plan.count(poison)
                        observed.update(
                            tag=tag, mode=mode, width=width, syntax=syntax,
                            caps=caps, document=document, source_bytes=len(source),
                            poison=poison, remaining_poison_bytes=remaining,
                            exact_pixels_sha256=pixel_oracle(f, source, caps, tag),
                        )
                        rows.append(observed)
                        (out / "progress.json").write_text(
                            json.dumps(rows, indent=2) + "\n")
                        print("PASS", tag, "reads", observed["reads"],
                              "writes", observed["writes"], "remaining", remaining,
                              flush=True)
        savings = measure_linked_savings(out)
        result = {
            "status": "PASS",
            "identity": gate.identity,
            "cases": rows,
            "case_count": len(rows),
            "semantic_cases": len(rows) // len(POISONS),
            "stale_plan_reads": sum(row["stale_reads"] for row in rows),
            "max_remaining_poison_bytes": max(row["remaining_poison_bytes"] for row in rows),
            "savings": savings,
            "scope": __doc__,
        }
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        f.close()


if __name__ == "__main__":
    out = OUT_ROOT / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    print("RUN", out, flush=True)
    result = run(out)
    print(json.dumps({
        "status": result["status"], "output": str(out),
        "stale_plan_reads": result["stale_plan_reads"],
        "savings": result["savings"],
    }, indent=2))
