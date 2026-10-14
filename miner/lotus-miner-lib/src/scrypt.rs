//! Direct Dogecoin Scrypt proof-of-work. CPU verification is independent of OpenCL.
use eyre::{eyre, Result};
use ocl::{Buffer, Context, Device, Kernel, Platform, Program, Queue};
use sha2::{Digest, Sha256};
use std::convert::TryInto;

// The mining password is always an 80-byte header, exceeding HMAC's 64-byte block.
fn hmac(key: &[u8], message: &[u8]) -> [u8; 32] {
    let key = Sha256::digest(key);
    let mut inner = [0x36; 64];
    let mut outer = [0x5c; 64];
    for i in 0..32 {
        inner[i] ^= key[i];
        outer[i] ^= key[i];
    }
    let digest = Sha256::new().chain(inner).chain(message).finalize();
    Sha256::new().chain(outer).chain(digest).finalize().into()
}
fn mix(x: &mut [u32; 32]) {
    let mut t = [0; 16];
    t.copy_from_slice(&x[16..]);
    for half in 0..2 {
        for i in 0..16 {
            t[i] ^= x[half * 16 + i];
        }
        let mut z = t;
        for _ in 0..4 {
            for [a, b, c, d] in [
                [0, 4, 8, 12],
                [5, 9, 13, 1],
                [10, 14, 2, 6],
                [15, 3, 7, 11],
                [0, 1, 2, 3],
                [5, 6, 7, 4],
                [10, 11, 8, 9],
                [15, 12, 13, 14],
            ] {
                z[b] ^= z[a].wrapping_add(z[d]).rotate_left(7);
                z[c] ^= z[b].wrapping_add(z[a]).rotate_left(9);
                z[d] ^= z[c].wrapping_add(z[b]).rotate_left(13);
                z[a] ^= z[d].wrapping_add(z[c]).rotate_left(18);
            }
        }
        for i in 0..16 {
            t[i] = t[i].wrapping_add(z[i]);
            x[half * 16 + i] = t[i];
        }
    }
}
// PBKDF2-HMAC-SHA256(password=header, salt=header, iterations=1),
// then ROMix(1024,r=1), then PBKDF2 again with the mixed block as salt.
pub fn hash(header: &[u8]) -> [u8; 32] {
    assert_eq!(header.len(), 80);
    let mut x = [0; 32];
    for j in 0..4 {
        let mut msg = header.to_vec();
        msg.extend_from_slice(&(j as u32 + 1).to_be_bytes());
        let digest = hmac(header, &msg);
        for i in 0..8 {
            x[j * 8 + i] = u32::from_le_bytes(digest[i * 4..i * 4 + 4].try_into().unwrap());
        }
    }
    let mut v = vec![[0; 32]; 1024];
    for row in &mut v {
        *row = x;
        mix(&mut x);
    }
    for _ in 0..1024 {
        let row = &v[(x[16] & 1023) as usize];
        for i in 0..32 {
            x[i] ^= row[i];
        }
        mix(&mut x);
    }
    let mut msg = Vec::with_capacity(132);
    for word in x {
        msg.extend_from_slice(&word.to_le_bytes());
    }
    msg.extend_from_slice(&1u32.to_be_bytes());
    hmac(header, &msg)
}
fn meets(hash: &[u8], target: &[u8]) -> bool {
    hash.iter().rev().cmp(target.iter().rev()).is_le()
}
pub struct DogeMiner {
    work_size: usize,
    kernel: Kernel,
    header: Buffer<u8>,
    hashes: Buffer<u8>,
}
impl DogeMiner {
    pub fn new(index: usize, work_size: usize) -> Result<Self> {
        if !(256..=4096).contains(&work_size) || !work_size.is_power_of_two() {
            return Err(eyre!(
                "scrypt_work_size must be a power of two from 256 to 4096 (32–512 MiB scratch)"
            ));
        }
        let mut devices = Vec::new();
        for platform in Platform::list() {
            for device in Device::list_all(platform)? {
                devices.push((platform, device));
            }
        }
        let (platform, device) = *devices
            .get(index)
            .ok_or_else(|| eyre!("OpenCL device not found"))?;
        println!(
            "Dogecoin Scrypt OpenCL: {} ({} nonces/batch, {} MiB scratch)",
            device.name()?,
            work_size,
            work_size / 8
        );
        let context = Context::builder()
            .platform(platform)
            .devices(device)
            .build()?;
        let queue = Queue::new(&context, device, None)?;
        let program = Program::builder()
            .src(include_str!("../../kernels/dogecoin.cl"))
            .devices(device)
            .build(&context)?;
        let header = Buffer::<u8>::builder()
            .queue(queue.clone())
            .len(80)
            .build()?;
        let hashes = Buffer::<u8>::builder()
            .queue(queue.clone())
            .len(work_size * 32)
            .build()?;
        let scratch = Buffer::<u32>::builder()
            .queue(queue.clone())
            .len(work_size * 32768)
            .build()?;
        let kernel = Kernel::builder()
            .program(&program)
            .queue(queue)
            .name("scrypt_hash")
            .global_work_size(work_size)
            .arg(&header)
            .arg(0u32)
            .arg(&scratch)
            .arg(&hashes)
            .build()?;
        Ok(Self {
            work_size,
            kernel,
            header,
            hashes,
        })
    }
    fn hashes(&self, header: &[u8], base: u32) -> Result<Vec<u8>> {
        self.header.write(header).enq()?;
        self.kernel.set_arg(1, base)?;
        unsafe {
            self.kernel.enq()?;
        }
        let mut hashes = vec![0; self.work_size * 32];
        self.hashes.read(&mut hashes).enq()?;
        Ok(hashes)
    }
    pub fn search(&self, header: &[u8], target: &[u8; 32], base: u64) -> Result<Option<u32>> {
        if base + self.work_size as u64 > 1u64 << 32 {
            return Ok(None);
        }
        let hashes = self.hashes(header, base as u32)?;
        for (i, digest) in hashes.as_chunks::<32>().0.iter().enumerate() {
            if meets(digest, target) {
                let nonce = base as u32 + i as u32;
                let mut solved = header.to_vec();
                solved[76..80].copy_from_slice(&nonce.to_le_bytes());
                let cpu = hash(&solved);
                if &cpu != digest {
                    return Err(eyre!("OpenCL Scrypt mismatch at nonce {}", nonce));
                }
                return Ok(Some(nonce));
            }
        }
        Ok(None)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn independent_vector() {
        // Python hashlib.scrypt(bytes(80), salt=bytes(80), n=1024, r=1, p=1, dklen=32)
        assert_eq!(
            hex::encode(hash(&[0; 80])),
            "161d0876f3b93b1048cda1bdeaa7332ee210f7131b42013cb43913a6553a4b69"
        );
    }
    #[test]
    fn target_comparison_is_inclusive_little_endian() {
        let mut target = [0; 32];
        target[31] = 1;
        assert!(meets(&target, &target));
        let mut lower = [255; 32];
        lower[31] = 0;
        assert!(meets(&lower, &target));
        assert!(!meets(&target, &lower));
    }
    #[test]
    #[ignore = "bounded OpenCL batch-size benchmark, at most 512 MiB"]
    fn opencl_batch_benchmark() {
        for size in [256, 1024, 4096] {
            let miner = DogeMiner::new(0, size).unwrap();
            let header: Vec<u8> = (0..80).collect();
            let hashes = miner.hashes(&header, u32::MAX - size as u32 + 1).unwrap();
            for index in [0, size / 2, size - 1] {
                let mut solved = header.clone();
                let nonce = u32::MAX - size as u32 + 1 + index as u32;
                solved[76..80].copy_from_slice(&nonce.to_le_bytes());
                assert_eq!(
                    hash(&solved).as_slice(),
                    &hashes[index * 32..index * 32 + 32]
                );
            }
            let start = std::time::Instant::now();
            for batch in 0..1024 {
                miner.hashes(&header, batch * size as u32).unwrap();
            }
            println!(
                "work_size={} hashes={} elapsed={:?} H/s={:.2}",
                size,
                size * 1024,
                start.elapsed(),
                (size * 1024) as f64 / start.elapsed().as_secs_f64()
            );
            assert!(miner
                .search(&header, &[255; 32], 1u64 << 32)
                .unwrap()
                .is_none());
        }
    }
    #[test]
    #[ignore = "requires OpenCL device; bounded 256-nonce benchmark"]
    fn opencl_matches_cpu() {
        let miner = DogeMiner::new(0, 256).unwrap();
        let start = std::time::Instant::now();
        let hashes = miner.hashes(&[0; 80], 0).unwrap();
        println!(
            "256 Scrypt hashes in {:?}, {:.2} H/s",
            start.elapsed(),
            256.0 / start.elapsed().as_secs_f64()
        );
        for i in 0u32..256 {
            let mut header = [0; 80];
            header[76..80].copy_from_slice(&i.to_le_bytes());
            assert_eq!(
                hash(&header).as_slice(),
                &hashes[i as usize * 32..i as usize * 32 + 32]
            );
        }
        let start = std::time::Instant::now();
        for batch in 1..17 {
            miner.hashes(&[0; 80], batch * 256).unwrap();
        }
        println!(
            "4096 warmed Scrypt hashes in {:?}, {:.2} H/s",
            start.elapsed(),
            4096.0 / start.elapsed().as_secs_f64()
        );
        assert_eq!(miner.search(&[0; 80], &[255; 32], 0).unwrap(), Some(0));
    }
}
