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
FIXTURES = ROOT/'daemon/patch-intake/20261023/queue-owner-audit/FIXTURE-CONTROLS.json'


def main():
    fixes = {row['point']: row for row in json.loads(FIXTURES.read_text())['controls']}
    commit = fixes['queue']['commit']
    entries = json.loads(PLAN.read_text())['stages']['ecash']['commits']
    notes = dict(status='prepared; corrected-fixture individual-owner gates pending',
        comparison='Same shared ABC/eCash workload; not native V2. Fresh matched study, not a splice of earlier medians.',
        points=[dict(point=n, commit=entries[n-1]['commit'] if n else json.loads(PLAN.read_text())['stages']['ecash']['input_commit'],
                     footnote=note) for n, note in [
            (0, 'Unmodified ABC1fb7db17.'), (1, 'Git metadata path handling; build-only change.'),
            (2, 'Currency caching; immediately follows1.'), (3, 'Count-only RPC fix; immediately follows2.'),
            (375, 'Remaining shared changes through WebTransport experiment tooling; transports disabled in this profile.'),
            (376, 'Pinned incremental reconciliation window; immediately follows375.'),
            (377, 'Bounded RPC commit owner PLUS peer-capability reversals; mixed owner, separate control below.'),
            (378, 'Slab-backed persistent transaction commitment trees; immediately follows377.')]])
    for entry in notes['points']:
        if str(entry['point']) in fixes:
            entry['commit'] = fixes[str(entry['point'])]['commit']
            entry['footnote'] += ' Test-only companion advertises the actual private capability; all production source bytes equal the numbered prefix.'
    study = DATA/'individual-owner-fixture-progression'
    study.mkdir(exist_ok=True)
    (study/'PLAN.json').write_text(json.dumps(notes, indent=2)+'\n')
    commands = [
        ('build-original-377-fixture', [TOOLS/'run.py', '--build-only', '--points', '377', '--plan', PLAN,
            '--variant', 'snapshot-count-order', '--data', DATA/'original-377-expanded-gate-build']),
        ('build-corrected-prefixes-fixture', [TOOLS/'run.py', '--build-only', '--points', '375,376', '--plan', PLAN,
            '--override-ref', '375='+fixes['375']['commit'], '--override-ref', '376='+fixes['376']['commit'],
            '--variant', 'peer-fixture-corrected', '--data', DATA/'peer-fixture-corrected-build']),
        ('build-queue-only-control-fixture', [TOOLS/'run.py', '--build-only', '--points', '377', '--plan', PLAN,
            '--override-ref', '377='+commit, '--variant', 'queue-only-fixture-corrected', '--data', DATA/'queue-only-fixture-corrected-build']),
        ('measure-individual-owners-fixture', [TOOLS/'progression.py', '--data', study, '--plan', PLAN,
            '--variant', 'snapshot-count-order', '--points', '0,1,2,3,375,376,377,378',
            '--override-ref', '375='+fixes['375']['commit'], '--override-ref', '376='+fixes['376']['commit'],
            '--point-variant', '375=peer-fixture-corrected', '--point-variant', '376=peer-fixture-corrected']),
        ('summarize-individual-owners-fixture', [TOOLS/'summarize.py', study/'RESULTS.json', '--output', study,
            '--notes', study/'PLAN.json']),
        ('measure-queue-with-peer-behavior-held-equal-fixture', [TOOLS/'paired_admission.py', '--point', '376',
            '--candidate-point', '377', '--plan', PLAN, '--reference-variant', 'peer-fixture-corrected',
            '--reference-ref', fixes['376']['commit'], '--candidate-ref', commit,
            '--variant', 'queue-only-fixture-corrected', '--data', DATA/'queue-only-admission-fixture-paired']),
        ('measure-peer-behavior-with-queue-held-equal-fixture', [TOOLS/'paired_admission.py', '--point', '377',
            '--plan', PLAN, '--reference-variant', 'queue-only-fixture-corrected', '--reference-ref', commit,
            '--candidate-ref', entries[376]['commit'], '--variant', 'snapshot-count-order',
            '--data', DATA/'queue-peer-capability-isolation-fixture-paired']),
    ]
    status = dict(status='running', control=commit, steps=[])
    status_path = DATA/'CONTINUATION-FIXTURE.json'
    audit.write(status_path, status)
    for name, args in commands:
        command = [sys.executable, *map(str, args)]
        print('PHASE', name, flush=True)
        log_path = DATA/(name+'.log')
        with log_path.open('x') as log:
            outcome = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        status['steps'].append(dict(name=name, argv=command, log=str(log_path), exit_code=outcome.returncode))
        if outcome.returncode:
            status.update(status='stopped; inspect failing gate, no downstream stage launched', stopped_at=name)
            audit.write(status_path, status)
            raise SystemExit(outcome.returncode)
        audit.write(status_path, status)
    status['status'] = 'measurements complete; source repair and attribution review still required'
    audit.write(status_path, status)


if __name__ == '__main__':
    main()
