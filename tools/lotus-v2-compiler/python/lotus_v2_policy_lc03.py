"""LC-1 named policies. Application hashes are diagnostics, never consensus fields."""
import json
import re
from lotus_v2_call_runtime import cs, hx, tagged, selected, encode_value, sized


def fail(message):
    raise ValueError(message)


def name(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', value): fail('policy name')


def hash32(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value): fail('policy hash')


METADATA_KEYS = ('target', 'targetDigest', 'profileDigest', 'compilerRevision', 'optimizerMode', 'constructor', 'bindings', 'provenance')
BRANCH_KEYS = ('name', 'index', 'kind', 'root', 'artifactDigest')


def fields(value, allowed):
    if any(key not in allowed for key in value): fail('policy unknown field')


def canonical_policy_json(value):
    if value is None or type(value) is bool: return json.dumps(value)
    if isinstance(value, str):
        if any(ord(c) < 32 or ord(c) > 126 for c in value): fail('policy JSON string')
        return json.dumps(value, ensure_ascii=False)
    if type(value) is int:
        if abs(value) > 9007199254740991: fail('policy JSON number')
        return str(value)
    if type(value) is float: fail('policy JSON number')
    if type(value) is list: return '[' + ','.join(canonical_policy_json(v) for v in value) + ']'
    if type(value) is dict:
        if any(type(k) is not str for k in value): fail('policy JSON value')
        return '{' + ','.join(canonical_policy_json(k) + ':' + canonical_policy_json(value[k]) for k in sorted(value)) + '}'
    fail('policy JSON value')


def program_artifact_digest(artifact):
    return tagged('app/program-artifact/1', canonical_policy_json(artifact).encode()).hex()


def build_policy(spec, metadata):
    fields(spec, ('name', 'branches', 'paths'))
    fields(metadata, METADATA_KEYS)
    name(spec['name'])
    if type(spec['branches']) is not list or not 1 <= len(spec['branches']) <= 16 or type(spec['paths']) is not list or not 1 <= len(spec['paths']) <= 16: fail('policy branch/path count')
    hash32(metadata.get('targetDigest')); hash32(metadata.get('profileDigest'))
    if any(type(metadata.get(k)) is not str or not metadata[k] for k in ('target', 'compilerRevision', 'optimizerMode')): fail('policy metadata')
    if type(metadata.get('constructor')) is not list or type(metadata.get('bindings')) is not dict or type(metadata.get('provenance')) is not dict: fail('policy metadata')
    canonical_policy_json(metadata)
    for branch in spec['branches']:
        if type(branch) is not dict: fail('policy artifact structure')
        fields(branch, BRANCH_KEYS)
        if type(branch.get('index')) is not int or not 0 <= branch['index'] <= 15: fail('policy slots')
    for path in spec['paths']:
        if type(path) is not dict: fail('policy artifact structure')
        fields(path, ('name', 'branches'))
    branches = sorted((dict(b) for b in spec['branches']), key=lambda b: b['index'])
    names, roots = set(), set()
    for i, b in enumerate(branches):
        name(b['name']); hash32(b['root'])
        if type(b['index']) is not int or b['index'] != i: fail('policy slots')
        if b['name'].lower() in names: fail('duplicate branch name')
        names.add(b['name'].lower())
        if b['root'] in roots: fail('duplicate branch root')
        roots.add(b['root'])
        if b['kind'] not in ('spend', 'data'): fail('policy branch kind')
        if b['kind'] == 'spend': hash32(b.get('artifactDigest'))
        elif 'artifactDigest' in b: fail('data artifact digest')
    paths, path_names = [], set()
    for p in spec['paths']:
        name(p['name'])
        if p['name'].lower() in path_names: fail('duplicate path name')
        path_names.add(p['name'].lower())
        if type(p['branches']) is not list or not 1 <= len(p['branches']) <= 16: fail('policy path')
        slots = []
        for n in p['branches']:
            b = next((b for b in branches if b['name'] == n), None)
            if b is None: fail('unknown branch')
            if b['kind'] != 'spend': fail('data branch in path')
            slots.append(b['index'])
        slots.sort()
        if len(set(slots)) != len(slots): fail('duplicate path slot')
        paths.append(dict(name=p['name'], pathIndex=0, slots=slots))
    paths.sort(key=lambda p: p['slots'])
    for i, p in enumerate(paths):
        if i and paths[i-1]['slots'] == p['slots']: fail('duplicate path')
        p['pathIndex'] = i
    encoding = cs(len(branches)) + b''.join(hx(b['root'], 32) for b in branches) + cs(len(paths)) + b''.join(cs(len(p['slots'])) + b''.join(cs(i) for i in p['slots']) for p in paths)
    return dict(metadata, schema='lotus-v2/policy-artifact/1', languageVersion=1, name=spec['name'], branches=branches, paths=paths, policyEncoding=encoding.hex(), policyDigest=tagged('app/policy/1', encoding).hex())


def assert_policy_artifact(artifact):
    if type(artifact) is not dict or type(artifact.get('branches')) is not list or type(artifact.get('paths')) is not list or any(type(b) is not dict for b in artifact['branches']) or any(type(p) is not dict or type(p.get('slots')) is not list or any(type(i) is not int for i in p['slots']) for p in artifact['paths']): fail('policy artifact structure')
    fields(artifact, (*METADATA_KEYS, 'schema', 'languageVersion', 'name', 'branches', 'paths', 'policyEncoding', 'policyDigest'))
    for branch in artifact['branches']: fields(branch, BRANCH_KEYS)
    for path in artifact['paths']: fields(path, ('name', 'pathIndex', 'slots'))
    if artifact.get('schema') != 'lotus-v2/policy-artifact/1' or type(artifact.get('languageVersion')) is not int or artifact['languageVersion'] != 1: fail('unsupported policy artifact')
    metadata = {k: v for k, v in artifact.items() if k not in ('schema', 'languageVersion', 'name', 'branches', 'paths', 'policyEncoding', 'policyDigest')}
    branches = artifact['branches']
    paths = [dict(name=p['name'], branches=[branches[i]['name'] if type(i) is int and 0 <= i < len(branches) else '' for i in p['slots']]) for p in artifact['paths']]
    fresh = build_policy(dict(name=artifact['name'], branches=branches, paths=paths), metadata)
    if canonical_policy_json(artifact) != canonical_policy_json(fresh): fail('policy artifact mismatch')


def _selected(w, kind, root, digest=None):
    a = w['artifact']
    if len({m['name'].lower() for m in a['methods']}) != len(a['methods']): fail('policy program artifact')
    if type(a.get('languageVersion')) is not int or a['languageVersion'] != 1 or any(m.get('invocation') != kind for m in a['methods']) or ('mint' if a.get('kind') == 'token' else 'spend') != kind: fail('policy invocation kind')
    # Validate the whole program before checking the selected name, like TypeScript.
    try: selected(a, a['methods'][0]['name'], allow_mint=True)
    except Exception: fail('policy program artifact')
    if a['policy']['root'] != root or digest is not None and program_artifact_digest(a) != digest: fail('policy program identity')
    m = next((m for m in a['methods'] if m['name'] == w['methodName']), None)
    if m is None: fail('policy method')
    args = [x['name'] for x in m['args']]
    if len(w['arguments']) != len(args) or any(n not in w['arguments'] for n in args): fail('policy arguments')
    values = []
    for arg in m['args']:
        value = w['arguments'][arg['name']]
        if value is None and arg['type'] == 'Signature': values.append(None); continue
        try: values.append(encode_value(arg['type'], value).hex())
        except Exception: fail('policy argument value')
    core = sized(hx(m['scriptHex'])) + cs(len(m['proof'])) + b''.join(hx(p, 32) for p in m['proof'])
    return dict(methodName=w['methodName'], scriptHex=m['scriptHex'], leaf=m['leaf'], proof=list(m['proof']), witnessCore=core.hex(), argumentNames=args, argumentOrder=values)


def select_policy_witnesses(policy, path_name, witnesses):
    assert_policy_artifact(policy)
    path = next((p for p in policy['paths'] if p['name'] == path_name), None)
    if path is None: fail('policy path name')
    if type(witnesses) is not list or len({w['branchName'] for w in witnesses}) != len(witnesses): fail('duplicate named witness')
    required = [policy['branches'][i] for i in path['slots']]
    if len(witnesses) != len(required) or any(not any(w['branchName'] == b['name'] for w in witnesses) for b in required): fail('policy witness membership')
    if any(w['artifact']['target'] != policy['target'] for w in witnesses): fail('policy program target')
    result = []
    for b in required:
        w = next(w for w in witnesses if w['branchName'] == b['name'])
        result.append(dict(branchName=b['name'], branchIndex=b['index'], root=b['root'], **_selected(w, 'spend', b['root'], b['artifactDigest'])))
    return dict(pathName=path_name, pathIndex=path['pathIndex'], witnesses=result)


def select_mint_witness(witness):
    root = witness['artifact']['policy']['root']
    result = _selected(witness, 'mint', root)
    if any(k in witness for k in ('branchName', 'branchIndex', 'pathName', 'pathIndex')): fail('mint policy selector')
    return dict(tokenId=root, **result)


def spend_policy_branch(branch_name, index, artifact):
    if artifact.get('languageVersion') != 1 or artifact.get('kind') == 'token' or any(m.get('invocation') != 'spend' for m in artifact['methods']): fail('policy invocation kind')
    try: selected(artifact, artifact['methods'][0]['name'], allow_mint=True)
    except Exception: fail('policy program artifact')
    return dict(name=branch_name, index=index, kind='spend', root=artifact['policy']['root'], artifactDigest=program_artifact_digest(artifact))


def require_every_path(policy, branch_name):
    assert_policy_artifact(policy)
    branch = next((b for b in policy['branches'] if b['name'] == branch_name), None)
    if branch is None or branch['kind'] != 'spend' or any(branch['index'] not in p['slots'] for p in policy['paths']): fail('policy every path')
