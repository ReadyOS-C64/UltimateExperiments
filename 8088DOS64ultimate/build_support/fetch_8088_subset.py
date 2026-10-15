"""Explicit, pinned import of a small hardware-generated functional corpus."""
import concurrent.futures
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request

PIN="aea84484abc79d09639d855b7b0ab32bc9e4dbeb"
BASE_OPCODES="B0 B7 B8 BF 90 97 A0 A1 A2 A3 E9 EA EB F5 F8 F9 FA FB FC FD".split()
# Every arithmetic direction/width and immediate extension gets a bounded
# projection; independently generated operand tests cover the address matrix.
ARITHMETIC=[f"{family+form:02X}" for family in range(0,0x40,8) for form in range(6)]
GROUPS=[f"{op:02X}.{extension}" for op in range(0x80,0x84) for extension in range(8)]
ADDED=(ARITHMETIC+[f"{op:02X}" for op in range(0x40,0x60)]+GROUPS+
       "06 07 0E 16 17 1E 1F 84 85 88 89 8A 8B 8C 8D 8E 9A 9C 9D 9E 9F C2 C3 C4 C5 C6 C7 CA CB E8".split())
CONTROL_STRINGS=([f"{op:02X}" for op in range(0x60,0x80)]+
                 "E0 E1 E2 E3 A4 A5 A6 A7 AA AB AC AD AE AF CC CD CE CF".split())
SHIFTS=[f"{op:02X}.{extension}" for op in range(0xd0,0xd4) for extension in range(8)]
MATH_INDIRECT=([f"{op}.{extension}" for op in ("F6","F7","FF") for extension in range(8)]+
               "FE.0 FE.1 8F 98 99 86 87 A8 A9".split())
# Indexed primary-source rows audited for original-8088 corner behavior.
EXTRA_ROWS={
    "F6.6":{197:"zero divisor",2152:"byte operand effective offset FFFF"},
    "F6.7":{11:"successful REP F3 quotient negation",14:"REP F2 divide overflow",54:"successful REP F2 quotient negation",213:"zero divisor",1828:"minimum signed quotient raises divide error"},
    "F7.7":{110:"REP F2 divide overflow",143:"successful REP F3 quotient negation",612:"successful REP F2 quotient negation",9837:"zero divisor"},
    "FF.6":{68:"original PUSH SP ordering"},"FF.7":{81:"PUSH SP alias ordering"},
}
ADJUST_OPCODES="27 2F 37 3F D4 D5 D6 D7".split()
OPCODES=BASE_OPCODES+ADDED+CONTROL_STRINGS+SHIFTS+MATH_INDIRECT+ADJUST_OPCODES
project=Path(__file__).resolve().parents[1]
scratch=project/"agentworking/scratch/sst8088"
vendor=project/"third_party/sst8088"
scratch.mkdir(parents=True,exist_ok=True);vendor.mkdir(parents=True,exist_ok=True)
prior=vendor/"UPSTREAM.json"
known=json.loads(prior.read_text()) if prior.exists() else {}
hashes={f["path"]:f["sha256"] for f in known.get("source_files",[])} if known.get("commit")==PIN else {}

def fetch(name):
    path=scratch/name
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=hashes.get(name):
        data=urllib.request.urlopen(f"https://raw.githubusercontent.com/SingleStepTests/8088/{PIN}/{name}",timeout=30).read()
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    return name,path.read_bytes()

