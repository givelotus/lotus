import { test } from 'node:test';
import assert from 'node:assert/strict';
import { detectProfile, profileFromHeaderHex, clientFromSubversion } from '../../src/lib/profile.js';
import { decode } from '../../src/lib/xpiaddr.js';

function fakeRpc({ chain = 'regtest', headerBytes = 80, xpiValid = false, ticker = 'XEC', decimals = 2 }) {
  const probes = [];
  const answers = {
    getblockchaininfo: { chain, bestblockhash: 'ab'.repeat(32) },
    getcurrencyinfo: { ticker, decimals, satoshisperunit: 10 ** decimals },
    getnetworkinfo: { subversion: '/Lotus:0.34.1(EB32.0)/', version: 340100 },
  };
  return {
    probes,
    batch: async (calls) => calls.map(([m]) => answers[m]),
    call: async (m, p) => {
      if (m === 'getblockheader') return '00'.repeat(headerBytes);
      if (m === 'validateaddress') { probes.push(p[0]); return { isvalid: xpiValid }; }
      throw new Error(m);
    },
  };
}

test('header size selects the profile', () => {
  assert.equal(profileFromHeaderHex(160), 'ecash');
  assert.equal(profileFromHeaderHex(268), 'lotus-v2');
  assert.equal(profileFromHeaderHex(320), 'generic');
});

test('eCash-style node: cashaddr, no xpi probe', async () => {
  const rpc = fakeRpc({ headerBytes: 80 });
  const p = await detectProfile(rpc);
  assert.deepEqual([p.profile, p.addressFormat, p.ticker, p.decimals, p.chain, p.client], ['ecash', 'cashaddr', 'XEC', 2, 'regtest', 'Lotus 0.34.1']);
  assert.equal(rpc.probes.length, 0);
});

test('Lotus V2 node before xpi addresses: probe rejected → cashaddr', async () => {
  const rpc = fakeRpc({ headerBytes: 134 });
  const p = await detectProfile(rpc);
  assert.equal(p.profile, 'lotus-v2');
  assert.equal(p.addressFormat, 'cashaddr');
  assert.equal(decode(rpc.probes[0]).hrp, 'rxpi');
});

test('Lotus V2 node with xpi addresses: probe accepted → xpi with chain hrp', async () => {
  const p = await detectProfile(fakeRpc({ headerBytes: 134, xpiValid: true, chain: 'main', ticker: 'XPI', decimals: 6 }));
  assert.deepEqual([p.addressFormat, p.hrp, p.ticker, p.decimals], ['xpi', 'xpi', 'XPI', 6]);
});

test('client name from subversion', () => {
  assert.equal(clientFromSubversion('/Bitcoin ABC:0.30.1(EB32.0)/'), 'Bitcoin ABC 0.30.1');
  assert.equal(clientFromSubversion(''), 'node');
});
