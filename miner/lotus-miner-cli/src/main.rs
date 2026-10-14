use std::{sync::Arc, time::Duration};

use lotus_miner_lib::{ConfigSettings, Protocol, Server, V2_UNAVAILABLE};

fn validate_cli_config(config: &ConfigSettings) -> Result<(), Box<dyn std::error::Error>> {
    if config.protocol == Protocol::V2 {
        return Err(V2_UNAVAILABLE.into());
    }
    if config.mine_to_address.is_empty() {
        return Err("V1 mining requires mine_to_address".into());
    }
    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let config: ConfigSettings = ConfigSettings::load(false)?;
    validate_cli_config(&config)?;
    let report_hashrate_interval = Duration::from_secs(10);
    let server = Arc::new(Server::from_config(config, report_hashrate_interval)?);
    tokio::spawn({
        let server = Arc::clone(&server);
        async move {
            loop {
                tokio::time::sleep(report_hashrate_interval).await;
                if let Some(hashrate) = server.log().hashrates().last() {
                    println!("{}", hashrate);
                }
            }
        }
    });
    server.run().await?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn v2_cli_refuses_before_server_setup() {
        let config = ConfigSettings {
            protocol: Protocol::V2,
            rpc_url: "http://127.0.0.1:1".into(),
            rpc_user: "".into(),
            rpc_password: "".into(),
            rpc_poll_interval: 3,
            mine_to_address: "".into(),
            kernel_size: 21,
            gpu_index: -1,
        };
        assert_eq!(
            validate_cli_config(&config).unwrap_err().to_string(),
            V2_UNAVAILABLE
        );
    }
}
