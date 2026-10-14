//! Lotus V1 signature preimages, matching daemon SignatureHashLotus.
//!
//! Spent outputs are complete locking outputs, in transaction input order.
//! They must not be replaced by redeem scripts. Hash bytes use wire order.
use crate::{
    get_merkle_root_and_height, BitcoinCode, Bytes, BytesMut, Hashed, MerkleMode, Sha256d,
    SigHashType, SigHashTypeInputs, SigHashTypeOutputs, SigHashTypeVariant, SignError, TxOutput,
    UnhashedTx,
};

/// Signature execution context. Key-path spends have no script extension.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LotusSighashContext {
    KeyPath,
    /// For Taproot this is the tagged TapLeaf hash. For other script execution
    /// this is SHA256d of the entire executed script, without CompactSize.
    ScriptPath {
        /// Opcode position of the last executed separator, or u32::MAX.
        codesep_pos: u32,
        executed_script_hash: [u8; 32],
    },
}

/// Build the bytes whose double SHA256 is a Lotus signature digest.
///
/// `replay_protection` is the consensus replay epoch, determined by the node's
/// activation rules (previous-block median time), not by transaction locktime.
/// The signature suffix remains the original one-byte sighash type in either
/// epoch; only the four-byte preimage hash type changes.
///
/// All input coins must be supplied in order. ANYONECANPAY reads only the
/// selected entry, so other entries may be placeholders in that mode.
pub fn lotus_sighash_preimage(
    tx: &UnhashedTx,
    spent_outputs: &[TxOutput],
    input_idx: usize,
    sighash_type: SigHashType,
    context: LotusSighashContext,
    replay_protection: bool,
) -> Result<Bytes, SignError> {
    if sighash_type.variant != SigHashTypeVariant::Lotus {
        return Err(SignError::InvalidSigHashType(sighash_type));
    }
    let input = tx
        .inputs
        .get(input_idx)
        .ok_or(SignError::LotusInputIndex(input_idx))?;
    let input_position =
        u32::try_from(input_idx).map_err(|_| SignError::LotusInputIndex(input_idx))?;
    if spent_outputs.len() != tx.inputs.len() {
        return Err(SignError::LotusSpentOutputsCount);
    }
    let coin = &spent_outputs[input_idx];
    checked_sum(std::slice::from_ref(coin))?;
    let fixed = sighash_type.input_type == SigHashTypeInputs::Fixed;
    let mut hash_type = sighash_type.to_u32();
    if replay_protection {
        hash_type |= 0xffdead00;
    }
    let mut preimage = BytesMut::new();
    hash_type.ser_to(&mut preimage);
    let mut input_data = BytesMut::new();
    let spend_type: u8 = match context {
        LotusSighashContext::KeyPath => 0,
        LotusSighashContext::ScriptPath { .. } => 2,
    };
    spend_type.ser_to(&mut input_data);
    input.prev_out.ser_to(&mut input_data);
    input.sequence.ser_to(&mut input_data);
    coin.ser_to(&mut input_data);
    Sha256d::digest(input_data.freeze()).ser_to(&mut preimage);
    if let LotusSighashContext::ScriptPath {
        codesep_pos,
        executed_script_hash,
    } = context
    {
        codesep_pos.ser_to(&mut preimage);
        preimage.put_slice(&executed_script_hash);
    }
    if fixed {
        input_position.ser_to(&mut preimage);
        output_root(spent_outputs).0.ser_to(&mut preimage);
        checked_sum(spent_outputs)?.ser_to(&mut preimage);
    }
    if sighash_type.output_type == SigHashTypeOutputs::All {
        checked_sum(&tx.outputs)?.ser_to(&mut preimage);
    }
    tx.version.ser_to(&mut preimage);
    if fixed {
        let leaves = tx
            .inputs
            .iter()
            .map(|input| {
                let mut data = BytesMut::new();
                input.prev_out.ser_to(&mut data);
                input.sequence.ser_to(&mut data);
                Sha256d::digest(data.freeze())
            })
            .collect();
        let (root, height) = get_merkle_root_and_height(leaves, MerkleMode::Lotus);
        root.ser_to(&mut preimage);
        (height as u8).ser_to(&mut preimage);
    }
    match sighash_type.output_type {
        SigHashTypeOutputs::Single => {
            let output = tx
                .outputs
                .get(input_idx)
                .ok_or(SignError::LotusSingleOutputMissing(input_idx))?;
            checked_sum(std::slice::from_ref(output))?;
            Sha256d::digest(output.ser()).ser_to(&mut preimage);
        }
        SigHashTypeOutputs::All => {
            let (root, height) = output_root(&tx.outputs);
            root.ser_to(&mut preimage);
            (height as u8).ser_to(&mut preimage);
        }
        SigHashTypeOutputs::None => {}
    }
    tx.lock_time.ser_to(&mut preimage);
    Ok(preimage.freeze())
}

fn checked_sum(outputs: &[TxOutput]) -> Result<i64, SignError> {
    outputs.iter().try_fold(0i64, |sum, output| {
        if output.value < 0 {
            return Err(SignError::LotusInvalidAmount);
        }
        sum.checked_add(output.value)
            .ok_or(SignError::LotusInvalidAmount)
    })
}

fn output_root(outputs: &[TxOutput]) -> (Sha256d, usize) {
    get_merkle_root_and_height(
        outputs
            .iter()
            .map(|output| Sha256d::digest(output.ser()))
            .collect(),
        MerkleMode::Lotus,
    )
}
