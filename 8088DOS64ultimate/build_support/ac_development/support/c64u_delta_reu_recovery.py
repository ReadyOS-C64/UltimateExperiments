"""Development recovery: inspect all4MiB, restore changed16KiB chunks, verify all.

The complete immutable backup and original sequenced native Service remain the
source of authority. The scan is exhaustive, so changes outside expected guest
regions are detected too. This saves slow128byte transport uploads for unchanged
REU data. No device contact occurs on import and no native service is changed.
"""
from c64u_bulk_reu_recovery import Service,SIZE,CHUNK


class DeltaService(Service):
    def restore(self,data,phase_seconds=600):
        if not isinstance(data,bytes) or len(data)!=SIZE:
            raise ValueError('Restoration requires verified whole immutable backup')
        if not 1<=phase_seconds<=600:raise ValueError('Delta restore phase must be bounded1..600seconds')
        deadline=self.clock()+phase_seconds
        def bound():
            if self.clock()>=deadline:raise TimeoutError('Whole delta restoration exceeded phase deadline')
        changed=[]
        for address in range(0,SIZE,CHUNK):
            bound()
            current=self.command(1,address,CHUNK)
            if not isinstance(current,bytes) or len(current)!=CHUNK:
                raise ValueError('Incomplete delta scan chunk; no restoration writes authorized')
            if current!=data[address:address+CHUNK]:changed.append(address)
        bound();self.check_code()
        self.journal('delta_scan_complete',scope_bytes=SIZE,compared_chunks=SIZE//CHUNK,
                     changed_chunks=len(changed),restoration_bytes=len(changed)*CHUNK,
                     unchanged_chunks=SIZE//CHUNK-len(changed))
        for address in changed:
            bound();self.command(0,address,CHUNK,data[address:address+CHUNK]);bound()
        self.check_code();bound()
        self.journal('delta_write_complete',scope_bytes=SIZE,changed_chunks=len(changed),
                     independent_full_readback_required=True)
