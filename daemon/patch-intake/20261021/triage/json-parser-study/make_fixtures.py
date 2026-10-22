#!/usr/bin/env python3
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent/'fixtures';ROOT.mkdir(exist_ok=True)
def save(name,data):
 raw=json.dumps(data,separators=(',',':'),ensure_ascii=False).encode()
 (ROOT/(name+'.json')).write_bytes(raw)
 return {'name':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
hex207=bytes(i%251 for i in range(207)).hex();hex414=bytes(i%251 for i in range(414)).hex()
fixtures=[]
for count,text,label in [(1,hex207,'single207'),(1,hex414,'single414'),(50,hex207,'array50_207'),(50,hex414,'array50_414')]:
 data=[{'jsonrpc':'1.0','id':i,'method':'sendrawtransaction','params':[text]} for i in range(count)]
 fixtures.append(save(label,data[0] if count==1 else data))
fixtures.append(save('batch200',{'jsonrpc':'1.0','id':1,'method':'submitrawtxbatch','params':[[hex207]*200]}))
# Deterministic block-like response. Synthetic structure; not a daemon timing result.
tx={'txid':'ab'*32,'hash':'cd'*32,'version':7,'size':207,'locktime':0,'vin':[{'txid':'ef'*32,'vout':0,'scriptSig':{'asm':'','hex':''},'sequence':4294967295}],'vout':[{'value':'0.00000001','n':0,'scriptPubKey':{'asm':'OP_TRUE','hex':'51','type':'pubkeyhash','addresses':['lotus_example']}}],'hex':hex414}
fixtures.append(save('block1000',{'result':{'hash':'aa'*32,'height':500000,'confirmations':1,'tx':[tx]*1000},'error':None,'id':1}))
(ROOT/'fixtures.json').write_text(json.dumps([x['name'] for x in fixtures],indent=2))
(ROOT/'manifest.json').write_text(json.dumps(fixtures,indent=2))
cases=[]
def test(name,text):
 if isinstance(text,str):text=text.encode()
 cases.append({'name':name,'input_hex':text.hex()})
for name,text in [
('null','null'),('true','true'),('false','false'),('zero','0'),('minuszero','-0'),('amount','0.00000001'),('trailingzero','1.2300e+03'),('largeint','9007199254740993'),('u64overflow','18446744073709551616'),('hugeint','9'*300),('hugeexp','1e9999'),('small_exp','1e-9999'),('dupes','{"x":1,"x":2,"a":3}'),('order','{"z":1,"a":2}'),('escapedkey','{"a\\u0000b":"x\\u0000y"}'),('utf8','{"a":"日本語 😀"}'),('surrogate_pair','["\\ud83d\\ude00"]'),('escape','["\\\"\\\\\\/\\b\\f\\n\\r\\t"]'),('ids','[{"id":null,"params":null},{"id":"42","params":[]},{"id":9007199254740993,"params":{}}]'),('depth512','['*512+'0'+']'*512),('depth513','['*513+'0'+']'*513),
('leadingzero','[01]'),('minusleadingzero','[-01]'),('fraction','[1.]'),('exp','[1e]'),('expplus','[1e+]'),('plus','[+1]'),('nan','[NaN]'),('inf','[Infinity]'),('hexfake','[0x1]'),('suffix','[1foo]'),('boolsuffix','[truex]'),('nullsuffix','[nullx]'),('surrogate_lone','["\\ud800"]'),('surrogate_low','["\\udc00"]'),('bad_escape','["\\q"]'),('control','["\x01"]'),('trail_comma','[1,]'),('missing_comma','[1 2]'),('missing_colon','{"a" 1}'),('truncated','[{"a":'),('trailing','{} []'),('later_bad_array','[{"method":"stop"},{"bad":01}]'),('embedded_nul','{}\x00{}')]:test(name,text)
for name,text in [('invalid_utf8',b'["\xff"]'),('overlong',b'["\xc0\xaf"]'),('utf8_surrogate',b'["\xed\xa0\x80"]'),('utf8_truncated',b'["\xf0\x9f"]')]:test(name,text)
(ROOT/'correctness.json').write_text(json.dumps(cases,indent=2))
print(json.dumps({'fixtures':fixtures,'correctness_cases':len(cases)},indent=2))
