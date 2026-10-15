//! Local P04 candidate jobs.
//!
//! JSON objects and `L2JB` byte fixtures can be parsed and hashed locally.
//! JSON fields are exactly `protocol` (`"v2"`), `job_id`, `chain_id`, `header`,
//! and `target`. Chain id, header, and target are hex; the target is raw
//! little-endian bytes, not the reversed V1 RPC display order.
//! Byte layout: `L2JB` || version `1` || job-id length `u8` || job id UTF-8
//! || chain id (32) || target (32) || header (134).
//! `submit` and `mine_network` refuse network mining. They do not connect,
//! spawn a daemon, or search nonces.

use thiserror::Error;

use crate::v2_header::{self, HEADER_LEN};

const MAGIC: &[u8] = b"L2JB";
const VERSION: u8 = 1;
const JSON_FIELDS: [&str; 5] = ["protocol", "job_id", "chain_id", "header", "target"];
const JOB_ID_MAX_LEN: usize = 128;
const V1_HEADER_LEN: usize = 160;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct V2Job {
    header: [u8; HEADER_LEN],
    chain_id: [u8; 32],
    target: [u8; 32],
    job_id: String,
}

#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum V2JobError {
    #[error("V2 header must be exactly {expected} bytes, got {len}")]
    WrongHeaderLength { len: usize, expected: usize },
    #[error("V2 target is truncated ({len} bytes, expected 32)")]
    TruncatedTarget { len: usize },
    #[error("V1 job cannot be used as a V2 job")]
    V1JobPresentedAsV2,
    #[error(
        "unsupported V2 network submission: daemon jobs and pool submission are not available"
    )]
    UnsupportedNetworkSubmission,
    #[error("malformed V2 job: {0}")]
    Malformed(&'static str),
}

impl V2Job {
    pub fn from_json(text: &str) -> Result<Self, V2JobError> {
        let value: serde_json::Value =
            serde_json::from_str(text).map_err(|_| V2JobError::Malformed("invalid JSON"))?;
        let obj = value
            .as_object()
            .ok_or(V2JobError::Malformed("expected a JSON object"))?;
        if is_v1_object(obj) {
            return Err(V2JobError::V1JobPresentedAsV2);
        }
        if obj.len() != JSON_FIELDS.len() || JSON_FIELDS.iter().any(|key| !obj.contains_key(*key)) {
            return Err(V2JobError::Malformed("unexpected or missing fields"));
        }
        let protocol = json_string(obj, "protocol")?;
        if protocol != "v2" {
            return Err(V2JobError::Malformed("protocol must be \"v2\""));
        }
        let job_id = json_string(obj, "job_id")?;
        if job_id.is_empty() || job_id.len() > JOB_ID_MAX_LEN {
            return Err(V2JobError::Malformed("job id must be 1..=128 bytes"));
        }
        let chain_bytes = decode_hex(json_string(obj, "chain_id")?, "chain id hex is invalid")?;
        if chain_bytes.len() != 32 {
            return Err(V2JobError::Malformed("chain id must be exactly 32 bytes"));
        }
        let header_bytes = decode_hex(json_string(obj, "header")?, "header hex is invalid")?;
        if header_bytes.len() == V1_HEADER_LEN {
            return Err(V2JobError::V1JobPresentedAsV2);
        }
        if header_bytes.len() != HEADER_LEN {
            return Err(V2JobError::WrongHeaderLength {
                len: header_bytes.len(),
                expected: HEADER_LEN,
            });
        }
        let target_bytes = decode_hex(json_string(obj, "target")?, "target hex is invalid")?;
        if target_bytes.len() < 32 {
            return Err(V2JobError::TruncatedTarget {
                len: target_bytes.len(),
            });
        } else if target_bytes.len() > 32 {
            return Err(V2JobError::Malformed("target must be exactly 32 bytes"));
        }
        let mut chain_id = [0u8; 32];
        chain_id.copy_from_slice(&chain_bytes);
        let mut target = [0u8; 32];
        target.copy_from_slice(&target_bytes);
        let mut header = [0u8; HEADER_LEN];
        header.copy_from_slice(&header_bytes);
        Ok(Self {
            header,
            chain_id,
            target,
            job_id: job_id.to_string(),
        })
    }

