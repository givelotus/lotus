// Evidence generator for these documentation examples. No consensus implementation.
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve, dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { compileContract } from '../../../../tools/lotus-v2-compiler/dist/generic.js';
import { prepareTransactionCall, finalizeTransactionCall, encodeAssetOutput } from '../../../../tools/lotus-v2-compiler/dist/transaction-runtime.js';
import { schnorr } from '../../../../tools/lotus-v2-compiler/node_modules/@noble/curves/secp256k1.js';
import { blake3 } from '../../../../tools/lotus-v2-compiler/node_modules/@noble/hashes/blake3.js';
const here = dirname(fileURLToPath(import.meta.url)), root = resolve(here, '../../../..');
if (!process.argv[2]) throw Error('Pass a NEW output directory; checked-in baseline evidence is immutable.');
const out = resolve(process.argv[2]);
if (existsSync(out)) throw Error('Output directory already exists; preserve prior evidence and choose a new path.');
mkdirSync(out, { recursive: true });
const h = b => Buffer.from(b).toString('hex');
const source = name => readFileSync(join(here, name), 'utf8');
const keys = [3n,4n,5n].map(x => { const b = Buffer.alloc(32); b[31] = Number(x); return { secret:b, public:h(schnorr.getPublicKey(b)) }; });
const sign = (digest, i) => schnorr.sign(Buffer.from(digest,'hex'), keys[i].secret, new Uint8Array(32));
const artifacts = {}, cases = [], diagnostics = [];
const tag = payload => blake3(Buffer.concat([Buffer.from('Lotus/v2/branch\0'),payload]));
function compact(n) {if(n<253)return Buffer.from([n]);const b=Buffer.alloc(3);b[0]=253;b.writeUInt16LE(n,1);return b;}
function compareLE(a,b){for(let i=31;i>=0;i--){if(a[i]!==b[i])return a[i]-b[i];}return 0;}
const compile = (name, file, contract, bindings) => {
  const text = source(file), a = compileContract(text, {contract, bindings});
  for (const m of a.methods) {
    const script=Buffer.from(m.scriptHex,'hex');
    let folded=tag(Buffer.concat([Buffer.from([0]),compact(script.length),script]));
    if(h(folded)!==m.leaf)throw Error('leaf mismatch');
    for(const sibling of m.proof){const b=Buffer.from(sibling,'hex');const [lo,hi]=compareLE(folded,b)<=0?[folded,b]:[b,folded];folded=tag(Buffer.concat([Buffer.from([1]),lo,hi]));}
    if(h(folded)!==a.policy.root)throw Error('proof root mismatch');
    if (m.sourceMap.some(x => ['DEFINE','INVOKE','OP_DEFINE','OP_INVOKE'].includes(x.op))) throw Error('forbidden VM call');
  }
  artifacts[name] = {source:file, sourceSha256:createHash('sha256').update(text).digest('hex'), artifact:a};
  writeFileSync(join(out,`${name}.json`), JSON.stringify(artifacts[name],null,2)+'\n');
  return a;
};
const threshold = compile('threshold','supported/threshold.lotus','Threshold',{Threshold:{alice:keys[0].public,bob:keys[1].public,carol:keys[2].public}});
const secret = Buffer.alloc(32, 7), digest = createHash('sha256').update(secret).digest('hex');
const escrow = compile('escrow','supported/escrow.lotus','HashEscrow',{HashEscrow:{seller:keys[0].public,buyer:keys[1].public,digest,refundHeight:100n}});
const fee = compile('fee-wallet','supported/per-mint-limit.lotus','FeeWallet',{FeeWallet:{owner:keys[0].public},PerMintLimit:{issuer:keys[0].public,limit:1000n}});
const mint = compile('per-mint-limit','supported/per-mint-limit.lotus','PerMintLimit',{FeeWallet:{owner:keys[0].public},PerMintLimit:{issuer:keys[0].public,limit:1000n}});
const amm = compile('amm-kernel','supported/amm-kernel.lotus','SwapKernel',{});
const opcode_costs = {};
for (const [lo,hi] of [[0,0x5d],[0x60,0x6b],[0x70,0x81],[0x88,0x94],[0x98,0xb4],[0xb8,0xc2],[0xc8,0xdd],[0xe0,0xea],[0xf0,0xf4]])
  for(let i=lo;i<=hi;i++) opcode_costs[i.toString(16).padStart(2,'0')] = [0xbb,0xbc,0xbd].includes(i)?1000:1;
