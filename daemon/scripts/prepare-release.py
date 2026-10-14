#!/usr/bin/env python3
"""Prepare release metadata without touching a daemon checkout or publishing."""
import argparse
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PATCH = "999-release-metadata.patch"
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")


def run(args, **kwargs):
    return subprocess.check_output(args, stderr=subprocess.PIPE, **kwargs)


def replace(text, pattern, value):
    result, count = re.subn(pattern, lambda _: value, text)
    if count != 1:
        raise ValueError(f"Expected exactly one occurrence of {pattern!r}; got {count}")
    return result


class Replay:
    """Use a private object database/index; upstream is only an object source."""
    def __init__(self, upstream, directory):
        self.repo = Path(directory) / "objects.git"
        run(["git", "init", "--bare", "-q", str(self.repo)])
        objects = run(["git", "-C", str(upstream), "rev-parse", "--git-path", "objects"]).decode().strip()
        objects = (Path(upstream) / objects).resolve()
        (self.repo / "objects/info/alternates").write_text(str(objects) + "\n")
        self.env = {**os.environ, "GIT_INDEX_FILE": str(Path(directory) / "index"),
                    "GIT_AUTHOR_NAME": "Lotus Release Tool", "GIT_AUTHOR_EMAIL": "build@givelotus.org",
                    "GIT_COMMITTER_NAME": "Lotus Release Tool", "GIT_COMMITTER_EMAIL": "build@givelotus.org",
                    "GIT_AUTHOR_DATE": "2001-09-17T00:00:00Z", "GIT_COMMITTER_DATE": "2001-09-17T00:00:00Z"}

    def git(self, *args, **kwargs):
        return run(["git", "--git-dir=" + str(self.repo), *args], env=self.env, **kwargs)

    def read(self, path):
        return self.git("show", ":" + path).decode()

    def apply(self, patch):
        self.git("apply", "--cached", "--whitespace=nowarn", "-", input=patch)


