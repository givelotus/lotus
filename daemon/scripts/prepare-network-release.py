#!/usr/bin/env python3
"""Optional network preparation for prepare-release.py; no writes or RPC by default."""
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

NETWORKS = {"main": ("CMainParams", "mainNet", "main", 10605),
            "test": ("CTestNetParams", "testNet", "test", 11605)}
HEX = re.compile(r"[0-9a-f]{64}\Z")


def hash_value(value, name):
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise ValueError(name + " must be a lowercase 32-byte hex hash")
    return value


def source_genesis(replay, network):
    text = replay.read("src/kernel/chainparams.cpp")
    cls = NETWORKS[network][0]
    if text.count("class " + cls + " :") != 1:
        raise ValueError("Cannot identify selected Lotus network class")
    section = text.split("class " + cls + " :", 1)[1].split("\nclass ", 1)[0]
    match = re.search(r'assert\(consensus.hashGenesisBlock\s*==\s*uint256S\(((?:\s*"[0-9a-f]+")+)\)\)', section)
    if not match:
        raise ValueError("Cannot identify Lotus genesis assertion in source")
    return hash_value("".join(re.findall(r'"([0-9a-f]+)"', match[1])), "Source genesis")


def lotus_header(raw_hex, height):
    """Lotus uses three single-SHA256 layers, not Bitcoin's double SHA256."""
    if not isinstance(raw_hex, str) or not re.fullmatch(r"[0-9a-fA-F]{320}", raw_hex):
        raise ValueError("Expected exactly 160 bytes of Lotus header")
    raw = bytes.fromhex(raw_hex)
    if raw[52] != 1 or int.from_bytes(raw[60:64], "little", signed=True) != height:
        raise ValueError("Lotus header version/height mismatch")
    layer3 = hashlib.sha256(raw[52:]).digest()
    layer2 = hashlib.sha256(raw[32:52] + layer3).digest()
    return hashlib.sha256(raw[:32] + layer2).digest()[::-1].hex()


def seed_changes(replay, network, seeds):
    if not isinstance(seeds, list) or not seeds:
        raise ValueError("seeds must be an explicit nonempty list of numeric IP:port endpoints")
    normalized = []
    for endpoint in seeds:
        if not isinstance(endpoint, str):
            raise ValueError("Seed endpoint must be text")
        match = re.fullmatch(r"\[([^\]]+)\]:([0-9]+)|([^:\s]+):([0-9]+)", endpoint)
        if not match:
            raise ValueError("Seed must include an explicit port (bracket IPv6)")
        host, port = (match[1], match[2]) if match[1] else (match[3], match[4])
        address = ipaddress.ip_address(host)
        if not address.is_global or address.is_multicast or "%" in host or not 1 <= int(port) <= 65535:
            raise ValueError("Seed must be globally routable with a valid port")
        normalized.append(f"[{address}]:{int(port)}" if address.version == 6 else f"{address}:{int(port)}")
    if len(set(normalized)) != len(normalized):
        raise ValueError("Duplicate seed endpoint")
    suffix = NETWORKS[network][2]
    path = f"contrib/seeds/nodes_{suffix}.txt"
    nodes = "\n".join(sorted(normalized)) + "\n"
    # Use the replayed existing generator offline, with only explicit seed input.
    with tempfile.TemporaryDirectory(prefix="lotus-seeds-") as directory:
        directory = Path(directory)
        generator = directory / "generate-seeds.py"
        generator.write_text(replay.read("contrib/seeds/generate-seeds.py"))
        for other in ("main", "test"):
            data = nodes if other == suffix else replay.read(f"contrib/seeds/nodes_{other}.txt")
            (directory / f"nodes_{other}.txt").write_text(data)
        generated = subprocess.check_output([sys.executable, str(generator), str(directory)], timeout=30).decode()
    pattern = rf"static SeedSpec6 pnSeed6_{suffix}\[\] = \{{.*?\n\}};"
    replacement = re.search(pattern, generated, re.S)
    if not replacement:
        raise ValueError("Existing seed generator output format changed")
    original = replay.read("src/chainparamsseeds.h")
    updated, count = re.subn(pattern, lambda _: replacement[0], original, flags=re.S)
    if count != 1:
        raise ValueError("Cannot identify selected network seed array")
    return {path: nodes, "src/chainparamsseeds.h": updated}


def make_rpc(checkpoint, network):
    cli = Path(checkpoint["cli"]).resolve(strict=True)
    datadir = Path(checkpoint["datadir"]).resolve(strict=True)
    if not cli.is_file() or not datadir.is_dir():
        raise ValueError("Explicit existing Lotus CLI and datadir required")
    expected = hash_value(checkpoint["cli_sha256"], "CLI SHA256")
    if hashlib.sha256(cli.read_bytes()).hexdigest() != expected:
        raise ValueError("Lotus CLI checksum mismatch")

    def rpc(method, *args):
        # No daemon startup or mutating RPC. Never inherit a selected network.
        if method not in {"getblockchaininfo", "getblockhash", "getblockheader"}:
            raise ValueError("RPC method is not read only")
        command = [str(cli), "-datadir=" + str(datadir), "-chain=" + network,
                   "-rpcclienttimeout=15", method, *map(str, args)]
        output = subprocess.check_output(command, stderr=subprocess.PIPE, timeout=20).decode().strip()
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return output
    return rpc


