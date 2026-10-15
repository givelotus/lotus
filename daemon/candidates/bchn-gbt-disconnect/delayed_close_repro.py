#!/usr/bin/env python3
"""Run the actual GBT error test through a TCP proxy that delays FIN propagation."""
import importlib.util
import pathlib
import socket
import sys
import threading
import time

source = pathlib.Path(sys.argv.pop(1))
sys.path.insert(0, str(source / 'test/functional'))
spec = importlib.util.spec_from_file_location('gbt_error_test', source / 'test/functional/mining_getblocktemplate_errors.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class DelayedCloseProxy:
    def __init__(self, target):
        self.target = target
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen()
        self.port = self.listener.getsockname()[1]
        threading.Thread(target=self.accept, daemon=True).start()

    def accept(self):
        while True:
            front, _ = self.listener.accept()
            back = socket.create_connection(('127.0.0.1', self.target))
            threading.Thread(target=self.relay_pair, args=(front, back), daemon=True).start()

    @staticmethod
    def relay_pair(front, back):
        def pump(src, dst):
            try:
                while True:
                    data = src.recv(65536)
                    if not data:
                        break
                    dst.sendall(data)
            except OSError:
                pass
            # Real payloads flow immediately; hold only close propagation so
            # a locally removed peer remains visible at the remote endpoint.
            time.sleep(3)
            try:
                dst.shutdown(socket.SHUT_WR)
            except OSError:
                pass
        threads = [threading.Thread(target=pump, args=(front, back)),
                   threading.Thread(target=pump, args=(back, front))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        front.close()
        back.close()

class ControlledDisconnectTest(module.GetBlockTemplateTest):
    def set_test_params(self):
        super().set_test_params()

    def run_test(self):
        super().run_test()

    def setup_network(self):
        self.setup_nodes()
        self.proxies = [DelayedCloseProxy(node.p2p_port) for node in self.nodes]
        for node, proxy in zip(self.nodes, self.proxies):
            node.p2p_port = proxy.port
        module.connect_nodes_bi(self.nodes[0], self.nodes[1])
        self.sync_all()

ControlledDisconnectTest().main()