def metadata(replay, version):
    changes = {}
    path = "CMakeLists.txt"
    changes[path] = replace(replay.read(path), r"(?m)^\s*VERSION [0-9]+\.[0-9]+\.[0-9]+$", "\tVERSION " + version)
    for name in ("lotus", "lotus-qt"):
        path = f"contrib/aur/{name}/PKGBUILD"
        text = replace(replay.read(path), r"(?m)^pkgver=.*$", "pkgver=" + version)
        text = replace(text, r"(?m)^pkgrel=.*$", "pkgrel=1")
        text = replace(text, r"https://github.com/[Ll]ogos[Ff]oundation/lotusd/archive/v\$pkgver.tar.gz", "https://github.com/givelotus/lotus/releases/download/v$pkgver/lotus-v$pkgver-source.tar.gz")
        # Replayed-source assets have one consistent top-level directory.
        text = text.replace("${pkgname}-$pkgver", "lotus-v$pkgver").replace("lotus-$pkgver", "lotus-v$pkgver")
        text = text.replace("arch=('i686' 'x86_64')", "arch=('x86_64')")
        text = text.replace(" 'zeromq'", " 'nng' 'utf8proc' 'sqlite'").replace(" 'miniupnpc'", "").replace(" 'libnatpmp'", "")
        text = text.replace("'cmake' 'ninja'", "'rustup' 'clang' 'curl' 'cmake' 'ninja'")
        text = text.replace("-DBUILD_QT=OFF", "-DBUILD_BITCOIN_QT=OFF").replace("    -DBUILD_IGUANA=OFF \\\n", "")
        text = text.replace("    -DENABLE_CLANG_TIDY=OFF", "    -DBUILD_CHRONIK=ON \\\n    -DRust_TOOLCHAIN=1.93.0 \\\n    -DPython_EXECUTABLE=/usr/bin/python3.13 \\\n    -DBUILD_BITCOIN_ZMQ=OFF \\\n    -DENABLE_UPNP=OFF \\\n    -DENABLE_NATPMP=OFF \\\n    -DENABLE_CLANG_TIDY=OFF")
        text = text.replace('source=(https:', 'source=(https:')
        # All supplementary files come from the authenticated source archive;
        # the historical qt directory did not contain these local inputs.
        start = text.index("source=(")
        end = text.index(")", start) + 1
        text = text[:start] + "source=(https://github.com/givelotus/lotus/releases/download/v$pkgver/lotus-v$pkgver-source.tar.gz)\nsha256sums=('SKIP')\n\nprepare() {\n  curl --fail --location --proto '=https' --tlsv1.2 \\\n    https://github.com/givelotus/lotus/releases/download/v$pkgver/SHA256SUMS -o SHA256SUMS\n  grep -E \"^[0-9a-f]{64}  lotus-v${pkgver//./\\.}-source\\.tar\\.gz$\" SHA256SUMS | sha256sum --check --strict -\n  rustup toolchain install 1.93.0 --profile minimal --component clippy\n}\n" + text[end:]
        text = text.replace("  ninja\n", "  PYO3_PYTHON=/usr/bin/python3.13 ninja\n").replace("  ninja check\n", "  PYO3_PYTHON=/usr/bin/python3.13 ninja check\n")
        text = text.replace('install=lotus.install', 'install=../common/lotus.install')
        for resource in ('lotus.conf', 'lotus.service', 'lotus-reindex.service', 'lotus.logrotate'):
            text = text.replace('"$srcdir/' + resource + '"', '"contrib/aur/common/' + resource + '"')
        text = text.replace('"$srcdir/lotusd.service"', '"contrib/aur/common/lotus.service"').replace('"$srcdir/lotus-reindexd.service"', '"contrib/aur/common/lotus-reindex.service"')
        text = '# Requires /usr/bin/python3.13 (PyO3 0.23); do not substitute newer Python.\n' + text
        changes[path] = text
    path = "contrib/aur/common/lotus.install"
    install = replay.read(path)
    # Package removal must never erase chain data or recursively delete homes.
    install = install.replace("  _rmuser\n  rm -rf /srv/lotus /run/lotus", "  : # Preserve the service account and chain data on uninstall")
    install = install.replace("userdel -rf", "userdel")
    changes[path] = install
    for path in ("contrib/aur/common/lotus.service", "contrib/aur/common/lotus-reindex.service"):
        changes[path] = replay.read(path).replace("ExecStop=/usr/bin/lotusd stop", "ExecStop=/usr/bin/lotus-cli -conf=/etc/lotus/lotus.conf -datadir=/srv/lotus stop")
    path = "contrib/docker/lotus/README.md"
    changes[path] = f'''# Lotus release container

Download `lotus-v{version}-x86_64-linux-gnu.tar.gz` and its SHA256SUMS from
https://github.com/givelotus/lotus/releases/tag/v{version}. Verify the checksum
before building. Run from this directory with the archive beside the Dockerfile:

```sh
docker build -t lotus:{version} --build-arg RELEASE_ARCHIVE=lotus-v{version}-x86_64-linux-gnu.tar.gz .
docker run --rm -v lotus-data:/data lotus:{version}
```

The volume must be writable by the container user. RPC remains bound to loopback;
configure authentication and network exposure explicitly. No image is published
by the release-preparation script. Release CI builds this image and checks lotusd/lotus-cli --version. It does not publish an image or run a synchronized container node.
'''
    path = "contrib/docker/lotus/Dockerfile"
    changes[path] = '''FROM debian:bookworm-slim
ARG RELEASE_ARCHIVE
COPY "${RELEASE_ARCHIVE}" /tmp/release.tar.gz
# Release binaries are dynamically linked; keep their runtime dependencies.
RUN apt-get update && apt-get install -y --no-install-recommends \\
    libboost-chrono1.74.0 libboost-filesystem1.74.0 libboost-system1.74.0 \\
    libboost-thread1.74.0 libevent-2.1-7 libevent-pthreads-2.1-7 \\
    libssl3 libnng1 libjemalloc2 libutf8proc2 libsqlite3-0 libdb5.3++ \\
    && rm -rf /var/lib/apt/lists/* \\
    && tar xzf /tmp/release.tar.gz -C /usr/local --strip-components=1 \\
    && rm /tmp/release.tar.gz
RUN groupadd -r lotus && useradd -rmg lotus lotus \\
    && mkdir /data && chown lotus:lotus /data \\
    && ln -s /data /home/lotus/.lotus
VOLUME /data
EXPOSE 10604 10605
USER lotus
CMD ["lotusd", "-datadir=/data"]
'''
    # The Linux archive is built on Ubuntu24.04. Its ABI cannot run on Debian12.
    changes[path] = changes[path].replace("debian:bookworm-slim", "ubuntu:24.04").replace("1.74.0", "1.83.0").replace("libevent-2.1-7 ", "libevent-2.1-7t64 ").replace("libevent-pthreads-2.1-7 ", "libevent-pthreads-2.1-7t64 ").replace("libssl3 ", "libssl3t64 ").replace("libdb5.3++ ", "libdb5.3++t64 ")
    return changes


