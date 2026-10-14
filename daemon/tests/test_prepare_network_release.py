import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("network_release", Path(__file__).resolve().parents[1] / "scripts/prepare-network-release.py")
network = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(network)
GENESIS = "c67ec4bf9a9866241cd576e7a9fe40d0d19628f8c0d9e30ec7d4d92abc613d56"
CHECKPOINT = "076a1c453c74e543a6ad022ce91aa2adb6b514b19b1e6784e3b30a200c6bb203"


def header(height):
    raw = bytearray(160)
    raw[52] = 1
    raw[60:64] = height.to_bytes(4, "little")
    return raw.hex()


class Replay:
    def read(self, path):
        if path == "src/kernel/chainparams.cpp":
            return f'class CMainParams : public X {{ assert(consensus.hashGenesisBlock == uint256S("{GENESIS}")); }}'
        if path == "src/networks/abc/checkpoints.cpp":
            return '''static CCheckpointData mainNetCheckpointData = {
    .mapCheckpoints = {
        {5, BlockHash{uint256S("old")}},
    }};
static CCheckpointData testNetCheckpointData = {
    .mapCheckpoints = {
    }};
'''
        if path == "src/chainparamsseeds.h":
            return 'static SeedSpec6 pnSeed6_main[] = {\nOLD_MAIN\n};\nstatic SeedSpec6 pnSeed6_test[] = {\nOLD_TEST\n};\n'
        if path == "contrib/seeds/generate-seeds.py":
            return "# generator comes from replayed source"
        if path.startswith("contrib/seeds/nodes_"):
            return "8.8.8.8:11605\n"
        raise AssertionError(path)


def config():
    observation = {"chain": "main", "initialblockdownload": False, "blocks": 120,
                   "genesis_hash": GENESIS, "checkpoint_hash": CHECKPOINT,
                   "genesis_header": header(0), "checkpoint_header": header(100)}
    return {"network": "main", "expected_genesis": GENESIS,
            "checkpoint": {"height": 100, "hash": CHECKPOINT, "confirmation_depth": 20,
                           "verification": {"first": observation, "rechecked": copy.deepcopy(observation)}}}


class NetworkReleaseTests(unittest.TestCase):
    def test_lotus_hash_and_height(self):
        self.assertEqual(network.lotus_header(header(100), 100), CHECKPOINT)
        for raw, height in (("00" * 80, 100), (header(100), 101)):
            with self.assertRaises(ValueError):
                network.lotus_header(raw, height)

    def test_offline_verified_checkpoint_is_deterministic_and_network_scoped(self):
        settings = config()
        with patch.object(network.subprocess, "check_output", side_effect=AssertionError("No RPC allowed")):
            changes, evidence = network.prepare_network(Replay(), settings)
            again, normalized = network.prepare_network(Replay(), evidence)
        self.assertEqual(changes, again)
        self.assertEqual(evidence, normalized)
        self.assertEqual(settings, config())
        self.assertIn(CHECKPOINT, changes["src/networks/abc/checkpoints.cpp"])
        original_testnet = Replay().read("src/networks/abc/checkpoints.cpp").split("static CCheckpointData testNet", 1)[1]
        self.assertEqual(changes["src/networks/abc/checkpoints.cpp"].split("static CCheckpointData testNet", 1)[1], original_testnet)

    def test_reorg_depth_identity_and_header_fail_closed(self):
        for field, value in (("checkpoint_hash", "a" * 64), ("blocks", 119), ("chain", "test"),
                             ("initialblockdownload", True), ("checkpoint_header", header(99)),
                             ("genesis_header", "00" * 160)):
            settings = config()
            settings["checkpoint"]["verification"]["rechecked"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                network.prepare_network(Replay(), settings)

    def test_rpc_requires_explicit_opt_in(self):
        settings = config()
        checkpoint = settings["checkpoint"]
        del checkpoint["verification"]
        checkpoint.update(cli="/missing", datadir="/missing", cli_sha256="0" * 64)
        with patch.object(network, "make_rpc", side_effect=AssertionError("No RPC")):
            with self.assertRaisesRegex(ValueError, "explicit"):
                network.prepare_network(Replay(), settings)

    def test_online_observations_normalize_to_offline_evidence(self):
        settings = config()
        online = copy.deepcopy(settings)
        del online["checkpoint"]["verification"]
        online["checkpoint"].update(cli="/reviewed/lotus-cli", datadir="/private/node", cli_sha256="0" * 64)
        with patch.object(network, "make_rpc", return_value=network.recorded_rpc(settings["checkpoint"])):
            changes, normalized = network.prepare_network(Replay(), online, allow_rpc=True)
        self.assertEqual(normalized, settings)
        self.assertNotIn("datadir", repr(normalized))
        self.assertEqual(changes, network.prepare_network(Replay(), normalized)[0])

    def test_seed_validation_and_preserving_other_network(self):
        output = 'static SeedSpec6 pnSeed6_main[] = {\nNEW_MAIN\n};\nstatic SeedSpec6 pnSeed6_test[] = {\nGENERATED_TEST\n};\n'
        with patch.object(network.subprocess, "check_output", return_value=output.encode()):
            changes = network.seed_changes(Replay(), "main", ["1.1.1.1:10605"])
        self.assertEqual(changes["contrib/seeds/nodes_main.txt"], "1.1.1.1:10605\n")
        self.assertIn("OLD_TEST", changes["src/chainparamsseeds.h"])
        self.assertIn("NEW_MAIN", changes["src/chainparamsseeds.h"])
        for seeds in ([], ["1.1.1.1"], ["127.0.0.1:10605"], ["1.1.1.1:0"], ["1.1.1.1:10605"] * 2):
            with self.subTest(seeds=seeds), self.assertRaises(ValueError):
                network.seed_changes(Replay(), "main", seeds)

    def test_ambiguous_network_and_genesis_rejected(self):
        for update in ({"network": "testnet"}, {"expected_genesis": "0" * 64}, {"unexpected": True}):
            settings = {**config(), **update}
            with self.assertRaises(ValueError):
                network.prepare_network(Replay(), settings)


if __name__ == "__main__":
    unittest.main()
