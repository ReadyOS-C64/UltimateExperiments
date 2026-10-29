"""Emit a seal macro and imports only, avoiding duplicate resident aliases."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
stem=a.report.name.removesuffix('-report.json');identity=verify(a.report.with_name(stem+'.prg'),a.report.with_name(stem+'.lbl'))
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+identity['digest'][i:i+2] for i in range(0,32,2))+'\n.endmacro\n')
