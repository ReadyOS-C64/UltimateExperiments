"""Collect genuine Ultimate stream PNGs with source-bound native RAM checks.

Offline only. Never contacts a device, alters originals or includes vendor disks.
"""
import argparse,hashlib,json,shutil,sys,zipfile
from pathlib import Path
from html import escape
from PIL import Image,ImageChops
from cga_cursor_oracle import render_text_capture
P=Path(__file__).resolve().parents[1]
PALETTE=[(0,0,0),(239,239,239),(141,47,52),(106,212,205),(152,53,164),(76,180,66),(44,41,177),(239,239,93),(152,78,32),(91,56,0),(209,103,109),(74,74,74),(123,123,123),(159,239,147),(109,106,239),(178,178,178)]
def sha(b):return hashlib.sha256(b).hexdigest()
def native_image(bitmap,matrix):
 image=Image.new('RGB',(320,200));pixels=image.load()
 for y in range(200):
  for x in range(320):
   cell=(y//8)*40+x//8;bits=bitmap[cell*8+y%8];pixels[x,y]=PALETTE[matrix[cell]>>4 if bits&(128>>(x%8))else matrix[cell]&15]
 return image

def collect(runs,out):
 out.mkdir(parents=True,exist_ok=False);items=[]
 for directory in runs:
  for png in sorted(directory.glob('*-VIC.png')):
   tag=png.name[:-8];name=f'{len(items)+1:03d}-{tag}';raw=png.read_bytes();destination=out/(name+'.png');destination.write_bytes(raw)
   row={'title':tag,'source':str(png.resolve()),'file':destination.name,'VIC_stream_sha256':sha(raw),'native_RAM_compared':False,'scope':'Actual Ultimate video stream PNG'}
   bitmap=directory/(tag+'-C64-bitmap.bin')
   if bitmap.is_file():
    matrix=(directory/(tag+'-C64-matrix.bin')).read_bytes();bits=bitmap.read_bytes();bda=(directory/(tag+'-BDA.bin')).read_bytes();video=(directory/(tag+'-CGA.bin')).read_bytes();state=(directory/(tag+'-CGA-state.bin')).read_bytes();blink=(directory/(tag+'-blink.bin')).read_bytes()[0];fonts=(directory/'native-fonts.bin').read_bytes();sourcefonts=(P/'assets/native-text/cp437-narrow4x8.bin').read_bytes()+(P/'assets/native-text/cp437-unscii8.bin').read_bytes();assert fonts==sourcefonts
    cga=bytearray(16384);offset=int.from_bytes(bda[0x4e:0x50],'little');cga[offset:offset+len(video)]=video
    expected=render_text_capture(bda,bytes(cga),fonts[:1024],fonts[1024:],registers=state[:18],control=state[18],control_valid=state[19],phase_valid=state[20],field_phase=state[21],blink_visible=blink,native_sha256='1506210a336fb034c1164cf6463ae17d4c335c586e561dc996d79212afcb9a39',expected_native_sha256='1506210a336fb034c1164cf6463ae17d4c335c586e561dc996d79212afcb9a39')
    assert expected['bitmap']==bits and expected['matrix']==matrix,(tag,'native RAM oracle')
    native=native_image(bits,matrix);frame=Image.open(png).convert('RGB');assert frame.size==(384,272),(tag,frame.size);assert ImageChops.difference(frame.crop((32,35,352,235)),native).getbbox()is None,(tag,'live VIC vs RAM')
    native.save(out/(name+'-RAM.png'));shutil.copyfile(directory/(tag+'.txt'),out/(name+'.txt'));row.update(native_RAM_compared=True,independent_cursor_aware_oracle=True,all8000_bitmap1000_matrix_bytes_equal=True,all64000_VIC_active_pixels_equal_native_RAM=True,columns=expected['metadata']['columns'],RAM_file=name+'-RAM.png')
   items.append(row)
 manifest={'status':'passed','source':'Actual physical C64 Ultimate stream captures, local native RAM/oracle comparisons where present','captures':len(items),'items':items,'vendor_disk_images_included':False,'physical_CIA_human_acceptance':False};(out/'GALLERY.json').write_text(json.dumps(manifest,indent=2)+'\n')
 cards=[]
 for row in items:
  title=row['title'].replace('-',' ');ram=f'<details><summary>Verified native display buffer</summary><img src="{row["RAM_file"]}" alt="native RAM display"></details>'if row.get('RAM_file')else''
  cards.append(f'<article><h2>{escape(title)}</h2><a href="{escape(row["file"])}"><img src="{escape(row["file"])}" alt="{escape(title)}"></a><p>Physical Ultimate video stream'+(' · pixel-verified against native RAM'if row['native_RAM_compared']else' · native application screen')+f'</p>{ram}</article>')
 html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>C64 Ultimate physical test screenshots</title><style>body{font:16px system-ui;background:#10151e;color:#eef2f8;margin:0 auto;padding:28px;max-width:1600px}h1{font-size:30px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,650px),1fr));gap:24px}article{padding:18px;background:#1d2635;border-radius:10px}h2{font-size:19px}img{width:100%;height:auto;image-rendering:pixelated;background:black}p{color:#bdcce2}a{color:#8ed0ff}summary{cursor:pointer}</style><h1>Physical C64 Ultimate test walkthrough</h1><p>Actual video-stream screenshots. Click any image for its original PNG. The DOS and application frames also have independent memory/cursor checks where indicated. Automated BIOS input is separate from human keyboard acceptance.</p><main>'''+''.join(cards)+'</main></html>'
 (out/'index.html').write_text(html);archive=out.with_suffix('.zip')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
  for file in sorted(out.iterdir()):z.write(file,file.name)
 return manifest
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);parser.add_argument('runs',type=Path,nargs='+');a=parser.parse_args();report=collect(a.runs,a.out);print(json.dumps({'status':report['status'],'captures':report['captures'],'out':str(a.out)}))
