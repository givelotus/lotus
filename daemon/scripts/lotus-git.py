#!/usr/bin/env python3
"""Mechanistic Git branch & patch-stack manager for Lotus monorepo subdaemons.

Provides a zero-footgun CLI wrapper around subdaemon workspaces so humans and AI
agents work with standard Git commits and branches (`daemon/v2`, `daemon/ecash`,
`daemon/v1`, `daemon/doged`, `daemon/bchn`, `daemon/bitcoin`) while keeping:
  1. Monorepo `main` strictly fast-forward (never force-pushed).
  2. Stacked branches (`base/abc -> daemon/ecash -> daemon/v2`) automatically
     aligned via `rebase.updateRefs=true`.
  3. `daemon/patches/<series>/` and `series` manifests deterministically
     synchronized from the workspace Git branches.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
DAEMON_DIR = SCRIPT_DIR.parent
MONOREPO_ROOT = DAEMON_DIR.parent


@dataclass(frozen=True)
class SeriesSpec:
    name: str
    workspace_dir: str
    branch: str
    pin_file: str
    head_pin_file: str
    base_tag: str
    patches_dir: str
    upstream_url: str
    parent_series: Optional[str] = None
    include_directive: Optional[str] = None


SERIES_SPECS: Dict[str, SeriesSpec] = {
    "ecash": SeriesSpec(
        name="ecash",
        workspace_dir="workspace-ecash",
        branch="daemon/ecash",
        pin_file="bitcoin-abc-version",
        head_pin_file="ecash-version",
        base_tag="base/abc",
        patches_dir="patches/ecash",
        upstream_url="https://github.com/Bitcoin-ABC/bitcoin-abc.git",
    ),
    "v2": SeriesSpec(
        name="v2",
        workspace_dir="workspace-v2",
        branch="daemon/v2",
        pin_file="bitcoin-abc-version",
        head_pin_file="v2-version",
        base_tag="base/abc",
        patches_dir="patches/v2",
        upstream_url="https://github.com/Bitcoin-ABC/bitcoin-abc.git",
        parent_series="ecash",
        include_directive="@include ../ecash/series",
    ),
    "v1": SeriesSpec(
        name="v1",
        workspace_dir="workspace-v1",
        branch="daemon/v1",
        pin_file="bitcoin-abc-v1-version",
        head_pin_file="lotusd-version",
        base_tag="base/v1",
        patches_dir="patches/v1",
        upstream_url="https://github.com/Bitcoin-ABC/bitcoin-abc.git",
    ),
    "doged": SeriesSpec(
        name="doged",
        workspace_dir="workspace-doged-abc",
        branch="daemon/doged",
        pin_file="bitcoin-abc-version",
        head_pin_file="doged-version",
        base_tag="base/abc",
        patches_dir="patches/doged",
        upstream_url="https://github.com/Bitcoin-ABC/bitcoin-abc.git",
    ),
    "bchn": SeriesSpec(
        name="bchn",
        workspace_dir="workspace-bchn",
        branch="daemon/bchn",
        pin_file="bchn-version",
        head_pin_file="bchn-head-version",
        base_tag="base/bchn",
        patches_dir="patches/bchn",
        upstream_url="https://gitlab.com/bitcoin-cash-node/bitcoin-cash-node.git",
    ),
    "bitcoin": SeriesSpec(
        name="bitcoin",
        workspace_dir="workspace-bitcoin",
        branch="daemon/bitcoin",
        pin_file="bitcoin-core-version",
        head_pin_file="bitcoin-head-version",
        base_tag="base/bitcoin",
        patches_dir="patches/bitcoin",
        upstream_url="https://github.com/bitcoin/bitcoin.git",
    ),
}


def run_git(repo: Path, *args: str, check: bool = True) -> str:
    res = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and res.returncode != 0:
        err = res.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {err}")
    return res.stdout.decode("utf-8", errors="replace").strip()


def run_git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args])


def ref_exists(repo: Path, ref: str) -> bool:
    res = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return res.returncode == 0


def read_pin_sha(spec: SeriesSpec) -> str:
    pin_path = DAEMON_DIR / spec.pin_file
    for line in pin_path.read_text().splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            return s
    raise RuntimeError(f"No SHA found in {pin_path}")


def read_head_pin_sha(spec: SeriesSpec) -> Optional[str]:
    pin_path = DAEMON_DIR / spec.head_pin_file
    if not pin_path.is_file():
        return None
    for line in pin_path.read_text().splitlines():
        s = line.strip()
        if s and not s.startswith("#") and re.match(r"^[0-9a-f]{40}$", s):
            return s
    return None


def write_head_pin_sha(spec: SeriesSpec, sha: str) -> None:
    pin_path = DAEMON_DIR / spec.head_pin_file
    header = (
        f"# Pinned {spec.branch} branch tip (base: {read_pin_sha(spec)[:12]}).\n"
        f"# Updated mechanistically by `make -C daemon sync SERIES={spec.name}`.\n"
    )
    pin_path.write_text(header + sha + "\n")


def read_manifest_entries(manifest_path: Path) -> List[str]:
    if not manifest_path.is_file():
        return []
    entries: List[str] = []
    for raw in manifest_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("@include "):
            continue
        entries.append(line)
    return entries


def slugify_subject(subject: str, max_slug_len: int = 52) -> str:
    """Convert a commit subject into a clean kebab-case patch filename slug."""
    s = subject.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > max_slug_len:
        s = s[:max_slug_len].rstrip("-")
    return s or "commit"


def extract_patch_subject(patch_file: Path) -> Optional[str]:
    """Read the Subject header from an existing git format-patch file."""
    if not patch_file.is_file():
        return None
    lines = patch_file.read_text(errors="replace").splitlines()
    subject_parts: List[str] = []
    in_subject = False
    for line in lines:
        if line.startswith("Subject: "):
            in_subject = True
            val = re.sub(r"^Subject:\s*(\[PATCH[^\]]*\]\s*)?", "", line)
            subject_parts.append(val.strip())
        elif in_subject:
            if line.startswith(" ") or line.startswith("\t"):
                subject_parts.append(line.strip())
            else:
                break
    return " ".join(subject_parts) if subject_parts else None


def resolve_ecash_boundary(ws: Path, base_sha: str) -> str:
    """Resolve the commit SHA of refs/heads/daemon/ecash marking the Tier-1/Tier-2 boundary."""
    head_commits = set(run_git(ws, "rev-list", f"{base_sha}..HEAD").splitlines())
    if ref_exists(ws, "refs/heads/daemon/ecash"):
        cand_sha = run_git(ws, "rev-parse", "refs/heads/daemon/ecash^{commit}")
        if cand_sha in head_commits or cand_sha == base_sha:
            return cand_sha

    pinned_ecash = read_head_pin_sha(SERIES_SPECS["ecash"])
    if pinned_ecash and (pinned_ecash in head_commits or pinned_ecash == base_sha):
        return pinned_ecash

    # Initial bootstrap fallback: count entries in daemon/patches/ecash/series
    ecash_entries = read_manifest_entries(DAEMON_DIR / "patches/ecash/series")
    commits = run_git(ws, "rev-list", "--reverse", f"{base_sha}..HEAD").splitlines()
    if len(commits) >= len(ecash_entries) and ecash_entries:
        return commits[len(ecash_entries) - 1]
    raise RuntimeError(
        f"Cannot determine daemon/ecash branch boundary in {ws}. "
        "Run `lotus-git.py init v2 --ecash-tip <sha>` to set it explicitly."
    )


def resolve_workspace_for_spec(spec: SeriesSpec) -> Optional[Path]:
    ws = DAEMON_DIR / spec.workspace_dir
    if ws.is_dir():
        return ws
    if spec.name == "ecash" and (DAEMON_DIR / "workspace-v2").is_dir():
        return DAEMON_DIR / "workspace-v2"
    return None


def ensure_workspace_configured(spec: SeriesSpec, ecash_tip_override: Optional[str] = None) -> Path:
    ws = resolve_workspace_for_spec(spec)
    if ws is None:
        raise RuntimeError(
            f"Workspace {DAEMON_DIR / spec.workspace_dir} does not exist yet. "
            f"Run `make -C daemon setup SERIES={spec.name}` first."
        )
    # Enable automatic stacked branch ref updates, --fixup autosquash, and rerere
    run_git(ws, "config", "rebase.updateRefs", "true")
    run_git(ws, "config", "rebase.autoSquash", "true")
    run_git(ws, "config", "rerere.enabled", "true")

    base_sha = read_pin_sha(spec)
    if ref_exists(ws, base_sha):
        run_git(ws, "tag", "-f", spec.base_tag, base_sha)

    if ws.name == "workspace-v2":
        ecash_sha = ecash_tip_override or resolve_ecash_boundary(ws, base_sha)
        run_git(ws, "branch", "-f", "daemon/ecash", ecash_sha)
        head_sha = run_git(ws, "rev-parse", "HEAD")
        run_git(ws, "branch", "-f", "daemon/v2", head_sha)
    else:
        head_sha = run_git(ws, "rev-parse", "HEAD")
        run_git(ws, "branch", "-f", spec.branch, head_sha)
    return ws


def extract_patch_commit_sha(patch_file: Path) -> Optional[str]:
    """Read the 40-char commit SHA from the first `From <sha>` line of a patch file."""
    if not patch_file.is_file():
        return None
    first_line = patch_file.read_text(errors="replace").splitlines()[:1]
    if not first_line:
        return None
    m = re.match(r"^From\s+([0-9a-f]{40})\b", first_line[0])
    return m.group(1) if m else None


def export_range_to_patches_dir(
    ws: Path,
    start_sha: str,
    end_sha: str,
    patches_dir: Path,
    include_directive: Optional[str] = None,
    header_comment: Optional[str] = None,
) -> Tuple[int, str]:
    """Deterministically export `start_sha..end_sha` into `patches_dir` and update `series`.

    Preserves existing patch filenames in `patches_dir` whenever the commit index and
    subject match, and preserves existing file bytes verbatim when the commit SHA is
    unchanged, eliminating unnecessary churn in monorepo git diffs.
    """
    commits = run_git(ws, "rev-list", "--reverse", f"{start_sha}..{end_sha}").splitlines()
    if not commits:
        raise RuntimeError(f"Commit range {start_sha[:10]}..{end_sha[:10]} is empty")

    # Verify linear history (no merge commits)
    parent = run_git(ws, "rev-parse", f"{start_sha}^{{commit}}")
    for c in commits:
        parents = run_git(ws, "rev-list", "--parents", "-n", "1", c).split()
        if parents != [c, parent]:
            raise RuntimeError(
                f"Non-linear commit history detected at {c[:10]} (expected single parent {parent[:10]}). "
                "Rebase to a linear stack before syncing."
            )
        parent = c

    existing_manifest = patches_dir / "series"
    existing_entries = read_manifest_entries(existing_manifest)

    # Map existing 1-based index -> (filename, subject, commit_sha)
    existing_by_idx: Dict[int, Tuple[str, Optional[str], Optional[str]]] = {}
    existing_by_sha: Dict[str, Tuple[str, Path]] = {}
    for idx, fname in enumerate(existing_entries, start=1):
        pfile = patches_dir / fname
        c_sha = extract_patch_commit_sha(pfile)
        existing_by_idx[idx] = (fname, extract_patch_subject(pfile), c_sha)
        if c_sha:
            existing_by_sha[c_sha] = (fname, pfile)

    # Preserve any leading `#` comment lines from existing series file if header_comment not supplied
    preserved_comments: List[str] = []
    if existing_manifest.is_file() and header_comment is None:
        for raw in existing_manifest.read_text().splitlines():
            if raw.startswith("#"):
                preserved_comments.append(raw)
            else:
                break
    elif header_comment:
        preserved_comments.append(header_comment)

    patches_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".lotus-sync-{patches_dir.name}-", dir=patches_dir.parent))
    try:
        # Copy any non-.patch metadata files (e.g. manifest.json) if present
        if patches_dir.is_dir():
            for item in patches_dir.iterdir():
                if item.is_file() and not item.name.endswith(".patch") and item.name != "series":
                    shutil.copy2(item, temp_dir / item.name)

        new_entries: List[str] = []
        used_names = set()
        for idx, commit in enumerate(commits, start=1):
            subject = run_git(ws, "log", "-1", "--format=%s", commit)
            prefix = f"{idx:03d}"

            chosen_name: Optional[str] = None
            reuse_existing_path: Optional[Path] = None

            if idx in existing_by_idx:
                old_name, old_subj, old_sha = existing_by_idx[idx]
                if (old_sha == commit or old_subj == subject) and old_name.startswith(f"{prefix}-") and old_name not in used_names:
                    chosen_name = old_name
                    if old_sha == commit and (patches_dir / old_name).is_file():
                        reuse_existing_path = patches_dir / old_name

            if not chosen_name:
                slug = slugify_subject(subject)
                chosen_name = f"{prefix}-{slug}.patch"
                if commit in existing_by_sha:
                    _, old_path = existing_by_sha[commit]
                    if old_path.is_file():
                        reuse_existing_path = old_path

            used_names.add(chosen_name)
            if reuse_existing_path is not None:
                shutil.copy2(reuse_existing_path, temp_dir / chosen_name)
            else:
                patch_bytes = run_git_bytes(
                    ws,
                    "-c",
                    "format.signature=",
                    "format-patch",
                    "--stdout",
                    "--binary",
                    "--full-index",
                    "--no-stat",
                    "-1",
                    commit,
                )
                if b"\ndiff --git " not in patch_bytes:
                    raise RuntimeError(f"Empty commit cannot be exported: {commit[:10]} ({subject})")
                (temp_dir / chosen_name).write_bytes(patch_bytes)
            new_entries.append(chosen_name)

        series_lines: List[str] = []
        series_lines.extend(preserved_comments)
        if include_directive:
            series_lines.append(include_directive)
        series_lines.extend(new_entries)
        (temp_dir / "series").write_text("\n".join(series_lines) + "\n")

        # Atomically swap temp_dir into patches_dir
        backup_dir = patches_dir.parent / f".lotus-old-{patches_dir.name}"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        if patches_dir.exists():
            os.rename(patches_dir, backup_dir)
        os.rename(temp_dir, patches_dir)
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    tree_sha = run_git(ws, "rev-parse", f"{end_sha}^{{tree}}")
    return len(commits), tree_sha


def cmd_status(args: argparse.Namespace) -> int:
    targets = [args.series] if args.series else list(SERIES_SPECS.keys())
    print(f"{'SERIES':<8} {'WORKSPACE':<22} {'BRANCH':<16} {'BASE':<12} {'COMMITS':<18} {'PATCHES':<14} {'STATE'}")
    print("-" * 108)
    for name in targets:
        spec = SERIES_SPECS[name]
        ws = resolve_workspace_for_spec(spec)
        base_sha = read_pin_sha(spec)[:10]
        manifest_count = len(read_manifest_entries(DAEMON_DIR / spec.patches_dir / "series"))
        if ws is None:
            print(
                f"{name:<8} {spec.workspace_dir:<22} {'(not created)':<16} {base_sha:<12} "
                f"{'-':<18} {str(manifest_count) + ' files':<14} uninitialized"
            )
            continue

        ws_label = ws.name if ws.name == spec.workspace_dir else f"{ws.name} (shared)"
        dirty = bool(run_git(ws, "status", "--porcelain", check=False))
        cur_branch = run_git(ws, "rev-parse", "--abbrev-ref", "HEAD", check=False)
        full_base = read_pin_sha(spec)
        if spec.name == "v2" and ref_exists(ws, full_base):
            try:
                ecash_sha = resolve_ecash_boundary(ws, full_base)
                ecash_cnt = int(run_git(ws, "rev-list", "--count", f"{full_base}..{ecash_sha}"))
                v2_cnt = int(run_git(ws, "rev-list", "--count", f"{ecash_sha}..HEAD"))
                commit_str = f"{ecash_cnt} ecash + {v2_cnt} v2"
                ecash_manifest_cnt = len(read_manifest_entries(DAEMON_DIR / "patches/ecash/series"))
                in_sync = (ecash_cnt == ecash_manifest_cnt) and (v2_cnt == manifest_count)
            except Exception:
                commit_str = "?"
                in_sync = False
        elif spec.name == "ecash" and ws.name == "workspace-v2" and ref_exists(ws, full_base):
            try:
                ecash_sha = resolve_ecash_boundary(ws, full_base)
                ecash_cnt = int(run_git(ws, "rev-list", "--count", f"{full_base}..{ecash_sha}"))
                cur_branch = "daemon/ecash"
                commit_str = f"{ecash_cnt} commits"
                in_sync = ecash_cnt == manifest_count
            except Exception:
                commit_str = "?"
                in_sync = False
        elif ref_exists(ws, full_base):
            cnt = int(run_git(ws, "rev-list", "--count", f"{full_base}..HEAD"))
            commit_str = f"{cnt} commits"
            in_sync = cnt == manifest_count
        else:
            commit_str = "?"
            in_sync = False

        state = "DIRTY" if dirty else ("SYNCED" if in_sync else "NEEDS_SYNC")
        print(
            f"{name:<8} {ws_label:<22} {cur_branch[:15]:<16} {base_sha:<12} "
            f"{commit_str:<18} {str(manifest_count) + ' files':<14} {state}"
        )
    return 0


def verify_linear_and_no_fixups(ws: Path, start_sha: str, end_sha: str, allow_fixups: bool = False) -> int:
    commits = run_git(ws, "rev-list", "--reverse", f"{start_sha}..{end_sha}").splitlines()
    parent = run_git(ws, "rev-parse", f"{start_sha}^{{commit}}")
    for c in commits:
        parents = run_git(ws, "rev-list", "--parents", "-n", "1", c).split()
        if parents != [c, parent]:
            raise RuntimeError(
                f"Non-linear commit history detected at {c[:10]} (expected single parent {parent[:10]}). "
                "Rebase to a linear stack before syncing."
            )
        subj = run_git(ws, "log", "-1", "--format=%s", c)
        if not allow_fixups and (subj.startswith("fixup! ") or subj.startswith("squash! ")):
            raise RuntimeError(
                f"Unsquashed fixup/squash commit detected at {c[:10]} ('{subj}'). "
                f"Run `make -C daemon autosquash SERIES=v2` (or `GIT_SEQUENCE_EDITOR=: git -C {ws} rebase -i {start_sha[:12]}`) to autosquash before syncing."
            )
        parent = c
    return len(commits)


def cmd_init(args: argparse.Namespace) -> int:
    spec = SERIES_SPECS[args.series]
    ws = ensure_workspace_configured(spec, ecash_tip_override=args.ecash_tip)
    base_sha = read_pin_sha(spec)
    print(f"Configured {ws} for mechanistic branch workflow:")
    print(f"  • rebase.updateRefs = true")
    print(f"  • rebase.autoSquash = true")
    print(f"  • rerere.enabled    = true")
    print(f"  • {spec.base_tag:<17} = {base_sha[:12]}")
    if ws.name == "workspace-v2":
        ecash_sha = run_git(ws, "rev-parse", "refs/heads/daemon/ecash")
        print(f"  • daemon/ecash      = {ecash_sha[:12]}")
    head_sha = run_git(ws, "rev-parse", f"refs/heads/{spec.branch}")
    print(f"  • {spec.branch:<17} = {head_sha[:12]}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    spec = SERIES_SPECS[args.series]
    ws = ensure_workspace_configured(spec)
    if run_git(ws, "status", "--porcelain"):
        raise RuntimeError(f"Workspace {ws} has uncommitted changes. Commit or stash before running sync.")

    base_sha = read_pin_sha(spec)
    head_sha = run_git(ws, "rev-parse", f"refs/heads/{spec.branch}")
    export_patches = getattr(args, "export_patches", False)

    if spec.name == "v2":
        ecash_sha = resolve_ecash_boundary(ws, base_sha)
        ecash_spec = SERIES_SPECS["ecash"]
        ecash_count = verify_linear_and_no_fixups(ws, base_sha, ecash_sha)
        v2_count = verify_linear_and_no_fixups(ws, ecash_sha, head_sha)
        write_head_pin_sha(ecash_spec, ecash_sha)
        write_head_pin_sha(spec, head_sha)
        print(f"Pinned two-tier branch SHAs from {ws.name}:")
        print(f"  • daemon/ecash ({ecash_count} commits) -> daemon/{ecash_spec.head_pin_file} ({ecash_sha[:12]})")
        print(f"  • daemon/v2    ({v2_count} commits) -> daemon/{spec.head_pin_file}    ({head_sha[:12]})")

        if export_patches:
            ecash_count, ecash_tree = export_range_to_patches_dir(
                ws=ws,
                start_sha=base_sha,
                end_sha=ecash_sha,
                patches_dir=DAEMON_DIR / ecash_spec.patches_dir,
            )
            v2_count, v2_tree = export_range_to_patches_dir(
                ws=ws,
                start_sha=ecash_sha,
                end_sha=head_sha,
                patches_dir=DAEMON_DIR / spec.patches_dir,
                include_directive=spec.include_directive,
            )
            print(f"Exported optional patch files:")
            print(f"  • daemon/{ecash_spec.patches_dir}/ (tree {ecash_tree[:12]})")
            print(f"  • daemon/{spec.patches_dir}/    (tree {v2_tree[:12]})")
    else:
        count = verify_linear_and_no_fixups(ws, base_sha, head_sha)
        write_head_pin_sha(spec, head_sha)
        print(f"Pinned {spec.branch} ({count} commits) -> daemon/{spec.head_pin_file} ({head_sha[:12]})")
        if export_patches:
            count, tree_sha = export_range_to_patches_dir(
                ws=ws,
                start_sha=base_sha,
                end_sha=head_sha,
                patches_dir=DAEMON_DIR / spec.patches_dir,
            )
            print(f"Exported {count} patches -> daemon/{spec.patches_dir}/ (tree {tree_sha[:12]})")

    if args.verify_replay and export_patches:
        series_file = DAEMON_DIR / spec.patches_dir / "series"
        expected_tree = run_git(ws, "rev-parse", f"refs/heads/{spec.branch}^{{tree}}")
        print(f"Verifying clean patch replay against {base_sha[:12]}...")
        subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "patch-series.py"),
                str(ws),
                str(series_file),
                "--base",
                base_sha,
                "--check",
                "--expect-tree",
                expected_tree,
            ],
            check=True,
        )
        print(f"Verified: exported patch series reproduces tree {expected_tree[:12]} byte-for-byte.")

    if args.push:
        monorepo_origin = run_git(MONOREPO_ROOT, "remote", "get-url", "origin")
        refs_to_push = [f"refs/heads/{spec.branch}:refs/heads/{spec.branch}"]
        if spec.name == "v2":
            refs_to_push.insert(0, "refs/heads/daemon/ecash:refs/heads/daemon/ecash")
        for refspec in refs_to_push:
            if "refs/heads/main" in refspec or "refs/heads/master" in refspec:
                raise RuntimeError("Refusing to force-push main/master!")
            print(f"Pushing {refspec} to {monorepo_origin} (--force-with-lease)...")
            run_git(ws, "push", "--force-with-lease", monorepo_origin, refspec)

    return 0


def cmd_sink_to_ecash(args: argparse.Namespace) -> int:
    """Move a commit from the daemon/v2 layer down onto the tip of daemon/ecash."""
    spec = SERIES_SPECS["v2"]
    ws = ensure_workspace_configured(spec)
    if run_git(ws, "status", "--porcelain"):
        raise RuntimeError(f"Workspace {ws} has uncommitted changes. Commit or stash first.")

    base_sha = read_pin_sha(spec)
    ecash_sha = resolve_ecash_boundary(ws, base_sha)
    head_sha = run_git(ws, "rev-parse", "HEAD")
    target_sha = run_git(ws, "rev-parse", f"{args.commit}^{{commit}}")

    v2_commits = run_git(ws, "rev-list", "--reverse", f"{ecash_sha}..{head_sha}").splitlines()
    if target_sha not in v2_commits:
        raise RuntimeError(
            f"Commit {target_sha[:10]} is not in the daemon/v2 layer ({ecash_sha[:10]}..{head_sha[:10]})."
        )

    remaining_v2 = [c for c in v2_commits if c != target_sha]
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_ref = f"refs/backups/pre-sink-{ts}"
    run_git(ws, "update-ref", backup_ref, head_sha)
    orig_branch = run_git(ws, "rev-parse", "--abbrev-ref", "HEAD")

    subj = run_git(ws, "log", "-1", "--format=%s", target_sha)
    print(f"Sinking commit {target_sha[:10]} ('{subj}') to the tip of daemon/ecash ({ecash_sha[:10]})...")
    print(f"Backup ref saved at {backup_ref}")

    try:
        run_git(ws, "checkout", "--detach", ecash_sha)
        run_git(ws, "cherry-pick", target_sha)
        new_ecash_sha = run_git(ws, "rev-parse", "HEAD")
        for c in remaining_v2:
            run_git(ws, "cherry-pick", c)
        new_v2_sha = run_git(ws, "rev-parse", "HEAD")

        # Update branch pointers atomically
        run_git(ws, "branch", "-f", "daemon/ecash", new_ecash_sha)
        run_git(ws, "branch", "-f", "daemon/v2", new_v2_sha)
        if orig_branch != "HEAD":
            run_git(ws, "checkout", "-B", orig_branch, new_v2_sha)
    except Exception as exc:
        print(f"ERROR during sink-to-ecash; restoring {orig_branch} to {head_sha[:10]}...", file=sys.stderr)
        run_git(ws, "cherry-pick", "--abort", check=False)
        if orig_branch != "HEAD":
            run_git(ws, "checkout", "-f", orig_branch, check=False)
            run_git(ws, "reset", "--hard", head_sha, check=False)
        else:
            run_git(ws, "checkout", "--detach", head_sha, check=False)
        raise RuntimeError(f"Failed to sink commit cleanly: {exc}") from exc

    print(f"Success! New daemon/ecash tip: {new_ecash_sha[:12]}, new daemon/v2 tip: {new_v2_sha[:12]}")
    if not args.no_sync:
        sync_ns = argparse.Namespace(
            series="v2",
            export_patches=getattr(args, "export_patches", False),
            verify_replay=False,
            push=False,
        )
        cmd_sync(sync_ns)
    return 0


def cmd_rebase_upstream(args: argparse.Namespace) -> int:
    """Rebase a subdaemon stack (including stacked ecash -> v2) onto a new upstream commit."""
    spec = SERIES_SPECS[args.series]
    ws = ensure_workspace_configured(spec)
    if run_git(ws, "status", "--porcelain"):
        raise RuntimeError(f"Workspace {ws} has uncommitted changes. Commit or stash first.")

    old_base = read_pin_sha(spec)
    head_sha = run_git(ws, "rev-parse", "HEAD")
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_ref = f"refs/backups/pre-rebase-{spec.name}-{ts}"
    run_git(ws, "update-ref", backup_ref, head_sha)

    if args.onto == "latest":
        print(f"Fetching latest default branch from {spec.upstream_url}...")
        run_git(ws, "fetch", spec.upstream_url, "HEAD")
        new_base = run_git(ws, "rev-parse", "FETCH_HEAD^{commit}")
    else:
        if not ref_exists(ws, args.onto):
            run_git(ws, "fetch", spec.upstream_url, args.onto)
        new_base = run_git(ws, "rev-parse", f"{args.onto}^{{commit}}")

    if new_base == old_base:
        print(f"{spec.name} is already based on {new_base[:12]}.")
        return 0

    print(f"Rebasing {spec.branch} from {old_base[:12]} onto {new_base[:12]} (with --update-refs)...")
    print(f"Backup ref saved at {backup_ref}")
    run_git(ws, "rebase", "--update-refs", "--onto", new_base, old_base, "HEAD")

    # Update the pin file and base tag
    pin_path = DAEMON_DIR / spec.pin_file
    pin_path.write_text(new_base + "\n")
    run_git(ws, "tag", "-f", spec.base_tag, new_base)

    print(f"Rebase complete! Updated daemon/{spec.pin_file} -> {new_base[:12]}")
    if not args.no_sync:
        sync_ns = argparse.Namespace(
            series=spec.name,
            export_patches=getattr(args, "export_patches", False),
            verify_replay=False,
            push=False,
        )
        cmd_sync(sync_ns)
    return 0


def cmd_extract_pr(args: argparse.Namespace) -> int:
    """Cherry-pick selected commit(s) onto a clean branch directly off the upstream base pin."""
    spec = SERIES_SPECS[args.series]
    ws = ensure_workspace_configured(spec)
    if run_git(ws, "status", "--porcelain"):
        raise RuntimeError(f"Workspace {ws} has uncommitted changes. Commit or stash first.")

    base_sha = read_pin_sha(spec)
    orig_head = run_git(ws, "rev-parse", "HEAD")
    orig_branch = run_git(ws, "rev-parse", "--abbrev-ref", "HEAD")

    resolved_commits: List[str] = []
    for item in args.commits:
        if ".." in item:
            resolved_commits.extend(run_git(ws, "rev-list", "--reverse", item).splitlines())
        else:
            resolved_commits.append(run_git(ws, "rev-parse", f"{item}^{{commit}}"))

    if not resolved_commits:
        raise RuntimeError("No commits specified to extract.")

    print(f"Creating clean upstream PR branch '{args.branch}' on {base_sha[:12]} ({spec.base_tag})...")
    try:
        run_git(ws, "checkout", "-B", args.branch, base_sha)
        for c in resolved_commits:
            subj = run_git(ws, "log", "-1", "--format=%s", c)
            print(f"  • cherry-picking {c[:10]}: {subj}")
            run_git(ws, "cherry-pick", c)
        pr_tip = run_git(ws, "rev-parse", "HEAD")
    finally:
        if orig_branch != "HEAD":
            run_git(ws, "checkout", orig_branch)
        else:
            run_git(ws, "checkout", "--detach", orig_head)

    print(
        f"Ready! Clean upstream PR branch '{args.branch}' ({len(resolved_commits)} commits, tip {pr_tip[:12]}) "
        f"created in {ws}."
    )
    return 0


def cmd_autosquash(args: argparse.Namespace) -> int:
    """Non-interactively autosquash all fixup!/squash! commits in base..HEAD and update stacked refs."""
    spec = SERIES_SPECS[args.series]
    ws = ensure_workspace_configured(spec)
    if run_git(ws, "status", "--porcelain"):
        raise RuntimeError(f"Workspace {ws} has uncommitted changes. Commit or stash first.")

    base_sha = read_pin_sha(spec)
    head_sha = run_git(ws, "rev-parse", "HEAD")
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_ref = f"refs/backups/pre-autosquash-{spec.name}-{ts}"
    run_git(ws, "update-ref", backup_ref, head_sha)

    print(f"Autosquashing fixup!/squash! commits in {base_sha[:12]}..HEAD (with --update-refs)...")
    print(f"Backup ref saved at {backup_ref}")
    env = dict(os.environ)
    env["GIT_SEQUENCE_EDITOR"] = "true"
    env["GIT_EDITOR"] = "true"
    subprocess.run(
        ["git", "-C", str(ws), "rebase", "-i", "--autosquash", "--update-refs", base_sha],
        env=env,
        check=True,
    )
    new_head = run_git(ws, "rev-parse", "HEAD")
    run_git(ws, "branch", "-f", spec.branch, new_head)
    print(f"Autosquash complete! New {spec.branch} tip: {new_head[:12]}")
    if not args.no_sync:
        sync_ns = argparse.Namespace(
            series=spec.name,
            export_patches=getattr(args, "export_patches", False),
            verify_replay=False,
            push=False,
        )
        cmd_sync(sync_ns)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("status", help="Show branch, base, and pin-sync status for subdaemons")
    p_status.add_argument("series", nargs="?", choices=list(SERIES_SPECS.keys()))
    p_status.set_defaults(func=cmd_status)

    p_init = sub.add_parser("init", help="Configure workspace Git refs, rebase.updateRefs, autoSquash, and rerere")
    p_init.add_argument("series", choices=list(SERIES_SPECS.keys()))
    p_init.add_argument("--ecash-tip", help="Explicit commit SHA for the daemon/ecash boundary in workspace-v2")
    p_init.set_defaults(func=cmd_init)

    p_sync = sub.add_parser("sync", help="Pin workspace Git branch SHAs (and optionally push or export legacy patches)")
    p_sync.add_argument("series", choices=list(SERIES_SPECS.keys()))
    p_sync.add_argument("--export-patches", action="store_true", help="Also export legacy .patch files to daemon/patches/")
    p_sync.add_argument("--verify-replay", action="store_true", help="Verify exported patches replay to exact HEAD^{tree}")
    p_sync.add_argument("--push", action="store_true", help="Push refs/heads/daemon/<series> to origin with --force-with-lease")
    p_sync.set_defaults(func=cmd_sync)

    p_autosquash = sub.add_parser(
        "autosquash",
        help="Non-interactively squash all fixup!/squash! commits in base..HEAD and update stacked refs",
    )
    p_autosquash.add_argument("series", nargs="?", default="v2", choices=list(SERIES_SPECS.keys()))
    p_autosquash.add_argument("--export-patches", action="store_true", help="Also export legacy .patch files after autosquash")
    p_autosquash.add_argument("--no-sync", action="store_true", help="Skip auto-syncing after autosquash")
    p_autosquash.set_defaults(func=cmd_autosquash)

    p_sink = sub.add_parser(
        "sink-to-ecash",
        help="Move a commit from the daemon/v2 layer down onto the tip of daemon/ecash in workspace-v2",
    )
    p_sink.add_argument("commit", nargs="?", default="HEAD", help="Commit in daemon/v2 to sink (default: HEAD)")
    p_sink.add_argument("--export-patches", action="store_true", help="Also export legacy .patch files after sinking")
    p_sink.add_argument("--no-sync", action="store_true", help="Skip auto-syncing after sinking")
    p_sink.set_defaults(func=cmd_sink_to_ecash)

    p_rebase = sub.add_parser(
        "rebase-upstream",
        help="Rebase daemon/<series> (and stacked daemon/ecash) onto a new upstream commit with --update-refs",
    )
    p_rebase.add_argument("series", choices=list(SERIES_SPECS.keys()))
    p_rebase.add_argument("--onto", required=True, help="Target upstream commit SHA, tag, or 'latest'")
    p_rebase.add_argument("--export-patches", action="store_true", help="Also export legacy .patch files after rebase")
    p_rebase.add_argument("--no-sync", action="store_true", help="Skip auto-syncing after rebase")
    p_rebase.set_defaults(func=cmd_rebase_upstream)

    p_pr = sub.add_parser(
        "extract-pr",
        help="Cherry-pick selected commit(s) onto a clean branch based directly on upstream for submitting PRs",
    )
    p_pr.add_argument("series", choices=list(SERIES_SPECS.keys()))
    p_pr.add_argument("--branch", required=True, help="Name of the clean upstream PR branch to create")
    p_pr.add_argument("commits", nargs="+", help="Commit SHA(s) or range(s) to cherry-pick onto base")
    p_pr.set_defaults(func=cmd_extract_pr)

    return p


def main() -> int:
    # The submodule source model replaces workspace replay for this migration.
    # Keep historical helper functions available for old evidence/tests.
    if (DAEMON_DIR / "sources.json").is_file():
        from daemon_sources import main as source_main
        return source_main(sys.argv[1:])
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(f"lotus-git error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
