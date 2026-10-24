#!/usr/bin/env python3
"""Render docs/lotus-v2/ Markdown specifications into an interactive multi-lens HTML site.

Usage:
    python3 docs/lotus-v2/tools/render_html.py [--out docs/lotus-v2/site]
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SPEC_ROOT = Path(__file__).resolve().parents[1]

# Executive "Why / How / What" Dual-Lens summaries injected onto technical spec pages
# that don't already have inline <div class="lens-grid"> blocks.
PAGE_SUMMARIES: Dict[str, Tuple[str, str, str]] = {
    "consensus.md": (
        "Why: Freeze a complete, deterministic validity function at Genesis so Lotus V2 scales to 100k–1M+ TPS without disruptive hard forks.",
        "In Practice: Every rule that makes a Lotus coin or token valid—how payments balance, how 50% of fees are burned, and why accepted transactions never break while waiting for a block—is locked in upfront.",
        "Under the Hood: Normative rules C01–C28 covering little-endian wire framing, 16-branch/16-path MAST authorization, IndexedTreeRoot commitments, monotone validity (C22a), static Cost Unit (cu) bounds, and 56-byte MonetaryState + history_root transitions.",
    ),
    "decisions/encoding-and-signatures.md": (
        "Why: Eliminate malleability, quadratic sighash bugs, and bloated parent-transaction proofs forever.",
        "In Practice: Every transaction has a fixed, predictable fingerprint so payments can be chained safely before confirmation, and hardware wallets can sign any transaction in constant time without downloading gigabytes of history.",
        "Under the Hood: 16-byte fixed prefix (version=7, packed 64-bit lock word, u16 counts), Merkleized TxID vs. TxHash separation, and O(1) 4-block BLAKE3 BIP340 sighash modes over InputsRoot, OutputsRoot, and CoinsRoot.",
    ),
    "decisions/commitments-and-state.md": (
        "Why: Authenticate every transaction, unspent coin, monetary counter, and historical block header with one hash primitive (BLAKE3) designed for horizontal CPU sharding.",
        "In Practice: Every 134-byte block header acts as a cryptographic vault receipt for the entire blockchain—letting mobile and browser wallets verify any coin balance or past block in ~1 KB.",
        "Under the Hood: Prefix-sharded Subtree A transaction tree, single-leaf-collapsed 256-bit sparse UTXO tree (~27 hashes at 10^8 coins), 56-byte MonetaryState, and O(ctz(H)) binary carry-chain HeaderHistoryFrontier.",
    ),
    "decisions/vm-semantics.md": (
        "Why: Enable rich financial contracts, tokens, covenants, and post-quantum/ZK verification without unbounded gas loops or reentrancy bugs.",
        "In Practice: Smart contracts on Lotus V2 can do high-precision financial math and loop over transaction inputs/outputs, yet their exact maximum cost is known before execution—so you never lose fees to an 'out of gas' revert.",
        "Under the Hood: Structured enumeration loops (depth <= 2), 16..1024-byte (int128..int8192) signed two's-complement arithmetic, OP_SUCCESS_N soft-fork extension scanning, and rich UTXO/output introspection.",
    ),
    "decisions/header-and-mining.md": (
        "Why: Unify block headers and Proof-of-Work on pure tagged BLAKE3 with 48-bit timestamps and smooth integer difficulty adjustment.",
        "In Practice: Blocks target a steady 120-second cadence with smooth difficulty adjustments after every block and year-2106-safe 48-bit timestamps.",
        "Under the Hood: 134-byte header split into 116-byte H_headerbody + 18-byte work suffix (nonce1:u64 || nonce2:u64 || extra_work:u16) hashed in a single 64-byte BLAKE3 compression block, plus exact integer ASERT.",
    ),
    "decisions/resources-and-parameters.md": (
        "Why: Replace arbitrary hard block-size walls with smooth, market-driven parabolic cost curves and automatic congestion fee burning.",
        "In Practice: Normal payments stay cheap (~1 atom/byte), while huge transactions or sudden spam bursts face a smoothly rising fee-burn floor that no miner can bypass.",
        "Under the Hood: Unified Cost Units (cu), one-pass AST size/cost upper bound, parabolic transaction cost C_tx = L + (L^2 >> 17), and rolling integer EMA E_n block fee-burn floor.",
    ),
    "decisions/issuance-and-time.md": (
        "Why: Combine a mathematically exact bootstrap reserve with a permanent work-responsive tail subsidy and 50% fee burn.",
        "In Practice: No abrupt 4-year halving cliffs; issuance decays smoothly block-by-block while rewarding growing mining security, and busy blocks burn XPI to offset issuance.",
        "Under the Hood: Additive subsidy S_n = B_n + T_n with telescoping B_n = max(1, R_n >> 20), integer square-root work response T_{n+1} = isqrt(T_g^2 W_n / W_g), and 50/25/25 Miner/Staker/Treasury coordination.",
    ),
    "addresses.md": (
        "Why: Make Lotus V2 addresses human-readable, error-checked, and compact for standard payments while supporting arbitrary smart-contract MAST roots.",
        "In Practice: Clean `xpi1...` addresses protect against typos and work seamlessly for both single-key payments and multi-branch smart vaults.",
        "Under the Hood: Typed CashAddr/Bech32-style payload binding explicit 32-byte MAST commitments or compact parameterized spending templates.",
    ),
    "psbt.md": (
        "Why: Let hardware wallets, multisig coordinators, and dApps construct and sign native V2 transactions offline.",
        "In Practice: Safely co-sign transactions across phones, browsers, and hardware keys without exposing your private keys.",
        "Under the Hood: Native Lotus V2 PSBT key-value profile carrying resolved Coin records, MAST branch scripts/proofs, and O(1) Merkleized sighash witnesses.",
    ),
    "browser-connect.md": (
        "Why: Connect web apps to wallets without leaking your identity across websites via injected window.* supercookies.",
        "In Practice: Websites can't secretly fingerprint your wallet or balances until you click Connect, and you see clear human-readable intent before signing.",
        "Under the Hood: Capability-scoped W3C MessageChannel (lotus-connect/1) transport with native Lotus V2 contract/branch invocation descriptors.",
    ),
    "peering.md": (
        "Why: Propagate blocks and reconcile high-throughput mempools in sub-second round trips.",
        "In Practice: Payments reach the whole network and lock in via Avalanche pre-consensus in under a second.",
        "Under the Hood: Compact `submitminedheader`, high-bandwidth `SHORTTX`, Avalanche batch voting, and bulk template pre-consensus.",
    ),
    "rationale.md": (
        "Why: Document the engineering tradeoffs that keep Lotus V2 parallelizable and Hard-Fork-Free.",
        "In Practice: Why Lotus avoids fragile design shortcuts from older blockchains and how developers build auctions, timers, and shared state safely.",
        "Under the Hood: Formal justification for excluding OP_BLOCKHEIGHT, OP_UTXOPROOFVERIFY, and read-only inputs to preserve C22a monotone mempool validity.",
    ),
}

NAV_SECTIONS: List[Tuple[str, List[Tuple[str, str]]]] = [
    (
        "1. Start With WHY & HOW",
        [
            ("README.md", "Overview: Why, How & What"),
            ("header-history-tree.md", "Header History Merkle Tree"),
            ("rationale.md", "Design Rationale & Tradeoffs"),
        ],
    ),
    (
        "2. Core Consensus (WHAT)",
        [
            ("consensus.md", "Consensus Rules (C01–C28)"),
            ("decisions/encoding-and-signatures.md", "P01: Encoding & Signatures"),
            ("decisions/commitments-and-state.md", "P02: Commitments & State"),
            ("decisions/vm-semantics.md", "P03: VM Semantics & Opcodes"),
            ("decisions/header-and-mining.md", "P04: 134B Header & BLAKE3 PoW"),
            ("decisions/resources-and-parameters.md", "P05: Cost Units & Parabolic Fees"),
            ("decisions/issuance-and-time.md", "P06: Issuance, Tail & Fee Burn"),
            ("deferred-checks.md", "Deferred Checks (C12a)"),
        ],
    ),
    (
        "3. Wallets, ABI & Contracts",
        [
            ("script-abi.md", "Script & Wallet ABI"),
            ("addresses.md", "Native Addresses (xpi1...)"),
            ("message-signing.md", "Message Signing & Proofs"),
            ("psbt.md", "Native PSBT Profile"),
            ("browser-connect.md", "Browser Connect (lotus-connect/1)"),
            ("examples/README.md", "Smart Contract Examples"),
            ("examples/evm-porting/README.md", "EVM-to-Lotus Porting Guide"),
            ("examples/evm-porting/erc20.md", "Porting ERC-20 Tokens"),
            ("examples/evm-porting/erc721.md", "Porting ERC-721 NFTs"),
            ("examples/evm-porting/markets.md", "Porting AMMs & Order Books"),
        ],
    ),
    (
        "4. Networking & Governance",
        [
            ("peering.md", "Peering & Avalanche Pre-Consensus"),
            ("mempool-reconciliation.md", "Mempool Set Reconciliation"),
            ("validation.md", "Validation & Conformance"),
            ("decisions.md", "Decision Register (D01–D15)"),
            ("decisions/history.md", "Decision History"),
        ],
    ),
    (
        "5. Research (Non-Normative)",
        [
            ("research/README.md", "Research Index"),
            ("research/mining-envelope-alternative.md", "SHA256D Mining Envelope"),
            ("research/burn-data-open-questions.md", "Prunable Burn Data"),
            ("research/burn-demand-economics.md", "Burn Demand Economics"),
            ("research/pairwise-reconciliation-scheduler.proposed.md", "Pairwise Reconciliation Scheduler"),
            ("research/epoch-root-gossip-loop.proposed.md", "Epoch Root Gossip Loop"),
            ("research/epoch-snapshot-routing.proposed.md", "Epoch Snapshot Routing"),
            ("research/shared-reconciliation-steering.proposed.md", "Shared Reconciliation Steering"),
            ("research/ten-root-candidate-study.proposed.md", "Ten-Root Candidate Study"),
            ("research/epoch-clock-open-questions.md", "Epoch Clock Study"),
            ("research/epoch-contribution-proposal.md", "Committed Contributions Review"),
            ("research/epoch-availability-open-decisions.md", "Epoch Availability Decisions"),
            ("research/review-notes.md", "Review Handoff (Oct 2026)"),
        ],
    ),
]


def convert_href(href: str, current_rel: Path) -> str:
    """Convert internal .md links to .html relative links."""
    if href.startswith(("http://", "https://", "mailto:", "#")):
        return href
    path_part, sep, frag = href.partition("#")
    if path_part.endswith(".md"):
        if path_part == "README.md" or path_part.endswith("/README.md"):
            target = (current_rel.parent / path_part).resolve()
            try:
                rel_to_spec = target.relative_to(SPEC_ROOT.resolve())
                if rel_to_spec == Path("README.md"):
                    path_part = path_part[:-9] + "index.html"
                else:
                    path_part = path_part[:-3] + ".html"
            except ValueError:
                path_part = path_part[:-3] + ".html"
        else:
            path_part = path_part[:-3] + ".html"
    return f"{path_part}{sep}{frag}"


def render_inline(text: str, current_rel: Path) -> str:
    """Render inline Markdown (code spans, links, bold, italics) while preserving inline HTML/math."""
    tokens: List[str] = []

    def save_token(val: str) -> str:
        idx = len(tokens)
        tokens.append(val)
        return f"\x00TOK{idx}\x00"

    # Protect inline code `...`
    text = re.sub(
        r"`([^`]+)`",
        lambda m: save_token(f"<code>{html.escape(m.group(1))}</code>"),
        text,
    )
    # Protect display/inline math $$...$$ and $...$
    text = re.sub(
        r"\$\$(.+?)\$\$",
        lambda m: save_token(f'<span class="math-display">$${html.escape(m.group(1))}$$</span>'),
        text,
    )
    text = re.sub(
        r"(?<!\\)\$([^\$\n]+?)\$",
        lambda m: save_token(f'<span class="math-inline">${html.escape(m.group(1))}$</span>'),
        text,
    )
    # Links [label](url)
    def replace_link(m: re.Match) -> str:
        label = m.group(1)
        url = convert_href(m.group(2).strip(), current_rel)
        return save_token(f'<a href="{html.escape(url, quote=True)}">{render_inline(label, current_rel)}</a>')

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, text)

    # Escape remaining HTML unless it's known safe inline tags
    text = html.escape(text, quote=False)
    # Bold **...** and Italic *...*
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)

    for i, tok in enumerate(tokens):
        text = text.replace(f"\x00TOK{i}\x00", tok)
    return text


def slugify(heading: str) -> str:
    s = re.sub(r"<[^>]+>", "", heading).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"


def markdown_to_html(md_text: str, current_rel: Path) -> str:
    lines = md_text.splitlines()
    out: List[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Raw HTML block tags for lens-grid / lens-card
        stripped = line.strip()
        if stripped in (
            '<div class="lens-grid">',
            '<div class="lens-card lens-consumer">',
            '<div class="lens-card lens-engineer">',
            "</div>",
        ):
            out.append(stripped)
            i += 1
            continue

        # Blank line
        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^---+\s*$", stripped):
            out.append("<hr/>")
            i += 1
            continue

        # Fenced code block
        m_fence = re.match(r"^(\s*)```(\w*)\s*$", line)
        if m_fence:
            lang = m_fence.group(2).strip()
            i += 1
            code_lines: List[str] = []
            while i < n and not re.match(r"^\s*```\s*$", lines[i]):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            raw_code = "\n".join(code_lines)
            if lang == "mermaid":
                out.append(f'<div class="mermaid">{html.escape(raw_code)}</div>')
            else:
                cls = f' class="language-{html.escape(lang)}"' if lang else ""
                out.append(f"<pre><code{cls}>{html.escape(raw_code)}</code></pre>")
            continue

        # Display math block $$...$$
        if stripped.startswith("$$"):
            math_lines = [line]
            if not (stripped.endswith("$$") and len(stripped) > 2):
                i += 1
                while i < n:
                    math_lines.append(lines[i])
                    if lines[i].strip().endswith("$$"):
                        break
                    i += 1
            i += 1
            out.append(f'<div class="math-block">{html.escape(chr(10).join(math_lines))}</div>')
            continue

        # Headings
        m_head = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m_head:
            level = len(m_head.group(1))
            content = render_inline(m_head.group(2).strip(), current_rel)
            hid = slugify(content)
            out.append(f'<h{level} id="{hid}">{content}</h{level}>')
            i += 1
            continue

        # Markdown Table
        if "|" in line and i + 1 < n and re.match(r"^\s*\|?[\s:-]+\|[\s|:-]*$", lines[i + 1]):
            headers = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows: List[List[str]] = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append('<div class="table-wrap"><table><thead><tr>')
            for hcell in headers:
                out.append(f"<th>{render_inline(hcell, current_rel)}</th>")
            out.append("</tr></thead><tbody>")
            for r in rows:
                out.append("<tr>")
                for cell in r:
                    out.append(f"<td>{render_inline(cell, current_rel)}</td>")
                out.append("</tr>")
            out.append("</tbody></table></div>")
            continue

        # Blockquote
        if stripped.startswith(">"):
            bq_lines: List[str] = []
            while i < n and lines[i].strip().startswith(">"):
                bq_lines.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append(f"<blockquote>{markdown_to_html(chr(10).join(bq_lines), current_rel)}</blockquote>")
            continue

        # Unordered or Ordered List
        m_list = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m_list:
            ordered = m_list.group(2).endswith(".")
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>")
            while i < n:
                m_item = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if not m_item:
                    break
                item_lines = [m_item.group(3)]
                i += 1
                while i < n and lines[i].strip() and not re.match(r"^(\s*)([-*]|\d+\.)\s+", lines[i]) and not lines[i].startswith("#"):
                    if lines[i].startswith("  ") or lines[i].startswith("\t"):
                        item_lines.append(lines[i].strip())
                        i += 1
                    else:
                        break
                out.append(f"<li>{render_inline(' '.join(item_lines), current_rel)}</li>")
            out.append(f"</{tag}>")
            continue

        # Paragraph
        para_lines: List[str] = []
        while (
            i < n
            and lines[i].strip()
            and not lines[i].startswith("#")
            and not lines[i].strip().startswith("```")
            and not lines[i].strip().startswith(">")
            and not lines[i].strip().startswith("<div")
            and not lines[i].strip().startswith("</div")
            and not re.match(r"^---+\s*$", lines[i].strip())
            and not re.match(r"^(\s*)([-*]|\d+\.)\s+", lines[i])
        ):
            para_lines.append(lines[i].strip())
            i += 1
        if para_lines:
            out.append(f"<p>{render_inline(' '.join(para_lines), current_rel)}</p>")

    return "\n".join(out)


def build_summary_banner(rel_str: str) -> str:
    if rel_str.startswith("research/"):
        return """
    <div class="exec-banner research-banner">
      <div class="exec-why"><strong>Research — non-normative.</strong> This page records an investigation. It defines no rule; a research result enters the specification only through a decision recorded in <a href="{ROOT_PREFIX}decisions/history.html">decision history</a>.</div>
    </div>
    """
    if rel_str not in PAGE_SUMMARIES:
        return ""
    why, everyday, engineer = PAGE_SUMMARIES[rel_str]
    return f"""
    <div class="exec-banner">
      <div class="exec-why"><strong>🎯 {html.escape(why)}</strong></div>
      <div class="lens-grid">
        <div class="lens-card lens-consumer">
          <p>{html.escape(everyday)}</p>
        </div>
        <div class="lens-card lens-engineer">
          <p>{html.escape(engineer)}</p>
        </div>
      </div>
    </div>
    """


def html_template(title: str, sidebar_html: str, banner_html: str, body_html: str, rel_str: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(title)} — Lotus V2 Specification</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css"/>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body, {{delimiters: [{{left: '$$', right: '$$', display: true}}, {{left: '$', right: '$', display: false}}]}});"></script>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
  </script>
  <style>
    :root {{
      --bg: #0b0f19;
      --bg-elev: #111827;
      --bg-card: #161f33;
      --border: #26324d;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --accent: #f472b6;
      --accent-2: #38bdf8;
      --consumer-bg: rgba(16, 185, 129, 0.08);
      --consumer-border: rgba(16, 185, 129, 0.35);
      --engineer-bg: rgba(56, 189, 248, 0.08);
      --engineer-border: rgba(56, 189, 248, 0.35);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.65;
      display: flex;
      min-height: 100vh;
    }}
    aside {{
      width: 290px;
      background: var(--bg-elev);
      border-right: 1px solid var(--border);
      padding: 1.25rem 1rem;
      position: sticky;
      top: 0;
      height: 100vh;
      overflow-y: auto;
      flex-shrink: 0;
    }}
    .brand {{
      font-size: 1.15rem;
      font-weight: 800;
      color: #fff;
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 1rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--border);
    }}
    .brand span {{ color: var(--accent); }}
    .nav-group-title {{
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin: 1.1rem 0 0.4rem 0.4rem;
      font-weight: 700;
    }}
    .nav-link {{
      display: block;
      padding: 0.38rem 0.6rem;
      border-radius: 6px;
      color: var(--text);
      text-decoration: none;
      font-size: 0.88rem;
      margin-bottom: 2px;
    }}
    .nav-link:hover {{ background: rgba(255,255,255,0.06); }}
    .nav-link.active {{
      background: rgba(244, 114, 182, 0.16);
      color: var(--accent);
      font-weight: 600;
    }}
    main {{
      flex: 1;
      max-width: 1080px;
      padding: 0 2.5rem 4rem 2.5rem;
      margin: 0 auto;
    }}
    header.topbar {{
      position: sticky;
      top: 0;
      z-index: 20;
      background: rgba(11, 15, 25, 0.88);
      backdrop-filter: blur(10px);
      border-bottom: 1px solid var(--border);
      padding: 0.75rem 0;
      margin-bottom: 1.75rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 0.75rem;
    }}
    .lens-controls {{
      display: flex;
      gap: 0.4rem;
      background: var(--bg-elev);
      padding: 0.25rem;
      border-radius: 8px;
      border: 1px solid var(--border);
    }}
    .lens-btn {{
      background: transparent;
      border: none;
      color: var(--muted);
      padding: 0.35rem 0.75rem;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
    }}
    .lens-btn.active {{
      background: var(--bg-card);
      color: #fff;
      box-shadow: 0 1px 3px rgba(0,0,0,0.4);
    }}
    .exec-banner {{
      background: var(--bg-elev);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.1rem 1.25rem;
      margin-bottom: 2rem;
    }}
    .research-banner {{
      border-color: #b45309;
      background: rgba(180, 83, 9, 0.12);
    }}
    .research-banner .exec-why {{ margin-bottom: 0; }}
    .exec-why {{
      color: #fff;
      font-size: 1rem;
      margin-bottom: 0.85rem;
    }}
    .lens-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
      gap: 1rem;
      margin: 1rem 0;
    }}
    .lens-card {{
      border-radius: 10px;
      padding: 1rem 1.2rem;
    }}
    .lens-consumer {{
      background: var(--consumer-bg);
      border: 1px solid var(--consumer-border);
    }}
    .lens-engineer {{
      background: var(--engineer-bg);
      border: 1px solid var(--engineer-border);
    }}
    body[data-lens="consumer"] .lens-engineer {{ display: none; }}
    body[data-lens="engineer"] .lens-consumer {{ display: none; }}
    h1, h2, h3, h4 {{ color: #fff; line-height: 1.3; }}
    h1 {{ font-size: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 0.6rem; }}
    h2 {{ font-size: 1.45rem; margin-top: 2.2rem; border-bottom: 1px solid var(--border); padding-bottom: 0.35rem; }}
    h3 {{ font-size: 1.15rem; margin-top: 1.5rem; }}
    a {{ color: var(--accent-2); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{
      font-family: "JetBrains Mono", "SFMono-Regular", Consolas, monospace;
      font-size: 0.86em;
      background: rgba(255,255,255,0.07);
      padding: 0.15em 0.38em;
      border-radius: 4px;
    }}
    pre {{
      background: #070a12;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem 1.2rem;
      overflow-x: auto;
    }}
    pre code {{ background: none; padding: 0; font-size: 0.84rem; }}
    .table-wrap {{ overflow-x: auto; margin: 1.2rem 0; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }}
    th, td {{
      border: 1px solid var(--border);
      padding: 0.55rem 0.8rem;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: var(--bg-elev); color: #fff; font-weight: 600; }}
    blockquote {{
      margin: 1rem 0;
      padding: 0.6rem 1rem;
      border-left: 4px solid var(--accent);
      background: rgba(244, 114, 182, 0.06);
      border-radius: 0 8px 8px 0;
    }}
    hr {{ border: none; border-top: 1px solid var(--border); margin: 2rem 0; }}
  </style>
</head>
<body data-lens="both">
  <aside>
    <a class="brand" href="{{ROOT_PREFIX}}index.html">🪷 <span>Lotus V2</span> Docs</a>
    {sidebar_html}
  </aside>
  <main>
    <header class="topbar">
      <div style="font-size:0.85rem;color:var(--muted);">
        Source: <code>docs/lotus-v2/{html.escape(rel_str)}</code>
      </div>
      <div class="lens-controls" role="group" aria-label="View Mode">
        <button class="lens-btn active" onclick="setLens('both', this)">Full View</button>
        <button class="lens-btn" onclick="setLens('consumer', this)">In Practice</button>
        <button class="lens-btn" onclick="setLens('engineer', this)">Under the Hood</button>
      </div>
    </header>
    {banner_html}
    <article>
      {body_html}
    </article>
  </main>
  <script>
    function setLens(mode, btn) {{
      document.body.setAttribute('data-lens', mode);
      document.querySelectorAll('.lens-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      localStorage.setItem('lotus_v2_lens', mode);
    }}
    const saved = localStorage.getItem('lotus_v2_lens');
    if (saved) {{
      const idx = {{both:0, consumer:1, engineer:2}}[saved] ?? 0;
      const btns = document.querySelectorAll('.lens-btn');
      if (btns[idx]) setLens(saved, btns[idx]);
    }}
  </script>
</body>
</html>
"""


