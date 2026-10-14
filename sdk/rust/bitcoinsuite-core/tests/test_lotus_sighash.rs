//! Daemon vectors: see fixtures/sighash_lotus.PROVENANCE.
use bitcoinsuite_core::{
    lotus_sighash_preimage, BitcoinCode, Bytes, Hashed, LotusSighashContext, Script, Sha256d,
    SigHashType, SigHashTypeInputs, SigHashTypeOutputs, SigHashTypeVariant, SignError, TxInput,
    TxOutput, UnhashedTx,
};
use serde_json::Value;

fn recursive_part(part: &Value) -> Vec<u8> {
    match part {
        Value::String(s) => hex::decode(s).unwrap(),
        Value::Array(parts) => {
            let bytes: Vec<u8> = parts.iter().flat_map(recursive_part).collect();
            Sha256d::digest(bytes.into()).as_slice().to_vec()
        }
        _ => panic!("invalid vector part"),
    }
}

fn parse_script(asm: &str) -> Script {
    // This deliberately narrow parser accepts precisely the daemon vector set.
    let mut bytes = Vec::new();
    for token in asm.split_whitespace() {
        match token {
            "3" => bytes.push(0x53),
            "5" => bytes.push(0x55),
            "8" => bytes.push(0x58),
            "OP_DUP" => bytes.push(0x76),
            "OP_HASH160" => bytes.push(0xa9),
            "OP_EQUAL" => bytes.push(0x87),
            "OP_EQUALVERIFY" => bytes.push(0x88),
            "OP_CHECKSIG" => bytes.push(0xac),
            _ if token.starts_with("0x") => bytes.extend(hex::decode(&token[2..]).unwrap()),
            _ => panic!("unknown fixture script token: {token}"),
        }
    }
    Script::from_slice(&bytes)
}

#[test]
fn daemon_script_and_keypath_vectors() {
    let vectors: Value = serde_json::from_str(include_str!("fixtures/sighash_lotus.json")).unwrap();
    let mut count = 0;
    for vector in vectors.as_array().unwrap() {
        let row = vector.as_array().unwrap();
        if row.len() == 1 {
            continue;
        }
        count += 1;
        let raw: String = row[0]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_str().unwrap())
            .collect();
        let tx = UnhashedTx::deser(&mut Bytes::from(hex::decode(raw).unwrap())).unwrap();
        let coins: Vec<TxOutput> = row[1]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| TxOutput {
                value: v[0].as_i64().unwrap(),
                script: parse_script(v[1].as_str().unwrap()),
            })
            .collect();
        let kind = row[2].as_str().unwrap();
        let sighash = SigHashType {
            variant: SigHashTypeVariant::Lotus,
            input_type: if kind.contains("ANYONECANPAY") {
                SigHashTypeInputs::AnyoneCanPay
            } else {
                SigHashTypeInputs::Fixed
            },
            output_type: if kind.starts_with("ALL") {
                SigHashTypeOutputs::All
            } else if kind.starts_with("NONE") {
                SigHashTypeOutputs::None
            } else {
                SigHashTypeOutputs::Single
            },
        };
        let input_idx = row[3].as_u64().unwrap() as usize;
        let replay = row[5].as_str().unwrap().contains("REPLAY_PROTECTION");
        let context = LotusSighashContext::ScriptPath {
            codesep_pos: row[4].as_u64().unwrap() as u32,
            executed_script_hash: Sha256d::digest(coins[input_idx].script.bytecode().clone())
                .as_slice()
                .try_into()
                .unwrap(),
        };
        let actual = lotus_sighash_preimage(&tx, &coins, input_idx, sighash, context, replay);
        let parts = row[6].as_array().unwrap();
        if parts[0] == "failure" {
            assert_eq!(
                actual.unwrap_err(),
                SignError::LotusSingleOutputMissing(input_idx)
            );
            assert_eq!(
                lotus_sighash_preimage(
                    &tx,
                    &coins,
                    input_idx,
                    sighash,
                    LotusSighashContext::KeyPath,
                    replay
                )
                .unwrap_err(),
                SignError::LotusSingleOutputMissing(input_idx)
            );
            continue;
        }
        let expected: Vec<u8> = parts.iter().flat_map(recursive_part).collect();
        assert_eq!(actual.unwrap().as_ref(), expected, "{}", row[7]);

        // Key path has spend_type=0, and omits codesep and script hash. Derive
        // the expected bytes from the daemon fixture, independently of our API.
        let mut key_input = parts[1].as_array().unwrap().clone();
        key_input[0] = Value::String("00".into());
        let mut key_expected = recursive_part(&parts[0]);
        key_expected.extend(recursive_part(&Value::Array(key_input)));
        key_expected.extend(parts[4..].iter().flat_map(recursive_part));
        let key_actual = lotus_sighash_preimage(
            &tx,
            &coins,
            input_idx,
            sighash,
            LotusSighashContext::KeyPath,
            replay,
        )
        .unwrap();
        assert_eq!(key_actual.as_ref(), key_expected, "keypath {}", row[7]);
    }
    assert_eq!(count, 28);
}

