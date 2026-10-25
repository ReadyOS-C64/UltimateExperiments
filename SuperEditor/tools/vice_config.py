"""Shared paths and step constructor for the existing .NET VICE harness."""
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HARNESS=Path(os.environ.get('VICE_TASKS_ROOT',str(
    ROOT.parent.parent/'agenticdevharness/tools/vice_tasks_dotnet'))).resolve()
PROJECT=HARNESS/'src/ViceTasks.Binary/ViceTasks.Binary.csproj'


def step(ident,kind,**params):
    return dict(id=ident,type=kind,criticality='control',params=params)
