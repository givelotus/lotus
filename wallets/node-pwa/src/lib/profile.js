// Network and profile detection.
//
// Nothing about the chain is hard-coded: the ticker and decimals come from
// getcurrencyinfo, the chain from getblockchaininfo, and the profile from the
// block header size (80 bytes: eCash-style; 134 bytes: Lotus V2). Under the
// Lotus V2 profile the address format is probed: if the node accepts an
// xpiaddr it is "xpi", otherwise the node predates xpi addresses and still
// uses cashaddr. validateaddress stays authoritative either way.

import { encode, HRP_FOR_CHAIN } from './xpiaddr.js';
import { RpcError } from './rpc.js';

/**
 * @typedef {{chain: string, ticker: string, decimals: number, profile: 'ecash'|'lotus-v2'|'generic',
 *            addressFormat: 'cashaddr'|'xpi', hrp: string|null, client: string, version: number}} Profile
 */

/** @param {number} hexLength length of getblockheader <hash> false */
export function profileFromHeaderHex(hexLength) {
  if (hexLength === 160) return 'ecash';
  if (hexLength === 268) return 'lotus-v2';
  return 'generic';
}

/** "/Lotus:0.34.1(EB32.0)/" → "Lotus 0.34.1" */
export function clientFromSubversion(sub) {
  const m = /^\/([^:/]+):([^(/]+)/.exec(sub ?? '');
  return m ? `${m[1]} ${m[2]}` : (sub ?? '').replace(/^\/|\/$/g, '') || 'node';
}

/**
 * @param {{call: Function, batch: Function}} rpc
 * @returns {Promise<Profile>}
 */
export async function detectProfile(rpc) {
  const [chainInfo, currency, net] = await rpc.batch([['getblockchaininfo'], ['getcurrencyinfo'], ['getnetworkinfo']]);
  for (const r of [chainInfo, currency, net]) if (r instanceof RpcError) throw r;
  const header = await rpc.call('getblockheader', [chainInfo.bestblockhash, false]);
  const profile = profileFromHeaderHex(String(header).length);
  const decimals = Number(currency.decimals);
  if (!Number.isInteger(decimals) || decimals < 0 || decimals > 18) throw new Error(`bad currency decimals ${currency.decimals}`);
  let addressFormat = 'cashaddr';
  let hrp = null;
  if (profile === 'lotus-v2' && Object.hasOwn(HRP_FOR_CHAIN, chainInfo.chain)) {
    const probe = encode(HRP_FOR_CHAIN[chainInfo.chain], new Uint8Array(32));
    const v = await rpc.call('validateaddress', [probe]).catch(() => ({ isvalid: false }));
    if (v?.isvalid === true) {
      addressFormat = 'xpi';
      hrp = HRP_FOR_CHAIN[chainInfo.chain];
    }
  }
  return {
    chain: chainInfo.chain,
    ticker: String(currency.ticker),
    decimals,
    profile,
    addressFormat,
    hrp,
    client: clientFromSubversion(net.subversion),
    version: Number(net.version),
  };
}
