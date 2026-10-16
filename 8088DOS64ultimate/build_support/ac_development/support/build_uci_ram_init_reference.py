#!/usr/bin/env python3
"""Link the frozen original RAM initializer against the current state symbols."""
from pathlib import Path
import re,subprocess,json,hashlib
root=Path(__file__).resolve().parents[1]
out=root/'build/uci-ram-init-reference';out.mkdir(parents=True,exist_ok=True)
labels=root/'build/dos64-tests.labels'
symbols={name:int(addr,16) for addr,name in re.findall(r'^al ([0-9A-Fa-f]+) \.([^\s]+)',labels.read_text(),re.M)}
source=root/'tests/fixtures/uci_ram_init_original.s'
names=sorted(set(re.findall(r'\bdos64_uci_\w+',source.read_text())))
(out/'uci_ram_init_state.inc').write_text('\n'.join(n+'=$%04x'%symbols[n] for n in names)+'\n')
(out/'link.cfg').write_text('MEMORY { RAM: start=$8000,size=$0800,file=%O; }\nSEGMENTS { CODE: load=RAM,type=ro; }\n')
subprocess.run(['ca65','-I',str(out),'-o',str(out/'original.o'),str(source)],check=True)
product=root/'build/original-init-reference.bin'
subprocess.run(['ld65','-C',str(out/'link.cfg'),'-o',str(product),str(out/'original.o')],check=True)
files=[Path(__file__).resolve(),source,labels,out/'uci_ram_init_state.inc',out/'link.cfg',product]
(out/'manifest.json').write_text(json.dumps({str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files},indent=2)+'\n')
