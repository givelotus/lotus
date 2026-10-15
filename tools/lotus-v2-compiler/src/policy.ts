/** LC-1 companion policy metadata; diagnostic hashes add no consensus fields. */
import { bytes, concat, cs, hex, tagged, unhex } from './compiler.js';
import { assertContractArtifact, encodeCallValue, type ContractArtifact, type CallValue } from './call-runtime.js';
export type PolicyBranch = {
    name: string;
    index: number;
    kind: 'spend' | 'data';
    root: string;
    artifactDigest?: string;
};
export type PolicySpec = {
    name: string;
    branches: PolicyBranch[];
    paths: {
        name: string;
        branches: string[];
    }[];
};
export type PolicyMetadata = {
    target: string;
    targetDigest: string;
    profileDigest: string;
    compilerRevision: string;
    optimizerMode: string;
    constructor: unknown[];
    bindings: Record<string, unknown>;
    provenance: Record<string, unknown>;
};
export type PolicyArtifact = PolicyMetadata & {
    schema: 'lotus-v2/policy-artifact/1';
    languageVersion: 1;
    name: string;
    branches: PolicyBranch[];
    paths: {
        name: string;
        pathIndex: number;
        slots: number[];
    }[];
    policyEncoding: string;
    policyDigest: string;
};
export type NamedWitness = {
    branchName: string;
    artifact: ContractArtifact & {
        languageVersion?: number;
    };
    methodName: string;
    arguments: Record<string, CallValue>;
};
function fail(s: string): never { throw new Error(s); }
function name(v: unknown) { if (typeof v !== 'string' || !/^[A-Za-z_][A-Za-z_0-9]*$/.test(v))
    fail('policy name'); }
function hash(v: unknown) { if (typeof v !== 'string' || !/^[0-9a-f]{64}$/.test(v))
    fail('policy hash'); }
const metadataKeys = ['target', 'targetDigest', 'profileDigest', 'compilerRevision', 'optimizerMode', 'constructor', 'bindings', 'provenance'];
const branchKeys = ['name', 'index', 'kind', 'root', 'artifactDigest'];
function fields(value: object, allowed: string[]): void {
    if (Object.keys(value).some(key => !allowed.includes(key))) fail('policy unknown field');
}
/** Sorted ASCII keys/strings and safe integral numbers, identically encoded in Python. */
export function canonicalPolicyJson(v: unknown): string {
    if (v === null || typeof v === 'boolean')
        return JSON.stringify(v);
    if (typeof v === 'string') {
        if (/[^\x20-\x7e]/.test(v))
            fail('policy JSON string');
        return JSON.stringify(v);
    }
    if (typeof v === 'number') {
        if (!Number.isSafeInteger(v))
            fail('policy JSON number');
        return String(v);
    }
    if (Array.isArray(v))
        return '[' + v.map(canonicalPolicyJson).join(',') + ']';
    if (v && typeof v === 'object' && Object.getPrototypeOf(v) === Object.prototype)
        return '{' + Object.keys(v).sort().map(k => canonicalPolicyJson(k) + ':' + canonicalPolicyJson((v as Record<string, unknown>)[k])).join(',') + '}';
    return fail('policy JSON value');
}
export function programArtifactDigest(a: ContractArtifact): string { return hex(tagged('app/program-artifact/1', new TextEncoder().encode(canonicalPolicyJson(a)))); }
function compare(a: number[], b: number[]): number { for (let i = 0; i < Math.min(a.length, b.length); i++)
    if (a[i] !== b[i])
        return a[i]! - b[i]!; return a.length - b.length; }
