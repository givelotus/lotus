import { readFileSync, writeFileSync } from 'node:fs';
import { schnorr } from '@noble/curves/secp256k1';
import { compileContract } from '../../../dist/generic.js';
import { hex, unhex } from '../../../dist/compiler.js';
import { encodeOutput } from '../../../dist/runtime.js';
import { finalizeContractCall, prepareContractCall, methodRoot } from '../../../dist/call-runtime.js';
import { contextProfile, transactionContext, runCorpus, saveReport, reportFailed } from '../../differential/harness.mjs';
const owner='79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';
const source='contract Payment<owner: PublicKey> { function spend(signature: Signature) { require(checksig(signature, owner)); } }';
const compiled=compileContract(source,{contract:'Payment',bindings:{Payment:{owner}}});
const handbuilt=structuredClone(compiled);
const script='20'+owner+'bb';
const root=methodRoot(script,[]);
Object.assign(handbuilt.methods[0],{scriptHex:script,leaf:root,root,sourceMap:[],staticResources:{scriptBytes:34,opcodes:2,maxStackItems:2,helperExpansions:0,dynamicSignatureChecks:1}});
Object.assign(handbuilt.policy,{root,branches:[root]});
const cases=[];
for(const [kind,artifact] of [['compiler',compiled],['handbuilt',handbuilt]]) {
 const context={profile:artifact.target,chainId:'44'.repeat(32),prevTxid:'11'.repeat(32),prevIndex:0,sequence:0xffffffff,coin:{value:2000n,branches:[artifact.policy.root],paths:[[0]]},outputs:[{value:1000n,branches:[artifact.policy.root],paths:[[0]]}]};
 const plan=prepareContractCall(artifact,'spend',context,{signature:null});
 const sig=schnorr.sign(unhex(plan.requests[0].digest),unhex('00'.repeat(31)+'01'),new Uint8Array(32));
 for(const bad of [false,true]) {
  const signature=sig.slice();if(bad)signature[0]^=1;
  const final=finalizeContractCall(plan,{signature});
  cases.push({id:`${kind}-${bad?'bad-signature':'valid'}`,expected:bad?'reject':'accept',source:kind==='compiler'?source:'PUSH_32 owner CHECKSIG',artifact,script:artifact.methods[0].scriptHex,args:[hex(signature)],input_count:1,output_count:1,profile:contextProfile,transaction_context:transactionContext(final.wire,context),native_context:[hex(final.wire),context.chainId,'0','0',hex(encodeOutput(context.coin))]});
 }
}
const report=runCorpus({schema:'lotus-v2/differential-corpus/1',seed:79225,cases},{native:process.env.LOTUS_V2_NATIVE_VM});
saveReport(report,new URL('./handbuilt/',import.meta.url).pathname);
for(const entry of report.cases)if(entry.python.status!==entry.case.expected||entry.native.status!==entry.case.expected)throw Error('unexpected fixture outcome');
console.log(JSON.stringify({cases:report.cases.length,discrepancies:report.cases.filter(c=>c.discrepancies.length).length,outcomes:report.cases.map(c=>({id:c.case.id,python:c.python.status,native:c.native.status,accounting:c.native.accounting_charge}))}));
process.exitCode=reportFailed(report)?1:0;
