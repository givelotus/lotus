//! HTTP/SSE V2 Mining Pool Client (`GET /pool/jobs` SSE stream & `POST /pool/submit`).
//!
//! Parses `event: job\ndata: {...}\n\n` Server-Sent Events from `/pool/jobs`,
//! validates canonical 134-byte Lotus V2 headers and 32-byte ChainID/Targets,
//! and submits verified winning nonces to `POST /pool/submit`.

use eyre::{bail, eyre, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};

use crate::{
    v2_header::{hashes, meets_target, HEADER_LEN, NONCE_OFFSET},
    v2_job::{V2Job, V2JobError},
};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PoolJobEvent {
    pub job: V2Job,
    pub height: Option<u64>,
    pub clean_jobs: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PoolShareSubmission {
    pub protocol: String,
    pub job_id: String,
    pub worker: String,
    pub nonce: u64,
    pub nonce_hex: String,
    pub header: String,
    pub block_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PoolSubmitResponse {
    pub accepted: bool,
    #[serde(default)]
    pub block_found: bool,
    #[serde(default)]
    pub shares_accepted: u64,
    #[serde(default)]
    pub subscription_unlocked: bool,
    #[serde(default)]
    pub vardiff_target: Option<String>,
    #[serde(default)]
    pub error: Option<String>,
}

/// Incremental SSE parser for `event: job\ndata: {...}\n\n` frames from `/pool/jobs`.
#[derive(Debug, Default)]
pub struct SseJobStreamParser {
    buffer: String,
}

impl SseJobStreamParser {
    pub fn new() -> Self {
        Self {
            buffer: String::new(),
        }
    }

    /// Push a UTF-8 chunk from the `/pool/jobs` response stream and return all
    /// completed `event: job` frames.
    pub fn push_chunk(&mut self, chunk: &str) -> Vec<Result<PoolJobEvent, V2JobError>> {
        self.buffer.push_str(&chunk.replace("\r\n", "\n"));
        let mut out = Vec::new();
        while let Some(sep_idx) = self.buffer.find("\n\n") {
            let raw_frame = self.buffer[..sep_idx].to_string();
            self.buffer.drain(..sep_idx + 2);
            if let Some(parsed) = Self::parse_frame(&raw_frame) {
                out.push(parsed);
            }
        }
        out
    }

    pub fn parse_frame(frame: &str) -> Option<Result<PoolJobEvent, V2JobError>> {
        let mut event_type: Option<&str> = None;
        let mut data_lines = Vec::new();

        for line in frame.lines() {
            let trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with(':') {
                continue;
            }
            if let Some(rest) = trimmed.strip_prefix("event:") {
                event_type = Some(rest.trim());
            } else if let Some(rest) = trimmed.strip_prefix("data:") {
                data_lines.push(rest.trim());
            }
        }

        if data_lines.is_empty() {
            return None;
        }
        // Only process `event: job` (or default unnamed events carrying job JSON)
        if let Some(ev) = event_type {
            if ev != "job" {
                return None;
            }
        }

        let data_json = data_lines.join("\n");
        Some(parse_pool_job_json(&data_json))
    }
}

/// Parses either a strict 5-field `V2Job` JSON or an extended `/pool/jobs` JSON object
/// containing optional pool metadata (`height`, `clean_jobs`) alongside the 5 required V2 fields.
pub fn parse_pool_job_json(text: &str) -> Result<PoolJobEvent, V2JobError> {
    let val: serde_json::Value =
        serde_json::from_str(text).map_err(|_| V2JobError::Malformed("invalid JSON"))?;
    let obj = val
        .as_object()
        .ok_or(V2JobError::Malformed("expected a JSON object"))?;

    let height = obj.get("height").and_then(|v| v.as_u64());
    let clean_jobs = obj
        .get("clean_jobs")
        .and_then(|v| v.as_bool())
        .unwrap_or(true);

    // If the JSON has only the 5 canonical fields, validate directly via V2Job::from_json
    if obj.len() == 5 {
        let job = V2Job::from_json(text)?;
        return Ok(PoolJobEvent {
            job,
            height,
            clean_jobs,
        });
    }

    // Reject V1 jobs immediately even when extra metadata is present
    if obj.contains_key("blockhex")
        || obj.get("protocol").and_then(|v| v.as_str()) == Some("v1")
        || obj
            .get("result")
            .and_then(|r| r.get("blockhex"))
            .is_some()
    {
        return Err(V2JobError::V1JobPresentedAsV2);
    }

    // Extract the 5 canonical fields and delegate strict validation to V2Job::from_json
    let mut canonical = serde_json::Map::new();
    for key in ["protocol", "job_id", "chain_id", "header", "target"] {
        if let Some(v) = obj.get(key) {
            canonical.insert(key.to_string(), v.clone());
        } else {
            return Err(V2JobError::Malformed("unexpected or missing fields"));
        }
    }
    let canonical_str = serde_json::Value::Object(canonical).to_string();
    let job = V2Job::from_json(&canonical_str)?;
    Ok(PoolJobEvent {
        job,
        height,
        clean_jobs,
    })
}

/// Builds a verified `PoolShareSubmission` for a winning `nonce` on `job`.
/// Verifies on the CPU that `BlockID <= target` before constructing the submission payload.
pub fn build_verified_submission(
    job: &V2Job,
    worker: &str,
    nonce: u64,
) -> Result<PoolShareSubmission> {
    if worker.trim().is_empty() {
        bail!("worker identifier cannot be empty");
    }
    let mut solved_header = [0u8; HEADER_LEN];
    solved_header.copy_from_slice(job.header());
    solved_header[NONCE_OFFSET..NONCE_OFFSET + 8].copy_from_slice(&nonce.to_le_bytes());

    let (_, _, block_id) = hashes(&solved_header, job.chain_id())?;
    if !meets_target(&block_id, job.target()) {
        bail!("candidate nonce {nonce} does not meet job target");
    }

    Ok(PoolShareSubmission {
        protocol: "v2".to_string(),
        job_id: job.job_id().to_string(),
        worker: worker.to_string(),
        nonce,
        nonce_hex: format!("{:016x}", nonce),
        header: hex::encode(solved_header),
        block_id: hex::encode(block_id),
    })
}

pub struct V2PoolClient {
    client: Client,
    base_url: String,
    worker: String,
}

impl V2PoolClient {
    pub fn new(base_url: impl Into<String>, worker: impl Into<String>) -> Result<Self> {
        let base_url = base_url.into().trim_end_matches('/').to_string();
        let worker = worker.into();
        if base_url.is_empty() {
            bail!("pool base_url cannot be empty");
        }
        if worker.trim().is_empty() {
            bail!("pool worker cannot be empty");
        }
        Ok(Self {
            client: Client::new(),
            base_url,
            worker,
        })
    }

    pub fn jobs_url(&self) -> String {
        format!("{}/pool/jobs?worker={}", self.base_url, self.worker)
    }

    pub fn submit_url(&self) -> String {
        format!("{}/pool/submit", self.base_url)
    }

    /// Fetches and parses SSE `event: job` events from `GET /pool/jobs`.
    pub async fn fetch_job_events(&self) -> Result<Vec<PoolJobEvent>> {
        let resp = self.client.get(&self.jobs_url()).send().await?;
        if !resp.status().is_success() {
            bail!("GET /pool/jobs failed with status {}", resp.status());
        }
        let body = resp.text().await?;
        let mut parser = SseJobStreamParser::new();
        let mut events = Vec::new();
        for res in parser.push_chunk(&body) {
            events.push(res.map_err(|e| eyre!(e))?);
        }
        Ok(events)
    }

    /// Verifies and submits a winning nonce to `POST /pool/submit`.
    pub async fn submit_share(&self, job: &V2Job, nonce: u64) -> Result<PoolSubmitResponse> {
        let submission = build_verified_submission(job, &self.worker, nonce)?;
        let payload = serde_json::to_string(&submission)?;
        let resp = self
            .client
            .post(&self.submit_url())
            .header("Content-Type", "application/json")
            .body(payload)
            .send()
            .await?;
        let status = resp.status();
        let text = resp.text().await?;
        if !status.is_success() {
            bail!("POST /pool/submit failed ({status}): {text}");
        }
        let parsed: PoolSubmitResponse = serde_json::from_str(&text)?;
        Ok(parsed)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    use tokio::net::TcpListener;

    const TEMPLATE_JSON: &str = r#"{"protocol":"v2","job_id":"native-037-template","chain_id":"000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f","header":"2ba3f975fbc1840b9cb4acc6aa84a88539010eb2132cb06a43168b1cb6b66ae5ffff002178f1536500000000000000000000020000009001000000000000050000000000000033333333333333333333333333333333333333333333333333333333333333334444444444444444444444444444444444444444444444444444444444444444","target":"000000000000000000000000000000000000000000000000000000000000ffff"}"#;

    #[test]
    fn parses_chunked_sse_job_stream_and_ignores_keepalive_or_other_events() {
        let mut parser = SseJobStreamParser::new();
        let sse_part1 = ": keepalive\n\nevent: stats\ndata: {\"miners\":4}\n\nevent: job\n";
        let sse_part2 = format!("data: {}\n\n", TEMPLATE_JSON);

        assert!(parser.push_chunk(sse_part1).is_empty());
        let events = parser.push_chunk(&sse_part2);
        assert_eq!(events.len(), 1);
        let ev = events[0].as_ref().unwrap();
        assert_eq!(ev.job.job_id(), "native-037-template");
        assert!(ev.clean_jobs);
    }

    #[test]
    fn build_verified_submission_checks_target_before_submitting() {
        let job = V2Job::from_json(TEMPLATE_JSON).unwrap();
        // Find a winning nonce within 0..8
        let mut winning_nonce = None;
        for nonce in 0..8u64 {
            if build_verified_submission(&job, "sub:alice@lotus.org", nonce).is_ok() {
                winning_nonce = Some(nonce);
                break;
            }
        }
        let nonce = winning_nonce.expect("template has a valid nonce in 0..8");
        let sub = build_verified_submission(&job, "sub:alice@lotus.org", nonce).unwrap();
        assert_eq!(sub.protocol, "v2");
        assert_eq!(sub.job_id, "native-037-template");
        assert_eq!(sub.worker, "sub:alice@lotus.org");
        assert_eq!(sub.nonce, nonce);
        assert_eq!(sub.header.len(), HEADER_LEN * 2);
        assert_eq!(sub.block_id.len(), 64);

        // Hard target of all zeros must reject submission
        let hard_json = TEMPLATE_JSON.replace(
            "000000000000000000000000000000000000000000000000000000000000ffff",
            &"00".repeat(32),
        );
        let hard_job = V2Job::from_json(&hard_json).unwrap();
        assert!(build_verified_submission(&hard_job, "sub:alice@lotus.org", nonce).is_err());
    }

    #[tokio::test]
    async fn pool_client_fetches_sse_job_and_submits_winning_share() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();

        let server_task = tokio::spawn(async move {
            for _ in 0..2 {
                let (mut stream, _) = listener.accept().await.unwrap();
                let mut buf = vec![0u8; 4096];
                let n = stream.read(&mut buf).await.unwrap();
                let req = String::from_utf8_lossy(&buf[..n]);
                if req.starts_with("GET /pool/jobs") {
                    let body = format!("event: job\ndata: {}\n\n", TEMPLATE_JSON);
                    let resp = format!(
                        "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                        body.len(),
                        body
                    );
                    stream.write_all(resp.as_bytes()).await.unwrap();
                } else if req.starts_with("POST /pool/submit") {
                    let body = r#"{"accepted":true,"block_found":false,"shares_accepted":1,"subscription_unlocked":true}"#;
                    let resp = format!(
                        "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                        body.len(),
                        body
                    );
                    stream.write_all(resp.as_bytes()).await.unwrap();
                }
            }
        });

        let client = V2PoolClient::new(format!("http://{}", addr), "sub:reader@lotus.org").unwrap();
        let jobs = client.fetch_job_events().await.unwrap();
        assert_eq!(jobs.len(), 1);
        let mut job = jobs[0].job.clone();
        assert!(job.mine_local(0, 8).unwrap());
        let mut nonce_bytes = [0u8; 8];
        nonce_bytes.copy_from_slice(&job.header()[NONCE_OFFSET..NONCE_OFFSET + 8]);
        let winning_nonce = u64::from_le_bytes(nonce_bytes);

        let submit_resp = client.submit_share(&job, winning_nonce).await.unwrap();
        assert!(submit_resp.accepted);
        assert_eq!(submit_resp.shares_accepted, 1);
        assert!(submit_resp.subscription_unlocked);

        server_task.await.unwrap();
    }
}
