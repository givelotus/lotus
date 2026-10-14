use crate::sign::Signatory;
use crate::{
    ecc::{Ecc, PubKey, SecKey},
    lotus_sighash_preimage,
    taproot::tap_tweak_hash,
    BytesMut, Hashed, LotusSighashContext, Result, Script, ScriptVariant, Sha256d, SigHashType,
    SigHashTypeInputs, SignError, TxOutput, UnsignedTxInput,
};

/// Lotus Schnorr key-path signer. The supplied internal key is tweaked with
/// the explicit script-tree root; the result must match the spent commitment.
pub struct P2TRKeyPathSignatory {
    pub seckey: SecKey,
    pub internal_pubkey: PubKey,
    pub sig_hash_type: SigHashType,
    pub merkle_root: [u8; 32],
    /// Set from the node's active replay-protection epoch, not wall-clock time.
    pub replay_protection: bool,
}

impl P2TRKeyPathSignatory {
    /// Key-path-only output: no script tree, before the replay epoch.
    pub fn new(seckey: SecKey, internal_pubkey: PubKey) -> Self {
        Self {
            seckey,
            internal_pubkey,
            sig_hash_type: SigHashType::ALL_LOTUS,
            merkle_root: [0; 32],
            replay_protection: false,
        }
    }
}

impl Signatory for P2TRKeyPathSignatory {
    fn sign_input<'tx>(&self, ecc: &dyn Ecc, mut input: UnsignedTxInput<'tx>) -> Result<()> {
        if ecc.derive_pubkey(&self.seckey) != self.internal_pubkey {
            return Err(SignError::InvalidTaprootKey.into());
        }
        let tweak = tap_tweak_hash(&self.internal_pubkey, &self.merkle_root);
        let tweaked_seckey = ecc
            .tweak_seckey(&self.seckey, &tweak)
            .map_err(|_| SignError::InvalidTaprootKey)?;
        let tx = input.unsigned_tx().tx();
        let mut spent_outputs = Vec::with_capacity(tx.inputs.len());
        for (idx, tx_input) in tx.inputs.iter().enumerate() {
            if self.sig_hash_type.input_type == SigHashTypeInputs::AnyoneCanPay
                && idx != input.input_idx()
            {
                spent_outputs.push(TxOutput::default());
                continue;
            }
            let sign_data = tx_input.sign_data.as_ref().ok_or(SignError::NoSignData)?;
            spent_outputs.push(TxOutput {
                value: sign_data.find_value()?,
                script: sign_data.find_output_script()?,
            });
        }
        let commitment = match spent_outputs[input.input_idx()].script.parse_variant() {
            ScriptVariant::P2TR(pubkey, _) => pubkey,
            _ => return Err(SignError::TaprootCommitmentMismatch.into()),
        };
        if ecc.derive_pubkey(&tweaked_seckey) != commitment {
            return Err(SignError::TaprootCommitmentMismatch.into());
        }
        let preimage = lotus_sighash_preimage(
            tx,
            &spent_outputs,
            input.input_idx(),
            self.sig_hash_type,
            LotusSighashContext::KeyPath,
            self.replay_protection,
        )?;
        let sighash = Sha256d::digest(preimage).byte_array().clone();
        let sig = ecc.schnorr_sign(&tweaked_seckey, sighash);
        let mut script = BytesMut::new();
        // A 65-byte push: 64-byte Schnorr signature followed by sighash suffix.
        script.put_slice(&[65]);
        script.put_bytes(sig);
        script.put_slice(&[self.sig_hash_type.to_u32() as u8]);
        *input.input_script_mut() = Script::from_slice(script.freeze().as_ref());
        Ok(())
    }
}
