# Monorepo history made public on 2026-11-01

## What happened

Local `main` was 795 commits ahead of `origin/main` in the public `givelotus/lotus`,
because the consolidation had deliberately not pushed. Pushing `reconcile/daemon-stack`
and `snowstorm-spec` published that history, about 2,040 files and 1.57M added lines.
The owner hadn't approved this. Nothing has been deleted or force-pushed.

## Findings

Pattern scan of all lines added in `origin/main..origin/reconcile/daemon-stack`. This
isn't a manual review of every file.

| Check | Result |
|---|---|
| GitHub, GitLab, Anthropic, AWS and Slack tokens | 0 hits |
| PEM private key bodies | 8 distinct prefixes, all found in Bitcoin ABC `1fb7db17` test fixtures |
| `xprv` keys | 61 distinct, all found in the ABC base |
| Mnemonics | 4 distinct, all found in the ABC base |
| RPC passwords | Placeholders and test fixtures in the lines sampled |
| Key, wallet and credential filenames | 0 hits |
| Commit author emails | `notvalid.com` and the GitHub noreply address only |

Personal or operational material that is public:

- `shammah.chancellor@gmail.com` appears on 1,630 added lines, inside stored patch files.
- `/Users/shammah` paths appear on about 192,000 added lines, mostly logs and evidence.
- `tools/lotus-v2-bench/results/*/host-{before,after}.txt` are process lists of the
  benchmark Mac (about 1,000 lines each), including installed apps such as 1Password.
  Their contents were pattern-checked for tokens and passwords, with no hits.
- Unreleased V2 specs, the node PWA, internal plans and evidence.

## Decision for the owner

Keep it public, or remove it. Removal means deleting `reconcile/daemon-stack` and
`snowstorm-spec` from the remote and closing PR #27. GitHub can keep cached views, and
anyone who fetched already has a copy, so treat everything above as disclosed. Local
`main` remains unpushed.
