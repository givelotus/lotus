# Worked contract examples

Status: semantic examples for review. These programs are pseudocode, not executable bytecode. Candidate byte/commitment/signature semantics now exist in P01–P03; generated signatures and complete execution results still await the reference assembler/evaluator; no illustrative hash is presented as a computed result.

The separately generated [structural fixtures](candidate-smoke-vectors.json) cover framing, hashing, trees and selected integer algorithms. Their [generator and scope](../tools/README.md) are explicit: they do not execute these contracts or verify a signed payment.

## Language conventions used here

The source language below is illustrative. No grammar, compiler or ABI file format is specified anywhere; the listings show how the opcodes of [P03](../decisions/vm-semantics.md) are meant to be used. Assembly uses symbolic opcode names, `<x>` for a push of constant `x`, and stack comments with the top on the right.

- **`contract`** declares a tree of spend methods. Its root appears on outputs as a branch. **`token`** declares a tree of mint methods. Its root is the token ID. Consensus hashes both the same way and does not tell a mint script from a spend script, so the two kinds must be kept in separate trees (P02).
- **Template parameters** are written in angle brackets after the name. Each must be given a constant value at compile time and is written into the script bytes, so it changes the root. A template has no root until every parameter is filled in.
- **`function`** inside a `contract` or `token` is a method: one leaf of the tree. Its parameters arrive as witness arguments. In a `token`, the first parameter of every method is the minted amount, which the node pushes on top of the arguments. A `function` outside both is a free helper that the compiler copies into each caller; it is not a leaf.
- **`merkle_root(X)`** is evaluated at compile time: the compiler builds `X`'s scripts and writes their root into the calling script as a 32-byte constant. `this.root` is the running script's own root, read with BRANCHROOT, since a script cannot contain its own hash.
- **`state { ... }`** declares fields a contract keeps between spends. They are stored by P02's data-leaf convention; example 5 shows the compiled form. In a contract with state, a method not marked **`ends`** must leave a successor. A contract without state never requires one, so its methods carry no marker.
- **`paired output`** refers to the output at the same position as the input the script is running for. Pairing by position stops two inputs from both claiming one output.

## 1. Ordinary payment

```text
contract Payment<owner: PublicKey> {
    function spend(signature: Signature) {
        require(checksig(signature, owner));
    }
}
```

Symbolic assembly: `<owner> CHECKSIG`. Arguments bottom-to-top: `[signature]`; pushing owner leaves signature below the key. CHECKSIG pops key then signature and pushes an int128 Boolean. Selected policy: one branch `Leaf(script)`, `paths=[[0]]`; path index zero, exactly one witness, empty membership proof.

Pre-state: one mature native coin with value 100000 and the payment policy. Transaction: consume it and create native outputs of 60000 and 39000 to two fully specified recipient policies, with no mint input. Expected native fee: 1000, of which the block's coinbase may collect at most half (C16). With valid authorization, the final stack is `[true]`, the input is removed and both outputs are inserted. Changing a committed output changes core identity and the signing message.

Cost report must include parsing, coin resolution, root verification, push/CHECKSIG and accounting; it cannot assume a signature-cache hit.

## 2. Wallet with recovery

```text
contract MyWallet<owner: PublicKey, guardian: PublicKey, delay: Blocks> {

    function normal(signature: Signature) {
        require(checksig(signature, owner));
    }

    function recover(signature: Signature) {
        require(input.age >= delay);          // relative lock
        require(checksig(signature, guardian));
    }
}

policy = { branches: [MyWallet], paths: [[0]] }
```

Both methods are leaves of one tree, so the coin has one branch and one path, and only the method used is ever revealed. `recover` compiles its delay to CHECKSEQUENCEVERIFY, which requires the spending input's relative lock to be at least `delay`. The alternative layout, two branches with `paths=[[0],[1]]`, is also valid; then the whole recovery condition, including its delay, must sit inside the recovery branch, because a path does not inherit a condition from another path.

Expected result: the selected path requires exactly its listed witness. A recovery spend before the delay has elapsed fails the relative lock in consensus, not in the script.

## 3. Token with a rules contract

