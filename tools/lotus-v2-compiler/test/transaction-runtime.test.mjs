import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { schnorr } from "@noble/curves/secp256k1";
import { compileContract } from "../dist/generic.js";
import { prepareContractCall } from "../dist/call-runtime.js";
import { hex, unhex } from "../dist/compiler.js";
import {
  finalizeTransactionCall,
  prepareTransactionCall,
} from "../dist/transaction-runtime.js";

const secret3 = unhex("00".repeat(31) + "03"),
  secret4 = unhex("00".repeat(31) + "04");
const owner3 = hex(schnorr.getPublicKey(secret3)),
  owner4 = hex(schnorr.getPublicKey(secret4));
const wallet = compileContract(
  "contract Wallet<owner: PublicKey> { function spend(signature: Signature) { require(checksig(signature, owner)); } }",
  { contract: "Wallet", bindings: { Wallet: { owner: owner3 } } },
);
const rules = compileContract(
  "contract Rules { function enforce() { require(true); } }",
  { contract: "Rules", bindings: {} },
);
const issuer = compileContract(
  "contract Issuer<owner: PublicKey> { function issue(signature: Signature) { require(checksig(signature, owner)); } }",
  { contract: "Issuer", bindings: { Issuer: { owner: owner4 } } },
);
issuer.kind = "token";
issuer.methods[0].invocation = "mint";
const tokenId = issuer.policy.root,
  walletRoot = wallet.policy.root,
  rulesRoot = rules.policy.root;
const native = (value) => ({
  flags: 0,
  value,
  branches: [walletRoot],
  paths: [[0]],
});
const token = (value) => ({
  flags: 1,
  value,
  tokenId,
  branches: [walletRoot, rulesRoot],
  paths: [[0, 1]],
});
const w = (artifact, methodName, args) => ({ artifact, methodName, args });
const nativeSpend = (prevTxid, prevIndex, coin) => ({
  kind: "spend",
  prevTxid,
  prevIndex,
  sequence: 0xffffffff,
  coin,
  pathIndex: 0,
  witnesses: [w(wallet, "spend", { signature: null })],
});
const intent = {
  profile: "P01-P02-P03-candidate-2026-10-14",
  chainId: "44".repeat(32),
  dustLimitAtoms: 500n,
  inputs: [
    nativeSpend("11".repeat(32), 0, native(10000n)),
    {
      kind: "mint",
      artifact: issuer,
      methodName: "issue",
      args: { signature: null },
    },
  ],
  outputs: [token(1000n), native(7000n)],
};
const sign = (plan) =>
  Object.fromEntries(
    plan.requests.map((r) => [
      r.key,
      schnorr.sign(
        unhex(r.digest),
        r.tokenId ? secret4 : secret3,
        new Uint8Array(32),
      ),
    ]),
  );

test("mint derives positive delta and FULL spend/mint selectors", () => {
  const plan = prepareTransactionCall(intent);
  assert.equal(plan.feeAtoms, 3000n);
  assert.equal(plan.tokenDeltas[tokenId], 1000n);
  assert.equal(plan.requests.length, 2);
  assert.equal(plan.requests[0].branchIndex, 0);
  assert.equal(plan.requests[1].tokenId, tokenId);
  assert.equal(plan.requests[1].positiveDelta, 1000n);
  assert.notEqual(plan.requests[0].digest, plan.requests[1].digest);
  const final = finalizeTransactionCall(plan, sign(plan));
  assert.equal(final.txid, plan.txid);
  assert.equal(final.wire.length, plan.projectedFullBytes);
  assert.notEqual(final.txhash, final.txid);
  const burnOutput = {
    flags: 3,
    value: 50n,
    tokenId,
    branches: [rulesRoot],
    paths: [],
  };
  const withExplicitBurn = prepareTransactionCall({
    ...intent,
    outputs: [token(950n), burnOutput, native(7000n)],
  });
  assert.equal(withExplicitBurn.tokenDeltas[tokenId], 1000n);
  assert.equal(withExplicitBurn.tokenBurns[tokenId], 50n);
  assert.throws(
    () =>
      finalizeTransactionCall(
        {
          ...plan,
          requests: [
            { ...plan.requests[0], digest: "00".repeat(32) },
            plan.requests[1],
          ],
        },
        sign(plan),
      ),
    /stale transaction plan/,
  );
});

