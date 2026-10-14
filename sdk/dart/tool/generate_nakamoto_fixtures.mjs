#!/usr/bin/env node
// Read-only reference generator. Public test keys below must never receive funds.
// node sdk/dart/tool/generate_nakamoto_fixtures.mjs /path/to/frank --output fixtures.json --provenance provenance.json
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, relative, resolve } from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';

const pinnedCommit = '8c9e38f46ee429826ff918df6eb79214a06af98c';
const args = process.argv.slice(2);
const frank = resolve(args.shift() ?? `${process.env.HOME}/repos/frank`);
const option = (flag) => {
  const index = args.indexOf(flag);
  return index < 0 ? null : args[index + 1];
};
const git = (...values) => execFileSync('git', ['-C', frank, ...values], { encoding: 'utf8' }).trim();
const commit = git('rev-parse', 'HEAD');
if (commit !== pinnedCommit) throw new Error(`Expected Frank ${pinnedCommit}, got ${commit}`);
if (git('status', '--porcelain', '--', 'packages/nakamoto', 'yarn.lock', 'docs/protocol/chains/v1.json')) {
  throw new Error('Reference source and dependency lock must be clean');
}
const requireFrank = createRequire(resolve(frank, 'packages/nakamoto/package.json'));
const { build, version: esbuildVersion } = requireFrank('esbuild');
const bundle = await build({
  entryPoints: [resolve(frank, 'packages/nakamoto/src/index.ts')],
  bundle: true, platform: 'node', format: 'esm', write: false, metafile: true,
});
const n = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].contents).toString('base64')}`);
const take = (result) => {
  if (!result.ok) throw new Error(JSON.stringify(result.error));
  return result.value;
};
const hex = (value) => Buffer.from(value).toString('hex');
const bytes = (value) => Uint8Array.from(Buffer.from(value, 'hex'));
const display = (value) => hex(Uint8Array.from(value).reverse());
const privateKeyHex = '00'.repeat(31) + '01';
const hash160Hex = '00112233445566778899aabbccddeeff00112233';
const seedHex = '000102030405060708090a0b0c0d0e0f';
const hdPath = "m/0'/1/2'/2/1000000000";
const key = take(n.privateKeyFromHex(privateKeyHex, true));
const publicKey = take(n.publicFromPrivate(key));
const master = take(n.hdPrivateFromSeed(bytes(seedHex)));
const derived = take(n.deriveHdPath(master, hdPath));
const destinations = ['p2pkh', 'p2sh'].map(kind => ({kind, hash: bytes(hash160Hex)}));
const chains = n.CHAINS.map(descriptor => {
  const addresses = destinations.map(destination => {
    const encodings = descriptor.family === 'xpi' ? ['lotus'] :
      descriptor.cashaddrPrefix ? ['base58check', 'cashaddr'] : ['base58check'];
    return {kind: destination.kind, scriptHex: hex(n.lockingScript(destination)),
      forms: encodings.map(encoding => ({encoding, text: take(n.encodeAddress(destination, descriptor, encoding))}))};
  });
  if (descriptor.bech32Hrp) {
    const destination = {kind: 'p2wpkh', hash: bytes(hash160Hex)};
    addresses.push({kind: 'p2wpkh', scriptHex: hex(n.lockingScript(destination)),
      forms: [{encoding: 'bech32', text: take(n.encodeAddress(destination, descriptor, 'bech32'))}]});
  }
  return {descriptor, addresses,
    wifCompressed: take(n.privateKeyToWif(key, descriptor)),
    wifUncompressed: take(n.privateKeyToWif(take(n.privateKeyFromHex(privateKeyHex, false)), descriptor)),
    hd: {masterPrivate: take(n.serializeHdPrivate(master, descriptor)),
      masterPublic: take(n.serializeHdPublic(take(n.hdPublicFromPrivate(master)), descriptor)),
      derivedPrivate: take(n.serializeHdPrivate(derived, descriptor)),
      derivedPublic: take(n.serializeHdPublic(take(n.hdPublicFromPrivate(derived)), descriptor))}};
});
const script = n.lockingScript(destinations[0]);
const baseTx = {version: 2, inputs: [
  {prevout: {txid: bytes('11'.repeat(32)), vout: 3}, scriptSig: bytes('0101'), sequence: 0xfffffffd},
  {prevout: {txid: bytes('22'.repeat(32)), vout: 0}, scriptSig: bytes('020203'), sequence: 0xfffffffe},
], outputs: [{value: 123456789n, scriptPubKey: script}, {value: 1000n, scriptPubKey: bytes('6a020102')}], locktime: 499999};
const transactions = n.CHAINS.filter(c => c.network === 'mainnet').flatMap(chain => {
  const variants = [{name: 'legacy', tx: baseTx}];
  if (chain.bech32Hrp) variants.push({name: 'segwit', tx: {...baseTx,
    inputs: baseTx.inputs.map((input, i) => ({...input, scriptSig: new Uint8Array(), witness: [bytes('010203'), bytes(i ? '0405' : '060708')]}))}});
  return variants.map(({name, tx}) => {
    const raw = take(n.serializeTransaction(tx, chain));
    const parsed = take(n.parseTransaction(raw, chain));
    if (hex(take(n.serializeTransaction(parsed, chain))) !== hex(raw)) throw new Error('Parse/serialize mismatch');
    const algorithms = chain.family === 'xpi' ? ['legacy', 'forkid', 'lotus'] :
      chain.cashaddrPrefix ? ['forkid'] : chain.bech32Hrp ? ['legacy', 'bip143'] : ['legacy'];
    const sighashes = algorithms.flatMap(algorithm => [1,2,3,129,130,131].map(type => {
      const hashType = algorithm === 'forkid' ? type | 0x40 : algorithm === 'lotus' ? type | 0x60 : type;
      const options = {algorithm, scriptCode: script, amount: 200000000n,
        spent: [{value: 200000000n, scriptPubKey: script}, {value: 5000000n, scriptPubKey: script}]};
      const digest = take(n.sighash(tx, 0, chain, hashType, options));
      const signature = take(n.signEcdsa(key, digest));
      if (!take(n.verifyEcdsa(signature, digest, publicKey.compressed))) throw new Error('ECDSA self-verification failed');
      return {algorithm, inputIndex: 0, hashType, scriptCodeHex: hex(script), amount: '200000000',
        spent: options.spent.map(output => ({value: output.value.toString(), scriptPubKeyHex: hex(output.scriptPubKey)})),
        digestHex: hex(digest), signatureDerHex: hex(signature)};
    }));
    const parsedFields = {version: parsed.version, locktime: parsed.locktime,
      inputs: parsed.inputs.map(input => ({prevTxidInternalHex: hex(input.prevout.txid),
        vout: input.prevout.vout, scriptSigHex: hex(input.scriptSig), sequence: input.sequence,
        witnessHex: (input.witness ?? []).map(hex)})),
      outputs: parsed.outputs.map(output => ({value: output.value.toString(), scriptPubKeyHex: hex(output.scriptPubKey)}))};
    return {family: chain.family, name, rawHex: hex(raw), parsed: parsedFields, txid: display(take(n.transactionId(tx, chain))),
      hash: display(take(n.transactionHash(tx, chain))), sighashes};
  });
});
const standardHeader = {kind: 'bitcoin-80', version: 4, prevBlock: bytes('33'.repeat(32)),
  merkleRoot: bytes('44'.repeat(32)), time: 1700000000, bits: 0x1d00ffff, nonce: 12345};
const lotusHeader = {kind: 'lotus', time: 1700000000000n, prevBlock: bytes('33'.repeat(32)), bits: 0x1d00ffff,
  reserved: 0, nonce: 9007199254740993n, headerVersion: 1, size: 1000000n, height: 1400000,
  epochBlock: bytes('55'.repeat(32)), merkleRoot: bytes('44'.repeat(32)), extendedMetadata: bytes('66'.repeat(32))};
const headers = n.CHAINS.filter(c => c.network === 'mainnet').map(chain => {
  const header = chain.family === 'xpi' ? lotusHeader : standardHeader;
  const raw = take(n.serializeHeader(header));
  const result = n.parseHeader(raw, chain);
  const fields = Object.fromEntries(Object.entries(header).map(([name, value]) =>
    [value instanceof Uint8Array ? `${name}InternalHex` : name, value instanceof Uint8Array ? hex(value) : value]));
  return {family: chain.family, fields, rawHex: hex(raw), hash: display(take(n.headerHash(header))),
    parseSupported: result.ok, ...(result.ok ? {} : {parseError: result.error.code})};
});
const scalarTwoHex = '00'.repeat(31) + '02';
const scalarSevenHex = '00'.repeat(31) + '07';
const peerKey = take(n.privateKeyFromHex(scalarSevenHex, true));
const peerPublicKey = take(n.publicFromPrivate(peerKey));
const ecdh = [privateKeyHex, scalarTwoHex, '80' + '00'.repeat(31)].map(secretHex => {
  const privateKey = take(n.privateKeyFromHex(secretHex, true));
  const shared = take(n.ecdh(privateKey, peerPublicKey.compressed));
  return {privateKeyHex: secretHex, peerPrivateKeyHex: scalarSevenHex,
    peerPublicKeyHex: hex(peerPublicKey.compressed), sharedCompressedHex: hex(shared.point),
    sha256CompressedHex: hex(take(n.ecdhWithHash(privateKey, peerPublicKey.compressed, point => n.cryptoBackend.sha256(point))))};
});
const resultHex = (result, convert) => result.ok ? {ok: true, hex: convert(result.value)} : {ok: false, error: result.error.code};
const tweaks = [privateKeyHex, '80' + '00'.repeat(31),
  'fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364140', '00'.repeat(32)].map(tweakHex => ({
  privateKeyHex, publicKeyHex: hex(publicKey.compressed), tweakHex,
  privateResult: resultHex(n.tweakAddPrivateKey(key, bytes(tweakHex)), value => hex(value.bytes)),
  publicResult: resultHex(n.tweakAddPublicKey(publicKey.compressed, bytes(tweakHex)), hex),
}));
const signer = take(n.signingKey('ecdsa', key));
const keyHash = n.cryptoBackend.hash160(publicKey.compressed);
const signedTransactions = n.CHAINS.filter(chain => chain.network === 'mainnet').flatMap(chain => {
  const variants = chain.family === 'xpi' ? [
    {kind: 'p2pkh', algorithm: 'legacy', hashType: 1, replayProtection: false},
    {kind: 'p2pkh', algorithm: 'forkid', hashType: 0x41, replayProtection: false},
    {kind: 'p2pkh', algorithm: 'forkid', hashType: 0x41, replayProtection: true},
    {kind: 'p2pkh', algorithm: 'lotus', hashType: 0x61, replayProtection: false},
  ] : [{kind: 'p2pkh', algorithm: chain.cashaddrPrefix ? 'forkid' : 'legacy',
    hashType: chain.cashaddrPrefix ? 0x41 : 1, replayProtection: false}];
  if (chain.bech32Hrp) variants.push({kind: 'p2wpkh', algorithm: 'bip143', hashType: 1, replayProtection: false});
  return variants.map(variant => {
    const spentScript = n.lockingScript({kind: variant.kind, hash: keyHash});
    const tx = {...baseTx, inputs: baseTx.inputs.map(input => ({...input, scriptSig: new Uint8Array()}))};
    const spent = [{value: 200000000n, scriptPubKey: spentScript}, {value: 5000000n, scriptPubKey: spentScript}];
    const options = {chain, algorithm: variant.algorithm, sighashType: variant.hashType, spent,
      replayProtection: variant.replayProtection, commitUtxos: false};
    const input = take(n.signInput(tx, 0, signer, options));
    const assignments = [{inputIndex: 1, signer}, {inputIndex: 0, signer}];
    const all = take(n.signAll(tx, assignments, options));
    const output = item => ({index: item.index ?? item.inputIndex,
      scriptSigHex: hex(item.scriptSig), witnessHex: item.witness === null ? null : item.witness.map(hex)});
    return {family: chain.family, ...variant, privateKeyHex, publicKeyHex: hex(publicKey.compressed),
      commitUtxos: false, unsignedRawHex: hex(take(n.serializeTransaction(tx, chain))),
      spent: spent.map(coin => ({value: coin.value.toString(), scriptPubKeyHex: hex(coin.scriptPubKey)})),
      assignments: assignments.map(item => ({inputIndex: item.inputIndex, privateKeyHex})),
      signInput: {...output(input), unsigned: input.unsigned,
        rawHex: hex(take(n.serializeTransaction(input.transaction, chain)))},
      signAll: {inputs: all.inputs.map(output), rawHex: hex(take(n.serializeTransaction(all.transaction, chain))),
        txid: display(take(n.transactionId(all.transaction, chain))), hash: display(take(n.transactionHash(all.transaction, chain)))}};
  });
});
const merkle = [n.BTC_MAINNET, n.XPI_MAINNET].map(chain => {
  const leaves = ['11'.repeat(32), '22'.repeat(32), '33'.repeat(32)];
  return {family: chain.family, leavesInternalHex: leaves, rootInternalHex: hex(n.merkleRoot(leaves.map(bytes), chain))};
});
const registryPath = 'docs/protocol/chains/v1.json';
const registry = JSON.parse(readFileSync(resolve(frank, registryPath), 'utf8'));
const protocolRegistry = n.CHAINS.map(chain => {
  const entry = registry.chains.find(item => item.id === chain.protocolId);
  if (!entry) throw new Error(`Registry missing ${chain.protocolId}`);
  return entry;
});
const fixtures = {schemaVersion: 1, frankCommit: commit, protocolRegistry,
  inputs: {privateKeyHex, hash160Hex, seedHex, hdPath, publicKeyHex: hex(publicKey.compressed)},
  chains, transactions, headers, signedTransactions, merkle, curve: {ecdh, tweaks}};
const stringify = value => JSON.stringify(value, (_, item) => typeof item === 'bigint' ? item.toString() : item, 2) + '\n';
const fixtureJson = stringify(fixtures);
const sha256 = data => createHash('sha256').update(data).digest('hex');
const sourcePaths = git('ls-files', 'packages/nakamoto/src', 'packages/nakamoto/package.json', 'packages/nakamoto/LICENSE', 'yarn.lock', registryPath).split('\n');
const sourceHashes = Object.fromEntries(sourcePaths.map(path => [path, sha256(readFileSync(resolve(frank, path)))]));
const installedPackage = (name, entry) => {
  let directory = dirname(requireFrank.resolve(entry));
  while (directory !== dirname(directory)) {
    const candidate = resolve(directory, 'package.json');
    if (existsSync(candidate)) {
      const content = readFileSync(candidate);
      const metadata = JSON.parse(content);
      if (metadata.name === name) return {version: metadata.version, packageJsonSha256: sha256(content)};
    }
    directory = dirname(directory);
  }
  throw new Error(`Cannot identify installed ${name}`);
};
const installedRuntimeDependencies = {
  '@noble/curves': installedPackage('@noble/curves', '@noble/curves/secp256k1'),
  '@noble/hashes': installedPackage('@noble/hashes', '@noble/hashes/sha256'),
};
const runtimeInputHashes = Object.fromEntries(Object.keys(bundle.metafile.inputs)
  .filter(path => path.includes('node_modules')).sort().map(path =>
    [relative(frank, resolve(path)), sha256(readFileSync(resolve(path)))]));
const provenance = {schemaVersion: 1, frankCommit: commit, fixtureSha256: sha256(fixtureJson),
  chainIndexSha256: sha256(readFileSync(resolve(frank, 'packages/nakamoto/src/chain/index.ts'))),
  protocolRegistrySha256: sha256(readFileSync(resolve(frank, registryPath))),
  nodeVersion: process.version, esbuildVersion,
  runtimeDependencies: JSON.parse(readFileSync(resolve(frank, 'packages/nakamoto/package.json'), 'utf8')).dependencies,
  installedRuntimeDependencies, runtimeInputHashes, sourceHashes,
  command: 'node sdk/dart/tool/generate_nakamoto_fixtures.mjs /path/to/frank --output sdk/dart/test/fixtures/nakamoto-parity.json --provenance sdk/dart/test/fixtures/nakamoto-provenance.json',
  notes: ['Generated using actual Frank TypeScript public exports, bundled in memory without modifying Frank.',
    'Public deterministic test keys only; no network calls or funded wallets.',
    'Dogecoin full AuxPoW header parsing is unsupported upstream; parseError records that limit.',
    'Header hashes here are identity hashes, not proof-of-work validation. Litecoin scrypt is not exercised.']};
if (option('--output')) writeFileSync(resolve(option('--output')), fixtureJson); else process.stdout.write(fixtureJson);
if (option('--provenance')) writeFileSync(resolve(option('--provenance')), stringify(provenance));
