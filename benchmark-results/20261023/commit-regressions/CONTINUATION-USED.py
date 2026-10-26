#!/usr/bin/env python3
"""Gate individual prefixes, measure a matched progression, isolate queue/relay changes."""
import json
import subprocess
import sys
from pathlib import Path

import run as audit

ROOT = audit.ROOT
TOOLS = Path(__file__).resolve().parent
PLAN = ROOT/'daemon/patch-intake/20261023/snapshot-count-order/CANDIDATE-STACK.json'
DATA = ROOT/'benchmark-results/20261023/commit-regressions'
CONTROL = ROOT/'daemon/patch-intake/20261023/queue-owner-audit/CONTROL.json'


def main():
    receipt = json.loads(CONTROL.read_text())
    commit = receipt['control']
    entries = json.loads(PLAN.read_text())['stages']['ecash']['commits']
    notes = dict(status='prepared; individual-owner builds pending',
        comparison='Same shared ABC/eCash workload; not native V2. Fresh matched study, not a splice of earlier medians.',
        points=[dict(point=n, commit=entries[n-1]['commit'] if n else json.loads(PLAN.read_text())['stages']['ecash']['input_commit'],
                     footnote=note) for n, note in [
            (0, 'Unmodified ABC1fb7db17.'), (1, 'Git metadata path handling; build-only change.'),
            (2, 'Currency caching; immediately follows1.'), (3, 'Count-only RPC fix; immediately follows2.'),
            (375, 'Remaining shared changes through WebTransport experiment tooling; transports disabled in this profile.'),
            (376, 'Pinned incremental reconciliation window; immediately follows375.'),
            (377, 'Bounded RPC commit owner PLUS peer-capability reversals; mixed owner, separate control below.'),
            (378, 'Slab-backed persistent transaction commitment trees; immediately follows377.')]])
    study = DATA/'individual-owner-progression'
    study.mkdir(exist_ok=True)
    (study/'PLAN.json').write_text(json.dumps(notes, indent=2)+'\n')
    commands = [
        ('build-individual-owners', [TOOLS/'run.py', '--build-only', '--points', '1,2,375,376,377', '--plan', PLAN,
            '--variant', 'snapshot-count-order', '--data', DATA/'individual-owner-build']),
        ('build-queue-only-control', [TOOLS/'run.py', '--build-only', '--points', '377', '--plan', PLAN,
            '--override-ref', '377='+commit, '--variant', 'queue-only-control', '--data', DATA/'queue-only-control-build']),
        ('measure-individual-owners', [TOOLS/'progression.py', '--data', study, '--plan', PLAN,
            '--variant', 'snapshot-count-order', '--points', '0,1,2,3,375,376,377,378']),
        ('summarize-individual-owners', [TOOLS/'summarize.py', study/'RESULTS.json', '--output', study,
            '--notes', study/'PLAN.json']),
        ('measure-queue-with-peer-behavior-held-equal', [TOOLS/'paired_admission.py', '--point', '376',
            '--candidate-point', '377', '--plan', PLAN, '--reference-variant', 'snapshot-count-order',
            '--candidate-ref', commit, '--variant', 'queue-only-control', '--data', DATA/'queue-only-admission-paired']),
        ('measure-peer-behavior-with-queue-held-equal', [TOOLS/'paired_admission.py', '--point', '377',
            '--plan', PLAN, '--reference-variant', 'queue-only-control', '--reference-ref', commit,
            '--candidate-ref', entries[376]['commit'], '--variant', 'snapshot-count-order',
            '--data', DATA/'queue-peer-capability-isolation-paired']),
    ]
    status = dict(status='running', control=commit, steps=[])
    audit.write(DATA/'CONTINUATION.json', status)
    for name, args in commands:
        command = [sys.executable, *map(str, args)]
        print('PHASE', name, flush=True)
        log_path = DATA/(name+'.log')
        with log_path.open('x') as log:
            outcome = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        status['steps'].append(dict(name=name, argv=command, log=str(log_path), exit_code=outcome.returncode))
        if outcome.returncode:
            status.update(status='stopped; inspect failing gate, no downstream stage launched', stopped_at=name)
            audit.write(DATA/'CONTINUATION.json', status)
            raise SystemExit(outcome.returncode)
        audit.write(DATA/'CONTINUATION.json', status)
    status['status'] = 'measurements complete; source repair and attribution review still required'
    audit.write(DATA/'CONTINUATION.json', status)


if __name__ == '__main__':
    main()
