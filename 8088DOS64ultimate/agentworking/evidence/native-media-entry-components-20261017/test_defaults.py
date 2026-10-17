from pathlib import Path
import hashlib,subprocess,shutil,json
P=Path(__file__).resolve().parent
W=P/'default-work'
if W.exists():raise RuntimeError('Fresh default-control directory required')
shutil.copytree(P/'work',W,ignore=shutil.ignore_patterns('build','__pycache__'))
profiles=[('undefined',{'DOS64_SAVE_HD_CONTEXT':'1','DOS64_EXPORT_CRC':'1'},['46fa2e54275818c1d946400c06c3e23bfd1c066c33fa967c399d39270d7f554f','63f131a7a3ec8deb4b6d9d77c76e14aadb529c36a7a6626b403d023ce3734439']),('explicit0',{'DOS64_MODAL_MENU':'0','DOS64_SAVE_HD_CONTEXT':'1','DOS64_EXPORT_CRC':'1'},None),('baseline',{'DOS64_MODAL_MENU':'0','DOS64_SAVE_HD_CONTEXT':'0','DOS64_EXPORT_CRC':'0'},['666089b57e5611a67b5d87ae84880256ef5dafb121b152e1de81b9ec1cc29064','b9e9cc9e7d87176848ccf8bae49dfe4f4ff0125b3aad5a1cb874341436b78df6'])]
records=[]
for name,flags,expected in profiles:
 if (W/'build').exists():shutil.rmtree(W/'build')
 with (P/('default-'+name+'.stdout')).open('wb')as out,(P/('default-'+name+'.stderr')).open('wb')as err:
  subprocess.run(['make','build/dos64.prg','build/dos64-tests.prg','verify-memory']+[k+'='+v for k,v in flags.items()],cwd=W,stdout=out,stderr=err,check=True)
 got=[hashlib.sha256((W/'build'/n).read_bytes()).hexdigest()for n in ['dos64.prg','dos64-tests.prg']]
 if expected is None:expected=records[0]['hashes']
 assert got==expected,(name,got,expected)
 records.append({'profile':name,'flags':flags,'hashes':got,'exact':True})
(P/'DEFAULT_RESULT.json').write_text(json.dumps({'passed':True,'records':records},indent=2)+'\n')
print('Three source-built profiles reproduce exact predecessor main/unit bytes')
