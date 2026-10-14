"""Feature selection must never silently enable policy patches or missing ports."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "feature_plan", Path(__file__).parents[1] / "scripts/feature-plan.py")
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


class FeatureSelectionTests(unittest.TestCase):
    def test_chronik_has_no_policy_dependencies(self):
        for target in ("v1", "ecash", "doged"):
            plan = planner.resolve(target, ["chronik"], False)
            self.assertEqual(plan["patches"], [])
            self.assertEqual(plan["cmake_args"], ["-DBUILD_CHRONIK=ON"])
            self.assertEqual(plan["features"][0]["requires"], [])

    def test_independent_disable_and_conflicts(self):
        plan = planner.resolve("v1", ["chronik", "nng-off", "zeromq-on"], False)
        self.assertIn("-DBUILD_BITCOIN_NNG=OFF", plan["cmake_args"])
        self.assertIn("-DBUILD_ZMQ=ON", plan["cmake_args"])
        for names in (["chronik", "chronik-off"], ["nng", "nng-off"],
                      ["zeromq-on", "zeromq-off"]):
            with self.assertRaises(ValueError):
                planner.resolve("v1", names, False)

    def test_unimplemented_ports_and_policy_are_rejected(self):
        for target, name in (("bitcoin", "chronik"), ("bitcoin", "nng"),
                             ("ecash", "tx-chain-limit"), ("v1", "tx-chain-limit"),
                             ("bchn", "long-chain-container-test"),
                             ("doged", "zeromq-remove")):
            with self.assertRaises(ValueError):
                planner.resolve(target, [name], True)

    def test_v1_custom_assembler_is_integrated(self):
        plan = planner.resolve("v1", ["block-construction"], False)
        self.assertEqual(plan["patches"], [])
        self.assertEqual(plan["cmake_args"], [])
        self.assertEqual(plan["features"][0]["kind"], "integrated-custom-assembler")
        self.assertEqual(plan["features"][0]["requires"], ["complete-v1-series"])

    def test_bchn_uses_reviewed_ready_priority_candidate(self):
        plan = planner.resolve("bchn", ["block-construction", "zeromq-off"], True)
        self.assertEqual([Path(p).name for p in plan["patches"]],
                         ["01-prioritize-ready-transactions.patch"])
        self.assertEqual(plan["cmake_args"], ["-DBUILD_BITCOIN_ZMQ=OFF"])
        self.assertEqual(plan["features"][0]["requires"], [])

    def test_bchn_nng_is_independent_and_requires_protocol_opt_in(self):
        with self.assertRaises(ValueError):
            planner.resolve("bchn", ["nng"], False)
        plan = planner.resolve("bchn", ["nng", "zeromq-on"], True)
        self.assertEqual([Path(p).name for p in plan["patches"]], ["10-nng-interface.patch"])
        self.assertEqual(plan["cmake_args"], ["-DBUILD_BITCOIN_NNG=ON", "-DBUILD_BITCOIN_ZMQ=ON"])
        self.assertEqual(plan["features"][0]["requires"], [])
        self.assertIn("not Lotus", plan["features"][0]["warning"])

    def test_bchn_diagnostic_check_is_independent_from_mining(self):
        plan = planner.resolve("bchn", ["mempool-check"], True)
        self.assertEqual([Path(p).name for p in plan["patches"]],
                         ["04-topological-mempool-check.patch"])
        self.assertEqual(plan["cmake_args"], [])
        self.assertEqual(plan["features"][0]["requires"], [])
        with self.assertRaises(ValueError):
            planner.resolve("ecash", ["mempool-check"], True)

    def test_experimental_selection_requires_opt_in(self):
        with self.assertRaises(ValueError):
            planner.resolve("ecash", ["block-construction"], False)
        plan = planner.resolve("ecash", ["block-construction"], True)
        self.assertEqual(len(plan["patches"]), 1)
        self.assertEqual(plan["cmake_args"], [])


if __name__ == "__main__":
    unittest.main()
