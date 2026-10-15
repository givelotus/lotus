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
        for target in ("v1", "ecash", "doged", "bchn", "bitcoin"):
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
        for target, name in (("bitcoin", "nng"),
                             ("ecash", "tx-chain-limit"), ("v1", "tx-chain-limit"),
                             ("bchn", "long-chain-container-test"),
                             ("doged", "zeromq-remove")):
            with self.assertRaises(ValueError):
                planner.resolve(target, [name], True)

    def test_native_chronik_host_profiles_are_independent_features(self):
        for target in ("bchn", "bitcoin"):
            plan = planner.resolve(target, ["chronik"], False)
            self.assertEqual(plan["patches"], [])
            self.assertEqual(plan["cmake_args"], ["-DBUILD_CHRONIK=ON"])
            self.assertEqual(plan["features"][0]["requires"], [])

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
        self.assertIn("FlatBuffers", plan["features"][0]["warning"])
        self.assertIn("separate Tobias legacy RPC", plan["features"][0]["warning"])

    def test_bchn_diagnostic_check_is_independent_from_mining(self):
        plan = planner.resolve("bchn", ["mempool-check"], True)
        self.assertEqual([Path(p).name for p in plan["patches"]],
                         ["04-topological-mempool-check.patch"])
        self.assertEqual(plan["cmake_args"], [])
        self.assertEqual(plan["features"][0]["requires"], [])

    def test_abc_derived_diagnostics_are_optional_independent_candidates(self):
        for target in ("v1", "ecash", "doged"):
            with self.assertRaises(ValueError):
                planner.resolve(target, ["mempool-check"], False)
            plan = planner.resolve(target, ["mempool-check", "chronik"], True)
            self.assertEqual(len(plan["patches"]), 1)
            self.assertIn("candidates/mempool-diagnostics/" + target,
                          plan["patches"][0])
            self.assertEqual(plan["features"][0]["requires"], [])
            self.assertEqual(plan["cmake_args"], ["-DBUILD_CHRONIK=ON"])
        with self.assertRaises(ValueError):
            planner.resolve("bitcoin", ["mempool-check"], True)

    def test_bchn_disable_then_remove_has_only_its_explicit_dependency(self):
        default = planner.resolve("bchn", ["zeromq-default-off"], True)
        self.assertEqual([Path(p).name for p in default["patches"]], ["11-disable-zeromq.patch"])
        self.assertEqual(default["features"][0]["requires"], [])
        for names in (["zeromq-remove"], ["zeromq-default-off", "zeromq-remove"],
                      ["zeromq-remove", "zeromq-default-off"]):
            plan = planner.resolve("bchn", names, True)
            self.assertEqual([Path(p).name for p in plan["patches"]],
                             ["11-disable-zeromq.patch", "12-remove-zeromq.patch"])
            self.assertEqual(plan["cmake_args"], [])
        plan = planner.resolve("bchn", ["zeromq-remove"], True)
        self.assertEqual(plan["features"][0]["requires"], ["zeromq-default-off"])
        for names in (["zeromq-on", "zeromq-remove"], ["zeromq-remove", "zeromq-off"]):
            with self.assertRaises(ValueError):
                planner.resolve("bchn", names, True)
        for target in ("ecash", "bitcoin", "doged", "v1"):
            with self.assertRaises(ValueError):
                planner.resolve(target, ["zeromq-remove"], True)
        with self.assertRaises(ValueError):
            planner.resolve("bchn", ["zeromq-remove"], False)

    def test_experimental_selection_requires_opt_in(self):
        with self.assertRaises(ValueError):
            planner.resolve("ecash", ["block-construction"], False)
        plan = planner.resolve("ecash", ["block-construction"], True)
        self.assertEqual(len(plan["patches"]), 1)
        self.assertEqual(plan["cmake_args"], [])


if __name__ == "__main__":
    unittest.main()
