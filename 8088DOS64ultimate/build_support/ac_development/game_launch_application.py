"""Retain actual load/SYS authority/events without replacing the first application error."""
from pathlib import Path
from c64u_native_file_runner import checked_application
from c64u_bulk_reu_recovery import dump

def application_with_launch_evidence(app):
    invoke=checked_application(app)
    def run(client,output):
        primary=None
        try:return invoke(client,output)
        except BaseException as error:primary=error;raise
        finally:
            try:dump(Path(output)/'native-load-SYS-handoff.json',{'authority':{k:v.hex()if isinstance(v,bytes)else v for k,v in client.authority.items()if k!='labels'},'events':client.events,'load_returned':client.load_returned,'SYS_count_verified':client.sys_go_verified,'start_resume_attempted':client.start_resume_attempted,'configured_native_unchanged':True,'hidden_preSYS_verified':False,'application_failed':primary is not None})
            except BaseException:
                if primary is None:raise
    return run

