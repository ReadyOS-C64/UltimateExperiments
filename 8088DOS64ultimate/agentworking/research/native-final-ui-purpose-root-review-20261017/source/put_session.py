"""Metadata hook only; exact reviewedFast firstcause/ownership lifecycle."""
import json
from fast import Fast
class Session(Fast):
 def __init__(self,*a,**kw):
  super().__init__(*a,**kw);self.wire.archive_request=lambda v:self.save(f'HTTP-request-plan-{v["index"]:04d}.json',(json.dumps(v,indent=2)+'\n').encode())
