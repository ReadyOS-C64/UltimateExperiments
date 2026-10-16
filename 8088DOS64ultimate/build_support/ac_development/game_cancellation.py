"""Report after original recovery finally; never replace the primary exception."""
import json
from pathlib import Path
from c64u_bulk_reu_recovery import dump

def recover_honestly(recovery,output,*args,**kwargs):
    try:
        return recovery(*args,output=output,**kwargs),None
    except BaseException as error:
        path=Path(output)/'result.json'
        result={'reu_restored':False,'configuration_restored':False,'reset_resumed':False,'outer_recovery_report_missing':True}
        attached=getattr(error,'dos64_recovery_report',None)
        if isinstance(attached,dict):
            result=dict(attached)
            result['recovery_report_from_pinned_orchestrator_memory']=True
        try:
            if path.is_file():
                candidate=json.loads(path.read_text())
                if not isinstance(candidate,dict):raise ValueError('Recovery report is not an object')
                result=candidate
        except BaseException as secondary:result['recovery_report_read_error']=repr(secondary)
        result.update(status='failed',error=repr(error),error_type=type(error).__name__)
        if isinstance(error,(KeyboardInterrupt,SystemExit)):result['cancelled']=True
        result['cancellation_reporting']='finalized after unchanged outer recovery finally'
        try:dump(path,result)
        except BaseException as secondary:result['cancellation_report_write_error']=repr(secondary)
        return result,error
