// One validated, immutable description of the connected node. Mining accepts
// only compiled-in algorithm identifiers; descriptors never provide code/URLs.
const ALGOS = Object.freeze({
  sha256d: Object.freeze({ headerbytes: 80, nonceoffset: 76, noncebytes: 4 }),
  'lotus-v2-blockid': Object.freeze({ headerbytes: 134, nonceoffset: 42, noncebytes: 8 }),
});

/** @typedef {'sha256d'|'lotus-v2-blockid'} MiningAlgorithm */
/** @typedef {{algorithm: MiningAlgorithm, headerbytes: number, nonceoffset: number, noncebytes: number, chainid?: string}} MiningDescriptor */
export function validateMiningDescriptor(value) {
  if (!value || value.version !== 1) throw new Error('This node does not advertise a supported mining descriptor.');
  const expected = Object.hasOwn(ALGOS, value.algorithm) ? ALGOS[value.algorithm] : null;
  if (!expected) throw new Error('This node advertises an unsupported proof-of-work algorithm.');
  for (const key of ['headerbytes', 'nonceoffset', 'noncebytes']) {
    if (value[key] !== expected[key]) throw new Error(`Unsupported mining header layout (${key}).`);
  }
  if (value.noncebyteorder !== 'little' || value.hashbyteorder !== 'little' || value.targetbyteorder !== 'big') throw new Error('Unsupported mining byte order.');
  if (value.template_rpc !== 'getrawunsolvedblock' || value.submit_rpc !== 'submitblock') throw new Error('Unsupported mining RPC contract.');
  if (value.algorithm === 'lotus-v2-blockid' && !/^[0-9a-f]{64}$/i.test(value.chainid ?? '')) throw new Error('Missing or invalid mining chain identifier.');
  return Object.freeze({ version: 1, algorithm: value.algorithm, ...expected,
    noncebyteorder: 'little', hashbyteorder: 'little', targetbyteorder: 'big',
    ...(value.algorithm === 'lotus-v2-blockid' ? { chainid: value.chainid.toLowerCase() } : {}),
    template_rpc: 'getrawunsolvedblock', submit_rpc: 'submitblock' });
}

export function resolveChainConfig({ chain, profile, currency, addressFormat, hrp, client, version, miningInfo }) {
  const rpcDecimals = Number(currency.decimals);
  if (!Number.isInteger(rpcDecimals) || rpcDecimals < 0 || rpcDecimals > 18) throw new Error(`bad currency decimals ${currency.decimals}`);
  const atomicUnitsPerCoin = String(currency.satoshisperunit ?? 10n ** BigInt(rpcDecimals));
  if (!/^\d+$/.test(atomicUnitsPerCoin) || BigInt(atomicUnitsPerCoin) !== 10n ** BigInt(rpcDecimals)) throw new Error('Currency atomic unit and RPC precision disagree.');
  const ticker = String(currency.ticker);
  if (!ticker || ticker.length > 16) throw new Error('Invalid currency ticker.');
  let mining;
  try { mining = Object.freeze({ supported: true, descriptor: validateMiningDescriptor(miningInfo?.pow) }); }
  catch (error) { mining = Object.freeze({ supported: false, reason: error.message }); }
  return Object.freeze({
    configVersion: 1,
    network: Object.freeze({ chain, profile, client, version }),
    currency: Object.freeze({ ticker, atomicUnitsPerCoin, rpcDecimals, displayDecimals: Math.min(2, rpcDecimals) }),
    address: Object.freeze({ format: addressFormat, hrp }),
    mining,
    rpc: Object.freeze({ testBlockGeneration: chain === 'regtest', template: mining.supported ? mining.descriptor.template_rpc : null,
      submission: mining.supported ? mining.descriptor.submit_rpc : null }),
    // Existing views read these aliases from the same resolver during migration.
    chain, profile, client, version, ticker, decimals: rpcDecimals, addressFormat, hrp,
  });
}
