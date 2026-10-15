use eyre::{eyre, Result};
use ocl::{
    builders::{DeviceSpecifier, ProgramBuilder},
    Buffer, Context, Device, Kernel, Platform, Queue,
};
use sha2::Digest;
use std::convert::TryInto;
use thiserror::Error;

use crate::{sha256::lotus_hash, Log};

#[derive(Debug, Error)]
pub enum MinerError {
    #[error("Ocl error: {0:?}")]
    Ocl(ocl::Error),
}

#[derive(Debug, Clone)]
pub struct MiningSettings {
    pub scrypt_work_size: u32,
    pub local_work_size: i32,
    pub kernel_size: u32,
    pub inner_iter_size: i32,
    pub kernel_name: String,
    pub sleep: u32,
    pub gpu_indices: Vec<usize>,
}

pub struct Miner {
    doge: Option<crate::scrypt::DogeMiner>,
    search_kernel: Option<Kernel>,
    header_buffer: Option<Buffer<u32>>,
    buffer: Option<Buffer<u32>>,
    settings: MiningSettings,
}

#[derive(Debug, Clone, Copy)]
pub struct Work {
    chain: crate::settings::Chain,
    header: [u8; 160],
    target: [u8; 32],
    pub nonce_idx: u32,
}

impl From<ocl::Error> for MinerError {
    fn from(err: ocl::Error) -> Self {
        MinerError::Ocl(err)
    }
}

use self::MinerError::*;

impl Work {
    pub fn from_header(header: [u8; 160], target: [u8; 32]) -> Work {
        Work {
            chain: crate::settings::Chain::Lotus,
            header,
            target,
            nonce_idx: 0,
        }
    }

    pub fn set_big_nonce(&mut self, big_nonce: u64) {
        match self.chain {
            crate::settings::Chain::Lotus => {
                self.header[44..52].copy_from_slice(&big_nonce.to_le_bytes())
            }
            crate::settings::Chain::Dogecoin => {
                self.header[76..80].copy_from_slice(&(big_nonce as u32).to_le_bytes())
            }
        }
    }

    pub fn with_chain(mut self, chain: crate::settings::Chain) -> Self {
        self.chain = chain;
        self
    }

    pub fn header(&self) -> &[u8; 160] {
        &self.header
    }
}

impl Default for Work {
    fn default() -> Self {
        Work {
            chain: crate::settings::Chain::Lotus,
            header: [0; 160],
            target: [0; 32],
            nonce_idx: 0,
        }
    }
}

impl Miner {
    pub fn setup(settings: MiningSettings) -> Result<Self> {
        if settings.kernel_name == "dogecoin" {
            return Ok(Self {
                doge: Some(crate::scrypt::DogeMiner::new(
                    settings.gpu_indices[0],
                    settings.scrypt_work_size as usize,
                )?),
                search_kernel: None,
                header_buffer: None,
                buffer: None,
                settings,
            });
        }
        let mut prog_builder = ProgramBuilder::new();
        prog_builder
            .src(match settings.kernel_name.as_str() {
                "lotus_og" => include_str!("../../kernels/lotus_og.cl"),
                name => return Err(eyre!("Unknown mining kernel: {}", name)),
            })
            .cmplr_def("WORKSIZE", settings.local_work_size)
            .cmplr_def("ITERATIONS", settings.inner_iter_size);
        let platforms = Platform::list();
        println!("Platforms:");
        for (platform_idx, platform) in platforms.iter().enumerate() {
            println!(
                "{}: {}",
                platform_idx,
                platform.name().unwrap_or("<invalid platform>".to_string())
            );
            let devices = Device::list_all(platform).map_err(Ocl)?;
            for (device_idx, device) in devices.iter().enumerate() {
                println!("- device {}: {}", device_idx, device.name().map_err(Ocl)?);
            }
        }
        let mut platform_device = None;
        let mut gpu_index = 0;
        for cur_platform in platforms {
            if let Ok(devices) = Device::list_all(cur_platform) {
                for cur_device in devices {
                    if gpu_index == settings.gpu_indices[0] {
                        platform_device = Some((cur_platform, cur_device));
                    }
                    gpu_index += 1;
                }
            }
        }
        let (platform, device) = platform_device
            .ok_or_else(|| eyre!("OpenCL device {} not found", settings.gpu_indices[0]))?;
        let ctx = Context::builder()
            .platform(platform)
            .devices(DeviceSpecifier::Single(device))
            .build()
            .map_err(Ocl)?;
        let queue = Queue::new(&ctx, device, None).map_err(Ocl)?;
        prog_builder.devices(DeviceSpecifier::Single(device));
        let program = prog_builder.build(&ctx).map_err(Ocl)?;
        let mut kernel_builder = Kernel::builder();
        kernel_builder
            .program(&program)
            .name("search")
            .queue(queue.clone());
        let buffer = Buffer::builder()
            .len(0xff)
            .queue(queue.clone())
            .build()
            .map_err(Ocl)?;
        let header_buffer = Buffer::builder()
            .len(0xff)
            .queue(queue)
            .build()
            .map_err(Ocl)?;
        let search_kernel = kernel_builder
            .arg_named("offset", 0u32)
            .arg_named("partial_header", None::<&Buffer<u32>>)
            .arg_named("output", None::<&Buffer<u32>>)
            .build()
            .map_err(Ocl)?;
        Ok(Miner {
            doge: None,
            search_kernel: Some(search_kernel),
            buffer: Some(buffer),
            header_buffer: Some(header_buffer),
            settings,
        })
    }

