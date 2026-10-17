All commands are local only. Run in the exact private work directory. No compiler, network or device is needed for these host composition controls; native component products are frozen reused inputs.

```
set -e
[[ $PWD == /Users/karlprosserpp/dev/c64projects/UltimateExperiments/8088DOS64ultimate/agentworking/scratch/native-copy20m-physical-purpose-20261017/work ]] || exit 1
/usr/bin/python3 -B test_copy.py
/usr/bin/python3 -B test_purpose.py
/usr/bin/python3 -B test_detached.py
/usr/bin/python3 -B launch.py --manifest "$PWD/LAUNCH_MANIFEST.json" --sha "$(cat LAUNCH_SHA.txt)" --offline
```

The process controls write local DETACHED_CONTROL/DETACHED_BOUNDS observations in this package. For independent replay, copy the sealed cohort to a fresh review directory and preserve existing observations; rebase only fixture/output paths with an explicit source derivative receipt. The physical preflight deliberately binds original paths and ACTIVE bytes; it should refuse an unrebased relocated live purpose. Do not rerun prepare.py against a frozen physical purpose. Do not dispatch without ROOT review of exact launch hash and unchanged predecessor.
