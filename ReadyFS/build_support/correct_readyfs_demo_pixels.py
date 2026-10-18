#!/usr/bin/env python3
"""Correct nibble order in the initial capture without changing its timing.

The initial runner borrowed an older stream decoder that exchanged adjacent
VIC pixels. Retain that first encoding as evidence and correct those pairs.
Future captures use the corrected low-nibble-first lookup directly.
"""
from pathlib import Path
import sys,subprocess,json,hashlib
from PIL import Image
root=Path(sys.argv[1])
def swap(rgb):
    out=bytearray(len(rgb))
    for channel in range(3):
        out[channel::6]=rgb[channel+3::6]
        out[channel+3::6]=rgb[channel::6]
    return bytes(out)
source=root/'readyfs-demo.mp4';original=root/'readyfs-demo-initial-decoder.mp4'
assert not original.exists(),'Do not correct twice'
source.rename(original)
ff='/opt/homebrew/bin/ffmpeg'
decoder=subprocess.Popen([ff,'-v','error','-i',str(original),'-vf','scale=384:272:flags=neighbor','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
report=json.loads((root/'video-report.json').read_text())
encoder=subprocess.Popen([ff,'-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','384x272','-framerate',str(report['fps']),'-i','-','-vf','scale=768:544:flags=neighbor,setsar=1','-c:v','libx264','-preset','fast','-crf','15','-pix_fmt','yuv420p','-movflags','+faststart',str(source)],stdin=subprocess.PIPE)
size=384*272*3;count=0
while True:
    frame=decoder.stdout.read(size)
    if not frame:break
    assert len(frame)==size
    encoder.stdin.write(swap(frame));count+=1
encoder.stdin.close();assert decoder.wait()==0 and encoder.wait()==0
assert count==report['frames'],(count,report['frames'])
for path in list(root.glob('chapter-*.png'))+[root/'poster.png']:
    image=Image.open(path).convert('RGB').resize((384,272),Image.Resampling.NEAREST)
    Image.frombytes('RGB',(384,272),swap(image.tobytes())).resize((768,544),Image.Resampling.NEAREST).save(path)
report.update({'pixel_decoder':'low nibble is left pixel; initial adjacent-pixel order corrected without cuts or speed changes','sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'megabytes':source.stat().st_size/1e6})
(root/'video-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
