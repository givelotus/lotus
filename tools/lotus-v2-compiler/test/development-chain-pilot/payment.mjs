// Explicit public fixture key. Never handles wallet secrets.
import { readFileSync } from 'node:fs';
import { schnorr } from '@noble/curves/secp256k1';
import { compileContract } from '../../dist/generic.js';
import { hex,unhex } from '../../dist/compiler.js';
import { prepareContractCall,finalizeContractCall } from '../../dist/call-runtime.js';
const request=JSON.parse(readFileSync(0,'utf8') || '{}');
const source=request.source ?? readFileSync(new URL('../../examples/gallery/payment.lotus',import.meta.url),'utf8');
const secret=unhex('00'.repeat(31)+'01');
const owner=hex(schnorr.getPublicKey(secret));
const artifact=compileContract(source,{contract:'Payment',bindings:{Payment:{owner}},...request.options});
if(process.argv[2]==='artifact')console.log(JSON.stringify({source,artifact,owner}));
else if(process.argv[2]==='sign') {
 const raw=request.context ?? request;
 const output=o=>({...o,value:BigInt(o.value)});
 const context={...raw,profile:artifact.target,coin:output(raw.coin),outputs:raw.outputs.map(output)};
 const method=request.method ?? 'spend';
 const signatureArgument=request.signature_argument ?? 'signature';
 const methodArtifact=artifact.methods.find(m=>m.name===method);
 if(!methodArtifact)throw Error('unknown pilot method');
 const args={...request.args,[signatureArgument]:null};
 for(const parameter of methodArtifact.args) {
  if(parameter.name===signatureArgument)continue;
  const value=args[parameter.name];
  args[parameter.name]=['Int','Amount'].includes(parameter.type)?BigInt(value):parameter.type==='Bool'?value:unhex(value);
 }
 const plan=prepareContractCall(artifact,method,context,args);
 const signature=schnorr.sign(unhex(plan.requests[0].digest),secret,new Uint8Array(32));
 const final=finalizeContractCall(plan,{[signatureArgument]:signature});
 const bad=signature.slice();bad[0]^=1;
 const mutated=finalizeContractCall(plan,{[signatureArgument]:bad});
 console.log(JSON.stringify({wire:hex(final.wire),bad_wire:hex(mutated.wire),txid:final.txid,txhash:final.txhash,digest:plan.requests[0].digest,signature:hex(signature)}));
} else throw Error('usage: node payment.mjs artifact|sign');
