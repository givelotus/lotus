import test from 'node:test';
import assert from 'node:assert/strict';
import {validateSemanticProgram,SEMANTIC_IR_LIMITS} from '../dist/semantic-ir.js';
const span=(start=0,end=start+1)=>({start,end,file:'contract.lotus'});
const arg=name=>({kind:'arg',name,span:span(1)});
const bytes=hex=>({kind:'bytes',hex,span:span(2)});
const bool=value=>({kind:'bool',value,span:span(3)});
const hash=(value,kind='sha256')=>({kind,value,span:span(4)});
const equal=(left,right)=>({kind:'equal',left,right,span:span(5)});
const require_=condition=>({kind:'require',condition,span:span(6)});
const program=()=>({schema:'lotus/semantic-ir/1',entrypoint:'main',args:[{name:'preimage',type:{kind:'bytes',length:32},span:span(7)}],body:[require_(equal(hash(arg('preimage')),bytes('ab'.repeat(32))))],span:span(0,99)});
function accepted(p){const r=validateSemanticProgram(p);assert.equal(r.ok,true,JSON.stringify(r));return r;}
function rejected(p,code){const r=validateSemanticProgram(p);assert.equal(r.ok,false,JSON.stringify(r));assert.equal(r.diagnostics.length,1);if(code)assert.equal(r.diagnostics[0].code,`semantic-ir-${code}`);return r.diagnostics[0];}
test('typed hashlock validates independently of any chain opcode and detaches spans/tree',()=>{
 const p=program(),r=accepted(p);assert.deepEqual(r.program,p);assert.notEqual(r.program,p);assert.notEqual(r.program.args[0].type,p.args[0].type);
 assert.deepEqual(r.requirements.map(x=>x.capability),['bytes','bytes','sha256','bytes','bytes','byte-equality','bool','require']);
 assert.ok(r.requirements.every(x=>x.span.file==='contract.lotus'));
 p.body[0].condition.left.value.name='changed';p.span.start=50;p.args[0].type.length=1;
 assert.equal(r.program.body[0].condition.left.value.name,'preimage');assert.equal(r.program.span.start,0);assert.equal(r.program.args[0].type.length,32);
 r.requirements[0].span.start=999;assert.equal(r.program.args[0].span.start,7);
});
test('both conditional arms require capabilities even behind a constant condition',()=>{
 const p=program();p.body=[{kind:'if',condition:bool(false),then:[require_(equal(hash(bytes(''),'hash256'),bytes('00'.repeat(32))))],otherwise:[require_(equal(bool(true),bool(false)))],span:span(8)}];
 const r=accepted(p);assert.ok(r.requirements.some(x=>x.capability==='hash256'));assert.ok(r.requirements.some(x=>x.capability==='if'));assert.equal(r.requirements.filter(x=>x.capability==='require').length,2);
 assert.deepEqual(validateSemanticProgram(p),r);
});
test('exact byte lengths include empty strings and the IR bound independently of backend limits',()=>{
 for(const length of [0,1,520,521,SEMANTIC_IR_LIMITS.maxBytes]){const p=program();p.args[0].type.length=length;p.body=[require_(equal(arg('preimage'),bytes('00'.repeat(length))))];accepted(p);}
 for(const length of [-1,0.5,NaN,Infinity,8193,'32']){const p=program();p.args[0].type.length=length;rejected(p,'type');}
 const p=program();p.body=[require_(equal(bytes(''),bytes('00')))];rejected(p,'type');
});
test('hashes are bytes-only and exactly 32 bytes, with no bool/byte coercions',()=>{
 for(const kind of ['sha256','hash256']){const p=program();p.body=[require_(equal(hash(bytes(''),kind),bytes('00'.repeat(32))))];accepted(p);p.body[0].condition.left.value=bool(true);rejected(p,'type');}
 for(const expression of [bytes('01'),equal(bool(true),bytes('01'))]){const p=program();p.body=[require_(expression)];rejected(p,'type');}
 const p=program();p.body=[{kind:'if',condition:bytes('01'),then:[],otherwise:[],span:span()}];rejected(p,'type');
});
test('unknown schema, fields, operations and chain-specific types reject explicitly',()=>{
 const bad=program();bad.schema='lotus/semantic-ir/2';rejected(bad,'schema');
 const unknown=program();unknown.bytecode='89';rejected(unknown,'shape');
 for(const kind of ['int','amount','signature','checksig','transaction-signature','reflection','invoke','define']){const p=program();p.body[0].condition={kind,span:span(11)};const d=rejected(p,'unsupported');assert.deepEqual(d.span,span(11));}
 for(const kind of ['int','amount','signature','public-key','input-index']){const p=program();p.args[0].type={kind};rejected(p,'unsupported');}
 for(const kind of ['invoke','define','loop','reflection','return']){const p=program();p.body=[{kind,span:span()}];rejected(p,'unsupported');}
 const p=program();p.body[0].condition={kind:'bool',value:true,opcode:0x89,span:span()};rejected(p,'shape');
});
test('argument declarations/references are named, typed and unambiguous',()=>{
 const p=program();p.args.push(structuredClone(p.args[0]));rejected(p,'argument');
 const missing=program();missing.body[0].condition.left.value.name='missing';rejected(missing,'argument');
 for(const name of ['', 'a.b','a-b',1]){const p=program();p.args[0].name=name;rejected(p,'name');}
 const b=program();b.args=[{name:'ok',type:{kind:'bool'},span:span()}];b.body=[require_(arg('ok'))];accepted(b);
 const empty=program();empty.args=[];empty.body=[];accepted(empty); // Explicitly trivial policies are representable.
});
test('constant byte/Boolean encodings are canonical rather than host truthiness',()=>{
 for(const hex of ['A0','0','0x00','gg','00 ','00\n',0]){const p=program();p.body=[require_(equal(bytes(hex),bytes('00')))];rejected(p,'constant');}
 const oversize=program();oversize.body[0].condition=equal(bytes('00'.repeat(8193)),bytes('00'.repeat(8193)));rejected(oversize,'constant');
 for(const value of [0,1,'true','',null]){const p=program();p.body=[require_(bool(value))];rejected(p,'constant');}
});
test('source spans validate UTF-8 offset shape and preserve each occurrence',()=>{
 for(const at of [{start:-1,end:2},{start:2,end:1},{start:0.5,end:2},{start:0,end:Infinity},{start:0,end:Number.MAX_SAFE_INTEGER+1},{start:0,end:1,file:3},{start:0,end:1,module:'x'},null]){const p=program();p.body[0].span=at;rejected(p,'span');}
 const p=program();p.span={start:0,end:0};accepted(p);
 const r=accepted(program());const ops=r.requirements.filter(x=>x.capability==='bytes');assert.deepEqual(ops.map(x=>x.span.start),[7,1,4,2]);
});
test('cycles, excessive nesting and node/argument budgets reject without host recursion overflow',()=>{
 const p=program(),expr=hash(bytes(''));expr.value=expr;p.body[0].condition=expr;rejected(p,'cycle');
 const s=program(),stmt={kind:'if',condition:bool(true),then:[],otherwise:[],span:span()};stmt.then=[stmt];s.body=[stmt];rejected(s,'cycle');
 const deep=program();let value=bytes('');for(let i=0;i<=SEMANTIC_IR_LIMITS.maxDepth;i++)value=hash(value);deep.body=[require_(equal(value,bytes('00'.repeat(32))))];rejected(deep,'limit');
 const wide=program();wide.body=Array.from({length:SEMANTIC_IR_LIMITS.maxNodes},()=>require_(bool(true)));rejected(wide,'limit');
 const args=program();args.args=Array.from({length:SEMANTIC_IR_LIMITS.maxArgs+1},(_,i)=>({name:`x${i}`,type:{kind:'bool'},span:span()}));rejected(args,'limit');
 // A shared acyclic expression is allowed and each occurrence is checked.
 const shared=program(),operand=hash(bytes(''));shared.body=[require_(equal(operand,operand))];accepted(shared);
});
test('malformed imported JSON-like values and sparse/accessor arrays never become implicit success',()=>{
 for(const value of [null,[],{},true,0,'',new Date()])rejected(value,'shape');
 const sparse=program();sparse.body=Array(1);rejected(sparse,'shape');
 const args=program();args.args=Array(1);rejected(args,'shape');
 const extra=program();extra.body.foo=true;rejected(extra,'shape');
 const getter=program();Object.defineProperty(getter.body[0],'condition',{get(){throw Error('must not run');},enumerable:true});rejected(getter,'shape');
 const array=program();Object.defineProperty(array.body,0,{get(){throw Error('must not run');}});rejected(array,'shape');
});