A token is two trees. The rules are a `contract` whose root every output of the token must carry as a branch. The mint policy is a `token` whose root is the token ID.

```text
contract MyTokenRules {

    function transfer() {
        token = this.coin.token_id;
        for output in tx.outputs {
            if output.token_id == token {
                // The output must carry this root as a branch, on every path.
                require(output.requires_branch(this.root));
            }
        }
    }
}

// A free function, copied into each method that calls it.
function minted_under_rules(token: TokenId) {
    for output in tx.outputs {
        if output.token_id == token {
            require(output.requires_branch(merkle_root(MyTokenRules)));
        }
    }
}

token MyToken<issuer: PublicKey, old_token: TokenId> {

    // The issuer creates new units.
    function issue(amount: Amount, signature: Signature) {
        require(checksig(signature, issuer));
        minted_under_rules(this.root);
    }

    // Anyone replaces old tokens with new ones, one for one.
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
        minted_under_rules(this.root);
    }
}

token_id = merkle_root(MyToken<issuer, old_token>)
```

`transfer` learns its own tree's root from BRANCHROOT:

```text
ENUMERATE_OUTPUTS                 ; loop; pushes the output index j
    DUP OUTPUTTOKENID             ; j, that output's token ID
    INPUTINDEX UTXOTOKENID EQUAL  ; same token as the coin being spent?
    IF
        BRANCHROOT                ; j, the root of the rules tree
        OUTPUTREQUIRESBRANCH      ; true if every path includes that root
        VERIFY
    ELSE
        DROP                      ; another asset: ignore it
    ENDIF
ENDENUMERATE
ONE                               ; the script's result
```

`minted_under_rules` is in a different tree, so the rules root is a compile-time constant there, and BRANCHROOT returns the mint tree's own root, which is the token ID. This is a fragment, copied into `issue` and `upgrade`; each of those also consumes the amount the node pushed and ends with a true value:

```text
ENUMERATE_OUTPUTS
    DUP OUTPUTTOKENID
    BRANCHROOT EQUAL              ; is it this token?
    IF
        <merkle_root(MyTokenRules)>
        OUTPUTREQUIRESBRANCH
        VERIFY
    ELSE
        DROP
    ENDIF
ENDENUMERATE
```

The two mint methods in full. A mint script starts with its witness arguments on the stack and the minted amount on top, pushed by the node; it must consume the amount and finish with one true value. `issue` allows any amount, so it drops it:

```text
; stack: signature amount
DROP                              ; signature
<issuer> CHECKSIGVERIFY           ; (empty)    the issuer signed this transaction
; ... the minted_under_rules loop above ...
ONE
```

`upgrade` takes no witness arguments. It adds up the old token spent, subtracts the old token recreated, and requires the remainder to cover the amount minted. Input flags `01` mark a spend; a mint input has no coin to read:

```text
; stack: amount
<0>                                       ; amount burned
ENUMERATE_INPUTS                          ; amount burned i
    DUP INPUTFLAGS ONE NUMEQUAL           ; amount burned i isSpend?
    IF
        DUP UTXOTOKENID <old_token> EQUAL ; amount burned i isOldToken?
        IF   UTXOVALUE ADD                ; amount burned'
        ELSE DROP
        ENDIF
    ELSE
        DROP
    ENDIF
ENDENUMERATE
ENUMERATE_OUTPUTS                         ; amount burned j
    DUP OUTPUTTOKENID <old_token> EQUAL
    IF   OUTPUTVALUE SUB                  ; amount burned'
    ELSE DROP
    ENDIF
ENDENUMERATE
SWAP GREATERTHANOREQUAL VERIFY            ; burned >= amount
; ... the minted_under_rules loop above ...
ONE
```

Why two trees: if `upgrade` sat in the same tree as `transfer`, a holder could satisfy the rules branch by revealing `upgrade` with made-up arguments and move units out from under the rules.

The presence check is deliberate. A holder adds a wallet branch of their own beside the rules, so the rules require only that they remain on every path. A typical holder policy is `branches=[MyWallet, MyTokenRules]`, `paths=[[0,1]]`.

