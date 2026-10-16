# Source-only before every project import; the owning launcher guards this module too.
import sys as _entry_sys
from pathlib import Path as _EntryPath
_entry_cache = _EntryPath(__file__).resolve().parent / '.source-import-cache-disabled'
if _entry_cache.exists():
    raise RuntimeError('Source-only cache path must remain absent before first project import')
_entry_sys.dont_write_bytecode = True
_entry_sys.pycache_prefix = str(_entry_cache)
import bootstrap
"""Opt-in finite Delta recovery phases; native command/data protocol is inherited."""
from game_recovery import DeadlineDeltaService
from c64u_bulk_reu_recovery import SIZE, CHUNK
from c64u_native_file_recovery import Budget, DeadlineClient

BATCH_CHUNKS = 64
MAX_BATCHES = 4
MAX_RESTORE_PHASES = 1 + MAX_BATCHES


class BatchedDeadlineDeltaService(DeadlineDeltaService):
    """One exhaustive scan, at most four 1MiB write batches, separate full compare.

    Each scan/write phase is <=600s; the entire restore is <=3000s. There is
    no internal command retry or deadline renewal within a batch. The caller's
    reviewed orchestrator owns any bounded fresh load/rescan restoration retry.
    Inherited load/snapshot/compare keep their original individual deadlines.
    """
    def _restore_phase(self, kind, operation, seconds, total_deadline, **fields):
        underlying = self.client.client
        if not isinstance(underlying, DeadlineClient):
            raise ValueError('reviewed deadline-aware underlying HTTP client required')
        previous = underlying.budget
        budget = Budget(self.clock, seconds)
        budget.deadline = min(budget.deadline, total_deadline)
        try:
            underlying.budget = budget
            budget.remaining()
            self.journal('delta_bounded_phase_started', phase=kind,
                         deadline=budget.deadline, **fields)
            budget.remaining()
            value = operation(budget)
            budget.remaining()
            self.journal('delta_bounded_phase_complete', phase=kind, **fields)
            budget.remaining()
            return value
        finally:
            underlying.budget = previous

    def _scan(self, data, budget):
        changed = []
        for address in range(0, SIZE, CHUNK):
            budget.remaining()
            current = self.command(1, address, CHUNK)
            if not isinstance(current, bytes) or len(current) != CHUNK:
                raise ValueError('Incomplete delta scan chunk; no restoration writes authorized')
            if current != data[address:address + CHUNK]:
                changed.append(address)
        budget.remaining()
        self.check_code()
        budget.remaining()
        self.journal('delta_scan_complete', scope_bytes=SIZE,
                     compared_chunks=SIZE // CHUNK, changed_chunks=len(changed),
                     restoration_bytes=len(changed) * CHUNK,
                     unchanged_chunks=SIZE // CHUNK - len(changed))
        return tuple(changed)

    def _write_batch(self, data, addresses, budget):
        budget.remaining()
        self.check_code()
        budget.remaining()
        for address in addresses:
            budget.remaining()
            self.command(0, address, CHUNK, data[address:address + CHUNK])
            budget.remaining()
        self.check_code()
        budget.remaining()

    def restore(self, data, phase_seconds=600):
        if not isinstance(data, bytes) or len(data) != SIZE:
            raise ValueError('Restoration requires verified whole immutable backup')
        if not 1 <= phase_seconds <= 600:
            raise ValueError('Delta restore phase must be bounded1..600seconds')
        total_deadline = self.clock() + MAX_RESTORE_PHASES * phase_seconds
        changed = self._restore_phase('scan', lambda budget: self._scan(data, budget),
                                      phase_seconds, total_deadline,
                                      compared_chunks=SIZE // CHUNK)
        if (not isinstance(changed, tuple) or len(changed) > SIZE // CHUNK
                or any(type(a) is not int or a < 0 or a >= SIZE or a % CHUNK for a in changed)
                or tuple(sorted(set(changed))) != changed):
            raise ValueError('Invalid exhaustive delta scan plan; writes forbidden')
        batches = tuple(changed[n:n + BATCH_CHUNKS]
                        for n in range(0, len(changed), BATCH_CHUNKS))
        if len(batches) > MAX_BATCHES:
            raise ValueError('Delta restore exceeds finite write-batch bound')
        for index, addresses in enumerate(batches, 1):
            self._restore_phase('write',
                                lambda budget: self._write_batch(data, addresses, budget),
                                phase_seconds, total_deadline, batch=index,
                                batch_count=len(batches), changed_chunks=len(addresses),
                                restoration_bytes=len(addresses) * CHUNK)
        if self.clock() >= total_deadline:
            raise TimeoutError('Finite batched delta restoration exceeded total deadline')
        self.journal('delta_write_complete', scope_bytes=SIZE,
                     changed_chunks=len(changed), write_batches=len(batches),
                     maximum_write_batches=MAX_BATCHES,
                     maximum_chunks_per_batch=BATCH_CHUNKS,
                     maximum_restore_seconds=MAX_RESTORE_PHASES * phase_seconds,
                     independent_full_readback_required=True)
        if self.clock() >= total_deadline:
            raise TimeoutError('Finite batched delta restoration exceeded total deadline')
