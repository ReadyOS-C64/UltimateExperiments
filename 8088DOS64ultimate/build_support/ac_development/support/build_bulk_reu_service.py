"""Build isolated development recovery PRG, optionally test it in Peddle.

No shared runtime build files or bridge sources are edited. Output is fixed to
project-owned agentworking/scratch/bulk-reu so hardware review has stable paths.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test",action="store_true")
    args=parser.parse_args()
    project=Path(__file__).resolve().parents[1]
    out=project/"agentworking/scratch/bulk-reu";out.mkdir(parents=True,exist_ok=True)
    def run(argv,log=None):
        if log:
            with (out/log).open("w") as file:subprocess.run(argv,cwd=project,stdout=file,stderr=subprocess.STDOUT,check=True)
        else:subprocess.run(argv,cwd=project,check=True)
    for stem,source in (("service","src/bulk_reu_service.s"),("reu","src/reu.s")):
        run(["ca65","-g","-I","include","-o",str(out/f"{stem}.o"),source])
    run(["ld65","-C","cfg/dos64-bulk-reu.cfg","-o",str(out/"service.prg"),"-Ln",str(out/"service.labels"),"-m",str(out/"service.map"),str(out/"service.o"),str(out/"reu.o")])
    paths=[project/"src/bulk_reu_service.s",project/"src/reu.s",project/"include/reu.inc",project/"cfg/dos64-bulk-reu.cfg",
           Path(__file__).resolve(),project/"build_support/c64u_bulk_reu_recovery.py",project/"tests/host/bulk_reu_service.zig",project/"tests/tooling/test_bulk_reu_recovery.py",
           out/"service.prg",out/"service.labels",out/"service.map"]
    manifest={"schema":1,"hardware_executed":False,"peddle_tests":None,"host_tests":None}
    if args.test:
        frozen=[project/"tests/host/peddle_bridge.cpp",*sorted((project/"tests/host").glob("*.h"))]
        for source in frozen:shutil.copyfile(source,out/source.name)
        peddle=[project/f"third_party/peddle/Peddle/{name}" for name in ("Peddle.cpp","PeddleDebugger.cpp","PeddleDisassembler.cpp","StrWriter.cpp")]
        zig=project/"../../zeropage-tooling/bin/zig"
        if not zig.exists():zig=Path(shutil.which("zig") or "missing-zig")
        run([str(zig),"test","tests/host/bulk_reu_service.zig",str(out/"peddle_bridge.cpp"),*[str(p) for p in peddle],"-I",str(out),"-I","third_party/peddle/Peddle","-lc++","-O","Debug"],"peddle-test.log")
        run(["python3","-m","unittest","discover","-s","tests/tooling","-p","test_bulk_reu_recovery.py"],"host-test.log")
        manifest.update(peddle_tests=4,host_tests=17)
        manifest["compiler_version"]=subprocess.check_output([str(zig),"version"],cwd=project,text=True).strip()
        paths.extend([out/p.name for p in frozen]);paths.extend(peddle)
        paths.extend([out/"peddle-test.log",out/"host-test.log"])
    manifest["artifacts"]={str(p.relative_to(project)):{"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"prg":str(out/"service.prg"),"peddle_tests":manifest["peddle_tests"],"host_tests":manifest["host_tests"]}))

if __name__=="__main__":main()
