//! Bounded P04 GPU hashing batches. Network mining remains disabled until V2 jobs exist.

use std::convert::TryInto;

use eyre::{bail, Result};
use ocl::{Buffer, Context, Device, Kernel, Platform, Program, Queue};

use crate::v2_header::{hashes, meets_target, HEADER_LEN, NONCE_OFFSET};

const MAX_BATCH: usize = 1_000_000;

fn validate_batch(header: &[u8], start_nonce: u64, count: usize) -> Result<()> {
    if count == 0 || count > MAX_BATCH {
        bail!("V2 GPU batch count must be between 1 and {MAX_BATCH}");
    }
    start_nonce
        .checked_add((count - 1) as u64)
        .ok_or_else(|| eyre::eyre!("V2 nonce range wraps u64"))?;
    if header.len() != HEADER_LEN {
        bail!("V2 header must be exactly {HEADER_LEN} bytes");
    }
    Ok(())
}

pub struct V2GpuHasher {
    queue: Queue,
    program: Program,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GpuNonceResult {
    pub nonce: u64,
    pub block_id: [u8; 32],
    pub meets_target: bool,
}

impl V2GpuHasher {
    pub fn setup(device_index: usize) -> Result<Self> {
        let mut index = 0;
        for platform in Platform::list() {
            for device in Device::list_all(platform)? {
                if index == device_index {
                    let context = Context::builder()
                        .platform(platform)
                        .devices(device)
                        .build()?;
                    let queue = Queue::new(&context, device, None)?;
                    let program = Program::builder()
                        .src(include_str!("../../kernels/lotus_v2.cl"))
                        .devices(device)
                        .build(&context)?;
                    return Ok(Self { queue, program });
                }
                index += 1;
            }
        }
        bail!("OpenCL device {device_index} not found")
    }

