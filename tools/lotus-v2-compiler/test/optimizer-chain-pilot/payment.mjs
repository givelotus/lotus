// Public fixture key; each compiled policy is prepared and signed separately.
import {readFileSync} from 'node:fs';
import {schnorr} from '@noble/curves/secp256k1';
import {compileContract} from '../../dist/generic.js';
import {hex,unhex} from '../../dist/compiler.js';
import {prepareContractCall,finalizeContractCall} from '../../dist/call-runtime.js';
const family=process.env.LOTUS_V2_OPTIMIZER_FAMILY;
const optimize=process.env.LOTUS_V2_OPTIMIZER_ENABLED;
if(!['payment','equal','literal'].includes(family)||!['0','1'].includes(optimize))
 throw Error('explicit optimizer family/payment|equal|literal and enabled/0|1 required');
const source={
 payment:'contract Payment<owner: PublicKey> { function spend(signature: Signature) { require(checksig(signature, owner)); } }',
 equal:'contract Payment<owner: PublicKey> { function spend(signature: Signature, x: Int) { require(x == 1); require(checksig(signature, owner)); } }',
 literal:'contract Payment<owner: PublicKey> { function spend(signature: Signature) { require((1 + 2) * (3 + 4) == 21); require(true && !false); require(checksig(signature, owner)); } }',
}[family];
const secret=unhex('00'.repeat(31)+'01');
const owner=hex(schnorr.getPublicKey(secret));
const artifact=compileContract(source,{contract:'Payment',bindings:{Payment:{owner}},optimize:optimize==='1'});
if(process.argv[2]==='artifact')console.log(JSON.stringify({source,artifact,owner}));
else if(process.argv[2]==='sign'){
 const request=JSON.parse(readFileSync(0,'utf8'));
 const raw=request.context ?? request;
 const output=o=>({...o,value:BigInt(o.value)});
 const context={...raw,profile:artifact.target,coin:output(raw.coin),outputs:raw.outputs.map(output)};
 function sign(x){
  const args={signature:null,...(family==='equal'?{x}: {})};
  const plan=prepareContractCall(artifact,'spend',context,args);
  const signature=schnorr.sign(unhex(plan.requests[0].digest),secret,new Uint8Array(32));
  return {plan,signature,final:finalizeContractCall(plan,{signature})};
 }
 const {plan,signature,final}=sign(1n);
 const bad=signature.slice();bad[0]^=1;
 const negatives=family==='equal'?[{name:'wrong-integer',wire:hex(sign(2n).final.wire)}]:[];
 console.log(JSON.stringify({wire:hex(final.wire),bad_wire:hex(finalizeContractCall(plan,{signature:bad}).wire),txid:final.txid,txhash:final.txhash,digest:plan.requests[0].digest,signature:hex(signature),negatives}));
}else throw Error('usage: node payment.mjs artifact|sign');
