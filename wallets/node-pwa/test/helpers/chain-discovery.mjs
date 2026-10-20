export function chainDiscovery({ native = false, network = 'regtest', genesis = 'ab'.repeat(32), cashaddr = true } = {}) {
  const kind = native ? 'lotus-v2' : 'ecash';
  const chainid = native ? '00'.repeat(32) : undefined;
  return { version: 1,
    chain: { family: 'bitcoin', kind, network, identifier: `${kind}-${network}:${genesis}`, genesis, ...(native ? { chainid } : {}) },
    currency: { ticker: native ? 'XPI' : 'XEC', atomsperunit: native ? '1000000' : '100', rpcdecimals: native ? 6 : 2, displaydecimals: 2 },
    address: { format: cashaddr ? 'cashaddr' : 'base58check', hrp: network === 'regtest' ? 'ecregtest' : 'ecash', types: [0, 1], acceptedformats: ['cashaddr', 'base58check'], base58prefixes: { pubkeyhash: '6f', scripthash: 'c4' } },
    mining: { testgeneration: network === 'regtest', pow: { version: 1, algorithm: native ? 'lotus-v2-blockid' : 'sha256d', headerbytes: native ? 134 : 80, nonceoffset: native ? 42 : 76, noncebytes: native ? 8 : 4, noncebyteorder: 'little', hashbyteorder: 'little', targetbyteorder: 'big', ...(native ? { chainid } : {}), template_rpc: 'getrawunsolvedblock', submit_rpc: 'submitblock' } },
    features: { legacytransactions: true, nativetransactions: native, message_signing: 'legacy-p2pkh' }, node: { client: native ? 'Lotus' : 'Bitcoin ABC', version: 340100 },
  };
}
