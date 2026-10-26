import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { compileContract, compileContractAsync, parseModuleSource, compileLinkedProgramAsync } from '../dist/generic.js';
const options = { contract:'C', bindings:{}, languageVersion:1 };
const compile = source => compileContract(source, options);

test('LC02 legacy artifacts retain exact baseline JSON bytes in version 0', () => {
  for (const {source,artifact} of JSON.parse(readFileSync(new URL('./fixtures/lc02/legacy.json',import.meta.url)))) {
    assert.equal(JSON.stringify(compileContract(source,{contract:'C',bindings:{}})),JSON.stringify(artifact));
    assert.equal(JSON.stringify(compileContract(source,{contract:'C',bindings:{},languageVersion:0})),JSON.stringify(artifact));
  }
});
test('LC02 explicit spend/mint and helpers; full method set persists', async () => {
  const source = 'private function ok(x: Bool): Bool { return x; } export contract C { entry a(x: Bool) { require(ok(x)); } entry b(x: Int) { require(x > 1); } }';
  const artifact=compile(source);
  assert.equal(artifact.languageVersion,1);
  assert.deepEqual(artifact.methods.map(m=>[m.name,m.invocation]),[['a','spend'],['b','spend']]);
  assert.deepEqual(await compileContractAsync(source,options),artifact);
  const program=parseModuleSource(source,true,'<source>',undefined,1);
  assert.deepEqual((await compileLinkedProgramAsync(program,options)).artifact,artifact);
  assert.deepEqual(compile(source+' private function extra(): Bool { return false; }'),artifact);
  const reversed=compile(source.replace('entry a(x: Bool) { require(ok(x)); } entry b(x: Int) { require(x > 1); }','entry b(x: Int) { require(x > 1); } entry a(x: Bool) { require(ok(x)); }'));
  assert.equal(reversed.policy.root,artifact.policy.root);
  const mint=compile('token C { mint issue(delta: Amount, flag: Bool) { require(flag); require(delta > 0); } }');
  assert.deepEqual(mint.methods[0].args,[{name:'flag',type:'Bool'}]);
  assert.equal(mint.methods[0].mintAmountParam,'delta');
  assert.equal(mint.methods[0].invocation,'mint');
});
test('LC02 version, kind, empty, collisions and duplicate leaves reject', () => {
  for (const source of ['contract C { function x() { require(true); } }','contract C { mint x() { require(true); } }','token C { entry x(delta: Amount) { require(true); } }','contract C {}','contract C { entry x() { require(true); } entry X() { require(false); } }','contract C { entry x() { require(true); } entry y() { require(true); } }','token C { mint x(delta: Int) { require(true); } }']) assert.throws(()=>compile(source));
  assert.throws(()=>compileContract('contract C { entry x() { require(true); } }',{contract:'C',bindings:{}}),/languageVersion 1/);
  assert.throws(()=>compileContract('contract C { function x() { require(true); } }',{...options,languageVersion:2}),/unsupported languageVersion/);
  assert.throws(()=>parseModuleSource('',false,'x',undefined,2),/unsupported languageVersion/);
});
test('LC02 inline recursion and expansion depth 16 remain bounded', () => {
  assert.throws(()=>compile('function coin(): Amount { return this.coin.value; } token C { mint issue(delta: Amount) { require(coin() > 0); } }'),/mint method has no coin/);
  assert.throws(()=>compile('function f(): Bool { return f(); } contract C { entry x() { require(f()); } }'),/recursive|cycle/);
  const chain=n=>Array.from({length:n},(_,i)=>`function h${i}(): Bool { return ${i===n-1?'true':`h${i+1}()`}; }`).join('\n')+' contract C { entry x() { require(h0()); } }';
  assert.equal(compile(chain(16)).methods.length,1);
  assert.throws(()=>compile(chain(17)),/depth|16/);
});
test('LC02 guarded scripts reject cross-kind reuse in independent Python VM', () => {
  const fixtures=[];
  for(const optimize of [false,true]) for(const [kind,source] of [['spend','contract C { entry use(x: Int) { require(x > 0); } }'],['mint','token C { mint issue(delta: Amount, x: Int) { require(x > 0); require(delta > 0); } }']]) {
    const method=compileContract(source,{...options,optimize}).methods[0];
    assert.equal(method.sourceMap[0].op,'INVOCATIONKIND');
    fixtures.push({kind,method});
  }
  const run=spawnSync(process.env.LOTUS_V2_PYTHON??'python3',[new URL('./lc02-vm.py',import.meta.url).pathname],{input:JSON.stringify(fixtures),encoding:'utf8',env:{...process.env,PYTHONPATH:new URL('../../lotus-v2-reference',import.meta.url).pathname}});
  assert.equal(run.status,0,run.stderr||run.stdout);
  assert.match(run.stdout,/16 cases passed/);
});
