#include "signing.h"
#include "commitment.h"

#include <algorithm>
#include <iostream>
#include <stdexcept>

using namespace lotus::v2;

static std::vector<uint8_t> Hex(const std::string &value) {
    if (value.size() % 2) throw std::runtime_error("hex width");
    std::vector<uint8_t> bytes;
    for (size_t i = 0; i < value.size(); i += 2) {
        const auto nibble = [](char c) -> uint8_t {
            if (c >= '0' && c <= '9') return c - '0';
            if (c >= 'a' && c <= 'f') return c - 'a' + 10;
            throw std::runtime_error("hex digit");
        };
        bytes.push_back((nibble(value[i]) << 4) | nibble(value[i + 1]));
    }
    return bytes;
}
static Hash HashHex(const std::string &value) {
    const auto bytes = Hex(value);
    if (bytes.size() != 32) throw std::runtime_error("hash width");
    Hash result{};
    std::copy(bytes.begin(), bytes.end(), result.begin());
    return result;
}

int main(int argc, char **argv) {
    try {
        if (argc != 9) throw std::runtime_error("wire coin chain pubkey txid txhash message valid|invalid");
        const TxProfile profile{32, 32, 8, 8192, 16, 8192, 64};
        const auto wire = Hex(argv[1]);
        const auto coin_wire = Hex(argv[2]);
        const auto chain_bytes = Hex(argv[3]);
        if (chain_bytes.size() != 32) throw std::runtime_error("chain width");
        ChainId chain{};
        std::copy(chain_bytes.begin(), chain_bytes.end(), chain.begin());
        Transaction tx;
        Output coin;
        std::string error;
        if (!DecodeTransaction(wire, profile, tx, error) || !DecodeOutput(coin_wire, coin, error)) throw std::runtime_error(error);
        const auto &input = tx.inputs.at(0);
        if (input.flags != 1 || input.path_index >= coin.paths.size() || coin.paths[input.path_index].size() != 1 || input.witnesses.size() != 1)
            throw std::runtime_error("unsupported path");
        const auto &witness = input.witnesses.at(0);
        const Hash leaf = BranchLeaf(witness.script);
        const Hash root = BranchProofRoot(leaf, witness.siblings);
        const Hash expected_root = coin.branches.at(coin.paths[input.path_index].at(0));
        if (std::string(argv[8]) == "invalid-proof") {
            if (root == expected_root) throw std::runtime_error("proof unexpectedly valid");
            return 0;
        }
        if (root != expected_root) throw std::runtime_error("branch proof mismatch");
        const ResolvedCoins resolved{coin};
        IdentityDigests ids;
        if (!ComputeIdentities(tx, profile, chain, ids, error)) throw std::runtime_error(error);
        if (std::string(argv[8]) == "valid" &&
            (ids.txid != HashHex(argv[5]) || ids.txhash != HashHex(argv[6]))) throw std::runtime_error("identity mismatch");
        Hash message;
        if (!SigningMessage(tx, profile, chain, resolved, 0, 0, 0, std::nullopt, message, error)) throw std::runtime_error(error);
        if (std::string(argv[8]) == "valid" && message != HashHex(argv[7])) throw std::runtime_error("message mismatch");
        const auto status = VerifyBip340Signature(Hex(argv[4]), tx.inputs.at(0).witnesses.at(0).arguments.at(0), message, false);
        const auto wanted = std::string(argv[8]) == "valid" ? SignatureStatus::Valid : SignatureStatus::InvalidSignature;
        if (status != wanted) throw std::runtime_error("signature status mismatch");
        std::cout << "native candidate " << argv[8] << " at framing/commitment/signature stages\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
