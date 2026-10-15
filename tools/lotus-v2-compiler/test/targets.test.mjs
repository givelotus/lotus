import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveTarget,checkCapabilities,checkEntrypoint,ECASH_REVISION} from '../dist/targets.js';
const portable=['bytes','bool','sha256','hash256','byte-equality','require','if'];
const specialized=['lotus-int128','transaction-signature','transaction-reflection','lotus-loop','lotus-token'];

test('target selection is exact and descriptors are deeply immutable',()=>{
 for(const id of ['ecash','lotus-v2']){
  const target=resolveTarget(id);
  assert.equal(target.id,id);assert.equal(target.capabilityScope,'compiler-implemented');
  assert.ok(Object.isFrozen(target));
  for(const field of ['limits','semantics','capabilities','evaluationFlags'])assert.ok(Object.isFrozen(target[field]));
  assert.throws(()=>{target.limits.maxElementBytes=99999;},TypeError);
  assert.throws(()=>target.capabilities.push('lotus-token'),TypeError);
 }
 for(const id of ['','ECash','LotusV2','bitcoin','ecash ','P01-P02-P03-candidate-2026-10-14'])
  assert.throws(()=>resolveTarget(id),/Unknown compiler target/);
});

test('portable requirements pass and Lotus obligations reject precisely on eCash',()=>{
 const ecash=resolveTarget('ecash'),lotus=resolveTarget('lotus-v2');
 assert.deepEqual(checkCapabilities(ecash,portable.map(capability=>({capability}))),[]);
 const requirements=specialized.map((capability,i)=>({capability,span:{start:i,end:i+1,file:'contract.lotus'}}));
 assert.deepEqual(checkCapabilities(lotus,requirements),[]);
 const errors=checkCapabilities(ecash,requirements);
 assert.equal(errors.length,5);assert.deepEqual(errors.map(e=>e.capability),specialized);
 for(let i=0;i<errors.length;i++){
  assert.equal(errors[i].code,'E0801');assert.deepEqual(errors[i].span,requirements[i].span);
  assert.notEqual(errors[i].span,requirements[i].span);assert.ok(errors[i].message.includes(ECASH_REVISION));
 }
 assert.match(errors[0].message,/sixteen-byte signed int128/);
 assert.match(errors[1].message,/P01 authenticated message/);
 assert.match(errors[2].message,/branch\/path semantics/);
 assert.match(errors[3].message,/transaction-context iteration/);
 assert.match(errors[4].message,/mint\/spend semantics/);
});

test('semantic models and entrypoints cannot inherit Lotus policy assumptions',()=>{
 const ecash=resolveTarget('ecash'),lotus=resolveTarget('lotus-v2');
 assert.equal(ecash.revision,'1fb7db17c176cdea8a2c60d887891589382ee4e3');
 assert.equal(ecash.profile,'ecash-script-minimal-cleanstack-1fb7db17');
 assert.deepEqual(ecash.limits,{maxScriptBytes:10000,maxElementBytes:520,maxStackItems:1000,maxOps:201});
 assert.equal(lotus.limits.maxStackItems,null);
 assert.equal(lotus.semantics.booleanEncoding,'canonical-int128-le');
 assert.equal(lotus.semantics.booleanConsumers,'canonical-zero-or-one');
 assert.equal(ecash.semantics.booleanEncoding,'minimal-scriptnum');
 assert.equal(ecash.semantics.booleanConsumers,'script-truthiness');
 assert.equal(ecash.semantics.signatureModel,'not-supported-by-compiler');
 assert.equal(ecash.semantics.commitmentModel,'external-script-wrapper-required');
 assert.equal(lotus.semantics.commitmentModel,'lotus-branches-and-paths');
 assert.deepEqual(checkEntrypoint(ecash,1),[]);assert.deepEqual(checkEntrypoint(lotus,2),[]);
 const span={start:4,end:20},[error]=checkEntrypoint(ecash,2,span);
 assert.equal(error.code,'E0802');assert.deepEqual(error.span,span);
 assert.match(error.message,/explicit selector\/dispatch ABI/);
 for(const n of [0,-1,1.5,NaN,Infinity,Number.MAX_SAFE_INTEGER+1])assert.equal(checkEntrypoint(lotus,n)[0].code,'E0802');
});

test('unknown runtime capabilities fail closed; repeated obligations retain locations',()=>{
 const result=checkCapabilities(resolveTarget('ecash'),[{capability:'dynamic-execution'},
  {capability:'lotus-loop',span:{start:1,end:2}},{capability:'lotus-loop',span:{start:9,end:10}}]);
 assert.equal(result.length,3);assert.match(result[0].message,/not implemented/);assert.equal(result[0].span,undefined);
 assert.deepEqual(result.slice(1).map(e=>e.span.start),[1,9]);
});
