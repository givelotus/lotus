import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { schnorr } from "@noble/curves/secp256k1";
import { hex, unhex, compilePayment, PAYMENT_SOURCE } from "../dist/compiler.js";
import {
  DEFAULT_COMPILER_EDITION,
  DEFAULT_OPTIMIZER_VERSION,
  OPTIMIZER_PASSES_BY_VERSION,
  SPEND_BUNDLE_SCHEMA,
  SUPPORTED_COMPILER_EDITIONS,
  SUPPORTED_OPTIMIZER_VERSIONS,
  assertSpendBundleReproducibility,
  compileContract,
  compileGenericContract,
  createSpendBundle,
  verifyBranchRootReproducibility,
  verifySpendBundleReproducibility,
} from "../dist/generic.js";
import { optimizeInstructions } from "../dist/optimizer.js";
import {
  PackageError,
  compilePackage,
  generateLock,
  parseManifest,
  updateLock,
} from "../dist/packages.js";
import {
  DEFAULT_DUST_LIMIT_ATOMS,
  DEFAULT_FEERATE_PER_KCU,
  DEFAULT_SDK_PADDING_BPS,
  DEFAULT_TX_KNEE_SHIFT,
  estimateTransactionCuAndFee,
  preparePayment,
  simulateFeeAndAdjustChange,
} from "../dist/runtime.js";
import {
  finalizeTransactionCall,
  prepareTransactionCall,
} from "../dist/transaction-runtime.js";

const secret1 = unhex("00".repeat(31) + "01");
const secret2 = unhex("00".repeat(31) + "02");
const owner1 = hex(schnorr.getPublicKey(secret1));
const owner2 = hex(schnorr.getPublicKey(secret2));

const VAULT_SOURCE = `
function addBonus(base: Amount, bonus: Int): Amount {
  return base + bonus;
}

contract Vault<owner: PublicKey, backup: PublicKey, floor: Amount> {
  function spend(sig: Signature, amount: Amount) {
    require(addBonus(amount, 10) >= floor && checksig(sig, owner));
  }
  function recover(sig: Signature) {
    require(checksig(sig, backup));
  }
}
`;

const VAULT_BINDINGS = {
  Vault: {
    owner: owner1,
    backup: owner2,
    floor: 500n,
  },
};

test("immutable compiler editions and versioned optimizer pass table", () => {
  assert.deepEqual(SUPPORTED_COMPILER_EDITIONS, ["2026.1"]);
  assert.equal(DEFAULT_COMPILER_EDITION, "2026.1");
  assert.deepEqual(SUPPORTED_OPTIMIZER_VERSIONS, ["none", "v1"]);
  assert.equal(DEFAULT_OPTIMIZER_VERSION, "v1");
  assert.equal(typeof OPTIMIZER_PASSES_BY_VERSION.none, "function");
  assert.equal(typeof OPTIMIZER_PASSES_BY_VERSION.v1, "function");

  const defaultArtifact = compileContract(VAULT_SOURCE, {
    contract: "Vault",
    bindings: VAULT_BINDINGS,
  });
  const explicitV1Artifact = compileGenericContract(VAULT_SOURCE, {
    contract: "Vault",
    bindings: VAULT_BINDINGS,
    edition: "2026.1",
    optimizerVersion: "v1",
  });
  assert.deepEqual(explicitV1Artifact, defaultArtifact);

  const unoptimizedLegacy = compileContract(VAULT_SOURCE, {
    contract: "Vault",
    bindings: VAULT_BINDINGS,
    optimize: false,
  });
  const explicitNoneArtifact = compileGenericContract(VAULT_SOURCE, {
    contract: "Vault",
    bindings: VAULT_BINDINGS,
    edition: "2026.1",
    optimizerVersion: "none",
  });
  assert.deepEqual(explicitNoneArtifact, unoptimizedLegacy);
  assert.notEqual(explicitNoneArtifact.policy.root, explicitV1Artifact.policy.root);
  assert.notEqual(
    explicitNoneArtifact.methods[0].scriptHex,
    explicitV1Artifact.methods[0].scriptHex,
  );

  // Unknown edition or optimizerVersion must fail deterministically
  assert.throws(
    () =>
      compileContract(VAULT_SOURCE, {
        contract: "Vault",
        bindings: VAULT_BINDINGS,
        edition: "2099.1",
      }),
    /E0133.*unsupported compiler edition/,
  );
  assert.throws(
    () =>
      compileContract(VAULT_SOURCE, {
        contract: "Vault",
        bindings: VAULT_BINDINGS,
        optimizerVersion: "v99",
      }),
    /E0134.*unsupported optimizerVersion/,
  );
  assert.throws(
    () =>
      compileContract(VAULT_SOURCE, {
        contract: "Vault",
        bindings: VAULT_BINDINGS,
        optimize: false,
        optimizerVersion: "v1",
      }),
    /E0134.*conflicting compile options/,
  );
  assert.throws(
    () =>
      compileContract(VAULT_SOURCE, {
        contract: "Vault",
        bindings: VAULT_BINDINGS,
        optimize: true,
        optimizerVersion: "none",
      }),
    /E0134.*conflicting compile options/,
  );
  assert.throws(
    () => optimizeInstructions([], 0, "v99"),
    /unsupported optimizerVersion/,
  );
});

