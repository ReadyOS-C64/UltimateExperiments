"""Private fastnormalR21 fit/component; explicit host-verified fontloan seam."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,binascii
import test_geos_strip_raster_candidate as build
import test_geos_literal_byte_candidate as proof
ROOT=build.ROOT;D=ROOT/'src/render/geos/expanded-font-candidate';BASE=ROOT/'build/geos-incremental-editor/20261025T174216345896Z/fixture'
def prepare(out,base,variant):
 old=build.D;build.D=D
 try:src,s,ls,raw,image,mods=build.build(out/'link',base,variant)
 finally:build.D=old
 return out/'link',src,s,ls,raw,image,mods
class Fixture(proof.Fixture):
 def __init__(self,*args):
  super().__init__(*args)
  font=self.font[::2]+self.widths;assert len(font)==1280 and binascii.crc_hqx(font,0xffff)==0x1857
  self.m.load(0x5000,font);self.m.write(0xCBD5,2)
def main():
 p=argparse.ArgumentParser();p.add_argument('--suite',choices=['fit','component'],default='fit');a=p.parse_args();out=ROOT/'build/geos-expanded-font'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 proof.prepare=prepare;proof.PRIVATE=D;proof.Fixture=Fixture
 if a.suite=='component':proof.component(out,BASE,'candidate')
 else:
  _,_,_,_,raw,image,mods=prepare(out,BASE,'candidate');print('FIT',len(raw),mods,flush=True)
if __name__=='__main__':main()
