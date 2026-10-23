#!/usr/bin/env python3
"""Use the frozen workload with domain-correct startup flags; timed core unchanged."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
SCRIPTS=ROOT/'daemon/patch-audit/consolidation/20261022/benchmark-tools/scripts'
sys.path.insert(0,str(SCRIPTS))
frozen=SCRIPTS/'matched_loopback.py'
lines=frozen.read_text().splitlines()
result=[];changed=0
for line in lines:
    if line.startswith('code=code.replace(') and '-txreconfull=1' in line:
        result.extend(["if a.series == 'v2':",'    '+line,'else:',
                       '    code=code.replace(\'"-server=1",\', \'"-server=1", "-avalanche=0",\')'])
        changed+=1
    elif line.startswith('adaptations.append(') and 'Explicit current527' in line:
        result.append("adaptations.append('Domain-correct startup: native full-membership option only for V2; Avalanche disabled; frozen timed ingestion unchanged')")
    else:result.append(line)
if changed!=1:raise RuntimeError('Frozen startup adapter changed; review before running')
exec(compile('\n'.join(result)+'\n',str(frozen),'exec'),{'__name__':'__main__','__file__':str(frozen)})