#[test]
fn validates_coin_data_and_sighash_mode() {
    let mut tx = UnhashedTx {
        inputs: vec![TxInput::default(); 3],
        outputs: vec![TxOutput::default(); 3],
        ..Default::default()
    };
    let coins = vec![
        TxOutput {
            value: 1,
            script: Script::from_slice(&[0x51])
        };
        3
    ];
    let call = |tx: &UnhashedTx, coins: &[TxOutput], idx, kind| {
        lotus_sighash_preimage(tx, coins, idx, kind, LotusSighashContext::KeyPath, false)
    };
    assert_eq!(
        call(&tx, &coins, 3, SigHashType::ALL_LOTUS).unwrap_err(),
        SignError::LotusInputIndex(3)
    );
    assert_eq!(
        call(&tx, &coins[..2], 0, SigHashType::ALL_LOTUS).unwrap_err(),
        SignError::LotusSpentOutputsCount
    );
    assert_eq!(
        call(&tx, &coins, 0, SigHashType::ALL_BIP143).unwrap_err(),
        SignError::InvalidSigHashType(SigHashType::ALL_BIP143)
    );
    let mut invalid = coins.clone();
    invalid[0].value = -1;
    assert_eq!(
        call(&tx, &invalid, 0, SigHashType::ALL_LOTUS).unwrap_err(),
        SignError::LotusInvalidAmount
    );
    invalid[0].value = i64::MAX;
    assert_eq!(
        call(&tx, &invalid, 0, SigHashType::ALL_LOTUS).unwrap_err(),
        SignError::LotusInvalidAmount
    );
    tx.outputs[0].value = -1;
    assert_eq!(
        call(&tx, &coins, 0, SigHashType::ALL_LOTUS).unwrap_err(),
        SignError::LotusInvalidAmount
    );
}

#[test]
fn odd_merkle_tree_and_coin_commitments() {
    let tx = UnhashedTx {
        inputs: vec![TxInput::default(); 3],
        outputs: vec![TxOutput::default(); 3],
        ..Default::default()
    };
    let coins = vec![
        TxOutput {
            value: 1,
            script: Script::from_slice(&[0x51])
        };
        3
    ];
    let call = |coins: &[TxOutput], kind| {
        lotus_sighash_preimage(&tx, coins, 0, kind, LotusSighashContext::KeyPath, false).unwrap()
    };
    let before = call(&coins, SigHashType::ALL_LOTUS);
    // Explicit independent three-leaf tree: third leaf pairs with zero.
    let leaf = Sha256d::digest(coins[0].ser());
    let pair = |a: &[u8], b: &[u8]| Sha256d::digest([a, b].concat().into());
    let left = pair(leaf.as_slice(), leaf.as_slice());
    let right = pair(leaf.as_slice(), &[0; 32]);
    let root = pair(left.as_slice(), right.as_slice());
    assert_eq!(&before.as_ref()[40..72], root.as_slice());
    assert_eq!(before.as_ref()[124], 3); // input tree height
    assert_eq!(before.as_ref()[157], 3); // output tree height
    let mut changed = coins.clone();
    changed[1].script = Script::from_slice(&[0x52]);
    assert_ne!(before, call(&changed, SigHashType::ALL_LOTUS));
    let acp = SigHashType {
        input_type: SigHashTypeInputs::AnyoneCanPay,
        ..SigHashType::ALL_LOTUS
    };
    assert_eq!(call(&coins, acp), call(&changed, acp));
    changed[0].script = Script::from_slice(&[0x52]);
    assert_ne!(call(&coins, acp), call(&changed, acp));
}