test("SpendBundle source & optimizer edition pinning reproduces exact BranchRoot and detects tampering", () => {
  const v1Artifact = compileContract(
    VAULT_SOURCE,
    {
      contract: "Vault",
      bindings: VAULT_BINDINGS,
      edition: "2026.1",
      optimizerVersion: "v1",
    },
    "src/vault.lotus",
  );
  const noneArtifact = compileContract(
    VAULT_SOURCE,
    {
      contract: "Vault",
      bindings: VAULT_BINDINGS,
      edition: "2026.1",
      optimizerVersion: "none",
    },
    "src/vault.lotus",
  );

  const bundleV1 = createSpendBundle(
    v1Artifact,
    { "src/vault.lotus": VAULT_SOURCE },
    { edition: "2026.1", optimizerVersion: "v1", entryFile: "src/vault.lotus" },
  );
  assert.equal(bundleV1.schema, SPEND_BUNDLE_SCHEMA);
  assert.equal(bundleV1.edition, "2026.1");
  assert.equal(bundleV1.optimizerVersion, "v1");
  assert.equal(bundleV1.expectedRoot, v1Artifact.policy.root);
  assert.equal(bundleV1.sources.length, 1);
  assert.equal(bundleV1.sources[0].path, "src/vault.lotus");

  const verifiedV1 = verifyBranchRootReproducibility(bundleV1);
  assert.equal(verifiedV1.ok, true);
  assert.equal(verifiedV1.matchesRoot, true);
  assert.equal(verifiedV1.matchesMethods, true);
  assert.equal(verifiedV1.recomputedRoot, v1Artifact.policy.root);
  assert.deepEqual(assertSpendBundleReproducibility(bundleV1), v1Artifact);

  const bundleNone = createSpendBundle(noneArtifact, VAULT_SOURCE, {
    edition: "2026.1",
    optimizerVersion: "none",
    entryFile: "src/vault.lotus",
  });
  const verifiedNone = verifySpendBundleReproducibility(bundleNone);
  assert.equal(verifiedNone.ok, true);
  assert.equal(verifiedNone.recomputedRoot, noneArtifact.policy.root);

  // Tampering with source content is caught by BLAKE3 file digest verification
  const tamperedSource = {
    ...bundleV1,
    sources: [{ ...bundleV1.sources[0], content: VAULT_SOURCE + "\n// comment\n" }],
  };
  const badSourceRes = verifyBranchRootReproducibility(tamperedSource);
  assert.equal(badSourceRes.ok, false);
  assert.match(badSourceRes.error ?? "", /source digest mismatch/);

  // Changing optimizerVersion without recomputing expectedRoot fails bundle digest or BranchRoot match
  const wrongOptimizerBundle = createSpendBundle(v1Artifact, VAULT_SOURCE, {
    edition: "2026.1",
    optimizerVersion: "none",
    entryFile: "src/vault.lotus",
  });
  const wrongOptRes = verifyBranchRootReproducibility(wrongOptimizerBundle);
  assert.equal(wrongOptRes.ok, false);
  assert.equal(wrongOptRes.matchesRoot, false);
  assert.match(wrongOptRes.error ?? "", /recomputed BranchRoot .* does not match expected/);
});

