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

function object(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`Invalid ${label}.`);
  return value;
}
function text(value, label, pattern) {
  if (typeof value !== 'string' || !value || value.length > 256 || (pattern && !pattern.test(value))) throw new Error(`Invalid ${label}.`);
  return value;
}
function integer(value, label, max) {
  if (!Number.isSafeInteger(value) || value < 0 || value > max) throw new Error(`Invalid ${label}.`);
  return value;
}
function bool(value, label) {
  if (typeof value !== 'boolean') throw new Error(`Invalid ${label}.`);
  return value;
}
function freeze(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    for (const child of Object.values(value)) freeze(child);
    Object.freeze(value);
  }
  return value;
}

/** Immutable facts and UI policy for one authenticated node connection.
 * Behavioral operations belong to ChainAdaptor, not this configuration.
 */
export class ChainConfig {
  constructor(raw) {
    object(raw, 'chain discovery');
    if (raw.version !== 1) throw new Error('Unsupported getchainconfig schema version.');
    const chain = object(raw.chain, 'chain identity');
    if (chain.family !== 'bitcoin' || !['ecash', 'lotus-v2'].includes(chain.kind) || !['main', 'test', 'regtest'].includes(chain.network)) throw new Error('Unsupported chain family, kind or network.');
    const genesis = text(chain.genesis, 'genesis hash', /^[0-9a-f]{64}$/);
    const identifier = text(chain.identifier, 'chain identifier');
    if (identifier !== `${chain.kind}-${chain.network}:${genesis}`) throw new Error('Chain identifier disagrees with genesis/network identity.');
    const native = chain.kind === 'lotus-v2';
    const chainid = native ? text(chain.chainid, 'native chain identifier', /^[0-9a-f]{64}$/) : null;
    const money = object(raw.currency, 'currency');
    const rpcDecimals = integer(money.rpcdecimals, 'RPC precision', 18);
    const displayDecimals = integer(money.displaydecimals, 'display precision', rpcDecimals);
    const atoms = text(money.atomsperunit, 'atomic units', /^[1-9][0-9]*$/);
    if (BigInt(atoms) !== 10n ** BigInt(rpcDecimals)) throw new Error('Currency atomic unit and RPC precision disagree.');
    const ticker = text(money.ticker, 'currency ticker', /^[A-Za-z0-9]{1,16}$/);
    const address = object(raw.address, 'address capabilities');
    if (!['cashaddr', 'base58check'].includes(address.format) || !Array.isArray(address.acceptedformats) || !address.acceptedformats.includes(address.format) || address.acceptedformats.some((f) => !['cashaddr', 'base58check'].includes(f))) throw new Error('Unsupported address codec.');
    if (!Array.isArray(address.types) || address.types.length !== 2 || !address.types.includes(0) || !address.types.includes(1)) throw new Error('Unsupported address destination types.');
    const hrp = text(address.hrp, 'address prefix', /^[a-z0-9]+$/);
    const prefixes = object(address.base58prefixes, 'Base58 prefixes');
    const pubkeyhash = text(prefixes.pubkeyhash, 'Base58 pubkey prefix', /^(?:[0-9a-f]{2})+$/);
    const scripthash = text(prefixes.scripthash, 'Base58 script prefix', /^(?:[0-9a-f]{2})+$/);
    const mining = object(raw.mining, 'mining capabilities');
    const pow = validateMiningDescriptor(mining.pow);
    if (pow.algorithm !== (native ? 'lotus-v2-blockid' : 'sha256d') || (native && pow.chainid !== chainid)) throw new Error('Proof-of-work descriptor disagrees with chain identity.');
    const testGeneration = bool(mining.testgeneration, 'test block generation');
    if (testGeneration && chain.network !== 'regtest') throw new Error('Test block generation advertised outside regtest.');
    const features = object(raw.features, 'protocol features');
    if (features.message_signing !== 'legacy-p2pkh') throw new Error('Unsupported message-signature scheme.');
    const legacy = bool(features.legacytransactions, 'legacy transaction capability');
    const nativeTransactions = bool(features.nativetransactions, 'native transaction capability');
    if (nativeTransactions !== native) throw new Error('Transaction capabilities disagree with chain kind.');
    const node = object(raw.node, 'node identity');
    const client = text(node.client, 'node client');
    const version = integer(node.version, 'node version', 0x7fffffff);
    Object.assign(this, {
      configVersion: 1, chainIdentifier: identifier,
      network: { family: chain.family, kind: chain.kind, chain: chain.network, chainIdentifier: identifier, genesis, chainid, client, version },
      currency: { ticker, atomicUnitsPerCoin: atoms, rpcDecimals, displayDecimals },
      address: { format: address.format, hrp, types: [...address.types], acceptedFormats: [...address.acceptedformats], base58Prefixes: { pubkeyhash, scripthash } },
      mining: { supported: true, descriptor: pow },
      rpc: { testBlockGeneration: testGeneration, template: pow.template_rpc, submission: pow.submit_rpc },
      features: { legacyTransactions: legacy, nativeTransactions, messageSigning: features.message_signing, nativeMessageSigning: false },
      // Existing view vocabulary references these same validated facts.
      chain: chain.network, profile: chain.kind, client, version, ticker, decimals: rpcDecimals, addressFormat: address.format, hrp,
    });
    freeze(this);
  }
}
