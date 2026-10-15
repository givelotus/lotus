// Copyright (c) 2026 The Lotus developers
// Distributed under the MIT software license; see the repository COPYING.
// An independent oracle using the pinned Core's actual serializers and hashes.
#include <consensus/validation.h>
#include <crypto/hex_base.h>
#include <primitives/transaction.h>
#include <primitives/block.h>
#include <streams.h>

#include <iostream>
#include <string>
#include <vector>

int main() {
    std::string hex;
    while (std::getline(std::cin, hex)) {
        try {
            if (hex.size() % 2) throw std::ios_base::failure("odd hex");
            std::vector<unsigned char> raw;
            for (size_t index = 0; index < hex.size(); index += 2) {
                raw.push_back(std::stoul(hex.substr(index, 2), nullptr, 16));
            }
            SpanReader reader{raw};
            CMutableTransaction mutable_tx;
            reader >> TX_WITH_WITNESS(mutable_tx);
            if (!reader.empty()) throw std::ios_base::failure("trailing bytes");
            const CTransaction tx{mutable_tx};
            DataStream stripped, full;
            stripped << TX_NO_WITNESS(tx);
            full << TX_WITH_WITNESS(tx);
            CBlock block;
            block.vtx = {MakeTransactionRef(tx), MakeTransactionRef(tx)};
            DataStream block_bytes;
            block_bytes << TX_WITH_WITNESS(block);
            SpanReader block_reader{block_bytes};
            CBlockHeader header;
            block_reader >> header;
            ReadCompactSize(block_reader);
            const size_t first_offset = block_bytes.size() - block_reader.size();
            CMutableTransaction first_tx;
            block_reader >> TX_WITH_WITNESS(first_tx);
            const size_t second_offset = block_bytes.size() - block_reader.size();
            std::cout << "{\"accepted\":true,\"txid\":\"" << tx.GetHash().ToString()
                      << "\",\"wtxid\":\"" << tx.GetWitnessHash().ToString()
                      << "\",\"stripped\":\"" << HexStr(stripped)
                      << "\",\"full\":\"" << HexStr(full)
                      << "\",\"weight\":" << GetTransactionWeight(tx)
                      << ",\"size\":" << full.size()
                      << ",\"stripped_size\":" << stripped.size()
                      << ",\"first_tx_offset\":" << first_offset
                      << ",\"second_tx_offset\":" << second_offset
                      << ",\"has_witness\":" << (tx.HasWitness() ? "true" : "false")
                      << "}\n";
        } catch (const std::exception&) {
            std::cout << "{\"accepted\":false}\n";
        }
    }
}
