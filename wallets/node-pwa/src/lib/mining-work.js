// Template ownership stays in the daemon. The browser changes only the nonce
// in an otherwise byte-identical serialized candidate block.
import { validateMiningDescriptor } from './chainconfig.js';
import { bytesToHex, hexToBytes, setHeaderNonce, sha256d, v2BlockHash, meetsTarget } from './mining-hashes.js';

export const MAX_BROWSER_BLOCK_BYTES = 32 * 1024 * 1024;
function bytes(hex, count, label) {
  if (typeof hex !== 'string' || !/^(?:[0-9a-f]{2})+$/i.test(hex) || (count !== null && hex.length !== count * 2)) throw new Error(`Invalid ${label} from node.`);
  return hexToBytes(hex);
}
export function compactTarget(bits) {
  const exponent = bits >>> 24;
  const mantissa = bits & 0x7fffff;
  if ((bits & 0x800000) || !mantissa) throw new Error('Invalid compact mining target.');
  let value = BigInt(mantissa);
  value = exponent <= 3 ? value >> BigInt(8 * (3 - exponent)) : value << BigInt(8 * (exponent - 3));
  if (value <= 0n || value >= 1n << 256n) throw new Error('Mining target out of range.');
  return hexToBytes(value.toString(16).padStart(64, '0')).reverse();
}
export function decodeMiningWork(raw, descriptor, expectedParent) {
  const pow = validateMiningDescriptor(descriptor);
  if (typeof raw?.blockhex !== 'string' || raw.blockhex.length > MAX_BROWSER_BLOCK_BYTES * 2) throw new Error('Block candidate exceeds the browser mining size limit.');
  const block = bytes(raw.blockhex, null, 'block candidate');
  if (block.length <= pow.headerbytes) throw new Error('Incomplete block candidate.');
  const header = block.slice(0, pow.headerbytes);
  const parentOffset = pow.algorithm === 'sha256d' ? 4 : 0;
  const parent = bytesToHex(header.slice(parentOffset, parentOffset + 32).reverse());
  if (!/^[0-9a-f]{64}$/i.test(expectedParent) || parent !== expectedParent.toLowerCase()) throw new Error('Mining template changed parent; retry.');
  const bitsOffset = pow.algorithm === 'sha256d' ? 72 : 32;
  const bits = new DataView(header.buffer).getUint32(bitsOffset, true);
  const target = bytes(raw.target, 32, 'mining target').reverse();
  if (bytesToHex(target) !== bytesToHex(compactTarget(bits))) throw new Error('Mining target differs from candidate header.');
  return { descriptor: pow, header, target, block, parent,
    chainid: pow.chainid ? hexToBytes(pow.chainid) : undefined };
}
export function validateCandidate(work, nonce) {
  const maxNonce = (1n << BigInt(work.descriptor.noncebytes * 8)) - 1n;
  if (typeof nonce !== 'bigint' || nonce < 0n || nonce > maxNonce) throw new Error('GPU returned an invalid nonce.');
  const header = setHeaderNonce(work.header, nonce);
  const digest = work.descriptor.algorithm === 'sha256d' ? sha256d(header) : v2BlockHash(header, work.chainid);
  if (!meetsTarget(digest, work.target)) throw new Error('GPU candidate failed CPU proof-of-work verification.');
  const block = work.block.slice();
  block.set(header);
  return { blockhex: bytesToHex(block), digest, header };
}
