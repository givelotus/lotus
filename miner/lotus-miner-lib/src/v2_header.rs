//! Candidate P04 header hashing. This module has no V2 job or GPU integration.

use eyre::{bail, Result};

pub const HEADER_LEN: usize = 134;
pub const NONCE_OFFSET: usize = 42;
pub const BODY_OFFSET: usize = 50;

fn tagged_hash(tag: &str, payload: &[u8]) -> [u8; 32] {
    let mut hasher = blake3::Hasher::new();
    hasher.update(tag.as_bytes());
    hasher.update(&[0]);
    hasher.update(payload);
    *hasher.finalize().as_bytes()
}

/// Returns BodyHash, WorkHash, and BlockID in consensus byte order.
/// `chain_id` is an explicit chain-manifest input; no network value is assumed.
pub fn hashes(header: &[u8], chain_id: &[u8; 32]) -> Result<([u8; 32], [u8; 32], [u8; 32])> {
    if header.len() != HEADER_LEN {
        bail!("V2 header must be exactly {HEADER_LEN} bytes");
    }
    let mut body_payload = [0u8; 116];
    body_payload[..32].copy_from_slice(chain_id);
    body_payload[32..].copy_from_slice(&header[BODY_OFFSET..]);
    let body_hash = tagged_hash("Lotus/v2/header/body", &body_payload);

    let mut work_payload = [0u8; 50];
    work_payload[..18].copy_from_slice(&header[32..BODY_OFFSET]);
    work_payload[18..].copy_from_slice(&body_hash);
    let work_hash = tagged_hash("Lotus/v2/header/work", &work_payload);

    let mut id_payload = [0u8; 64];
    id_payload[..32].copy_from_slice(&header[..32]);
    id_payload[32..].copy_from_slice(&work_hash);
    let block_id = tagged_hash("Lotus/v2/blockid", &id_payload);
    Ok((body_hash, work_hash, block_id))
}

/// Compare the raw 32-byte hashes as little-endian unsigned integers.
pub fn meets_target(block_id: &[u8; 32], target: &[u8; 32]) -> bool {
    block_id.iter().rev().cmp(target.iter().rev()).is_le()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_noncanonical_header_length() {
        assert!(hashes(&[0; HEADER_LEN - 1], &[0; 32]).is_err());
        assert!(hashes(&[0; HEADER_LEN + 1], &[0; 32]).is_err());
    }

    #[test]
    fn nonce_changes_work_and_block_id_but_not_body() {
        let mut header = [0u8; HEADER_LEN];
        header[BODY_OFFSET..BODY_OFFSET + 4].copy_from_slice(&2u32.to_le_bytes());
        let first = hashes(&header, &[7; 32]).unwrap();
        header[NONCE_OFFSET] = 1;
        let second = hashes(&header, &[7; 32]).unwrap();
        assert_eq!(first.0, second.0);
        assert_ne!(first.1, second.1);
        assert_ne!(first.2, second.2);
    }

    #[test]
    fn target_is_inclusive_little_endian() {
        let mut id = [0u8; 32];
        id[0] = 1;
        let mut target = [0u8; 32];
        target[1] = 1;
        assert!(meets_target(&id, &id));
        assert!(meets_target(&id, &target));
        assert!(!meets_target(&target, &id));
    }

    #[test]
    fn independent_p04_vector() {
        let chain_id: [u8; 32] = std::array::from_fn(|index| index as u8);
        let mut header = hex::decode(concat!(
            "202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f",
            "ffff001d0605040302010f0e0d0c0b0a0908020000008877665544332211",
            "00ffeeddccbbaa99404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f",
            "606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f"
        ))
        .unwrap();
        let first = hashes(&header, &chain_id).unwrap();
        assert_eq!(
            hex::encode(first.0),
            "1704e11edcbc47eb829d210ac1affb606dd4021c82305e07a028962456efec3d"
        );
        assert_eq!(
            hex::encode(first.1),
            "56c49269bcb4709b42d48312a382badc0906162e5bd6e49aac48a7096288ffd1"
        );
        assert_eq!(
            hex::encode(first.2),
            "fbe9243579627fc3a41043c80395d33a8a01b91a9b86b6c6e629530595c83370"
        );
        header[NONCE_OFFSET] = 0x10;
        let second = hashes(&header, &chain_id).unwrap();
        assert_eq!(second.0, first.0);
        assert_eq!(
            hex::encode(second.1),
            "3df1f29ca207e25132c7b3fdddfae0163b16d0c6bf7488e2810858e84f0673e5"
        );
        assert_eq!(
            hex::encode(second.2),
            "8a967f4522d06f683830cf003b9f456001e045f617bf4d4336754a91c75f5824"
        );
    }
}