Scenario: a mint input authorizes a positive delta of 1000 units into a recipient policy carrying the rules branch; native inputs separately cover fees and the token output burn (C14a). A later transaction consuming 1000 units and producing 700 + 250 burns 50 units and has no mint input. Every consumed token coin executes every branch on its selected path, so `transfer` runs on each. A mint may appear at most once per token in a transaction, and `upgrade` reads coin fields only at inputs whose flags mark a spend, since a mint input resolves no coin.

Key rotation: `issuer` is part of the token ID. An issuer who needs to rotate keys makes the template parameter a cold key that signs certificates for working keys, or identifies an authority coin that every mint must spend and recreate. A certificate cannot expire (C22a).

## 4. Limit order

```text
// pay_to: the maker's own script tree.  price: XPI per unit.
contract LimitOrder<pay_to: Root, price: Amount> {

    // Anyone may take the order by paying the maker.
    function fill() {
        paired output payment {
            token_id == native;
            value    >= this.coin.value * price;
            // Spendable by the maker's tree alone, and never without it.
            exclusive_branch == pay_to;
        }
    }
}

// The order coin. Either path spends it.
policy = {
    branches: [LimitOrder<root of MakerWallet, 1042>, MakerWallet],
    paths:    [[0],          // anyone, by filling the order
               [1]],         // the maker, to withdraw it
}
```

The order coin holds the tokens for sale, so `this.coin.value` is the number of units. The order lasts until it is filled or the maker spends it through the second path. Both spend the coin, so nothing has to expire. If the token has a rules contract, its branch is added to both paths.

`exclusive_branch` compiles to `INPUTINDEX <pay_to> OUTPUTEXCLUSIVEBRANCH`. It is true when the payment output has a path that is `pay_to` alone and every other path includes `pay_to`. A presence check would not do here: a taker could add a branch of their own to the payment and leave the maker unable to spend it without them.

The terms are template parameters, so each order has its own root and an order coin is not recognizable by scanning the chain. The maker announces the coin and its terms; anyone can rebuild the script from them and confirm its root is a branch of that coin.

Pairing: with two order coins from one maker at inputs 0 and 1, each requires its own payment at outputs 0 and 1. Without pairing both could be satisfied by one payment.

## 5. Contract state

Outputs have no state field. A contract with `state` is laid out as one data leaf beside the subtree of its methods (P02):

```text
            root
           /    \
  data leaf      M     (root of the methods subtree; never changes)
```

```text
contract Counter<owner: PublicKey> {

    state {
        n: Amount,
    }

    // Assigns a field, so the successor must hold the new value.
    function increment() {
        n = n + 1;
    }

    // Ends the contract. No successor is required.
    function close(signature: Signature) ends {
        require(checksig(signature, owner));
    }
}
```

The wallet supplies the current value and `M` as two hidden leading arguments. `increment`:

```text
; witness args: n (a 16-byte number), M (32 bytes)

; 1. Check the state the wallet supplied.
OVER <10> SWAP CAT <6a> CAT          ; n M ds    ds = data script: push n, RETURN
LEAFHASH                             ; n M D     D  = data leaf holding n
OVER NODEHASH                        ; n M R     R  = Node(D, M)
BRANCHROOT EQUALVERIFY               ; n M       n and M are genuine

; 2. Compute the new state.
SWAP 1ADD                            ; M n'      n' = n + 1

; 3. Compute the root the successor must have.
<10> SWAP CAT <6a> CAT LEAFHASH      ; M D'
NODEHASH                             ; R'        R' = Node(D', M)

; 4. Require it on the output at this input's position.
INPUTINDEX SWAP                      ; i R'
OUTPUTEXCLUSIVEBRANCH                ; spendable with R' alone, never without it
```

A method's membership proof ends with the data leaf's hash, so the wallet rebuilds the proof from the current values on every spend. The data script ends in RETURN so that it can never be run as a method. Numbers in state are kept at the VM's 16-byte width, so no conversion is needed.

These checks cover every step but not the start: no script runs when a coin is created, so anyone can make a coin whose root is a `Counter` holding any `n`. Where the history matters, a mint script requires the first coin to carry the contract's root for the starting values, and the contract's methods require the token to move to the successor.