def diff(replay, changes):
    parts = []
    for path, new in sorted(changes.items()):
        old = replay.read(path)
        if old != new:
            parts.append(f"diff --git a/{path} b/{path}\n")
            parts.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile="a/" + path, tofile="b/" + path))
    return "".join(parts).encode()


def atomic_write(outputs):
    """Validate/stage every byte first and restore all originals on failure.

    This is a review transaction, not a filesystem snapshot: readers must not
    consume the candidate while it is being prepared.
    """
    originals = {path: path.read_bytes() if path.exists() else None for path in outputs}
    staged = {}
    replaced = []
    try:
        for path, data in outputs.items():
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".release-", delete=False) as stream:
                staged[path] = Path(stream.name)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        for path, temporary in staged.items():
            os.replace(temporary, path)
            replaced.append(path)
    except BaseException:
        for path in reversed(replaced):
            if originals[path] is None:
                path.unlink()
            else:
                path.write_bytes(originals[path])
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


def publish(root, version, reviewed_commit, validation_run=None):
    """Publish only an immutable tag on the exact reviewed, clean main commit.

    Tag CI builds/tests and publishes the binary and replayed-source assets.
    This deliberately never replaces an existing tag or release.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", reviewed_commit):
        raise ValueError("--reviewed-commit must be an exact commit hash")
    def git(*args):
        return run(["git", "-C", str(root), *args]).decode().strip()
    if git("status", "--porcelain"):
        raise ValueError("Publish requires a clean reviewed checkout")
    if git("rev-parse", "HEAD") != reviewed_commit:
        raise ValueError("HEAD differs from --reviewed-commit")
    remote_main = git("ls-remote", "origin", "refs/heads/main").split()
    if not remote_main or remote_main[0] != reviewed_commit:
        raise ValueError("Publish requires the exact reviewed commit on origin/main")
    if validation_run is None:
        raise ValueError("--publish requires --validation-run from successful artifact-only release CI")
    validation = json.loads(run(["gh", "run", "view", str(validation_run), "--repo", "givelotus/lotus",
                                 "--json", "headSha,conclusion,event,workflowName"]))
    if (validation.get("headSha") != reviewed_commit or validation.get("conclusion") != "success"
            or validation.get("event") != "workflow_dispatch"
            or validation.get("workflowName") != "Build & Release Lotus Daemon (with Chronik)"):
        raise ValueError("Validation run must be successful artifact-only release CI for the exact reviewed commit")
    tag = "v" + version
    if git("tag", "--list", tag) or git("ls-remote", "origin", "refs/tags/" + tag):
        raise ValueError("Tag already exists; published releases are immutable")
    manifest = json.loads((root / "daemon/release-manifest.json").read_text())
    git("tag", "-a", tag, reviewed_commit, "-m", f"Lotus {tag}\nSource tree: {manifest['source_tree']}")
    # Leave the new local tag available for an operator to reconcile if the
    # transport fails ambiguously after the remote accepted it.
    git("push", "--atomic", "origin", "refs/tags/" + tag)
    return tag


def prepare(root, upstream, version, write=False, check=False, archive=None, network=None, allow_network_rpc=False):
    if not VERSION.fullmatch(version):
        raise ValueError("Version must be three numeric components without a v prefix or leading zeros")
    daemon = root / "daemon"
    base = (daemon / "bitcoin-abc-v1-version").read_text().splitlines()[0]
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("V1 upstream must be pinned to an exact 40-character commit")
    series_path = daemon / "patches/v1/series"
    series = series_path.read_text()
    entries = [s for s in series.splitlines() if s and not s.startswith("#")]
    if PATCH in entries and entries[-1] != PATCH:
        raise ValueError("Generated release patch must be the final series entry")
    with tempfile.TemporaryDirectory(prefix="lotus-release-") as directory:
        replay = Replay(upstream, directory)
        replay.git("read-tree", base)
        hashes = {}
        for entry in entries:
            if Path(entry).name != entry:
                raise ValueError("Series entries must be patch basenames")
            if entry == PATCH:
                continue
            patch = (daemon / "patches/v1" / entry).read_bytes()
            replay.apply(patch)
            hashes[entry] = hashlib.sha256(patch).hexdigest()
        changes = metadata(replay, version)
        network_path = daemon / "release-network.json"
        config = network if network is not None else (json.loads(network_path.read_text()) if network_path.exists() else None)
        evidence = None
        if config is not None:
            spec = importlib.util.spec_from_file_location("network_release", Path(__file__).with_name("prepare-network-release.py"))
            helper = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(helper)
            network_changes, evidence = helper.prepare_network(replay, config, allow_rpc=allow_network_rpc)
            changes.update(network_changes)
        before_tree = replay.git("write-tree").decode().strip()
        parent = replay.git("commit-tree", before_tree, "-p", base, input=b"Replayed historical Lotus patches\n").decode().strip()
        replay.apply(diff(replay, changes))
        tree = replay.git("write-tree").decode().strip()
        message = (f"Prepare Lotus {version} release metadata\n\n"
                   "Keep daemon version, Arch recipes and container inputs consistent.\n"
                   "Preserve historical patches and chain data; record explicit network\n"
                   "inputs and verification evidence separately when selected.\n\n"
                   "Generated reproducibly by daemon/scripts/prepare-release.py; the\n"
                   "fixed author date is an artifact epoch, not a historical attribution.\n")
        commit = replay.git("commit-tree", tree, "-p", parent, input=message.encode()).decode().strip()
        patch = replay.git("format-patch", "-1", "--stdout", "--no-signature", "--full-index", "--no-stat", commit)
        hashes[PATCH] = hashlib.sha256(patch).hexdigest()
        manifest = {"version": version, "upstream_commit": base, "source_tree": tree, "patch_sha256": hashes}
        outputs = {
            daemon / "release-version": (version + "\n").encode(),
            daemon / "patches/v1" / PATCH: patch,
            daemon / "release-manifest.json": (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
            series_path: (series if PATCH in entries else series.rstrip() + "\n" + PATCH + "\n").encode(),
        }
        if evidence is not None:
            outputs[network_path] = (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode()
        strategy = daemon / "docs/patch-strategy.md"
        if strategy.exists():
            outputs[strategy] = replace(strategy.read_text(), r"(?m)^\*\*Release:\*\* `v[0-9]+\.[0-9]+\.[0-9]+`$", f"**Release:** `v{version}`").encode()
        changed = [str(p.relative_to(root)) for p, data in outputs.items() if not p.exists() or p.read_bytes() != data]
        if check and changed:
            raise ValueError("Release metadata drift: " + ", ".join(changed))
        if write:
            atomic_write(outputs)
        if archive:
            if changed:
                raise ValueError("Run --write followed by --check before archiving")
            # Archive a private deterministic commit so Git uses a fixed mtime
            # even on Git versions predating archive --mtime.
            snapshot = replay.git("commit-tree", tree, input=b"Lotus release source\n").decode().strip()
            replay.git("archive", "--format=tar.gz", f"--prefix=lotus-v{version}/", "--output=" + str(Path(archive).resolve()), snapshot)
        return {"version": version, "source_tree": tree, "changed": changed, "written": write}


def candidate(root, upstream, version, destination, network=None, allow_network_rpc=False):
    """Promote an entire isolated Git candidate with one directory rename.

    Snapshot tracked content plus local edits; never copy ignored workspaces,
    chain data, credentials, or unrelated untracked files.
    """
    destination = destination.resolve()
    if destination.exists():
        raise ValueError("Candidate destination already exists")
    if not destination.parent.is_dir():
        raise ValueError("Candidate parent must already exist")
    with tempfile.TemporaryDirectory(prefix=".lotus-candidate-", dir=destination.parent) as temporary:
        checkout = Path(temporary) / "candidate"
        run(["git", "clone", "--quiet", "--no-hardlinks", "--no-local", str(root), str(checkout)])
        # A worktree HEAD may differ from a clone's default branch.
        head = run(["git", "-C", str(root), "rev-parse", "HEAD"]).decode().strip()
        run(["git", "-C", str(checkout), "checkout", "--quiet", "--detach", head])
        tracked = run(["git", "-C", str(root), "ls-files", "-z"]).decode().split("\0")
        for name in filter(None, tracked):
            source, target = root / name, checkout / name
            if source.exists() or source.is_symlink():
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() or target.is_symlink():
                    target.unlink()
                if source.is_symlink():
                    target.symlink_to(os.readlink(source))
                else:
                    shutil.copy2(source, target)
            else:
                target.unlink(missing_ok=True)
        result = prepare(checkout, upstream, version, write=True, network=network, allow_network_rpc=allow_network_rpc)
        prepare(checkout, upstream, version, check=True)
        os.rename(checkout, destination)
    result["candidate"] = str(destination)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True, help="Existing Git repository containing the pinned ABC base; read only")
    parser.add_argument("--version", help="Target version (default: daemon/release-version)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Write candidate metadata and patch; never commit or publish")
    mode.add_argument("--candidate", type=Path, help="Atomically create a complete isolated Git candidate at a NEW path")
    mode.add_argument("--check", action="store_true", help="Fail if checked-in generated metadata differs")
    mode.add_argument("--publish", action="store_true", help="Check then publish a NEW immutable tag, triggering tested release CI")
    parser.add_argument("--network-input", type=Path, help="Explicit seeds/checkpoint JSON; otherwise preserve recorded release-network.json")
    parser.add_argument("--allow-network-rpc", action="store_true", help="Permit only read-only checkpoint RPC with explicitly supplied CLI/datadir")
    parser.add_argument("--validation-run", help="Successful artifact-only release CI run for the reviewed commit; required for --publish")
    parser.add_argument("--reviewed-commit", help="Exact reviewed origin/main commit; required for --publish")
    parser.add_argument("--archive", type=Path, help="Explicit output path for replayed-source archive; requires --check")
    args = parser.parse_args()
    if args.archive and not args.check:
        parser.error("--archive requires --check")
    if args.publish and (not args.reviewed_commit or not args.validation_run):
        parser.error("--publish requires --reviewed-commit and --validation-run")
    try:
        version = args.version or (ROOT / "daemon/release-version").read_text().strip()
        network = json.loads(args.network_input.read_text()) if args.network_input else None
        if args.candidate:
            result = candidate(ROOT, args.upstream, version, args.candidate, network, args.allow_network_rpc)
        else:
            result = prepare(ROOT, args.upstream, version, args.write, args.check or args.publish, args.archive, network, args.allow_network_rpc)
        if args.publish:
            result["published_tag"] = publish(ROOT, version, args.reviewed_commit, args.validation_run)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        detail = error.stderr.decode() if isinstance(error, subprocess.CalledProcessError) else str(error)
        parser.exit(1, detail + "\n")


if __name__ == "__main__":
    main()
