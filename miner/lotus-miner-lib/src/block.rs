use std::convert::TryInto;

use serde::Deserialize;

pub struct Block {
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

pub fn create_block(unsolved_block_and_target: &RawUnsolvedBlockAndTarget) -> eyre::Result<Block> {
    let block = hex::decode(&unsolved_block_and_target.blockhex)?;
    if block.len() < 160 {
        return Err(eyre::eyre!(
            "Mining block is shorter than the 160-byte Lotus header"
        ));
    }
    let mut target: [u8; 32] = hex::decode(&unsolved_block_and_target.target)?
        .try_into()
        .map_err(|_| eyre::eyre!("Mining target must be 32 bytes"))?;
    target.reverse();
    Ok(Block {
        header: block[0..160].try_into().unwrap(),
        body: block[160..].to_vec(),
        target,
    })
}

impl Block {
    pub fn prev_hash(&self) -> &[u8] {
        &self.header[..32]
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
