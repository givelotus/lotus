//! Public-chain fixtures captured from lotusd RPC on 2026-10-14.
use bitcoinsuite_core::{
    ecc::PubKey, lotus_txid, BitcoinCode, Bytes, Hashed, LotusAddress, LotusBlock, LotusHeader,
    LotusMetadataField, Net, Script, Sha256d, Tx, LOTUS_PREFIX,
};
use serde_json::Value;

#[test]
fn test_mainnet_rpc_parity() -> Result<(), Box<dyn std::error::Error>> {
    let fixtures: Value = serde_json::from_str(include_str!("fixtures/lotus_mainnet.json"))?;
    let mut non_coinbase = 0;
    for fixture in fixtures["blocks"].as_array().unwrap() {
        let raw = Bytes::from(hex::decode(fixture["raw"].as_str().unwrap())?);
        let mut remaining = raw.clone();
        let mut block = LotusBlock::deser(&mut remaining)?;
        assert!(remaining.is_empty());
        assert_eq!(block.ser(), raw);
        assert_eq!(block.header.ser().len(), 160);
        assert_eq!(block.header.calc_hash().to_hex_be(), fixture["hash"]);
        assert_eq!(
            block.header.height as i64,
            fixture["height"].as_i64().unwrap()
        );
        let header = block.header.clone();
        block.update_merkle_root();
        block.update_extended_metadata_hash();
        block.update_size();
        assert_eq!(block.header, header);
        for (idx, (tx, tx_fixture)) in block
            .txs
            .iter()
            .zip(fixture["transactions"].as_array().unwrap())
            .enumerate()
        {
            assert_eq!(tx.raw().hex(), tx_fixture["raw"]);
            assert_eq!(tx.tx_hash().to_hex_be(), tx_fixture["hash"]);
            assert_eq!(tx.lotus_txid().to_hex_be(), tx_fixture["txid"]);
            assert_ne!(tx.tx_hash(), &tx.lotus_txid());
            let mut changed = tx.unhashed_tx().clone();
            changed.inputs[0].script = Script::from_slice(&[0x51]);
            assert_eq!(lotus_txid(&changed), tx.lotus_txid());
            assert_ne!(changed.hashed().tx_hash(), tx.tx_hash());
            non_coinbase += usize::from(idx != 0);
        }
    }
    assert!(non_coinbase > 0);
    Ok(())
}

#[test]
fn test_metadata_roundtrip() -> Result<(), Box<dyn std::error::Error>> {
    let mut block = LotusBlock {
        header: LotusHeader::default(),
        metadata: vec![LotusMetadataField {
            field_id: 0x12345678,
            field_value: vec![0xab, 0xcd],
        }],
        txs: vec![Tx::default()],
    };
    block.update_extended_metadata_hash();
    block.update_size();
    let raw = block.ser();
    assert_eq!(
        &raw[160..169],
        &[1, 0x78, 0x56, 0x34, 0x12, 2, 0xab, 0xcd, 1]
    );
    let mut bytes = raw.clone();
    assert_eq!(LotusBlock::deser(&mut bytes)?.ser(), raw);
    assert!(bytes.is_empty());
    Ok(())
}

#[test]
fn test_mainnet_address_rpc_parity() -> Result<(), Box<dyn std::error::Error>> {
    let fixtures: Value = serde_json::from_str(include_str!("fixtures/lotus_addresses.json"))?;
    for fixture in fixtures.as_array().unwrap() {
        let script = Script::from_hex(fixture["script"].as_str().unwrap())?;
        let address = LotusAddress::from_script(LOTUS_PREFIX, Net::Mainnet, &script)?;
        assert_eq!(address.as_str().parse::<LotusAddress>()?.script(), &script);
        let node_address = fixture["decoded"]["addresses"][0].as_str().unwrap();
        let decoded: LotusAddress = node_address.parse()?;
        if script.bytecode().len() == 25 || script.bytecode().len() == 23 {
            assert_eq!(address.as_str(), node_address);
            assert_eq!(decoded.script(), &script);
        } else {
            let pubkey = PubKey::new_unchecked(script.bytecode()[3..36].try_into()?);
            assert_eq!(
                LotusAddress::from_taproot(LOTUS_PREFIX, Net::Mainnet, &pubkey).as_str(),
                node_address
            );
            assert_eq!(decoded.script(), &Script::p2tr(&pubkey, None));
        }
    }
    // Existing Bitcoin raw-hash behavior remains explicit and unchanged.
    assert_eq!(Tx::default().tx_hash(), &Sha256d::default());
    Ok(())
}