Scope of the exclusive check. OUTPUTEXCLUSIVEBRANCH names one root, so it applies to an output that needs no other mandatory branch: a contract's own successor, or a payment in XPI or in a token without a rules contract. That covers the uses here, where a method pays out a different asset from the one it guards. It cannot be applied to an output that itself holds a token with a rules contract, because the rules require their root on every path of that output.

### Merging two coins

By default two coins of one contract cannot become one: each demands a successor at its own position. A merge is a method the author writes.

```text
function merge(other: input Counter) {
    n = n + other.n;
}
```

Both coins are spent, so both run a script. The compiler generates two from the one method: `merge` for the coin that survives and `absorbed` for the one that does not. Neither can see which method the other ran, so each makes its own checks, and positions do the rest: the survivor is at input `i`, the absorbed coin at input `i+1`, and the merged coin is output `i`, which must be the last output.

A transaction merging coin A (`n = 5`) and coin B (`n = 7`), with an XPI input for the fee:

```text
inputs                          outputs
0: XPI coin (fee)               0: XPI change
1: Counter A, n = 5   merge     1: Counter, n = 12
2: Counter B, n = 7   absorbed
```

A runs `merge` with arguments `5`, `M`, `7`:

1. Its own state is genuine: `Node(Leaf(data 5), M)` equals BRANCHROOT.
2. The other coin is a Counter holding 7: `Node(Leaf(data 7), M)` is on every path of the coin at input 2 (UTXOREQUIRESBRANCH). The same `M` serves, because it is the same contract.
3. The transaction has exactly 2 outputs, its own position plus one. There is then no output at position 2, so B cannot have continued as a separate coin: every continuing method of B demands a successor there.
4. Output 1 carries `Node(Leaf(data 12), M)` exclusively.

B runs `absorbed` with arguments `7`, `M`, `5`:

1. Its own state is genuine.
2. The coin at input 1 is a Counter holding 5.
3. Output 1, the position before its own, carries `Node(Leaf(data 12), M)` exclusively.

What each check prevents:

- **Without A's step 3**, B could run `increment` instead and continue at output 2 with `n = 8`, while A still counted B's 7. B's value would exist twice.
- **Without B's checks**, anyone could destroy B by calling `absorbed` in a transaction that merges it into nothing.
- **Mismatched methods fail.** If A ran `increment` it would require output 1 to hold `n = 6` while B requires `n = 12`; no output satisfies both.
- **A third coin cannot join.** A coin C at input 3 running `absorbed` would look for its survivor at input 2 and the merged coin at output 2, which does not exist.

Other outputs, such as change, sit at positions before the survivor's, opposite inputs that make no demand on them.

Two limits. The merge is only as trustworthy as the coins fed to it: anyone can create a coin whose root is a `Counter` with any `n`, so a contract that must not accept forged state has to check that the other coin carries its token, as described above. And a quantity that must never be duplicated is better held as a token amount, which consensus conserves, than as state.

One shape is not defined: a method that both continues the contract and pays someone. Both want the output at the input's position.

## 6. Cost of loops

A script that scans I inputs against O outputs does I×O body work per invocation. Repeating it on K inputs charges K×I×O, plus other costs. Execution is independent: no input is excused because another coin carries the same branch root. Static bounds ignore early exit and cache reuse (P05). The token rules above scan outputs once per token input, so a transaction moving K coins of one token to O outputs charges K×O for the rules.

## 7. Shared data

There are no read-only inputs. A transaction that needs data held in a shared coin, such as an oracle value, spends that coin and recreates it in the same transaction; the coin's own policy decides who may do so and under what conditions. Two transactions that use the same shared coin conflict, so they must be chained one after the other or the data must be supplied another way, such as a signed record passed as a witness argument. A signed record cannot carry an expiry (C22a).

## Completion contract

Deliver these examples in order. Each becomes executable only when it includes source, assembly, bytecode, canonical arguments, initial coin records, complete transaction bytes, commitments, signing data, final stack, static cost and post-state/undo result, produced by pinned tools. Pair each with focused local conformance cases for its requirements. The schema for those records and the outstanding evidence are in [validation](../validation.md).
