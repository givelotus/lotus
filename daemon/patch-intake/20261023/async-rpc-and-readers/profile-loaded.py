#!/usr/bin/env python3
"""Matched diagnostic profiles; never publish their instrumented throughput."""
import importlib.util,sys,json,fcntl,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('audit',ROOT/'daemon/bench/commit-regressions/run.py'); audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
lock=(ROOT/'daemon/.local-artifact-archive/benchmark-host.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
source_lock=(audit.SOURCE/'.git/progression.lock').open('a');fcntl.flock(source_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
base=ROOT/'daemon/patch-intake/20261023/async-rpc-and-readers/loaded-profiles';base.mkdir(exist_ok=False)
for name,variant,ref in [('before','queue-only-fixture-corrected','94453bdd7d8a681d6a872df85366f370bfa78089'),('after','async-admission-and-info','d2e4db32265dd92bbced94c9861af449ca0d8f9c')]:
 audit.checkout(ref)
 receipt=json.loads((ROOT/'daemon/.local-artifact-archive/commit-regressions'/variant/'point-377/BUILD.json').read_text());assert audit.sha(receipt['binary'])==receipt['binary_sha256']
 directory=base/name;directory.mkdir();output=directory/'result.json'
 argv=[sys.executable,ROOT/'daemon/bench/commit-regressions/steady_loopback.py','--series','l1','--daemon',receipt['binary'],'--source',audit.SOURCE,'--output',output,'--steady','--case','single_tx_loaded_steady','--max-fixture-transactions','800000','--fixture-fee-sats','10000','--hierarchical-funding','--maxmempool-mb','4096','--port-base','39110','--sample-node0-output',directory/'node0.sample.txt']
 audit.write(directory/'INPUTS.json',{'source':receipt,'argv':list(map(str,argv)),'timing_publishable':False})
 print(name,flush=True)
 env=dict(os.environ,TMPDIR=str(ROOT/'daemon/.local-artifact-archive/commit-regressions/runtime'))
 resources=audit.guarded(argv,directory/'stdout.log',env);audit.write(directory/'RESOURCES.json',resources)
