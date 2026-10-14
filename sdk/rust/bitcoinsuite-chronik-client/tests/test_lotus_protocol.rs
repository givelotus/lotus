use bitcoinsuite_chronik_client::{proto, ChronikClient, ScriptType};
use bitcoinsuite_core::{BitcoinCode, Bytes, Hashed, LotusHeader, Sha256d, Tx};
use prost::Message;

#[test]
fn test_lotus_protocol_fixtures() -> Result<(), Box<dyn std::error::Error>> {
    let fixtures: serde_json::Value = serde_json::from_str(include_str!(
        "../../bitcoinsuite-core/tests/fixtures/lotus_mainnet.json"
    ))?;
    let block = fixtures["blocks"].as_array().unwrap().last().unwrap();
    let transaction = block["transactions"].as_array().unwrap().last().unwrap();
    let header = proto::BlockHeader::decode(include_bytes!("fixtures/header.bin").as_slice())?;
    assert_eq!(header.raw_header.len(), 160);
    let mut raw_header = Bytes::from(header.raw_header);
    assert_eq!(
        LotusHeader::deser(&mut raw_header)?.calc_hash().to_hex_be(),
        block["hash"]
    );
    assert!(raw_header.is_empty());
    let tx = proto::Tx::decode(include_bytes!("fixtures/tx.bin").as_slice())?;
    let raw = proto::RawTx::decode(include_bytes!("fixtures/raw_tx.bin").as_slice())?;
    let mut raw_bytes = Bytes::from(raw.raw_tx);
    let decoded = Tx::deser(&mut raw_bytes)?;
    assert!(raw_bytes.is_empty());
    assert_eq!(decoded.lotus_txid().as_slice(), tx.txid);
    assert_eq!(decoded.lotus_txid().to_hex_be(), transaction["txid"]);
    assert_eq!(decoded.tx_hash().to_hex_be(), transaction["hash"]);
    assert_eq!(decoded.inputs().len(), tx.inputs.len());
    assert_eq!(decoded.outputs().len(), tx.outputs.len());
    for (output, indexed) in decoded.outputs().iter().zip(tx.outputs) {
        assert_eq!(output.value, indexed.sats);
        assert_eq!(output.script.bytecode().as_ref(), indexed.output_script);
    }
    assert_eq!(ScriptType::P2tr.to_string(), "p2tr");
    Ok(())
}

/// Read-only integration; never broadcasts transactions or changes node state.
#[tokio::test]
#[ignore = "requires LOTUS_CHRONIK_URL pointing at a running Lotus V1 node"]
async fn test_live_lotus_chronik() -> Result<(), Box<dyn std::error::Error>> {
    let client = ChronikClient::new(std::env::var("LOTUS_CHRONIK_URL")?)?;
    let info = client.blockchain_info().await?;
    assert!(info.tip_height >= 1_100_000);
    for height in [0, 1, 1_100_000] {
        let header = client.block_header(height).await?;
        assert_eq!(header.raw_header.len(), 160);
        let mut raw = Bytes::from(header.raw_header);
        let decoded_header = LotusHeader::deser(&mut raw)?;
        let block = client.block_by_height(height).await?;
        assert_eq!(
            decoded_header.calc_hash().as_slice(),
            block.block_info.unwrap().hash
        );
        let page = client.block_txs_by_height(height, 0).await?;
        for tx in page.txs {
            let txid = Sha256d::from_slice(&tx.txid)?;
            let mut raw = client.raw_tx(&txid).await?;
            let decoded = Tx::deser(&mut raw)?;
            assert!(raw.is_empty());
            assert_eq!(decoded.lotus_txid().as_slice(), tx.txid);
            assert_eq!(client.tx(&txid).await?.txid, tx.txid);
        }
    }
    let commitment =
        hex::decode("0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798")?;
    // An empty result still verifies the endpoint's commitment type and payload.
    client.script(ScriptType::P2tr, &commitment).utxos().await?;
    Ok(())
}