def build_sidebar(current_rel: Path) -> str:
    depth = len(current_rel.parts) - 1
    root_prefix = "../" * depth
    parts: List[str] = []
    for section_title, items in NAV_SECTIONS:
        parts.append(f'<div class="nav-group-title">{html.escape(section_title)}</div>')
        for md_rel, label in items:
            out_rel = "index.html" if md_rel == "README.md" else md_rel[:-3] + ".html"
            active = " active" if Path(md_rel) == current_rel else ""
            parts.append(
                f'<a class="nav-link{active}" href="{root_prefix}{out_rel}">{html.escape(label)}</a>'
            )
    return "\n".join(parts).replace("{ROOT_PREFIX}", root_prefix)


def render_site(out_dir: Path) -> int:
    md_files = sorted(SPEC_ROOT.rglob("*.md"))
    count = 0
    for md_path in md_files:
        rel = md_path.relative_to(SPEC_ROOT)
        if "site" in rel.parts:
            continue
        out_rel = Path("index.html") if rel == Path("README.md") else rel.with_suffix(".html")
        dest = out_dir / out_rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        raw_md = md_path.read_text(encoding="utf-8")
        m_title = re.search(r"^#\s+(.+)$", raw_md, flags=re.MULTILINE)
        title = m_title.group(1).strip() if m_title else rel.stem

        depth = len(rel.parts) - 1
        root_prefix = "../" * depth
        sidebar = build_sidebar(rel)
        banner = build_summary_banner(rel.as_posix())
        body = markdown_to_html(raw_md, rel)
        page = html_template(title, sidebar, banner, body, rel.as_posix()).replace("{ROOT_PREFIX}", root_prefix)
        dest.write_text(page, encoding="utf-8")
        count += 1
    print(f"Rendered {count} HTML pages to {out_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(SPEC_ROOT / "site"), help="Output HTML directory")
    args = parser.parse_args()
    return render_site(Path(args.out).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
