"""Deadline brackets only; inherits every original DeltaService data/handshake algorithm."""
import inspect
from c64u_delta_reu_recovery import DeltaService
from c64u_native_file_recovery import Budget,DeadlineClient

class DeadlineDeltaService(DeltaService):
    def phase(self,method,*args,**kwargs):
        bound=inspect.signature(method).bind(*args,**kwargs)
        seconds=bound.arguments.get('phase_seconds',600)
        underlying=self.client.client
        if not isinstance(underlying,DeadlineClient):raise ValueError('reviewed deadline-aware underlying HTTP client required')
        previous=underlying.budget;underlying.budget=Budget(self.clock,seconds)
        try:
            value=method(*args,**kwargs);underlying.budget.remaining();return value
        finally:underlying.budget=previous
    def load(self):return self.phase(super().load)
    def snapshot(self,*args,**kwargs):return self.phase(super().snapshot,*args,**kwargs)
    def restore(self,*args,**kwargs):return self.phase(super().restore,*args,**kwargs)
    def compare(self,*args,**kwargs):return self.phase(super().compare,*args,**kwargs)

class ApplicationBudget:
    def __init__(self,application):self.application=application
    def remaining(self):
        self.application.bound()
        return self.application.deadline-self.application.clock()