    pub fn list_device_names() -> Vec<String> {
        let platforms = Platform::list();
        let mut device_names = Vec::new();
        for platform in platforms.iter() {
            let platform_name = platform.name().unwrap_or("<invalid platform>".to_string());
            let devices = Device::list_all(platform).unwrap_or(vec![]);
            for device in devices.iter() {
                device_names.push(format!(
                    "{} - {}",
                    platform_name,
                    device.name().unwrap_or("<invalid device>".to_string())
                ));
            }
        }
        device_names
    }

    pub fn has_nonces_left(&self, work: &Work) -> bool {
        (work.nonce_idx as u64) * self.num_nonces_per_search() < (1u64 << 32)
    }

    pub fn num_nonces_per_search(&self) -> u64 {
        if self.doge.is_some() {
            self.settings.scrypt_work_size as u64
        } else {
            self.settings.kernel_size as u64 * self.settings.inner_iter_size as u64
        }
    }

    pub fn find_nonce(&mut self, work: &Work, log: &Log) -> Result<Option<u64>> {
        if let Some(doge) = &self.doge {
            return doge
                .search(
                    &work.header[..80],
                    &work.target,
                    work.nonce_idx as u64 * self.num_nonces_per_search(),
                )
                .map(|nonce| nonce.map(u64::from));
        }
        let search_kernel = self.search_kernel.as_ref().unwrap();
        let header_buffer = self.header_buffer.as_ref().unwrap();
        let buffer = self.buffer.as_ref().unwrap();
        let base = match work
            .nonce_idx
            .checked_mul(self.num_nonces_per_search().try_into().unwrap())
        {
            Some(base) => base,
            None => {
                log.error(
                    "Error: Nonce base overflow, skipping. This could be fixed by lowering \
                           rpc_poll_interval.",
                );
                return Ok(None);
            }
        };
        let mut partial_header = [0u8; 84];
        partial_header[..52].copy_from_slice(&work.header[..52]);
        partial_header[52..].copy_from_slice(&sha2::Sha256::digest(&work.header[52..]));
        let mut partial_header_ints = [0u32; 21];
        for (chunk, int) in partial_header.chunks(4).zip(partial_header_ints.iter_mut()) {
            *int = u32::from_be_bytes(chunk.try_into().unwrap());
        }
        header_buffer
            .write(&partial_header_ints[..])
            .enq()
            .map_err(Ocl)?;
        search_kernel
            .set_arg("partial_header", header_buffer)
            .map_err(Ocl)?;
        search_kernel.set_arg("output", buffer).map_err(Ocl)?;
        search_kernel.set_arg("offset", base).map_err(Ocl)?;
        let mut vec = vec![0; buffer.len()];
        buffer.write(&vec).enq().map_err(Ocl)?;
        let cmd = search_kernel
            .cmd()
            .global_work_size(self.settings.kernel_size);
        unsafe {
            cmd.enq().map_err(Ocl)?;
        }
        buffer.read(&mut vec).enq().map_err(Ocl)?;
        if vec[0x80] != 0 {
            let mut header = work.header;
            'nonce: for &nonce in &vec[..0x7f] {
                let nonce = nonce.swap_bytes();
                if nonce != 0 {
                    header[44..48].copy_from_slice(&nonce.to_le_bytes());
                    let result_nonce = u64::from_le_bytes(header[44..52].try_into().unwrap());
                    let hash = lotus_hash(&header);
                    let mut candidate_hash = hash;
                    candidate_hash.reverse();
                    log.info(format!(
                        "Candidate: nonce={}, hash={}",
                        result_nonce,
                        hex::encode(candidate_hash)
                    ));
                    if hash.last() != Some(&0) {
                        log.bug(
                            "BUG: found nonce's hash has no leading zero byte. Contact the \
                                   developers.",
                        );
                    }
                    for (&h, &t) in hash.iter().zip(work.target.iter()).rev() {
                        if h > t {
                            continue 'nonce;
                        }
                        if t > h {
                            return Ok(Some(result_nonce));
                        }
                    }
                }
            }
        }
        Ok(None)
    }

    pub fn set_intensity(&mut self, intensity: i32) {
        self.settings.kernel_size = 1 << intensity;
    }

    pub fn update_gpu_index(&mut self, gpu_index: i64) -> Result<()> {
        if self.settings.gpu_indices[0] == gpu_index as usize {
            return Ok(());
        }
        let mut settings = self.settings.clone();
        settings.gpu_indices = vec![gpu_index.try_into().unwrap()];
        *self = Miner::setup(settings)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dogecoin_nonce_changes_only_four_header_bytes() {
        let header = [0x55; 160];
        let mut work =
            Work::from_header(header, [0xff; 32]).with_chain(crate::settings::Chain::Dogecoin);
        work.set_big_nonce(u32::MAX as u64);
        assert_eq!(&work.header()[..76], &header[..76]);
        assert_eq!(&work.header()[76..80], &[255; 4]);
        assert_eq!(&work.header()[80..], &header[80..]);
    }
    #[test]
    #[ignore = "requires an installed OpenCL runtime and device"]
    fn compile_embedded_kernel() {
        // Compiles the kernel and allocates buffers; does not start mining or use RPC.
        Miner::setup(MiningSettings {
            scrypt_work_size: 1024,
            local_work_size: 256,
            kernel_size: 256,
            inner_iter_size: 16,
            kernel_name: "lotus_og".into(),
            sleep: 0,
            gpu_indices: vec![0],
        })
        .unwrap();
    }
}
