from pathlib import Path
import ast,binascii,json
root=Path(__file__).resolve().parents[1]
from cache_job_build import editor_names
names=editor_names(root);assert len(names)==63 and names[-1]=='paint'
raw=(root/'build/overlays/geospage.bin').read_bytes();assert len(raw)==4096
out=root/'build/geos-prod/convergence-witness.inc'
out.write_text('CV_C21_INDEX='+str(names.index('geospage'))+'\nCV_C21_SIZE='+str(len(raw))+'\nCV_C21_CRC='+str(binascii.crc_hqx(raw,65535))+'\n')
