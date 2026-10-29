"""Package only the privately qualified R21 into an owned, coherent D81 fixture."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_strip_raster_candidate as builder
from d81_image import D81Image

def package(out,base):
    D=Path(__file__).resolve().parent
    saved=builder.D;builder.D=D
    try:_,_,labels,raw,image,_=builder.build(out/'leaf',base,'candidate')
    finally:builder.D=saved
    target=out/'fixture';shutil.copytree(base,target)
    path=target/'build/overlays/geosrow.seo';path.write_bytes(image)
    for suffix in ['bin','lbl','map']:shutil.copy2(out/'leaf'/('geosrow.'+suffix),target/'build/overlays'/('geosrow.'+suffix))
    identity=json.loads((target/'freeze.json').read_text())
    sha=lambda b:hashlib.sha256(b).hexdigest()
    old=identity['assets']['geosrow'];identity['assets']['geosrow']=sha(image)
    replacements={f'src/render/geos/literal-byte/{n}':(D/n).read_bytes()for n in ['row.s','measure.s','glyph.s','assets.s']}
    archive=target/'product-sources.zip';temp=target/'product-sources-new.zip'
    with zipfile.ZipFile(archive)as source,zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED)as dest:
        for item in source.infolist():dest.writestr(item,replacements.get(item.filename,source.read(item.filename)))
    temp.replace(archive)
    for name,data in replacements.items():identity['sources'][name]=sha(data)
    command=['c1541','-attach',str(target/'build/supereditor.d81'),'-delete','geosrow','-write',str(path),'geosrow,s']
    result=subprocess.run(command,text=True,capture_output=True);(out/'package.log').write_text(result.stdout+result.stderr);assert not result.returncode
    disk=D81Image((target/'build/supereditor.d81').read_bytes())
    assert disk.read(b'SUPEREDITOR',kind=2).data==(target/'build/editor.prg').read_bytes()
    for name in identity['names']:assert disk.read(name.upper().encode(),kind=1).data==(target/'build/overlays'/(name+'.seo')).read_bytes(),name
    identity['disk_sha256']=sha((target/'build/supereditor.d81').read_bytes())
    identity['private_R21_substitution']=dict(before=old,after=sha(image),payload=len(raw),only_asset_changed=True,source_archive_updated=True,fixed_font_addresses=[hex(labels[n])for n in ['se_geos_packed','se_geos_widths','row_clear']])
    (target/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
    return target

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);a=p.parse_args()
    out=ROOT/'build/geos-phase-dispatch-packaged'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    print('FIXTURE',package(out,a.base.resolve()),flush=True)
