// Built-in Lotus V2 pool RPC contract. Uses the existing authenticated node
// connection; never exposes credentials to a worker or a public pool route.
import { validateMiningDescriptor } from './chainconfig.js';
import { compactTarget } from './mining-work.js';
import { bytesToHex, hexToBytes, setHeaderNonce, v2BlockHash, meetsTarget } from './mining-hashes.js';
import { decodeTyped } from './xpiaddr.js';

function target(hex, label) {
  if (typeof hex !== 'string' || !/^[0-9a-f]{64}$/i.test(hex) || BigInt(`0x${hex}`) === 0n) throw new Error(`Invalid pool ${label}.`);
  return hexToBytes(hex).reverse();
}
export function poolWorkerId(address, label, config) {
  if (config.network.kind !== 'lotus-v2') throw new Error('Built-in pooled mining requires Lotus V2.');
  if (!config.address?.nativeHrp || !config.address.acceptedFormats?.includes('xpiaddr')) throw new Error('This node does not advertise a supported native payout address codec.');
  decodeTyped(address, config.address.nativeHrp);
  if (!/^[A-Za-z0-9_-]{1,32}$/.test(label)) throw new Error('Worker name must contain 1–32 letters, numbers, underscores or hyphens.');
  return `${address.toLowerCase()}.${label}`;
}
export function poolTerms(raw) {
  if (!raw || raw.enabled !== true || raw.payout_ready !== true) throw new Error(raw?.payout_error || 'Pool is disabled or its payout destination is unavailable.');
  if (!Number.isInteger(raw.operator_fee_bps) || raw.operator_fee_bps < 0 || raw.operator_fee_bps > 10000 || typeof raw.operator_address !== 'string' || (raw.operator_fee_bps && !raw.operator_address)) throw new Error('Invalid pool operator commission.');
  if (typeof raw.pool_address !== 'string' || !raw.pool_address) throw new Error('Pool payout destination is unavailable.');
  if (!Number.isSafeInteger(raw.pplns_window_max) || raw.pplns_window_max <= 0) throw new Error('Invalid PPLNS reward window.');
  return Object.freeze({ poolAddress: raw.pool_address, feeBps: raw.operator_fee_bps, operatorAddress: raw.operator_address, window: raw.pplns_window_max });
}
export function assertPoolTerms(raw, terms) {
  if ((Object.hasOwn(raw, 'pool_address') && raw.pool_address !== terms.poolAddress) || raw.operator_fee_bps !== terms.feeBps || raw.operator_address !== terms.operatorAddress) throw new Error('Pool commission changed. Review the pool terms and press Start again.');
}
export function decodePoolJob(raw, descriptor, workerId, terms) {
  const pow = validateMiningDescriptor(descriptor);
  if (pow.algorithm !== 'lotus-v2-blockid' || raw?.protocol !== 'v2') throw new Error('Unsupported pool proof-of-work protocol.');
  if (raw.worker_id !== workerId || typeof raw.job_id !== 'string' || !/^[1-9][0-9]*$/.test(raw.job_id) || BigInt(raw.job_id) >= 1n << 64n) throw new Error('Invalid pool worker or job identifier.');
  if (typeof raw.header_hex !== 'string' || !/^[0-9a-f]{268}$/i.test(raw.header_hex) || raw.chain_id?.toLowerCase() !== pow.chainid) throw new Error('Invalid pool header or chain identifier.');
  if (!Number.isInteger(raw.nonce_prefix) || raw.nonce_prefix <= 0 || raw.nonce_prefix > 0xffffff) throw new Error('Invalid pool nonce prefix.');
  assertPoolTerms(raw, terms);
  const header = hexToBytes(raw.header_hex);
  const networkTarget = target(raw.network_target, 'network target');
  if (bytesToHex(networkTarget) !== bytesToHex(compactTarget(new DataView(header.buffer).getUint32(32, true)))) throw new Error('Pool network target differs from header.');
  const parent = bytesToHex(header.slice(0, 32).reverse());
  if (raw.prev_block_hash !== parent) throw new Error('Pool header parent differs from job.');
  const nonceStart = BigInt(raw.nonce_prefix) << 40n;
  const nonceEnd = nonceStart + (1n << 40n);
  const headerNonce = new DataView(header.buffer).getBigUint64(42, true);
  if (headerNonce >> 40n !== BigInt(raw.nonce_prefix)) throw new Error('Pool header nonce prefix differs from job.');
  return { descriptor: pow, header, chainid: hexToBytes(pow.chainid), target: target(raw.share_target, 'share target'), networkTarget,
    parent, jobId: raw.job_id, workerId, nonceStart, nonceEnd, raw };
}
export function validatePoolCandidate(work, nonce) {
  if (typeof nonce !== 'bigint' || nonce < work.nonceStart || nonce >= work.nonceEnd) throw new Error('GPU candidate escaped the assigned pool nonce range.');
  const header = setHeaderNonce(work.header, nonce);
  const digest = v2BlockHash(header, work.chainid);
  if (!meetsTarget(digest, work.target)) throw new Error('GPU share failed CPU proof-of-work verification.');
  return { nonce: nonce.toString(), digest, blockCandidate: meetsTarget(digest, work.networkTarget) };
}