test("lotus.toml and lotus.lock pin compiler edition and optimizer version for packages", async () => {
  const dir = mkdtempSync(join(tmpdir(), "lotus-pkg-edition-"));
  try {
    mkdirSync(join(dir, "src"), { recursive: true });
    const manifestV1 = [
      "[package]",
      'name = "pinned_vault"',
      'version = "0.1.0"',
      'kind = "contract"',
      'source = "src"',
      'entry = "main"',
      'modules = ["main"]',
      'edition = "2026.1"',
      'optimizer = "v1"',
      "",
    ].join("\n");
    writeFileSync(join(dir, "lotus.toml"), manifestV1);
    writeFileSync(join(dir, "src", "main.lotus"), VAULT_SOURCE);

    const parsed = parseManifest(manifestV1, "lotus.toml");
    assert.equal(parsed.edition, "2026.1");
    assert.equal(parsed.optimizer, "v1");

    const lockText = updateLock(dir);
    const lockJson = JSON.parse(lockText);
    assert.equal(lockJson.root.edition, "2026.1");
    assert.equal(lockJson.root.optimizer, "v1");

    const buildV1 = await compilePackage(dir, {
      contract: "Vault",
      bindings: VAULT_BINDINGS,
    });
    assert.equal(buildV1.artifact.build?.compiler.edition, "2026.1");
    assert.equal(buildV1.artifact.build?.compiler.optimizerVersion, "v1");
    assert.equal(buildV1.artifact.build?.compiler.profile, "optimized");

    // Conflicting compile option vs manifest optimizer is rejected
    await assert.rejects(
      () =>
        compilePackage(dir, {
          contract: "Vault",
          bindings: VAULT_BINDINGS,
          optimizerVersion: "none",
        }),
      (err) => err instanceof PackageError && err.code === "manifest",
    );

    // Changing manifest optimizer to "none" without updating lotus.lock fails with lock-mismatch
    const manifestNone = manifestV1.replace('optimizer = "v1"', 'optimizer = "none"');
    writeFileSync(join(dir, "lotus.toml"), manifestNone);
    await assert.rejects(
      () =>
        compilePackage(dir, {
          contract: "Vault",
          bindings: VAULT_BINDINGS,
        }),
      (err) => err instanceof PackageError && err.code === "lock-mismatch",
    );

    // Updating lotus.lock with optimizer = "none" compiles unoptimized and records optimizerVersion: "none"
    updateLock(dir);
    const buildNone = await compilePackage(dir, {
      contract: "Vault",
      bindings: VAULT_BINDINGS,
    });
    assert.equal(buildNone.artifact.build?.compiler.edition, "2026.1");
    assert.equal(buildNone.artifact.build?.compiler.optimizerVersion, "none");
    assert.equal(buildNone.artifact.build?.compiler.profile, "unoptimized");
    assert.notEqual(buildNone.artifact.policy.root, buildV1.artifact.policy.root);

    // Also support [build] section in lotus.toml
    const manifestBuildTable = [
      "[package]",
      'name = "pinned_vault"',
      'version = "0.1.0"',
      'kind = "contract"',
      'source = "src"',
      'entry = "main"',
      'modules = ["main"]',
      "",
      "[build]",
      'edition = "2026.1"',
      'optimizer_version = "v1"',
      "",
    ].join("\n");
    const parsedBuild = parseManifest(manifestBuildTable, "lotus.toml");
    assert.equal(parsedBuild.edition, "2026.1");
    assert.equal(parsedBuild.optimizer, "v1");

    // Existing diamond fixture lockfile remains 100% byte-identical when edition/optimizer are omitted
    const diamondDir = join(process.cwd(), "examples/packages/diamond");
    assert.equal(
      generateLock(diamondDir),
      readFileSync(join(diamondDir, "lotus.lock"), "utf8"),
    );
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("SDK deterministic CU fee simulator & auto-change output adjuster", () => {
  assert.equal(DEFAULT_FEERATE_PER_KCU, 1000n);
  assert.equal(DEFAULT_SDK_PADDING_BPS, 500);
  assert.equal(DEFAULT_TX_KNEE_SHIFT, 17n);
  assert.equal(DEFAULT_DUST_LIMIT_ATOMS, 546n);

  const wallet = compileContract(
    "contract Wallet<owner: PublicKey> { function spend(signature: Signature) { require(checksig(signature, owner)); } }",
    { contract: "Wallet", bindings: { Wallet: { owner: owner1 } } },
  );
  const issuer = compileContract(
    "token Issuer<owner: PublicKey> { function issue(amount: Amount, signature: Signature) { require(amount > 0); require(checksig(signature, owner)); } }",
    { contract: "Issuer", bindings: { Issuer: { owner: owner2 } } },
  );
  const walletRoot = wallet.policy.root;
  const tokenId = issuer.policy.root;

  const nativeOut = (value) => ({
    flags: 0,
    value,
    branches: [walletRoot],
    paths: [[0]],
  });
  const tokenOut = (value) => ({
    flags: 1,
    value,
    tokenId,
    branches: [walletRoot],
    paths: [[0]],
  });

  // 1. Standard native payment with auto-change adjustment and simulated VM executedCu
  const baseIntent = {
    profile: "P01-P02-P03-candidate-2026-10-14",
    chainId: "44".repeat(32),
    dustLimitAtoms: 546n,
    inputs: [
      {
        kind: "spend",
        prevTxid: "11".repeat(32),
        prevIndex: 0,
        sequence: 0xffffffff,
        coin: nativeOut(20_000n),
        pathIndex: 0,
        witnesses: [{ artifact: wallet, methodName: "spend", args: { signature: null } }],
      },
    ],
    outputs: [
      nativeOut(12_000n), // recipient output
      nativeOut(0n),      // change output placeholder (auto-adjusted)
    ],
  };

  const sim = simulateFeeAndAdjustChange(baseIntent, {
    executedCu: 500n,
    feeratePerKCu: 1000n,
    sdkPaddingBps: 500, // +5%
  });
  assert.equal(sim.changeOutputIndex, 1);
  assert.equal(sim.totalNativeInputs, 20_000n);
  assert.equal(sim.nonChangeNativeOutputs, 12_000n);
  assert.equal(sim.estimate.vmCu, 500n);
  assert.equal(sim.estimate.sdkPaddingBps, 500);
  assert.equal(
    sim.estimate.paddingCu,
    (sim.estimate.effectiveCu * 500n + 9999n) / 10000n,
  );
  assert.equal(
    sim.estimate.paddedCu,
    sim.estimate.effectiveCu + sim.estimate.paddingCu,
  );
  assert.equal(sim.requiredFeeAtoms, sim.estimate.paddedCu);
  assert.equal(sim.changeValue, 20_000n - 12_000n - sim.requiredFeeAtoms);
  assert.equal(sim.adjustedOutputs[1].value, sim.changeValue);

  // Verify adjustedIntent passes prepareTransactionCall and finalizeTransactionCall with exact projected bytes
  const plan = prepareTransactionCall(sim.adjustedIntent);
  assert.equal(plan.projectedFullBytes, sim.estimate.wireBytes);
  assert.equal(plan.feeAtoms, sim.requiredFeeAtoms);
  const sigs = Object.fromEntries(
    plan.requests.map((r) => [
      r.key,
      schnorr.sign(unhex(r.digest), secret1, new Uint8Array(32)),
    ]),
  );
  const finalTx = finalizeTransactionCall(plan, sigs);
  assert.equal(finalTx.wire.length, sim.estimate.wireBytes);

  // 2. Token-bearing transaction where C14a token-output burn floor (2 * dustLimit * tokenOutputs) dominates
  const tokenMintIntent = {
    profile: "P01-P02-P03-candidate-2026-10-14",
    chainId: "44".repeat(32),
    dustLimitAtoms: 1_000n,
    inputs: [
      {
        kind: "spend",
        prevTxid: "22".repeat(32),
        prevIndex: 0,
        sequence: 0xffffffff,
        coin: nativeOut(50_000n),
        pathIndex: 0,
        witnesses: [{ artifact: wallet, methodName: "spend", args: { signature: null } }],
      },
      {
        kind: "mint",
        artifact: issuer,
        methodName: "issue",
        args: { signature: null },
      },
    ],
    outputs: [
      tokenOut(500n),
      tokenOut(500n),
      nativeOut(10_000n), // recipient native output
      nativeOut(0n),      // native change output
    ],
  };
  const tokenSim = simulateFeeAndAdjustChange(tokenMintIntent);
  assert.equal(tokenSim.estimate.tokenOutputCount, 2);
  assert.equal(tokenSim.estimate.tokenBurnFloorAtoms, 4_000n); // 2 * 1000 * 2
  assert.equal(tokenSim.requiredFeeAtoms, 4_000n);
  assert.equal(tokenSim.changeOutputIndex, 3);
  assert.equal(tokenSim.changeValue, 50_000n - 10_000n - 4_000n);
  const tokenPlan = prepareTransactionCall(tokenSim.adjustedIntent);
  assert.equal(tokenPlan.feeAtoms, 4_000n);
  assert.equal(tokenPlan.minimumFeeAtoms, 4_000n);

  // 3. PaymentArtifact + PaymentContext compatibility
  const paymentArt = compilePayment(PAYMENT_SOURCE, owner1);
  const paymentCtx = {
    profile: "payment-fixture-p01-v1",
    chainId: "44".repeat(32),
    prevTxid: "33".repeat(32),
    prevIndex: 0,
    sequence: 0xffffffff,
    coin: { value: 10_000n, branches: [paymentArt.policy.leaf], paths: [[0]] },
    outputs: [
      { value: 6_000n, branches: [paymentArt.policy.leaf], paths: [[0]] },
      { value: 0n, branches: [paymentArt.policy.leaf], paths: [[0]] },
    ],
  };
  const paySim = simulateFeeAndAdjustChange({ artifact: paymentArt, context: paymentCtx });
  const payPlan = preparePayment(paymentArt, paySim.adjustedContext);
  assert.equal(payPlan.signingIntent.feeAtoms, paySim.requiredFeeAtoms);

  // 4. Rejects when native inputs are insufficient
  assert.throws(
    () =>
      simulateFeeAndAdjustChange({
        ...baseIntent,
        outputs: [nativeOut(19_800n), nativeOut(0n)],
      }),
    /insufficient native input funds/,
  );

  // 5. Rejects when adjusted change output falls below dustLimitAtoms
  const exactRemainingForDust = 20_000n - sim.requiredFeeAtoms - 200n; // leaves 200n < 546n dustLimit
  assert.throws(
    () =>
      simulateFeeAndAdjustChange({
        ...baseIntent,
        outputs: [nativeOut(exactRemainingForDust), nativeOut(0n)],
      }),
    /below dust limit/,
  );

  // 6. Rejects when designated change output is a token output
  assert.throws(
    () =>
      simulateFeeAndAdjustChange(tokenMintIntent, {
        changeOutputIndex: 0,
      }),
    /designated change output must be a native spendable output/,
  );
});