test("transfer requires both positional branches and records implicit token burn", () => {
  const mintPlan = prepareTransactionCall(intent);
  const outputs = [token(700n), token(250n), native(4000n)];
  const transfer = {
    ...intent,
    inputs: [
      {
        kind: "spend",
        prevTxid: mintPlan.txid,
        prevIndex: 0,
        sequence: 0xffffffff,
        coin: token(1000n),
        pathIndex: 0,
        witnesses: [
          w(wallet, "spend", { signature: null }),
          w(rules, "enforce", {}),
        ],
      },
      nativeSpend(mintPlan.txid, 1, native(7000n)),
    ],
    outputs,
  };
  const plan = prepareTransactionCall(transfer);
  assert.equal(plan.tokenBurns[tokenId], 50n);
  assert.deepEqual(plan.tokenDeltas, {});
  assert.deepEqual(
    plan.requests.map((r) => r.branchIndex),
    [0, 0],
  );
  assert.equal(plan.feeAtoms, 3000n);
  assert.equal(finalizeTransactionCall(plan, sign(plan)).txid, plan.txid);
  assert.throws(
    () =>
      prepareTransactionCall({
        ...transfer,
        inputs: [
          {
            ...transfer.inputs[0],
            witnesses: [w(wallet, "spend", { signature: null })],
          },
          transfer.inputs[1],
        ],
      }),
    /required witness count/,
  );
  // A weaker successor path is a VM policy failure, outside local framing/accounting.
  assert.throws(
    () =>
      prepareTransactionCall({
        ...transfer,
        outputs: [token(1001n), native(4000n)],
      }),
    /mint inputs do not match/,
  );
  assert.throws(
    () =>
      prepareTransactionCall({
        ...transfer,
        inputs: [transfer.inputs[0], transfer.inputs[0], transfer.inputs[1]],
      }),
    /duplicate input outpoint/,
  );
});

test("wrong artifact kind, malformed mint and insufficient fee reject", () => {
  assert.throws(
    () => prepareContractCall(issuer, "issue", {}, { signature: null }),
    /mint artifact requires transaction runtime/,
  );
  assert.throws(
    () =>
      prepareTransactionCall({
        ...intent,
        inputs: [
          intent.inputs[0],
          {
            kind: "mint",
            artifact: wallet,
            methodName: "spend",
            args: { signature: null },
          },
        ],
      }),
    /wrong artifact or method invocation kind/,
  );
  assert.throws(
    () =>
      prepareTransactionCall({
        ...intent,
        inputs: [
          {
            ...intent.inputs[0],
            witnesses: [w(issuer, "issue", { signature: null })],
          },
          intent.inputs[1],
        ],
      }),
    /wrong artifact or method invocation kind/,
  );
  assert.throws(
    () =>
      prepareTransactionCall({
        ...intent,
        outputs: [token(1000n), native(9999n)],
      }),
    /native fee below/,
  );
  assert.throws(
    () => prepareTransactionCall({ ...intent, inputs: [intent.inputs[0]] }),
    /mint inputs do not match/,
  );
  assert.throws(
    () => prepareTransactionCall({ ...intent, inputs: [intent.inputs[1]] }),
    /needs consuming input/,
  );
  assert.throws(
    () =>
      prepareTransactionCall({
        ...intent,
        outputs: [{ ...token(1000n), tokenId: "00".repeat(32) }, native(7000n)],
      }),
    /token ID required/,
  );
});

test('Python planner matches signed mint and transfer bytes and selectors', t => {
  const python = process.env.LOTUS_V2_PYTHON ?? 'python3';
  const probe = spawnSync(python, ['-c', 'import blake3'], { encoding: 'utf8' });
  if (probe.status !== 0) { t.skip('install python/requirements.txt and set LOTUS_V2_PYTHON'); return; }
  const mintPlan = prepareTransactionCall(intent);
  const transfer = { ...intent, inputs: [
    { kind: 'spend', prevTxid: mintPlan.txid, prevIndex: 0, sequence: 0xffffffff,
      coin: token(1000n), pathIndex: 0, witnesses: [w(wallet, 'spend', { signature: null }), w(rules, 'enforce', {})] },
    nativeSpend(mintPlan.txid, 1, native(7000n))],
    outputs: [token(700n), token(250n), native(4000n)] };
  for (const selectedIntent of [intent, transfer]) {
    const plan = prepareTransactionCall(selectedIntent);
    const signatures = sign(plan);
    const result = finalizeTransactionCall(plan, signatures);
    const payload = { intent: selectedIntent, signatures: Object.fromEntries(Object.entries(signatures).map(([key, value]) => [key, hex(value)])) };
    const input = JSON.stringify(payload, (_, value) => typeof value === 'bigint' ? value.toString() : value);
    const run = spawnSync(python, ['test/python-transaction-run.py'], { input, encoding: 'utf8' });
    assert.equal(run.status, 0, run.stderr);
    assert.deepEqual(JSON.parse(run.stdout), { wire: hex(result.wire), txid: result.txid, txhash: result.txhash,
      feeAtoms: plan.feeAtoms.toString(), minimumFeeAtoms: plan.minimumFeeAtoms.toString(),
      tokenDeltas: Object.fromEntries(Object.entries(plan.tokenDeltas).map(([key, value]) => [key, value.toString()])),
      tokenBurns: Object.fromEntries(Object.entries(plan.tokenBurns).map(([key, value]) => [key, value.toString()])),
      requests: plan.requests.map(r => ({ key: r.key, digest: r.digest, leaf: r.leaf, branchIndex: r.branchIndex ?? null,
        tokenId: r.tokenId ?? null, positiveDelta: r.positiveDelta?.toString() ?? null })) });
  }
});
