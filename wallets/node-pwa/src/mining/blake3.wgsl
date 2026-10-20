// One candidate per invocation. Header words and output digest words are packed
// little-endian bytes. params = [nonceLow, count, nonceHigh, reserved].
// Dispatch ceil(count/64) workgroups; bound count and buffers on the host.
@group(0) @binding(0) var<storage, read> header: array<u32>;
@group(0) @binding(1) var<storage, read> params: array<u32>;
@group(0) @binding(2) var<storage, read_write> output: array<u32>;
fn rr(x:u32,n:u32)->u32 { return (x>>n)|(x<<(32u-n)); }
const IV = array<u32,8>(0x6a09e667u,0xbb67ae85u,0x3c6ef372u,0xa54ff53au,0x510e527fu,0x9b05688cu,0x1f83d9abu,0x5be0cd19u);
fn swap(x:u32)->u32 { return ((x&255u)<<24u)|((x&65280u)<<8u)|((x>>8u)&65280u)|(x>>24u); }
@group(0) @binding(3) var<storage, read> chain:array<u32>;
const PERM = array<u32,16>(2u,6u,3u,10u,7u,0u,4u,13u,1u,11u,12u,5u,9u,14u,15u,8u);
fn mix(p:ptr<function,array<u32,16>>,a:u32,b:u32,c:u32,d:u32,x:u32,y:u32) {
 (*p)[a]+=(*p)[b]+x;(*p)[d]=rr((*p)[d]^(*p)[a],16u);(*p)[c]+=(*p)[d];(*p)[b]=rr((*p)[b]^(*p)[c],12u);
 (*p)[a]+=(*p)[b]+y;(*p)[d]=rr((*p)[d]^(*p)[a],8u);(*p)[c]+=(*p)[d];(*p)[b]=rr((*p)[b]^(*p)[c],7u);
}
fn blake(data:array<u32,64>,length:u32)->array<u32,8> {
 var cv=IV;let blocks=(length+63u)/64u;
 for(var block=0u;block<blocks;block++) {
  var m:array<u32,16>;
  for(var j=0u;j<16u;j++){m[j]=data[block*16u+j];}
  let last=block+1u==blocks;
  var v:array<u32,16>;
  for(var j=0u;j<8u;j++){v[j]=cv[j];}
  for(var j=0u;j<4u;j++){v[j+8u]=IV[j];}
  v[14]=min(64u,length-block*64u);v[15]=select(0u,1u,block==0u)|select(0u,10u,last);
  for(var r=0u;r<7u;r++) {
   mix(&v,0u,4u,8u,12u,m[0],m[1]);mix(&v,1u,5u,9u,13u,m[2],m[3]);
   mix(&v,2u,6u,10u,14u,m[4],m[5]);mix(&v,3u,7u,11u,15u,m[6],m[7]);
   mix(&v,0u,5u,10u,15u,m[8],m[9]);mix(&v,1u,6u,11u,12u,m[10],m[11]);
   mix(&v,2u,7u,8u,13u,m[12],m[13]);mix(&v,3u,4u,9u,14u,m[14],m[15]);
   var next:array<u32,16>;for(var j=0u;j<16u;j++){next[j]=m[PERM[j]];}m=next;
  }
  for(var j=0u;j<8u;j++){cv[j]=v[j]^v[j+8u];}
 }
 return cv;
}
fn put(p:ptr<function,array<u32,64>>,offset:u32,value:u32) {(*p)[offset/4u]|=(value&255u)<<((offset%4u)*8u);}
fn getHeader(offset:u32)->u32{return (header[offset/4u]>>((offset%4u)*8u))&255u;}
fn bodyTag()->array<u32,64> {var data:array<u32,64>;
 put(&data,0u,76u);
 put(&data,1u,111u);
 put(&data,2u,116u);
 put(&data,3u,117u);
 put(&data,4u,115u);
 put(&data,5u,47u);
 put(&data,6u,118u);
 put(&data,7u,50u);
 put(&data,8u,47u);
 put(&data,9u,104u);
 put(&data,10u,101u);
 put(&data,11u,97u);
 put(&data,12u,100u);
 put(&data,13u,101u);
 put(&data,14u,114u);
 put(&data,15u,47u);
 put(&data,16u,98u);
 put(&data,17u,111u);
 put(&data,18u,100u);
 put(&data,19u,121u);
 put(&data,20u,0u);
return data;}
fn workTag()->array<u32,64> {var data:array<u32,64>;
 put(&data,0u,76u);
 put(&data,1u,111u);
 put(&data,2u,116u);
 put(&data,3u,117u);
 put(&data,4u,115u);
 put(&data,5u,47u);
 put(&data,6u,118u);
 put(&data,7u,50u);
 put(&data,8u,47u);
 put(&data,9u,104u);
 put(&data,10u,101u);
 put(&data,11u,97u);
 put(&data,12u,100u);
 put(&data,13u,101u);
 put(&data,14u,114u);
 put(&data,15u,47u);
 put(&data,16u,119u);
 put(&data,17u,111u);
 put(&data,18u,114u);
 put(&data,19u,107u);
 put(&data,20u,0u);
return data;}
fn idTag()->array<u32,64> {var data:array<u32,64>;
 put(&data,0u,76u);
 put(&data,1u,111u);
 put(&data,2u,116u);
 put(&data,3u,117u);
 put(&data,4u,115u);
 put(&data,5u,47u);
 put(&data,6u,118u);
 put(&data,7u,50u);
 put(&data,8u,47u);
 put(&data,9u,98u);
 put(&data,10u,108u);
 put(&data,11u,111u);
 put(&data,12u,99u);
 put(&data,13u,107u);
 put(&data,14u,105u);
 put(&data,15u,100u);
 put(&data,16u,0u);
return data;}
@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid:vec3<u32>) {
 let index=gid.x;if(index>=params[1]){return;}
 let low=params[0]+index;let high=params[2]+select(0u,1u,low<params[0]);
 var body=bodyTag();
 for(var i=0u;i<32u;i++){put(&body,21u+i,(chain[i/4u]>>((i%4u)*8u))&255u);}
 for(var i=0u;i<84u;i++){put(&body,53u+i,getHeader(50u+i));}
 let bodyHash=blake(body,137u);
 var work=workTag();
 for(var i=0u;i<10u;i++){put(&work,21u+i,getHeader(32u+i));}
 for(var i=0u;i<4u;i++){put(&work,31u+i,low>>(i*8u));put(&work,35u+i,high>>(i*8u));}
 for(var i=0u;i<32u;i++){put(&work,39u+i,(bodyHash[i/4u]>>((i%4u)*8u))&255u);}
 let workHash=blake(work,71u);
 var id=idTag();
 for(var i=0u;i<32u;i++){put(&id,17u+i,getHeader(i));put(&id,49u+i,(workHash[i/4u]>>((i%4u)*8u))&255u);}
 let result=blake(id,81u);
 for(var i=0u;i<8u;i++){output[index*8u+i]=result[i];}
}
