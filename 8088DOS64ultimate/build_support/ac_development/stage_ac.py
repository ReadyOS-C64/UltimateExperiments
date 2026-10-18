#!/usr/bin/env python3
import sys
from pathlib import Path
_cache=Path(__file__).resolve().parent/'.source-import-cache-disabled'
if _cache.exists():raise RuntimeError('Source-only cache path must remain absent')
sys.dont_write_bytecode=True;sys.pycache_prefix=str(_cache)
import bootstrap,argparse,json
from ac_contract import read_json
from ac_staging import stage_media
from ac_helper_staging import stage_helper
from ac_runner import connect_factory
from c64u_ftp_put_transport import prepare_prgs
p=argparse.ArgumentParser();p.add_argument('phase',choices=['media','prgs','helper']);p.add_argument('--arguments',required=True);p.add_argument('--run-id',required=True);p.add_argument('--output',required=True);p.add_argument('--prepared');a=p.parse_args();args=read_json(a.arguments);connect=connect_factory(args['host'])
if a.phase=='media':r=stage_media(connect,args['floppy'],args['hd'],a.run_id,a.output)
else:
 if not a.prepared:p.error('--prepared required')
 prepared=Path(a.prepared);receipt=read_json(prepared/'prepared.json')
 if a.phase=='helper':r=stage_helper(connect,prepared/'HD-CLOSE.PRG',receipt['helper_sha256'],a.run_id,a.output)
 else:r=prepare_prgs(lambda:connect(5),{role:{'path':str(prepared/leaf),'sha256':receipt[key]} for role,leaf,key in [('native','NATIVE-DOS.PRG','native_sha256'),('recovery','REU-RECOVERY.PRG','service_sha256')]},a.run_id,a.output)
print(json.dumps({'status':r['status'],'hardware_executed':False,'remote_directory':r['remote_directory']}))
