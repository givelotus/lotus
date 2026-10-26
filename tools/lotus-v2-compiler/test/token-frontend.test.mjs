import test from 'node:test';
import assert from 'node:assert/strict';
import { compileContract } from '../dist/generic.js';

const source = `
contract Rules {
  function transfer() {
    for output in tx.outputs {
      if output.token_id == this.coin.token_id {
        require(output.requires_branch(this.root));
      }
    }
  }
}
token Token<issuer: PublicKey, old_token: TokenId> {
  function issue(amount: Amount, signature: Signature) {
    require(checksig(signature, issuer));
    for output in tx.outputs {
      if output.token_id == this.root {
        require(output.requires_branch(contract_root(Rules)));
      }
    }
  }
  function upgrade(amount: Amount) {
    burned = 0;
    for input in tx.inputs {
      if input.is_spend && input.coin.token_id == old_token {
        burned += input.coin.value;
      }
    }
    for output in tx.outputs {
      if output.token_id == old_token {
        burned -= output.value;
      }
    }
    require(burned >= amount);
    for output in tx.outputs {
      if output.token_id == this.root {
        require(output.requires_branch(contract_root(Rules)));
      }
    }
  }
}`;
const bindings = { Token: { issuer: '79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798', old_token: '11'.repeat(32) } };

test('contract rules and token mint are separate typed trees with node supplied amount', () => {
  const rules = compileContract(source, { contract: 'Rules', bindings });
  const token = compileContract(source, { contract: 'Token', bindings });
  assert.equal(rules.kind, 'contract');
  assert.equal(token.kind, 'token');
  assert.notEqual(rules.policy.root, token.policy.root);
  assert.equal(rules.methods[0].invocation, 'spend');
  assert.equal(token.methods[0].invocation, 'mint');
  assert.equal(token.methods[0].mintAmountParam, 'amount');
  assert.deepEqual(token.methods[0].args, [{ name: 'signature', type: 'Signature' }]);
  assert.deepEqual(token.methods[1].args, []);
  const transfer = rules.methods[0].sourceMap.map(x => x.op);
  assert.ok(transfer.includes('ENUMERATE_OUTPUTS'));
  assert.ok(transfer.includes('UTXOTOKENID'));
  assert.ok(transfer.includes('OUTPUTREQUIRESBRANCH'));
  const upgrade = token.methods[1].sourceMap.map(x => x.op);
  assert.ok(upgrade.includes('ENUMERATE_INPUTS'));
  assert.ok(upgrade.includes('INPUTFLAGS'));
  assert.ok(upgrade.includes('UTXOVALUE'));
  assert.ok(upgrade.includes('GREATERTHANOREQUAL'));
  assert.ok(upgrade.includes('OUTPUTREQUIRESBRANCH'));
  assert.ok(upgrade.indexOf('INPUTFLAGS') < upgrade.indexOf('IF'));
  assert.ok(upgrade.indexOf('IF') < upgrade.indexOf('UTXOTOKENID'));
});

test('token amount comes first in source and has Amount type', () => {
  assert.throws(() => compileContract('token Bad { function issue(signature: Signature) { require(true); } }', { contract: 'Bad', bindings: {} }), /first parameter must be Amount/);
  assert.throws(() => compileContract('token Bad { function issue(amount: Int) { require(true); } }', { contract: 'Bad', bindings: {} }), /first parameter must be Amount/);
});

test('nested loop depth and record-index assignments reject', () => {
  const deep = 'contract Bad { function spend() { for a in tx.outputs { for b in tx.outputs { for c in tx.outputs { require(true); } } } } }';
  assert.throws(() => compileContract(deep, { contract:'Bad', bindings:{} }), /loop nesting exceeds two/);
  const assignment = 'contract Bad { function spend() { for output in tx.outputs { output = 1; } } }';
  assert.throws(() => compileContract(assignment, { contract:'Bad', bindings:{} }), /cannot assign output/);
});
