#!/usr/bin/env python3
"""Fold the measured HTTP repair into owner86 on the separate ordering candidate."""
import copy
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT/'daemon/worktrees/grok-progression-source'
OUT = Path(__file__).resolve().parent
INTAKE = ROOT/'daemon/patch-intake/20261023'
ARCHIVE = ROOT/'daemon/.local-artifact-archive/commit-regressions'
FILE = 'src/httpserver.cpp'
ANCHOR = b'        if (!parser.is_done()) {\n            auto [body_ec, body_n] = co_await http::async_read('
INSERT = b'''        if (!parser.is_done()) {
            // Beast otherwise reuses its initial 512-byte capacity as the
            // parser consumes each chunk. Grow lazily for bodies, with bounded
            // read-ahead rather than one receive operation per tiny chunk.
            constexpr uint64_t body_read_chunk = 16 * 1024;
            buffer.reserve(std::min<uint64_t>(
                body_read_chunk, parser.content_length().value_or(body_read_chunk)));
            auto [body_ec, body_n] = co_await http::async_read('''

def git(*args, data=None, env=None):
    return subprocess.check_output(['git','-C',str(SOURCE),*args], input=data, env=env)

def main():
    assert not git('status','--porcelain').strip()
    bundles = [ROOT/'daemon/.local-artifact-archive/lotusd-published-source-20261023-full.bundle',
               ARCHIVE/'template-test-order-candidate.bundle', ARCHIVE/'http-body16k-queued-candidate.bundle']
    preservation = []
    for bundle in bundles:
        result = subprocess.run(['git','-C',str(SOURCE),'bundle','verify',str(bundle)],capture_output=True,text=True,check=True)
        preservation.append(dict(bundle=str(bundle), verification=result.stdout+result.stderr))
    plan = json.loads((INTAKE/'perf-prefix-order-repair/CANDIDATE-STACK.json').read_text())
    stages = plan['stages']
    entries = stages['ecash']['commits'] + stages['v2']['commits']
    assert len(entries) == 531 and len(stages['ecash']['commits']) == 378
    assert stages['v2']['reviewed_reference_tip'] == '2d89f642753880f8d7c28495cfe2f4180887d497'
    # Prove the literal insertion is the exact measured source change.
    before = git('show','acf7f61425e613581ddd0f0b71e8ccacd4ef2656:'+FILE)
    after = git('show','95c1d9cd79d0cc387e2821673e31606f32a81914:'+FILE)
    assert before.count(ANCHOR) == 1 and before.replace(ANCHOR, INSERT) == after
    candidate = copy.deepcopy(plan)
    outputs = candidate['stages']['ecash']['commits'] + candidate['stages']['v2']['commits']
    parent = stages['ecash']['input_commit']
    ledger = []
    env = dict(os.environ, GIT_INDEX_FILE=str(ARCHIVE/'fold-http.index'))
    for position, (entry, output) in enumerate(zip(entries, outputs), 1):
        original = entry['commit']
        headers, message = git('cat-file','commit',original).split(b'\n\n',1)
        lines = headers.splitlines()
        assert sum(line.startswith(b'parent ') for line in lines) == 1
        assert not any(line.startswith((b'gpgsig ',b'mergetag ')) for line in lines)
        old_tree = lines[0].split()[1].decode()
        tree = old_tree
        if position >= 86:
            blob = git('show',original+':'+FILE)
            assert blob.count(ANCHOR) == 1, position
            oid = git('hash-object','-w','--stdin',data=blob.replace(ANCHOR,INSERT)).strip().decode()
            git('read-tree',old_tree,env=env)
            git('update-index','--cacheinfo',f'100644,{oid},{FILE}',env=env)
            tree = git('write-tree',env=env).strip().decode()
            assert git('diff','--numstat',old_tree,tree).decode().strip() == '6\t0\t'+FILE
        if position == 86:
            message += (b'\nPerformance repair (2026-10-23): coalesce larger HTTP body reads with bounded lazy16KiB read-ahead.\n'
                        b'Folded measured fixup95c1d9cd79d0cc387e2821673e31606f32a81914.\n'
                        b'Evidence: benchmark-results/20261023/commit-regressions/REPORT.md in the parent Lotus repository.\n'
                        b'Large-array RPC gap recovered; no500K admission speedup claimed. Earlier unqueued admission controls were mixed.\n')
        rewritten = [b'tree '+tree.encode() if line.startswith(b'tree ') else
                     b'parent '+parent.encode() if line.startswith(b'parent ') else line for line in lines]
        new = git('hash-object','-t','commit','-w','--stdin',data=b'\n'.join(rewritten)+b'\n\n'+message).strip().decode()
        output['commit'] = new
        output['parents'] = [parent]
        ledger.append(dict(position=position, original=original, candidate=new,
                           original_tree=old_tree, candidate_tree=tree,
                           disposition='All tracked content identical' if position < 86 else
                           'Exact input tree plus only six measured HTTP read-ahead lines; all other source/test/build/config/documentation content retained'))
        parent = new
    shared = ledger[377]['candidate']
    native = ledger[-1]['candidate']
    assert int(git('rev-list','--count',stages['ecash']['input_commit']+'..'+native)) == 531
    git('merge-base','--is-ancestor',shared,native)
    for stage, tip in (('ecash',shared),('v2',native)):
        candidate['stages'][stage]['reviewed_reference_tip'] = tip
        candidate['stages'][stage]['reviewed_reference_tree'] = git('rev-parse',tip+'^{tree}').strip().decode()
        candidate['stages'][stage]['review_status'] = 'HTTP performance repair candidate; full gates pending'
    candidate['stages']['v2']['input_commit'] = shared
    for label, tip in (('ecash',shared),('v2',native)):
        git('update-ref',f'refs/benchmark/perf-regression-repaired-{label}-20261023',tip)
        old = stages[label]['reviewed_reference_tip']
        (OUT/f'{label}-reviewed-production-delta.diff').write_bytes(git('diff',old,tip))
    (OUT/'CANDIDATE-STACK.json').write_text(json.dumps(candidate,indent=2)+'\n')
    (OUT/'LEDGER.json').write_text(json.dumps(dict(status='unpromoted; full gates pending',
        input_stage='Separate tree-preserving test-order candidate', preservation=preservation,
        behavior_change='Exactly six HTTP read-ahead lines; explicitly separate from pure ownership movement',
        owning_position=86, measured_fixup='95c1d9cd79d0cc387e2821673e31606f32a81914', commits=ledger),indent=2)+'\n')
    print(json.dumps(dict(shared=shared,native=native,shared_tree=ledger[377]['candidate_tree'],native_tree=ledger[-1]['candidate_tree'])))

if __name__ == '__main__':
    main()