const vmProfile = {max_script_bytes:8192,max_arguments:32,max_element_bytes:8192,max_stack_items:256,max_altstack_items:128,max_vm_bytes:65536,max_ast_depth:32,max_invocation_cost:1000000,structural_byte_cost:1,opcode_costs};
const txProfile = {max_inputs:65535,max_outputs:65535,max_mints:32,max_arguments:32,max_script_bytes:8192,max_argument_bytes:8192,max_branch_proof_depth:64};
function invoke(name, expected, request) {
  const p = spawnSync(process.env.LOTUS_V2_PYTHON ?? 'python3', ['-m','lotus_v2_reference.vm_runner'],{input:JSON.stringify({...request,profile:vmProfile}),encoding:'utf8',cwd:root,env:{...process.env,PYTHONPATH:join(root,'tools/lotus-v2-reference')}});
  if(!p.stdout) throw Error(`runner ${p.status}: ${p.stderr}`);
  const outcome=JSON.parse(p.stdout); cases.push({name,expected,request:{...request,profile:vmProfile},exitStatus:p.status,outcome});
  // Persist before checking: unexpected outcomes remain reviewable.
  writeFileSync(join(out,'cases.json'),JSON.stringify(cases,null,2)+'\n');
  if(outcome.accepted_invocation !== expected) throw Error(`${name}: ${JSON.stringify(outcome)}`);
}
const coinFor = a => ({flags:0,value:100000n,branches:[a.policy.root],paths:[[0]]});
function transactionCase(name,a,method,args,keyByArg,{lock=0n,valid=true,prev='55'.repeat(32),mintUnits}={}) {
  const coin=coinFor(a), outputs=[{...coinFor(fee),value:95000n}];
  const inputs=[{kind:'spend',prevTxid:prev,prevIndex:0,sequence:0xffffffff,coin,pathIndex:0,witnesses:[{artifact:a,methodName:method,args}]}];
  if(mintUnits !== undefined) { inputs.push({kind:'mint',artifact:mint,methodName:'issue',args:{sig:null}}); outputs.push({flags:1,value:mintUnits,tokenId:mint.policy.root,branches:[fee.policy.root],paths:[[0]]}); }
  const plan=prepareTransactionCall({profile:a.target,chainId:'44'.repeat(32),dustLimitAtoms:1n,lock,inputs,outputs});
  const signatures={}; for(const r of plan.requests) signatures[r.key]=sign(r.digest,r.inputIndex===1?0:keyByArg[r.argument]);
  if(!valid) { const k=plan.requests[0].key; signatures[k]=Buffer.from(signatures[k]); signatures[k][0]^=1; }
  const final=finalizeTransactionCall(plan,signatures), inputIndex=mintUnits===undefined?0:1, active=mintUnits===undefined?a:mint;
  const m=active.methods.find(m=>m.name===(mintUnits===undefined?method:'issue'));
  const wireArgs=m.args.map(arg=>{
    const r=plan.requests.find(r=>r.inputIndex===inputIndex&&r.argument===arg.name);
    return r?h(signatures[r.key]):h(args[arg.name]);
  });
  const request={script:m.scriptHex,args:wireArgs,transaction_context:{full_tx:h(final.wire),chain_id:'44'.repeat(32),coins:[h(encodeAssetOutput(coin)),...(inputIndex===1?[null]:[])],input_index:inputIndex,witness_index:0,profile:txProfile}};
  return {request,txid:final.txid};
}
for(const [method,args,owners] of [['aliceBob',{a:null,b:null},{a:0,b:1}],['aliceCarol',{a:null,c:null},{a:0,c:2}],['bobCarol',{b:null,c:null},{b:1,c:2}]]) {
  invoke(`threshold-${method}`,true,transactionCase(method,threshold,method,args,owners).request);
}
invoke('threshold-bad-signature',false,transactionCase('bad',threshold,'aliceBob',{a:null,b:null},{a:0,b:1},{valid:false}).request);
invoke('escrow-claim',true,transactionCase('claim',escrow,'claim',{sig:null,secret},{sig:0}).request);
invoke('escrow-bad-secret',false,transactionCase('claim',escrow,'claim',{sig:null,secret:Buffer.alloc(32,8)},{sig:0}).request);
invoke('escrow-refund-lock-100',true,transactionCase('refund',escrow,'refund',{sig:null},{sig:1},{lock:(100n<<8n)|1n}).request);
invoke('escrow-refund-lock-99',false,transactionCase('refund',escrow,'refund',{sig:null},{sig:1},{lock:(99n<<8n)|1n}).request);
invoke('escrow-claim-after-refund-bound',true,transactionCase('claim',escrow,'claim',{sig:null,secret},{sig:0},{lock:(101n<<8n)|1n}).request);
for(const [name,amount,prev] of [['first',1000n,'61'.repeat(32)],['again',1000n,'62'.repeat(32)],['excess',1001n,'63'.repeat(32)]]) {
  invoke(`per-mint-${name}`,amount<=1000n,transactionCase(name,fee,'spend',{sig:null},{sig:0},{mintUnits:amount,prev}).request);
}
const num = n => { let x=BigInt(n); if(x<0)x+=(1n<<128n); const b=Buffer.alloc(16); for(let i=0;i<16;i++){b[i]=Number(x&255n);x>>=8n;}return h(b); };
for(const [name,values,expected] of [['valid',[1000,1000,1100,910,100],true],['overpay',[1000,1000,1100,909,100],false],['negative',[-1000,1000,1100,910,100],false],['range',[2n**50n,1000,2n**50n+100n,910,100],false]]) {
  invoke(`amm-${name}`,expected,{script:amm.methods[0].scriptHex,args:values.map(num),input_count:1,output_count:1});
}
for(const [file,contract,bindings] of [['less-equal','PerMintLimit',{PerMintLimit:{issuer:keys[0].public,limit:1000n}}],['entry-policy','Owner',{Owner:{key:keys[0].public}}],['state','Allowance',{}],['division','Quotient',{}],['data-signature','Permit',{Permit:{owner:keys[0].public}}]]) {
  const s=source(`proposed/${file}.lotus`);
  try {const a=compileContract(s,{contract,bindings});diagnostics.push({file,source:s,compiledArtifact:a,execution:'not run: capability probe only; compare with retained baseline failure'});}
  catch(e) {diagnostics.push({file,source:s,error:String(e.message),bytecode:null,execution:'not run: frontend rejected'});}
}
writeFileSync(join(out,'frontend-gaps.json'),JSON.stringify(diagnostics,null,2)+'\n');
const summary={baselineSourceRevision:'9939ab0d881ce9f1791546a0dc57b1e9580cf835',compiler:'@lotus/v2-payment-compiler 0.1.0',target:threshold.target,optimized:true,artifacts:Object.keys(artifacts),invocations:cases.length,accepted:cases.filter(c=>c.outcome.accepted_invocation).length,rejected:cases.filter(c=>!c.outcome.accepted_invocation).length,frontendRejections:diagnostics.filter(x=>x.error).length,frontendAccepted:diagnostics.filter(x=>x.compiledArtifact).length,limitations:['VM invocation only: no UTXO resolution, block lock eligibility, full transaction accounting or connected block verdict.','AMM is an arithmetic kernel, not reserve authentication.','Per-mint limit accepts repeated issuance.','Illustrative VM cost schedule, not frozen P05 values.','Public test scalars 3/4/5 only.','baselineSourceRevision names the archived evidence base, not a claim about the compiler revision in a future run.']};
writeFileSync(join(out,'summary.json'),JSON.stringify(summary,null,2)+'\n');
console.log(JSON.stringify(summary,null,2));
