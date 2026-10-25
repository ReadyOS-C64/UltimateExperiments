"""Exact unmodified combined48 control for the local-status PAL10 scenario."""
import sys
from pathlib import Path
import test_grid_typing_local_vice as local
if __name__=='__main__':
 local.profile.scenario=local.scenario
 sys.argv=[sys.argv[0],'--fixture',str(local.ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture')]
 local.profile.main()
