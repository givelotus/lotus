// One candidate per invocation. Header words and output digest words are packed
// little-endian bytes. params = [nonceLow, count, nonceHigh, reserved].
// Dispatch ceil(count/64) workgroups; bound count and buffers on the host.
@group(0) @binding(0) var<storage, read> header: array<u32>;
@group(0) @binding(1) var<storage, read> params: array<u32>;
@group(0) @binding(2) var<storage, read_write> output: array<u32>;
fn rr(x:u32,n:u32)->u32 { return (x>>n)|(x<<(32u-n)); }
const IV = array<u32,8>(0x6a09e667u,0xbb67ae85u,0x3c6ef372u,0xa54ff53au,0x510e527fu,0x9b05688cu,0x1f83d9abu,0x5be0cd19u);
fn swap(x:u32)->u32 { return ((x&255u)<<24u)|((x&65280u)<<8u)|((x>>8u)&65280u)|(x>>24u); }
const K = array<u32,64>(0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u);

fn digest(data:array<u32,32>, blocks:u32)->array<u32,8> {
 var h=IV;
 for(var block=0u;block<blocks;block++) {
  var w:array<u32,64>;
  for(var i=0u;i<16u;i++){w[i]=data[block*16u+i];}
  for(var i=16u;i<64u;i++) {
   let x=w[i-15u];let y=w[i-2u];
   w[i]=w[i-16u]+(rr(x,7u)^rr(x,18u)^(x>>3u))+w[i-7u]+(rr(y,17u)^rr(y,19u)^(y>>10u));
  }
  var a=h[0];var b=h[1];var c=h[2];var d=h[3];var e=h[4];var f=h[5];var g=h[6];var z=h[7];
  for(var i=0u;i<64u;i++) {
   let t=z+(rr(e,6u)^rr(e,11u)^rr(e,25u))+((e&f)^(~e&g))+K[i]+w[i];
   let u=(rr(a,2u)^rr(a,13u)^rr(a,22u))+((a&b)^(a&c)^(b&c));
   z=g;g=f;f=e;e=d+t;d=c;c=b;b=a;a=t+u;
  }
  h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=z;
 }
 return h;
}
@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid:vec3<u32>) {
 let index=gid.x;if(index>=params[1]){return;}
 var input:array<u32,32>;
 for(var i=0u;i<20u;i++){input[i]=swap(header[i]);}
 input[19]=swap(params[0]+index);
 input[20]=0x80000000u;input[31]=640u;
 let first=digest(input,2u);
 var second:array<u32,32>;
 for(var i=0u;i<8u;i++){second[i]=first[i];}
 second[8]=0x80000000u;second[15]=256u;
 let result=digest(second,1u);
 for(var i=0u;i<8u;i++){output[index*8u+i]=swap(result[i]);}
}