    pub fn from_bytes(bytes: &[u8]) -> Result<Self, V2JobError> {
        if bytes.len() == V1_HEADER_LEN && !bytes.starts_with(MAGIC) {
            return Err(V2JobError::V1JobPresentedAsV2);
        }
        if !bytes.starts_with(MAGIC) {
            return Err(V2JobError::Malformed("V2 job bytes must start with L2JB"));
        }
        if bytes.len() < 6 {
            return Err(V2JobError::Malformed("truncated V2 job"));
        }
        if bytes[4] != VERSION {
            return Err(V2JobError::Malformed("unsupported V2 job byte version"));
        }
        let job_id_len = usize::from(bytes[5]);
        if job_id_len == 0 || job_id_len > JOB_ID_MAX_LEN {
            return Err(V2JobError::Malformed("job id length must be 1..=128"));
        }
        let id_end = 6 + job_id_len;
        if bytes.len() < id_end {
            return Err(V2JobError::Malformed("truncated job id"));
        }
        let job_id = std::str::from_utf8(&bytes[6..id_end])
            .map_err(|_| V2JobError::Malformed("job id must be utf-8"))?
            .to_string();
        let chain_end = id_end + 32;
        if bytes.len() < chain_end {
            return Err(V2JobError::Malformed("truncated chain id"));
        }
        let mut chain_id = [0u8; 32];
        chain_id.copy_from_slice(&bytes[id_end..chain_end]);
        let target_end = chain_end + 32;
        if bytes.len() < target_end {
            return Err(V2JobError::TruncatedTarget {
                len: bytes.len() - chain_end,
            });
        }
        let mut target = [0u8; 32];
        target.copy_from_slice(&bytes[chain_end..target_end]);
        let header_len = bytes.len() - target_end;
        if header_len == V1_HEADER_LEN {
            return Err(V2JobError::V1JobPresentedAsV2);
        }
        if header_len != HEADER_LEN {
            return Err(V2JobError::WrongHeaderLength {
                len: header_len,
                expected: HEADER_LEN,
            });
        }
        let mut header = [0u8; HEADER_LEN];
        header.copy_from_slice(&bytes[target_end..]);
        Ok(Self {
            header,
            chain_id,
            target,
            job_id,
        })
    }

    pub fn to_bytes(&self) -> Vec<u8> {
        debug_assert!(self.job_id.len() <= JOB_ID_MAX_LEN);
        let mut out = Vec::with_capacity(6 + self.job_id.len() + 32 + 32 + HEADER_LEN);
        out.extend_from_slice(MAGIC);
        out.push(VERSION);
        out.push(self.job_id.len() as u8);
        out.extend_from_slice(self.job_id.as_bytes());
        out.extend_from_slice(&self.chain_id);
        out.extend_from_slice(&self.target);
        out.extend_from_slice(&self.header);
        out
    }

    pub fn header(&self) -> &[u8; HEADER_LEN] {
        &self.header
    }

    pub fn chain_id(&self) -> &[u8; 32] {
        &self.chain_id
    }

    pub fn target(&self) -> &[u8; 32] {
        &self.target
    }

    pub fn job_id(&self) -> &str {
        &self.job_id
    }

    pub fn hashes(&self) -> eyre::Result<([u8; 32], [u8; 32], [u8; 32])> {
        v2_header::hashes(&self.header, &self.chain_id)
    }

    /// Refuses pool and lotusd submission. No socket, daemon, or nonce search.
    pub fn mine_network(&self) -> Result<(), V2JobError> {
        Err(V2JobError::UnsupportedNetworkSubmission)
    }

    /// Refuses network submission of this job. No socket, daemon, or nonce search.
    pub fn submit(&self) -> Result<(), V2JobError> {
        self.mine_network()
    }
}

fn is_v1_object(obj: &serde_json::Map<String, serde_json::Value>) -> bool {
    if obj.contains_key("blockhex") {
        return true;
    }
    if obj.get("protocol").and_then(|value| value.as_str()) == Some("v1") {
        return true;
    }
    obj.get("result")
        .and_then(|result| result.get("blockhex"))
        .is_some()
}

fn json_string<'a>(
    obj: &'a serde_json::Map<String, serde_json::Value>,
    key: &'static str,
) -> Result<&'a str, V2JobError> {
    match obj.get(key) {
        Some(serde_json::Value::String(value)) => Ok(value),
        _ => Err(V2JobError::Malformed("V2 job fields must be strings")),
    }
}

