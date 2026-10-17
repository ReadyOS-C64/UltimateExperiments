from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-post-oracle');assert not Path(sys.pycache_prefix).exists()
import json,hashlib
p=next((P/'execution/fresh40').glob('*fresh-COM-returned.txt'));lines=[line.strip()for line in p.read_text().splitlines()if line.strip()]
expected=['C>C:'+chr(92)+'V1TRAP.COM','C>ECHO V1_FRESH_RUN_OK','V1_FRESH_RUN_OK','C>'];assert lines==expected,(lines,expected)
a=(P/'media/C-closed-debug.IMG').read_bytes();b=(P/'execution/C-after-fresh-Finish.IMG').read_bytes();assert a==b
result=json.loads((P/'execution/RESULT.json').read_text());assert result['passed']and result['fresh40_wire']['WRITE05_commands']==0
finish=json.loads((P/'execution/fresh40/CIA_FINISH.json').read_text());assert finish['passed']and finish['actual_one_C_CLOSE']and finish['private_safe']and finish['no_resume']and finish['full4M_exact']
(P/'POST_EXECUTION_ORACLE.json').write_text(json.dumps({'passed':True,'exact_complete_post_CLS_COM_output':lines,'no_silent_error_text_or_stale_TYPE':True,'full_C_exact':True,'full_C_sha256':hashlib.sha256(b).hexdigest(),'fresh_WRITE05':0,'CIA_privateSafe_one_known_C_CLOSE':True},indent=2)+'\n')