    pub fn hash_nonces(
        &self,
        header: &[u8],
        chain_id: &[u8; 32],
        target: &[u8; 32],
        start_nonce: u64,
        count: usize,
    ) -> Result<Vec<GpuNonceResult>> {
        validate_batch(header, start_nonce, count)?;
        let (body_hash, _, _) = hashes(header, chain_id)?;
        let mut work_template = b"Lotus/v2/header/work\0".to_vec();
        work_template.extend_from_slice(&header[32..NONCE_OFFSET]);
        work_template.extend_from_slice(&[0; 8]);
        work_template.extend_from_slice(&body_hash);
        let mut id_template = b"Lotus/v2/blockid\0".to_vec();
        id_template.extend_from_slice(&header[..32]);
        id_template.extend_from_slice(&[0; 32]);
        debug_assert_eq!(work_template.len(), 71);
        debug_assert_eq!(id_template.len(), 81);

        let work_buffer = Buffer::<u8>::builder()
            .queue(self.queue.clone())
            .len(work_template.len())
            .copy_host_slice(&work_template)
            .build()?;
        let id_buffer = Buffer::<u8>::builder()
            .queue(self.queue.clone())
            .len(id_template.len())
            .copy_host_slice(&id_template)
            .build()?;
        let target_buffer = Buffer::<u8>::builder()
            .queue(self.queue.clone())
            .len(32)
            .copy_host_slice(target)
            .build()?;
        let digest_buffer = Buffer::<u8>::builder()
            .queue(self.queue.clone())
            .len(count * 32)
            .build()?;
        let match_buffer = Buffer::<u32>::builder()
            .queue(self.queue.clone())
            .len(count)
            .build()?;
        let kernel = Kernel::builder()
            .program(&self.program)
            .name("hash_nonces")
            .queue(self.queue.clone())
            .global_work_size(count)
            .arg(&work_buffer)
            .arg(&id_buffer)
            .arg(&target_buffer)
            .arg(start_nonce)
            .arg(&digest_buffer)
            .arg(&match_buffer)
            .build()?;
        unsafe { kernel.enq()? };
        let mut digest_bytes = vec![0; count * 32];
        let mut matches = vec![0u32; count];
        digest_buffer.read(&mut digest_bytes).enq()?;
        match_buffer.read(&mut matches).enq()?;
        let mut results = Vec::with_capacity(count);
        for (i, gpu_match) in matches.into_iter().enumerate() {
            let block_id: [u8; 32] = digest_bytes[i * 32..(i + 1) * 32].try_into()?;
            let nonce = start_nonce + i as u64;
            if gpu_match > 1 {
                bail!("V2 GPU returned invalid match flag at nonce {nonce}");
            }
            let accepted = gpu_match == 1;
            if accepted {
                let mut candidate_header = header.to_vec();
                candidate_header[NONCE_OFFSET..NONCE_OFFSET + 8]
                    .copy_from_slice(&nonce.to_le_bytes());
                let cpu_id = hashes(&candidate_header, chain_id)?.2;
                if block_id != cpu_id || !meets_target(&cpu_id, target) {
                    bail!("V2 GPU candidate failed independent CPU verification at nonce {nonce}");
                }
            }
            results.push(GpuNonceResult {
                nonce,
                block_id,
                meets_target: accepted,
            });
        }
        Ok(results)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_overflow_and_bad_batch_before_opencl() {
        let header = [0u8; HEADER_LEN];
        assert!(validate_batch(&header, 0, 0).is_err());
        assert!(validate_batch(&header, 0, MAX_BATCH + 1).is_err());
        assert!(validate_batch(&header, u64::MAX, 2).is_err());
        assert!(validate_batch(&header, u64::MAX - 1, 2).is_ok());
        assert!(validate_batch(&header[..HEADER_LEN - 1], 0, 1).is_err());
    }

    #[test]
    #[ignore = "requires an installed OpenCL runtime and device"]
    fn gpu_cpu_parity_and_target_boundaries() {
        let gpu = V2GpuHasher::setup(0).unwrap();
        let chain_id: [u8; 32] = std::array::from_fn(|i| i as u8);
        let mut header = [0u8; HEADER_LEN];
        for (i, byte) in header.iter_mut().enumerate() {
            *byte = i as u8;
        }
        header[50..54].copy_from_slice(&2u32.to_le_bytes());
        let starts = [0u64, 255, 0xffff_ffff - 1, u64::MAX - 3];
        for &start in &starts {
            let all = gpu
                .hash_nonces(&header, &chain_id, &[0xff; 32], start, 4)
                .unwrap();
            for item in &all {
                header[NONCE_OFFSET..NONCE_OFFSET + 8].copy_from_slice(&item.nonce.to_le_bytes());
                assert_eq!(item.block_id, hashes(&header, &chain_id).unwrap().2);
                assert!(item.meets_target);
            }
            let boundary = all[1].block_id;
            let equal = gpu
                .hash_nonces(&header, &chain_id, &boundary, start + 1, 1)
                .unwrap();
            assert!(equal[0].meets_target);
            let zero = gpu
                .hash_nonces(&header, &chain_id, &[0; 32], start, 4)
                .unwrap();
            assert!(zero.iter().all(|item| !item.meets_target));
            let mut just_below = boundary;
            for byte in &mut just_below {
                if *byte != 0 {
                    *byte -= 1;
                    break;
                }
                *byte = 0xff;
            }
            let below = gpu
                .hash_nonces(&header, &chain_id, &just_below, start + 1, 1)
                .unwrap();
            assert!(!below[0].meets_target);
        }

        let vector_header = hex::decode(concat!(
            "202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f",
            "ffff001d0605040302010f0e0d0c0b0a0908020000008877665544332211",
            "00ffeeddccbbaa99404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f",
            "606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f"
        ))
        .unwrap();
        let vector = gpu
            .hash_nonces(
                &vector_header,
                &chain_id,
                &[0xff; 32],
                0x0809_0a0b_0c0d_0e0f,
                2,
            )
            .unwrap();
        assert_eq!(
            hex::encode(vector[0].block_id),
            "fbe9243579627fc3a41043c80395d33a8a01b91a9b86b6c6e629530595c83370"
        );
        assert_eq!(
            hex::encode(vector[1].block_id),
            "8a967f4522d06f683830cf003b9f456001e045f617bf4d4336754a91c75f5824"
        );
        let last = gpu
            .hash_nonces(&vector_header, &chain_id, &[0xff; 32], u64::MAX, 1)
            .unwrap();
        assert_eq!(
            hex::encode(last[0].block_id),
            "ce606e015b769cf60502917d0bac3597048e25668c7df323f817b53969aab371"
        );
    }

    #[test]
    #[ignore = "requires an installed OpenCL runtime and device"]
    fn gpu_diverse_header_and_batch_corpus() {
        let gpu = V2GpuHasher::setup(0).unwrap();
        let base_header: [u8; HEADER_LEN] = std::array::from_fn(|i| (i as u8).wrapping_mul(17));
        let base_chain: [u8; 32] = std::array::from_fn(|i| (i as u8).wrapping_mul(13));
        let mut cases = Vec::new();
        cases.push((base_header, base_chain));
        let mut chain = base_chain;
        chain[31] ^= 0x80;
        cases.push((base_header, chain));
        for &offset in &[0, 32, 36, 50, 54, 62, 70, 102] {
            let mut header = base_header;
            header[offset] ^= 0x80;
            cases.push((header, base_chain));
        }

        let mut baseline = None;
        for (case_index, (header, chain_id)) in cases.into_iter().enumerate() {
            let count = [1, 2, 7, 16][case_index % 4];
            let start = if case_index % 2 == 0 {
                0xffff_ffffu64 - 3
            } else {
                u64::MAX - (count as u64 - 1)
            };
            let results = gpu
                .hash_nonces(&header, &chain_id, &[0xff; 32], start, count)
                .unwrap();
            for item in &results {
                let mut cpu_header = header;
                cpu_header[NONCE_OFFSET..NONCE_OFFSET + 8]
                    .copy_from_slice(&item.nonce.to_le_bytes());
                assert_eq!(item.block_id, hashes(&cpu_header, &chain_id).unwrap().2);
                assert!(item.meets_target);
            }
            let fixed_nonce_id = gpu
                .hash_nonces(&header, &chain_id, &[0xff; 32], 0, 1)
                .unwrap()[0]
                .block_id;
            if case_index == 0 {
                baseline = Some(fixed_nonce_id);
            } else {
                // Each case changes one independent header field or ChainID.
                assert_ne!(fixed_nonce_id, baseline.unwrap());
            }
            let selected = results[0].block_id;
            let equal = gpu
                .hash_nonces(&header, &chain_id, &selected, start, 1)
                .unwrap();
            assert!(equal[0].meets_target);
            let mut lower = selected;
            for byte in &mut lower {
                if *byte != 0 {
                    *byte -= 1;
                    break;
                }
                *byte = 0xff;
            }
            assert!(
                !gpu.hash_nonces(&header, &chain_id, &lower, start, 1)
                    .unwrap()[0]
                    .meets_target
            );
        }
    }
}