names=["LICENSE","v2/metadata.json"]+[f"v2/{op}.json.gz" for op in OPCODES]
files=dict(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(fetch,names))
(vendor/"LICENSE").write_bytes(files["LICENSE"])
metadata=json.loads(files["v2/metadata.json"])
cases=[]
for op in OPCODES:
    source=json.loads(gzip.decompress(files[f"v2/{op}.json.gz"]))
    chosen=list(range(128 if op in ADJUST_OPCODES else 24 if op in BASE_OPCODES else 8))
    if op in ("27","2F","37","3F"):
        edges={0,1,5,6,0x99,0x9a,0x9f,0xa0,0xf9,0xfa,0xff}
        chosen+= [i for i,t in enumerate(source) if (t["initial"]["regs"]["ax"]&255) in edges and i not in chosen]
    if op in ("D4","D5"):
        seen=set()
        for i,t in enumerate(source):
            base=t["bytes"][-1]
            if base not in seen or (op=="D4" and base==0):
                if i not in chosen:chosen.append(i)
                seen.add(base)
    for i in EXTRA_ROWS.get(op,{}):
        if i not in chosen:chosen.append(i)
    # C6/C7 contain undefined extension aliases in this original-8088 source.
    # Retain all eight observed extensions rather than filtering to /0.
    alias_extensions={}
    if op in ("C6","C7"):
        for i,t in enumerate(source):
            pos=0
            while t["bytes"][pos] in (0x26,0x2e,0x36,0x3e,0xf0,0xf2,0xf3):pos+=1
            extension=(t["bytes"][pos+1]>>3)&7
            if extension not in alias_extensions:alias_extensions[extension]=i
        for i in alias_extensions.values() or i in EXTRA_ROWS.get(op,{}):
            if i not in chosen:chosen.append(i)
    # Add a late boundary case if present; do not claim random sampling proves
    # segment-FFFF behavior when this opcode's corpus contains no such case.
    edge=next((i for i,t in enumerate(source) if t["initial"]["regs"]["ip"]>=0xfffc),None)
    if op=="A3":edge=9570  # audited hardware FFFE offset vector
    if op in BASE_OPCODES and edge is not None and edge not in chosen:chosen.append(edge)
    for selection_index,i in enumerate(chosen):
        t=source[i]
        case={k:t[k] for k in ("name","bytes","initial","final","hash","idx")}
        case["initial"]={k:case["initial"][k] for k in ("regs","ram")}
        case["final"]={k:case["final"][k] for k in ("regs","ram")}
        case["opcode"]=op
        case["quick"]=selection_index<2 or (op in BASE_OPCODES and selection_index>=24) or i in alias_extensions.values() or i in EXTRA_ROWS.get(op,{})
        base,_,extension=op.partition(".")
        info=metadata["opcodes"][base]
        if extension:info=info["reg"][extension]
        if base in ("C6","C7","8F"):info=info["reg"]["0"]
        case["flags_mask"]=info.get("flags-mask",65535)
        # DIV/IDIV status flags are undefined, including the flags word pushed
        # by divide-error entry. Mask those same upstream-declared bits only;
        # return IP/CS, reserved/control bits, and all other RAM stay exact.
        if base in ("F6","F7") and extension in ("6","7") and t["final"]["regs"].get("sp")==((t["initial"]["regs"]["sp"]-6)&65535):
            flags_offset=(t["initial"]["regs"]["sp"]-2)&65535
            ss=t["initial"]["regs"]["ss"]
            case["ram_masks"]=[[(ss*16+flags_offset)&0xfffff,case["flags_mask"]&255],
                               [(ss*16+((flags_offset+1)&65535))&0xfffff,case["flags_mask"]>>8]]
        cases.append(case)
fixture=project/"tests/fixtures/8088-subset.json"
fixture.write_text(json.dumps(cases,separators=(",",":"))+"\n")
record={"repository":"https://github.com/SingleStepTests/8088","commit":PIN,
        "license":"MIT; LICENSE retained alongside this record","selection":"first24 per baseline opcode plus audited boundary rows; first8 per added opcode/extension including first hardware C6/C7 case of every extension alias; adjust first128 each plus all BCD AL edge rows, every AAM/AAD base first row and every AAM0 row; quick rows explicit",
        "limitations":"Functional state only; cycles/queue omitted; register flags use upstream-defined masks; divide-error saved FLAGS masks only the same undefined arithmetic bits; no throughput coverage",
        "audited_extra_rows":EXTRA_ROWS,
        "source_gaps":["FE.2 through FE.7 are absent at this pin", "8F source contains only /0", "F6/F7 MUL, IMUL and unsigned DIV sources contain no REP prefixes; IDIV prefixes are covered", "Adjust opcode sources contain no REP prefixes; independent microcode-derived behavior tests cover that gap"],
        "source_files":[{"path":name,"sha256":hashlib.sha256(data).hexdigest()} for name,data in files.items()],
        "fixture":"tests/fixtures/8088-subset.json","fixture_sha256":hashlib.sha256(fixture.read_bytes()).hexdigest(),"cases":len(cases)}
(vendor/"UPSTREAM.json").write_text(json.dumps(record,indent=2)+"\n")
print(f"Imported {len(cases)} pinned hardware cases")