export function buildPolicy(spec: PolicySpec, metadata: PolicyMetadata): PolicyArtifact {
    fields(spec, ['name', 'branches', 'paths']);
    fields(metadata, metadataKeys);
    name(spec.name);
    if (!Array.isArray(spec.branches) || spec.branches.length < 1 || spec.branches.length > 16 || !Array.isArray(spec.paths) || spec.paths.length < 1 || spec.paths.length > 16)
        fail('policy branch/path count');
    hash(metadata.targetDigest);
    hash(metadata.profileDigest);
    for (const k of ['target', 'compilerRevision', 'optimizerMode'] as const)
        if (typeof metadata[k] !== 'string' || !metadata[k])
            fail('policy metadata');
    if (!Array.isArray(metadata.constructor) || !metadata.bindings || Object.getPrototypeOf(metadata.bindings) !== Object.prototype || !metadata.provenance || Object.getPrototypeOf(metadata.provenance) !== Object.prototype)
        fail('policy metadata');
    canonicalPolicyJson(metadata);
    for (const branch of spec.branches) {
        if (!branch || typeof branch !== 'object' || Array.isArray(branch)) fail('policy artifact structure');
        fields(branch, branchKeys);
        if (!Number.isInteger(branch.index) || branch.index < 0 || branch.index > 15) fail('policy slots');
    }
    for (const path of spec.paths) {
        if (!path || typeof path !== 'object' || Array.isArray(path)) fail('policy artifact structure');
        fields(path, ['name', 'branches']);
    }
    const branches = spec.branches.map(b => ({ ...b })).sort((a, b) => a.index - b.index), names = new Set<string>(), roots = new Set<string>();
    branches.forEach((b, i) => { name(b.name); hash(b.root); if (!Number.isInteger(b.index) || b.index !== i)
        fail('policy slots'); if (names.has(b.name.toLowerCase()))
        fail('duplicate branch name'); names.add(b.name.toLowerCase()); if (roots.has(b.root))
        fail('duplicate branch root'); roots.add(b.root); if (b.kind !== 'spend' && b.kind !== 'data')
        fail('policy branch kind'); if (b.kind === 'spend')
        hash(b.artifactDigest);
    else if (b.artifactDigest !== undefined)
        fail('data artifact digest'); });
    const pn = new Set<string>();
    const paths = spec.paths.map(p => { name(p.name); if (pn.has(p.name.toLowerCase()))
        fail('duplicate path name'); pn.add(p.name.toLowerCase()); if (!Array.isArray(p.branches) || !p.branches.length || p.branches.length > 16)
        fail('policy path'); const slots = p.branches.map(n => { const b = branches.find(b => b.name === n); if (!b)
        return fail('unknown branch'); if (b.kind !== 'spend')
        fail('data branch in path'); return b.index; }).sort((a, b) => a - b); if (new Set(slots).size !== slots.length)
        fail('duplicate path slot'); return { name: p.name, pathIndex: 0, slots }; }).sort((a, b) => compare(a.slots, b.slots));
    paths.forEach((p, i) => { if (i && compare(paths[i - 1]!.slots, p.slots) === 0)
        fail('duplicate path'); p.pathIndex = i; });
    const encoding = concat(cs(branches.length), ...branches.map(b => unhex(b.root, 32)), cs(paths.length), ...paths.map(p => concat(cs(p.slots.length), ...p.slots.map(cs))));
    return { ...metadata, schema: 'lotus-v2/policy-artifact/1', languageVersion: 1, name: spec.name, branches, paths, policyEncoding: hex(encoding), policyDigest: hex(tagged('app/policy/1', encoding)) };
}
export function assertPolicyArtifact(a: PolicyArtifact): void {
    if (!a || typeof a !== 'object' || !Array.isArray(a.branches) || !Array.isArray(a.paths) || a.branches.some(b => !b || typeof b !== 'object' || Array.isArray(b)) || a.paths.some(p => !p || typeof p !== 'object' || Array.isArray(p) || !Array.isArray(p.slots) || p.slots.some(i => !Number.isInteger(i))))
        fail('policy artifact structure');
    fields(a, [...metadataKeys, 'schema', 'languageVersion', 'name', 'branches', 'paths', 'policyEncoding', 'policyDigest']);
    for (const branch of a.branches) fields(branch, branchKeys);
    for (const path of a.paths) fields(path, ['name', 'pathIndex', 'slots']);
    if (a.schema !== 'lotus-v2/policy-artifact/1' || a.languageVersion !== 1)
        fail('unsupported policy artifact');
    const { schema: _s, languageVersion: _l, name: n, branches, paths, policyEncoding: _e, policyDigest: _d, ...metadata } = a;
    const fresh = buildPolicy({ name: n, branches, paths: paths.map(p => ({ name: p.name, branches: p.slots.map(i => branches[i]?.name ?? '') })) }, metadata);
    if (canonicalPolicyJson(a) !== canonicalPolicyJson(fresh))
        fail('policy artifact mismatch');
}
function selected(w: Omit<NamedWitness, 'branchName'>, kind: 'spend' | 'mint', root: string, digest?: string) {
    if (new Set(w.artifact.methods.map(m => m.name.toLowerCase())).size !== w.artifact.methods.length)
        fail('policy program artifact');
    if (w.artifact.languageVersion !== 1 || w.artifact.methods.some(m => m.invocation !== kind) || (w.artifact.kind === 'token' ? 'mint' : 'spend') !== kind)
        fail('policy invocation kind');
    try {
        assertContractArtifact(w.artifact);
    }
    catch {
        fail('policy program artifact');
    }
    if (w.artifact.policy.root !== root || (digest !== undefined && programArtifactDigest(w.artifact) !== digest))
        fail('policy program identity');
    const m = w.artifact.methods.find(m => m.name === w.methodName);
    if (!m)
        return fail('policy method');
    const args = m.args.map(a => a.name);
    if (Object.keys(w.arguments).length !== args.length || args.some(n => !Object.hasOwn(w.arguments, n)))
        fail('policy arguments');
    const argumentOrder = m.args.map(a => { const v = w.arguments[a.name]!; if (v === null && a.type === 'Signature')
        return null; try {
        return hex(encodeCallValue(a.type, v));
    }
    catch {
        return fail('policy argument value');
    } });
    const witnessCore = hex(concat(bytes(unhex(m.scriptHex)), cs(m.proof.length), ...m.proof.map(p => unhex(p, 32))));
    return { methodName: w.methodName, scriptHex: m.scriptHex, leaf: m.leaf, proof: [...m.proof], witnessCore, argumentNames: args, argumentOrder };
}
export function selectPolicyWitnesses(policy: PolicyArtifact, pathName: string, witnesses: NamedWitness[]) {
    assertPolicyArtifact(policy);
    const path = policy.paths.find(p => p.name === pathName);
    if (!path)
        return fail('policy path name');
    if (!Array.isArray(witnesses) || new Set(witnesses.map(w => w.branchName)).size !== witnesses.length)
        fail('duplicate named witness');
    const required = path.slots.map(i => policy.branches[i]!);
    if (witnesses.length !== required.length || required.some(b => !witnesses.some(w => w.branchName === b.name)))
        fail('policy witness membership');
    for (const w of witnesses)
        if (w.artifact.target !== policy.target)
            fail('policy program target');
    return { pathName, pathIndex: path.pathIndex, witnesses: required.map(b => ({ branchName: b.name, branchIndex: b.index, root: b.root, ...selected(witnesses.find(w => w.branchName === b.name)!, 'spend', b.root, b.artifactDigest) })) };
}
/** Mint identity has no output slot or path index. */
export function selectMintWitness(w: Omit<NamedWitness, 'branchName'>) {
    const result = selected(w, 'mint', w.artifact.policy.root);
    if (['branchName', 'branchIndex', 'pathName', 'pathIndex'].some(k => Object.hasOwn(w, k)))
        fail('mint policy selector');
    return { tokenId: w.artifact.policy.root, ...result };
}
/** Construct an executable branch from a verified spend program, never a mint. */
export function spendPolicyBranch(name: string, index: number, artifact: NamedWitness['artifact']): PolicyBranch {
    if (artifact.languageVersion !== 1 || artifact.kind === 'token' || artifact.methods.some(m => m.invocation !== 'spend'))
        fail('policy invocation kind');
    try {
        assertContractArtifact(artifact);
    }
    catch {
        fail('policy program artifact');
    }
    return { name, index, kind: 'spend', root: artifact.policy.root, artifactDigest: programArtifactDigest(artifact) };
}
/** Build-time assertion only. On-chain covenants must check successors themselves. */
export function requireEveryPath(policy: PolicyArtifact, branchName: string): void {
    assertPolicyArtifact(policy);
    const b = policy.branches.find(b => b.name === branchName);
    if (!b || b.kind !== 'spend' || policy.paths.some(p => !p.slots.includes(b.index)))
        fail('policy every path');
}
