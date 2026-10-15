#!/usr/bin/env python3
"""Exercise existing NNG consumers with nonzero selection-only fee deltas."""
from decimal import Decimal
from interface_nng_compat import NngCompatTest
from test_framework.util import assert_equal


class CombinedFeeDeltaTest(NngCompatTest):
    applied_delta = False

    def set_test_params(self):
        super().set_test_params()

    def probe(self, command, *args, fails=False, legacy=False):
        if command == "mining" and not fails and not self.applied_delta:
            txids = self.nodes[0].getrawmempool()
            if len(txids) == 1:
                self.nodes[0].prioritisetransaction(txids[0], 0, 123456)
                entry = self.nodes[0].getmempoolentry(txids[0])
                assert_equal(entry["fees"]["modified"] - entry["fees"]["base"], Decimal("0.00123456"))
                self.applied_delta = True
                self.log.info("Applied +123456 sat selection delta; existing template test must still report exactly 1000 sat actual fees and submit a valid block")
        return super().probe(command, *args, fails=fails, legacy=legacy)

    def run_test(self):
        super().run_test()
        assert self.applied_delta


if __name__ == "__main__":
    CombinedFeeDeltaTest().main()
