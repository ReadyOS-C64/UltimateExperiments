"""Explicit, pinned import of a small hardware-generated functional corpus."""
import concurrent.futures
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request

PIN="aea84484abc79d09639d855b7b0ab32bc9e4dbeb"
OPCODES="B0 B7 B8 BF 90 97 A0 A1 A2 A3 E9 EA EB F5 F8 F9 FA FB FC FD".split()
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
    chosen=list(range(24))
    # Add a late boundary case if present; do not claim random sampling proves
    # segment-FFFF behavior when this opcode's corpus contains no such case.
    edge=next((i for i,t in enumerate(source) if t["initial"]["regs"]["ip"]>=0xfffc),None)
    if op=="A3":edge=9570  # audited hardware FFFE offset vector
    if edge is not None and edge not in chosen:chosen.append(edge)
    for i in chosen:
        t=source[i]
        case={k:t[k] for k in ("name","bytes","initial","final","hash","idx")}
        case["initial"]={k:case["initial"][k] for k in ("regs","ram")}
        case["final"]={k:case["final"][k] for k in ("regs","ram")}
        case["opcode"]=op
        case["flags_mask"]=metadata["opcodes"][op].get("flags-mask",65535)
        cases.append(case)
fixture=project/"tests/fixtures/8088-subset.json"
fixture.write_text(json.dumps(cases,separators=(",",":"))+"\n")
record={"repository":"https://github.com/SingleStepTests/8088","commit":PIN,
        "license":"MIT; LICENSE retained alongside this record","selection":"first 24 per selected opcode plus audited boundary rows",
        "limitations":"Functional state only; cycles/queue omitted, no interrupt or throughput coverage",
        "source_files":[{"path":name,"sha256":hashlib.sha256(data).hexdigest()} for name,data in files.items()],
        "fixture":"tests/fixtures/8088-subset.json","fixture_sha256":hashlib.sha256(fixture.read_bytes()).hexdigest(),"cases":len(cases)}
(vendor/"UPSTREAM.json").write_text(json.dumps(record,indent=2)+"\n")
print(f"Imported {len(cases)} pinned hardware cases")
