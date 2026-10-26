// Compile for a native wallet's public key. No signing or private key APIs.
import { readFileSync } from 'node:fs';
import { compileContract } from '../../dist/generic.js';
const request=JSON.parse(readFileSync(0,'utf8'));
if(typeof request.owner!=='string'||!/^[0-9a-f]{64}$/.test(request.owner))throw Error('native x-only public key required');
const source=readFileSync(new URL('../../examples/gallery/payment.lotus',import.meta.url),'utf8');
const artifact=compileContract(source,{contract:'Payment',bindings:{Payment:{owner:request.owner}}});
const method=artifact.methods.find(m=>m.name==='spend');
if(method.proof.length)throw Error('wallet pilot requires sole Payment method');
console.log(JSON.stringify({source,artifact,owner:request.owner,script:method.scriptHex,proof:method.proof,root:artifact.policy.root}));
