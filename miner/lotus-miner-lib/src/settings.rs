use std::{convert::TryFrom, io::Write};

use clap::{crate_description, crate_version, load_yaml, App};
use config::{Config, ConfigError, File};
use serde::{Deserialize, Serialize};

pub const DEFAULT_URL: &str = "http://127.0.0.1:10604";
pub const DEFAULT_USER: &str = "lotus";
pub const DEFAULT_PASSWORD: &str = "lotus";
pub const DEFAULT_RPC_POLL_INTERVAL: i64 = 3;
pub const FOLDER_DIR: &str = ".lotus-miner";
pub const DEFAULT_KERNEL_SIZE: i64 = 21;
pub const DEFAULT_GPU_INDEX: i64 = 0;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum Protocol {
    #[default]
    V1,
    V2,
}

#[derive(Debug, Deserialize)]
pub struct ConfigSettings {
    pub protocol: Protocol,
    pub rpc_url: String,
    pub rpc_user: String,
    pub rpc_password: String,
    pub rpc_poll_interval: i64,
    pub mine_to_address: String,
    pub kernel_size: i64,
    pub gpu_index: i64,
}

const DEFAULT_CONFIG_FILE_CONTENT: &str = r#"mine_to_address = ""
protocol = "v1"
rpc_url = "http://127.0.0.1:10604"
rpc_poll_interval = 3
rpc_user = "lotus"
rpc_password = "lotus"
gpu_index = 0
kernel_size = 23
"#;

fn default_config() -> Result<Config, ConfigError> {
    let mut s = Config::new();
    s.set_default("rpc_url", DEFAULT_URL)?;
    s.set_default("rpc_poll_interval", DEFAULT_RPC_POLL_INTERVAL)?;
    s.set_default("rpc_user", DEFAULT_USER)?;
    s.set_default("rpc_password", DEFAULT_PASSWORD)?;
    s.set_default("kernel_size", DEFAULT_KERNEL_SIZE)?;
    s.set_default("gpu_index", DEFAULT_GPU_INDEX)?;
    s.set_default("protocol", "v1")?;
    s.set_default("mine_to_address", "")?;
    Ok(s)
}

fn parse_i64_arg(value: &str, name: &str) -> Result<i64, ConfigError> {
    value
        .parse::<i64>()
        .map_err(|_| ConfigError::Message(format!("{} must be a signed 64-bit integer", name)))
}