#[test]
fn test_keypath_signing_both_epochs() -> Result<(), Box<dyn std::error::Error>> {
    use bitcoinsuite_core::{
        ecc::Ecc, lotus_sighash_preimage, taproot::tap_tweak_hash, LotusSighashContext,
        P2TRKeyPathSignatory, SigHashType, SignData, SignField, Signatory, TxInput, TxOutput,
        UnhashedTx, UnsignedTx,
    };
    use bitcoinsuite_ecc_secp256k1::EccSecp256k1;
    let ecc = EccSecp256k1::default();
    let key = ecc.seckey_from_array([1; 32])?;
    let internal = ecc.derive_pubkey(&key);
    for merkle_root in [[0; 32], [0x11; 32]] {
        let tweak = tap_tweak_hash(&internal, &merkle_root);
        let commitment = ecc.tweak_pubkey(&internal, &tweak)?;
        let coin = TxOutput {
            value: 100_000,
            script: Script::p2tr(&commitment, Some([0xab; 32])),
        };
        for replay in [false, true] {
            for flags in [0x61, 0x62, 0x63, 0xe1, 0xe2, 0xe3] {
                let sighash_type = SigHashType::from_u32(flags).unwrap();
                let tx = UnhashedTx {
                    version: 2,
                    inputs: vec![TxInput {
                        sign_data: Some(SignData::new(vec![
                            SignField::Value(coin.value),
                            SignField::OutputScript(coin.script.clone()),
                        ])),
                        ..Default::default()
                    }],
                    outputs: vec![TxOutput {
                        value: 90_000,
                        script: Script::from_slice(&[0x51]),
                    }],
                    lock_time: 42,
                };
                let preimage = lotus_sighash_preimage(
                    &tx,
                    std::slice::from_ref(&coin),
                    0,
                    sighash_type,
                    LotusSighashContext::KeyPath,
                    replay,
                )?;
                let digest = Sha256d::digest(preimage).byte_array().clone();
                let mut unsigned = UnsignedTx::new(tx);
                let mut signer = P2TRKeyPathSignatory::new(key.clone(), internal);
                signer.merkle_root = merkle_root;
                signer.replay_protection = replay;
                signer.sig_hash_type = sighash_type;
                signer.sign_input(&ecc, unsigned.input_at(0))?;
                let script = unsigned.tx().inputs[0].script.bytecode();
                assert_eq!(script.len(), 66);
                assert_eq!(script[0], 65);
                assert_eq!(script[65], flags as u8);
                ecc.schnorr_verify(&commitment, digest, &Bytes::from(script[1..65].to_vec()))?;
                let mut wrong_epoch = unsigned.tx().clone();
                wrong_epoch.inputs[0].script = Script::default();
                let other = Sha256d::digest(lotus_sighash_preimage(
                    &wrong_epoch,
                    std::slice::from_ref(&coin),
                    0,
                    sighash_type,
                    LotusSighashContext::KeyPath,
                    !replay,
                )?);
                assert!(ecc
                    .schnorr_verify(
                        &commitment,
                        other.byte_array().clone(),
                        &Bytes::from(script[1..65].to_vec())
                    )
                    .is_err());
            }
        }
    }
    Ok(())
}

#[test]
fn test_keypath_rejects_wrong_coin_commitment() -> Result<(), Box<dyn std::error::Error>> {
    use bitcoinsuite_core::{
        ecc::Ecc, P2TRKeyPathSignatory, SignData, SignField, Signatory, TxInput, TxOutput,
        UnhashedTx, UnsignedTx,
    };
    use bitcoinsuite_ecc_secp256k1::EccSecp256k1;
    let ecc = EccSecp256k1::default();
    let key = ecc.seckey_from_array([1; 32])?;
    let internal = ecc.derive_pubkey(&key);
    let tx = UnhashedTx {
        inputs: vec![TxInput {
            sign_data: Some(SignData::new(vec![
                SignField::Value(10),
                SignField::OutputScript(Script::p2tr(&internal, None)),
            ])),
            ..Default::default()
        }],
        outputs: vec![TxOutput::default()],
        ..Default::default()
    };
    let mut unsigned = UnsignedTx::new(tx);
    let signer = P2TRKeyPathSignatory::new(key, internal);
    assert!(signer.sign_input(&ecc, unsigned.input_at(0)).is_err());
    Ok(())
}

#[test]
fn test_bip143_replay_epoch() -> Result<(), Box<dyn std::error::Error>> {
    use bitcoinsuite_core::{
        SigHashType, SignData, SignField, TxInput, TxOutput, UnhashedTx, UnsignedTx,
    };
    let tx = UnhashedTx {
        inputs: vec![TxInput {
            sign_data: Some(SignData::new(vec![
                SignField::Value(1000),
                SignField::OutputScript(Script::from_slice(&[0x51])),
            ])),
            ..Default::default()
        }],
        outputs: vec![TxOutput::default()],
        ..Default::default()
    };
    let mut unsigned = UnsignedTx::new(tx);
    let input = unsigned.input_at(0);
    let current = input.sighash_preimage(SigHashType::ALL_BIP143, None)?.bytes;
    let replay = input
        .sighash_preimage_with_replay_protection(SigHashType::ALL_BIP143, None, true)?
        .bytes;
    assert_eq!(&current[..current.len() - 4], &replay[..replay.len() - 4]);
    assert_eq!(&current[current.len() - 4..], &[0x41, 0, 0, 0]);
    assert_eq!(&replay[replay.len() - 4..], &[0x41, 0xad, 0xde, 0xff]);
    assert_ne!(Sha256d::digest(current), Sha256d::digest(replay));
    Ok(())
}