def checkpoint_changes(replay, network, genesis, checkpoint, rpc):
    height, depth = checkpoint["height"], checkpoint["confirmation_depth"]
    if type(height) is not int or height <= 0 or type(depth) is not int or depth < 1:
        raise ValueError("Checkpoint height and confirmation_depth must be positive integers")
    expected = hash_value(checkpoint["hash"], "Checkpoint")

    def verify():
        info = rpc("getblockchaininfo")
        if info.get("chain") != network or info.get("initialblockdownload") is not False:
            raise ValueError("Node network mismatch or initial block download incomplete")
        if type(info.get("blocks")) is not int or info["blocks"] - height < depth:
            raise ValueError("Checkpoint is too recent for requested confirmation depth")
        genesis_hash, block_hash = rpc("getblockhash", 0), rpc("getblockhash", height)
        if genesis_hash != genesis or block_hash != expected:
            raise ValueError("Node genesis/checkpoint identity mismatch")
        genesis_header = rpc("getblockheader", genesis, "false")
        checkpoint_header = rpc("getblockheader", expected, "false")
        if lotus_header(genesis_header, 0) != genesis or lotus_header(checkpoint_header, height) != expected:
            raise ValueError("Locally hashed Lotus header does not match genesis/checkpoint")
        return {"chain": network, "initialblockdownload": False, "blocks": info["blocks"],
                "genesis_hash": genesis_hash, "checkpoint_hash": block_hash,
                "genesis_header": genesis_header, "checkpoint_header": checkpoint_header}

    first = verify()
    path = "src/networks/abc/checkpoints.cpp"
    text = replay.read(path)
    prefix = NETWORKS[network][1]
    pattern = rf"(static CCheckpointData {prefix}CheckpointData = \{{\s*\.mapCheckpoints = \{{)(.*?)(\n    \}}\}};)"
    match = re.search(pattern, text, re.S)
    if not match:
        raise ValueError("Cannot locate selected checkpoint map")
    existing = [int(value) for value in re.findall(r"\{\s*([0-9]+)\s*,", match[2])]
    if existing and height <= max(existing):
        raise ValueError("New checkpoint must be above existing checkpoints")
    body = match[2].rstrip() + f'\n        // Release checkpoint\n        {{{height}, BlockHash{{uint256S("{expected}")}}}},'
    updated = text[:match.start(2)] + body + text[match.end(2):]
    second = verify()  # Refuse a stale/reorged checkpoint before returning any change.
    return {path: updated}, {"height": height, "hash": expected, "confirmation_depth": depth,
                            "verification": {"first": first, "rechecked": second}}


def recorded_rpc(checkpoint):
    """Revalidate operator-reviewed evidence offline; does not assert new freshness."""
    evidence = checkpoint["verification"]
    if not isinstance(evidence, dict) or set(evidence) != {"first", "rechecked"}:
        raise ValueError("Verification requires first and rechecked node observations")
    observations = iter((evidence["first"], evidence["rechecked"]))
    current = None

    def rpc(method, *args):
        nonlocal current
        if method == "getblockchaininfo":
            current = next(observations)
            return current
        if method == "getblockhash":
            return current["genesis_hash" if args[0] == 0 else "checkpoint_hash"]
        if method == "getblockheader":
            return current["genesis_header" if args[0] == current["genesis_hash"] else "checkpoint_header"]
        raise ValueError("Unexpected recorded RPC")
    return rpc



def prepare_network(replay, config, *, allow_rpc=False):
    """Return candidate file replacements and public evidence; caller writes atomically."""
    if not isinstance(config, dict) or set(config) - {"network", "expected_genesis", "seeds", "checkpoint"}:
        raise ValueError("Unknown network release configuration fields")
    network = config.get("network")
    if not isinstance(network, str) or network not in NETWORKS:
        raise ValueError("Select exact network main or test")
    genesis = hash_value(config.get("expected_genesis"), "Expected genesis")
    if source_genesis(replay, network) != genesis:
        raise ValueError("Configured genesis disagrees with replayed Lotus source")
    if "seeds" not in config and "checkpoint" not in config:
        raise ValueError("Supply explicit seeds and/or checkpoint inputs")
    changes, evidence = {}, {"network": network, "expected_genesis": genesis}
    if "seeds" in config:
        changes.update(seed_changes(replay, network, config["seeds"]))
        evidence["seeds"] = config["seeds"]
    if "checkpoint" in config:
        checkpoint = config["checkpoint"]
        common = {"height", "hash", "confirmation_depth"}
        online = common | {"cli", "cli_sha256", "datadir"}
        offline = common | {"verification"}
        if not isinstance(checkpoint, dict) or set(checkpoint) not in (online, offline):
            raise ValueError("Checkpoint requires height/hash/confirmation_depth plus CLI/datadir/checksum or recorded verification")
        if set(checkpoint) == offline:
            rpc = recorded_rpc(checkpoint)
        else:
            if not allow_rpc:
                raise ValueError("Checkpoint verification requires explicit --allow-network-rpc")
            rpc = make_rpc(checkpoint, network)
        files, evidence["checkpoint"] = checkpoint_changes(replay, network, genesis, checkpoint, rpc)
        changes.update(files)
    return changes, evidence
