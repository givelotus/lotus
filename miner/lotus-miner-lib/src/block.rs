use std::convert::TryInto;

use serde::Deserialize;

pub struct Block {
    pub chain: crate::settings::Chain,
    pub header: [u8; 160],
    pub body: Vec<u8>,
    pub target: [u8; 32],
}

#[derive(Deserialize, Debug, Clone)]
pub struct GetRawUnsolvedBlockResponse {
    pub result: Option<RawUnsolvedBlockAndTarget>,
    pub error: Option<serde_json::Value>,
}

#[derive(Deserialize, Debug, Clone)]
pub struct RawUnsolvedBlockAndTarget {
    pub blockhex: String,
    pub target: String,
}

#[cfg(test)]
pub fn create_block(unsolved_block_and_target: &RawUnsolvedBlockAndTarget) -> eyre::Result<Block> {
    create_block_for_chain(unsolved_block_and_target, crate::settings::Chain::Lotus)
}

pub fn create_block_for_chain(
    unsolved_block_and_target: &RawUnsolvedBlockAndTarget,
    chain: crate::settings::Chain,
) -> eyre::Result<Block> {
    let size = chain.header_len();
    let block = hex::decode(&unsolved_block_and_target.blockhex)?;
    if block.len() < size {
        return Err(eyre::eyre!(
            "Mining block is shorter than its configured chain header"
        ));
    }
    let mut target: [u8; 32] = hex::decode(&unsolved_block_and_target.target)?
        .try_into()
        .map_err(|_| eyre::eyre!("Mining target must be 32 bytes"))?;
    target.reverse();
    let mut header = [0; 160];
    header[..size].copy_from_slice(&block[..size]);
    if chain == crate::settings::Chain::Dogecoin {
        let version = u32::from_le_bytes(header[..4].try_into().unwrap());
        if version & 256 != 0 {
            return Err(eyre::eyre!(
                "AuxPoW jobs require a parent-chain miner; expected a direct Scrypt job"
            ));
        }
        // The direct-mining RPC contract uses Dogecoin chain ID 98 and base
        // version 4. Fail closed if pointed at a Lotus/Bitcoin endpoint or if a
        // future protocol version needs explicit miner compatibility review.
        if version >> 16 != 98 || version & 0xffff != 4 {
            return Err(eyre::eyre!(
                "Expected a modern Dogecoin direct-mining job (chain ID 98, version 4); check --chain and rpc_url"
            ));
        }
    }
    Ok(Block {
        chain,
        header,
        body: block[size..].to_vec(),
        target,
    })
}

impl Block {
    pub fn prev_hash(&self) -> &[u8] {
        match self.chain {
            crate::settings::Chain::Lotus => &self.header[..32],
            crate::settings::Chain::Dogecoin => &self.header[4..36],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn job_preserves_lotus_header_and_metadata() {
        let bytes: Vec<u8> = (0..164).map(|i| i as u8).collect();
        let job = RawUnsolvedBlockAndTarget {
            blockhex: hex::encode(&bytes),
            target: format!("{}01", "00".repeat(31)),
        };
        let block = create_block(&job).unwrap();
        assert_eq!(block.header.as_slice(), &bytes[..160]);
        assert_eq!(block.body, bytes[160..]);
        assert_eq!(block.target[0], 1);
        assert_eq!(block.target[31], 0);
        assert_eq!(block.prev_hash(), &bytes[..32]);
    }

    #[test]
    fn dogecoin_job_preserves_wire_body_and_target() {
        let mut bytes: Vec<u8> = (0..192).map(|i| i as u8).collect();
        bytes[..4].copy_from_slice(&0x620004u32.to_le_bytes());
        let block = create_block_for_chain(
            &RawUnsolvedBlockAndTarget {
                blockhex: hex::encode(&bytes),
                target: format!("01{}", "00".repeat(31)),
            },
            crate::settings::Chain::Dogecoin,
        )
        .unwrap();
        assert_eq!(&block.header[..80], &bytes[..80]);
        assert_eq!(block.body, bytes[80..]);
        assert_eq!(block.prev_hash(), &bytes[4..36]);
        assert_eq!(block.target[31], 1);
        bytes[1] |= 1;
        assert!(create_block_for_chain(
            &RawUnsolvedBlockAndTarget {
                blockhex: hex::encode(&bytes),
                target: "ff".repeat(32)
            },
            crate::settings::Chain::Dogecoin
        )
        .is_err());
    }

    #[test]
    fn dogecoin_rejects_mismatched_chain_and_unsupported_versions() {
        for version in [0u32, 1, 4, 0x630004, 0x620003, 0x620005, 0x620204] {
            let mut bytes = vec![0; 164];
            bytes[..4].copy_from_slice(&version.to_le_bytes());
            let job = RawUnsolvedBlockAndTarget {
                blockhex: hex::encode(bytes),
                target: "ff".repeat(32),
            };
            assert!(
                create_block_for_chain(&job, crate::settings::Chain::Dogecoin).is_err(),
                "version {:#x}",
                version
            );
            // A longer Lotus body is not evidence that a job is Dogecoin.
            assert!(create_block(&job).is_ok());
        }
    }

    #[test]
    fn invalid_job_returns_error() {
        for (blockhex, target) in [("00", "00".repeat(32)), ("invalid", "00".repeat(32))] {
            assert!(create_block(&RawUnsolvedBlockAndTarget {
                blockhex: blockhex.into(),
                target,
            })
            .is_err());
        }
        assert!(create_block(&RawUnsolvedBlockAndTarget {
            blockhex: "00".repeat(160),
            target: "00".into(),
        })
        .is_err());
    }

    #[test]
    fn accepts_standard_json_rpc_error() {
        let response: GetRawUnsolvedBlockResponse = serde_json::from_str(
            r#"{"result":null,"error":{"code":-8,"message":"Invalid address"}}"#,
        )
        .unwrap();
        assert!(response.result.is_none());
        assert_eq!(response.error.unwrap()["code"], -8);
    }
}