impl ConfigSettings {
    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.rpc_poll_interval <= 0 {
            return Err(ConfigError::Message(
                "rpc_poll_interval must be positive".into(),
            ));
        }
        if !(0..=27).contains(&self.kernel_size) {
            return Err(ConfigError::Message(
                "kernel_size must be between 0 and 27".into(),
            ));
        }
        if self.gpu_index < 0 || usize::try_from(self.gpu_index).is_err() {
            return Err(ConfigError::Message(
                "gpu_index must be a nonnegative device index".into(),
            ));
        }
        Ok(())
    }

    pub fn load(expect_mine_to_address: bool) -> Result<Self, ConfigError> {
        let mut s = default_config()?;

        // Set defaults
        let yaml = load_yaml!("cli.yaml");
        let matches = App::from_yaml(yaml)
            .about(crate_description!())
            .author(env!("CARGO_PKG_AUTHORS"))
            .version(crate_version!())
            .get_matches();
        let home_dir = match dirs::home_dir() {
            Some(some) => some,
            None => return Err(ConfigError::Message("no home directory".to_string())),
        };
        // Load config from file
        let default_config = home_dir;
        let default_config_folder = default_config.join(FOLDER_DIR);
        let default_config_toml = default_config_folder.join("config.toml");
        let default_config = default_config_folder.join("config");
        let default_config_str = default_config.to_str().unwrap();
        let config_path = match matches.value_of("config") {
            Some(config_path) => config_path,
            None => {
                if !default_config_toml.exists() {
                    if let Err(err) = std::fs::create_dir_all(&default_config_folder) {
                        eprintln!(
                            "Error: Couldn't create default config folder {}: {}",
                            default_config_folder.to_string_lossy(),
                            err
                        );
                    }
                    match std::fs::File::create(&default_config_toml) {
                        Ok(mut file) => {
                            if let Err(err) = file.write_all(DEFAULT_CONFIG_FILE_CONTENT.as_bytes())
                            {
                                eprintln!(
                                    "Error: Couldn't write default config toml file {}: {}",
                                    default_config_toml.to_string_lossy(),
                                    err
                                );
                            }
                        }
                        Err(err) => {
                            eprintln!(
                                "Error: Couldn't create default config toml file {}: {}",
                                default_config_toml.to_string_lossy(),
                                err
                            );
                        }
                    };
                }
                default_config_str
            }
        };
        s.merge(File::with_name(config_path).required(false))?;

        // Set bind address from cmd line
        if let Some(rpc_url) = matches.value_of("rpc_url") {
            s.set("rpc_url", rpc_url)?;
        }

        // Set the bitcoin network
        if let Some(rpc_poll_interval) = matches.value_of("rpc_poll_interval") {
            s.set(
                "rpc_poll_interval",
                parse_i64_arg(rpc_poll_interval, "rpc_poll_interval")?,
            )?;
        }

        // Set bind address from cmd line
        if let Some(rpc_password) = matches.value_of("rpc_password") {
            s.set("rpc_password", rpc_password)?;
        }

        // Set the bitcoin network
        if let Some(rpc_user) = matches.value_of("rpc_user") {
            s.set("rpc_user", rpc_user)?;
        }

        // Set the bitcoin network
        if let Some(mine_to_address) = matches.value_of("mine_to_address") {
            s.set("mine_to_address", mine_to_address)?;
        }
        if expect_mine_to_address
            && s.get_str("mine_to_address")
                .map(|mine_to_address| mine_to_address.is_empty())
                .unwrap_or(true)
        {
            return Err(ConfigError::Message(format!(
                "Must set mine_to_address config option. You can find it in {}.toml",
                std::fs::canonicalize(config_path)
                    .map(|path| path.to_string_lossy().to_string())
                    .unwrap_or_else(|_| config_path.to_string())
            )));
        }

        // Set the bitcoin network
        if let Some(kernel_size) = matches.value_of("kernel_size") {
            s.set("kernel_size", parse_i64_arg(kernel_size, "kernel_size")?)?;
        }

        // Set the GPU index
        if let Some(gpu_index) = matches.value_of("gpu_index") {
            s.set("gpu_index", parse_i64_arg(gpu_index, "gpu_index")?)?;
        }

        if let Some(protocol) = matches.value_of("protocol") {
            s.set("protocol", protocol)?;
        }

        let settings: Self = s.try_into()?;
        settings.validate()?;
        Ok(settings)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn protocol_defaults_to_v1() {
        let settings: ConfigSettings = default_config().unwrap().try_into().unwrap();
        assert_eq!(settings.protocol, Protocol::V1);
    }

    #[test]
    fn invalid_protocol_is_rejected() {
        let mut config = default_config().unwrap();
        config.set("protocol", "v3").unwrap();
        let result: Result<ConfigSettings, ConfigError> = config.try_into();
        assert!(result.is_err());
    }

    #[test]
    fn numeric_config_errors_are_fallible() {
        assert!(parse_i64_arg("not-a-number", "kernel_size").is_err());
        for (key, value) in [
            ("rpc_poll_interval", -1),
            ("kernel_size", -1),
            ("kernel_size", 28),
            ("gpu_index", -1),
        ] {
            let mut config = default_config().unwrap();
            config.set(key, value).unwrap();
            let settings: ConfigSettings = config.try_into().unwrap();
            assert!(settings.validate().is_err(), "{}={}", key, value);
        }
    }
}