fn decode_hex(text: &str, invalid: &'static str) -> Result<Vec<u8>, V2JobError> {
    hex::decode(text).map_err(|_| V2JobError::Malformed(invalid))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::v2_header::{hashes, NONCE_OFFSET};

    const HEADER_HEX: &str = concat!(
        "202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f",
        "ffff001d0605040302010f0e0d0c0b0a0908020000008877665544332211",
        "00ffeeddccbbaa99404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f",
        "606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f"
    );

    fn chain_id() -> [u8; 32] {
        std::array::from_fn(|index| index as u8)
    }

    fn target() -> [u8; 32] {
        [0x11; 32]
    }

    fn sample_json() -> String {
        serde_json::json!({
            "protocol": "v2",
            "job_id": "p04-local-1",
            "chain_id": hex::encode(chain_id()),
            "header": HEADER_HEX,
            "target": hex::encode(target()),
        })
        .to_string()
    }

    fn sample_job() -> V2Job {
        V2Job::from_json(&sample_json()).unwrap()
    }

    #[test]
    fn parses_json_and_bytes_and_matches_header_hashes() {
        let job = sample_job();
        assert_eq!(job.job_id(), "p04-local-1");
        assert_eq!(job.chain_id(), &chain_id());
        assert_eq!(job.target(), &target());
        assert_eq!(job.header().as_slice(), hex::decode(HEADER_HEX).unwrap());
        assert_eq!(
            job.hashes().unwrap(),
            hashes(job.header(), job.chain_id()).unwrap()
        );
        let bytes = job.to_bytes();
        assert_eq!(V2Job::from_bytes(&bytes).unwrap(), job);

        let original = job.hashes().unwrap();
        for nonce in 0..4u64 {
            let mut header = *job.header();
            header[NONCE_OFFSET..NONCE_OFFSET + 8].copy_from_slice(&nonce.to_le_bytes());
            let cpu = hashes(&header, job.chain_id()).unwrap();
            assert_eq!(cpu.0, original.0);
            assert_ne!(cpu.1, original.1);
            assert_ne!(cpu.2, original.2);
        }
    }

    #[test]
    fn rejects_wrong_header_length() {
        let mut json: serde_json::Value = serde_json::from_str(&sample_json()).unwrap();
        json["header"] = serde_json::Value::String("aa".repeat(10));
        assert_eq!(
            V2Job::from_json(&json.to_string()).unwrap_err(),
            V2JobError::WrongHeaderLength {
                len: 10,
                expected: HEADER_LEN,
            }
        );

        let bytes = sample_job().to_bytes();
        assert_eq!(
            V2Job::from_bytes(&bytes[..bytes.len() - 10]).unwrap_err(),
            V2JobError::WrongHeaderLength {
                len: HEADER_LEN - 10,
                expected: HEADER_LEN,
            }
        );
        let mut longer = bytes;
        longer.push(0);
        assert_eq!(
            V2Job::from_bytes(&longer).unwrap_err(),
            V2JobError::WrongHeaderLength {
                len: HEADER_LEN + 1,
                expected: HEADER_LEN,
            }
        );
    }

    #[test]
    fn rejects_truncated_target() {
        let mut json: serde_json::Value = serde_json::from_str(&sample_json()).unwrap();
        json["target"] = serde_json::Value::String("abcd".to_string());
        assert_eq!(
            V2Job::from_json(&json.to_string()).unwrap_err(),
            V2JobError::TruncatedTarget { len: 2 }
        );
        json["target"] = serde_json::Value::String(String::new());
        assert_eq!(
            V2Job::from_json(&json.to_string()).unwrap_err(),
            V2JobError::TruncatedTarget { len: 0 }
        );

        let bytes = sample_job().to_bytes();
        let target_at = bytes.len() - HEADER_LEN - 32;
        assert_eq!(
            V2Job::from_bytes(&bytes[..target_at + 16]).unwrap_err(),
            V2JobError::TruncatedTarget { len: 16 }
        );
    }

    #[test]
    fn rejects_v1_job_presented_as_v2() {
        let v1_fields = serde_json::json!({
            "blockhex": "00".repeat(80),
            "target": "11".repeat(32),
        });
        assert_eq!(
            V2Job::from_json(&v1_fields.to_string()).unwrap_err(),
            V2JobError::V1JobPresentedAsV2
        );
        let envelope = serde_json::json!({
            "result": {"blockhex": "00".repeat(160), "target": "11".repeat(32)},
            "error": null,
        });
        assert_eq!(
            V2Job::from_json(&envelope.to_string()).unwrap_err(),
            V2JobError::V1JobPresentedAsV2
        );

        let mut labeled = serde_json::from_str::<serde_json::Value>(&sample_json()).unwrap();
        labeled["protocol"] = serde_json::Value::String("v1".to_string());
        assert_eq!(
            V2Job::from_json(&labeled.to_string()).unwrap_err(),
            V2JobError::V1JobPresentedAsV2
        );
        labeled["protocol"] = serde_json::Value::String("v2".to_string());
        labeled["header"] = serde_json::Value::String("00".repeat(V1_HEADER_LEN));
        assert_eq!(
            V2Job::from_json(&labeled.to_string()).unwrap_err(),
            V2JobError::V1JobPresentedAsV2
        );
        labeled = serde_json::from_str(&sample_json()).unwrap();
        labeled["blockhex"] = serde_json::Value::String("00".to_string());
        assert_eq!(
            V2Job::from_json(&labeled.to_string()).unwrap_err(),
            V2JobError::V1JobPresentedAsV2
        );

        assert_eq!(
            V2Job::from_bytes(&[9u8; V1_HEADER_LEN]).unwrap_err(),
            V2JobError::V1JobPresentedAsV2
        );
        let mut header_bytes = sample_job().to_bytes();
        header_bytes.truncate(header_bytes.len() - HEADER_LEN);
        header_bytes.extend(std::iter::repeat_n(0, V1_HEADER_LEN));
        assert_eq!(
            V2Job::from_bytes(&header_bytes).unwrap_err(),
            V2JobError::V1JobPresentedAsV2
        );
    }

    #[test]
    fn network_submission_is_unsupported() {
        let job = sample_job();
        let expected =
            "unsupported V2 network submission: daemon jobs and pool submission are not available";
        for err in [job.submit().unwrap_err(), job.mine_network().unwrap_err()] {
            assert_eq!(err, V2JobError::UnsupportedNetworkSubmission);
            assert_eq!(err.to_string(), expected);
        }
        assert_eq!(
            job.hashes().unwrap(),
            hashes(job.header(), job.chain_id()).unwrap()
        );
    }

    #[test]
    fn parses_cpp_block_template_and_refuses_network_submission() {
        // Nonce-0 header from the native-037 BuildChildHeader fixture.
        // Digests are that process's BodyHash, WorkHash, and BlockId.
        const JSON: &str = r#"{"protocol":"v2","job_id":"native-037-template","chain_id":"000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f","header":"2ba3f975fbc1840b9cb4acc6aa84a88539010eb2132cb06a43168b1cb6b66ae5ffff002178f1536500000000000000000000020000009001000000000000050000000000000033333333333333333333333333333333333333333333333333333333333333334444444444444444444444444444444444444444444444444444444444444444","target":"000000000000000000000000000000000000000000000000000000000000ffff"}"#;
        let job = V2Job::from_json(JSON).unwrap();
        assert_eq!(job.job_id(), "native-037-template");
        assert_eq!(job.header().len(), HEADER_LEN);
        assert_eq!(job.chain_id().len(), 32);
        assert_eq!(job.target().len(), 32);
        let (body, work, block_id) = job.hashes().unwrap();
        assert_eq!(
            hex::encode(body),
            "e6488811010b45ed6ce854cdc9758edb80b552d23e75948e7ccc1fe0f5145bea"
        );
        assert_eq!(
            hex::encode(work),
            "67609329f280d16be8df0d4c20d8e2ffd6fadca4b69750f93bd432d492e1587c"
        );
        assert_eq!(
            hex::encode(block_id),
            "d9ba1f949132940f2a3e4c1cf5c15dd8ecdb7718055f686ac5e3d3b2c5824d2a"
        );
        assert_eq!(
            job.hashes().unwrap(),
            hashes(job.header(), job.chain_id()).unwrap()
        );
        let expected =
            "unsupported V2 network submission: daemon jobs and pool submission are not available";
        for err in [job.submit().unwrap_err(), job.mine_network().unwrap_err()] {
            assert_eq!(err, V2JobError::UnsupportedNetworkSubmission);
            assert_eq!(err.to_string(), expected);
        }
    }

    #[test]
    #[ignore = "requires an installed OpenCL runtime and device"]
    fn job_gpu_batch_matches_cpu_for_four_nonces() {
        // Digest parity only. This does not accept or submit a block.
        let job = sample_job();
        let gpu = crate::v2_gpu::V2GpuHasher::setup(0).unwrap();
        let results = gpu
            .hash_nonces(job.header(), job.chain_id(), job.target(), 0, 4)
            .unwrap();
        assert_eq!(results.len(), 4);
        for (index, item) in results.iter().enumerate() {
            assert_eq!(item.nonce, index as u64);
            let mut header = *job.header();
            header[NONCE_OFFSET..NONCE_OFFSET + 8].copy_from_slice(&item.nonce.to_le_bytes());
            assert_eq!(item.block_id, hashes(&header, job.chain_id()).unwrap().2);
        }
    }
}
