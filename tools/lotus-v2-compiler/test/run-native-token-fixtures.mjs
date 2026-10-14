import { readFileSync, existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const executable = process.argv[2];
const baselineOnly = process.argv[3] === '--baseline-only';
if (!executable || (process.argv[3] && !baselineOnly))
  throw new Error('usage: node test/run-native-token-fixtures.mjs NATIVE_CHECK_EXECUTABLE [--baseline-only]');

function deltaHex(value) {
  if (value == null) return '-';
  if (typeof value === 'string' && /^[0-9a-f]{32}$/.test(value)) return value;
  const amount = BigInt(value);
  if (amount <= 0n || amount >= (1n << 128n)) throw new Error('positive delta out of u128 range');
  return Array.from({ length: 16 }, (_, i) => Number((amount >> (8n * BigInt(i))) & 255n)
    .toString(16).padStart(2, '0')).join('');
}

function run(testCase, expectedFailure) {
  const args = [testCase.wire, testCase.chainId, testCase.txid, testCase.txhash,
    String(testCase.coinWires.length), ...testCase.coinWires.map(coin => coin ?? '-'),
    String(testCase.requests.length)];
  for (const request of testCase.requests) {
    args.push(String(request.inputIndex), String(request.witnessIndex), String(request.argumentIndex ?? 0),
      request.publicKey, request.digest, request.branchIndex == null ? '-' : String(request.branchIndex),
      deltaHex(request.positiveDelta));
  }
  const result = spawnSync(executable, args, { encoding: 'utf8' });
  if (result.error) throw result.error;
  if (expectedFailure) {
    if (result.status === 0 || !result.stderr.includes(expectedFailure))
      throw new Error(`expected ${expectedFailure}, got status=${result.status}: ${result.stderr}`);
  } else if (result.status !== 0) {
    throw new Error(result.stderr || `native checker exited ${result.status}`);
  } else {
    console.log(result.stdout.trim());
  }
}

const generic = JSON.parse(readFileSync(new URL('../fixtures/generic-payment-v2.json', import.meta.url)));
const payment = { ...generic.valid, chainId: generic.context.chainId,
  coinWires: [generic.context.coinWire], requests: [{ inputIndex: 0, witnessIndex: 0,
    argumentIndex: 0, publicKey: generic.publicTestKey, digest: generic.valid.message,
    branchIndex: 0 }] };
run(payment);
run({ ...payment, chainId: '45'.repeat(32) }, 'core TxID mismatch');
run({ ...payment, requests: [{ ...payment.requests[0], branchIndex: 1 }] }, 'spend selector branch index mismatch');
run({ ...payment, requests: [{ ...payment.requests[0], digest: '00'.repeat(32) }] }, 'FULL signing message mismatch');
const changedSignature = (generic.valid.signature[0] === 'f' ? 'e' : 'f') + generic.valid.signature.slice(1);
if (!payment.wire.includes(generic.valid.signature)) throw new Error('generic fixture signature not found');
run({ ...payment, wire: payment.wire.replace(generic.valid.signature, changedSignature),
  txhash: '-' }, 'BIP340 signature mismatch');
// Same canonical framing, altered script leaf, and therefore a false membership proof.
const scriptPrefix = '2320' + generic.publicTestKey;
const alteredScript = '2320' + (generic.publicTestKey[0] === 'f' ? 'e' : 'f') + generic.publicTestKey.slice(1);
if (!payment.wire.includes(scriptPrefix)) throw new Error('generic fixture script not found');
run({ ...payment, wire: payment.wire.replace(scriptPrefix, alteredScript),
  txid: '-', txhash: '-' }, 'selected branch proof mismatch');

const tokenFixture = new URL('../fixtures/fungible-token-v2.json', import.meta.url);
if (existsSync(tokenFixture)) {
  const fixture = JSON.parse(readFileSync(tokenFixture));
  const transactions = fixture.transactions ?? {};
  for (const [name, tx] of Object.entries(transactions)) {
    run(tx);
    const proofScript = (name === 'mint' ? fixture.artifacts.FungibleToken : fixture.artifacts.FungibleRules).methods[0].scriptHex;
    if (!tx.wire.includes(proofScript)) throw new Error(`${name}: proof script not found in wire`);
    const modifiedScript = (proofScript[0] === 'f' ? 'e' : 'f') + proofScript.slice(1);
    run({ ...tx, wire: tx.wire.replace(proofScript, modifiedScript), txid: '-', txhash: '-' },
      name === 'mint' ? 'mint branch proof mismatch' : 'selected branch proof mismatch');
    const spendRequest = tx.requests.find(request => request.branchIndex != null);
    if (spendRequest) {
      const requests = tx.requests.map(request => request === spendRequest ?
        { ...request, branchIndex: request.branchIndex + 1 } : request);
      run({ ...tx, requests }, 'spend selector branch index mismatch');
    }
    if (tx.requests.some(request => request.positiveDelta)) {
      const requests = tx.requests.map(request => ({ ...request }));
      const request = requests.find(item => item.positiveDelta);
      const original = deltaHex(request.positiveDelta);
      request.positiveDelta = (original.slice(0, 2) === '01' ? '02' : '01') + original.slice(2);
      run({ ...tx, requests }, 'mint positive delta mismatch');
    }
    console.log(`${name}: native fixture verified`);
  }
} else {
  if (!baselineOnly) throw new Error('required fungible-token-v2.json fixture missing');
  console.log('generic native checker baseline passed');
}
