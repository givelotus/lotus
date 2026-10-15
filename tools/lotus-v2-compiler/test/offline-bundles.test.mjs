import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
// Consumer path deliberately imports no dist module and never invokes generation.
const canonical = x => x === null || typeof x !== 'object' ? JSON.stringify(x) : Array.isArray(x) ? '[' + x.map(canonical).join(',') + ']' : '{' + Object.keys(x).sort().map(k => JSON.stringify(k) + ':' + canonical(x[k])).join(',') + '}';
const python=process.env.LOTUS_V2_PYTHON??'python3';
function run(bundle) { return spawnSync(python,[new URL('./offline-bundle-consumer.py',import.meta.url).pathname],{input:JSON.stringify(bundle),encoding:'utf8'}); }
const load=name=>JSON.parse(readFileSync(new URL(`../fixtures/offline/${name}.json`,import.meta.url)));
const seal=b=>{b.sha256=createHash('sha256').update(canonical(b.payload)).digest('hex');return b;};
for(const name of ['payment','fungible-token','linked']) test(`checked-in ${name} bytes execute offline`,()=>{
 const b=load(name),r=run(b);assert.equal(r.status,0,r.stderr);assert.equal(JSON.parse(r.stdout).verified_invocations,b.payload.cases.length);
 assert.ok(b.payload.cases.some(c=>c.expected.accepted_invocation));
 assert.ok(b.payload.cases.some(c=>!c.expected.accepted_invocation));
});
test('byte, version, expected charge, script, amount, and proof mutations reject',()=>{
 const mutations=[
 b=>{b.schema='lotus-v2/offline-bundle/2';},
 b=>{b.payload.files[0].utf8+=' ';},
 b=>{b.payload.cases[0].expected.charged_cost++;seal(b);},
 b=>{b.payload.cases[0].input.script='51';seal(b);},
 b=>{b.payload.artifacts.Payment.policy.root='00'.repeat(32);seal(b);},
 b=>{b.payload.cases[0].input.signing.messages[0]='00'.repeat(32);seal(b);},
 ];
 for(const mutate of mutations){const b=load('payment');mutate(b);const r=run(b);assert.notEqual(r.status,0,'mutation unexpectedly passed');}
 const b=load('fungible-token');b.payload.cases[0].input.invocation.outputs[0].value='01000';seal(b);assert.notEqual(run(b).status,0);
});

test('proof mismatch rejects even with refreshed artifact and envelope checksums',()=>{
 const b=load('payment');b.payload.artifacts.Payment.policy.root='00'.repeat(32);
 const utf8=canonical(b.payload.artifacts.Payment);b.payload.artifactBytes.Payment={utf8,sha256:createHash('sha256').update(utf8).digest('hex')};seal(b);
 const r=run(b);assert.notEqual(r.status,0);assert.match(r.stderr,/proof root mismatch/);
});
