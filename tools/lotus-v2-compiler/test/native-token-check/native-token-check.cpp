// Independent native checks of compiler-emitted P01 transaction and signing bytes.
// The native P01 candidate does not execute scripts or validate whole blocks.
#include "signing.h"

#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

using namespace lotus::v2;

namespace {
std::vector<uint8_t> Hex(const std::string &value) {
    if (value.size() % 2) throw std::runtime_error("hex width");
    std::vector<uint8_t> bytes;
    for (size_t i = 0; i < value.size(); i += 2) {
        const auto nibble = [](char c) -> uint8_t {
            if (c >= '0' && c <= '9') return uint8_t(c - '0');
            if (c >= 'a' && c <= 'f') return uint8_t(c - 'a' + 10);
            throw std::runtime_error("hex digit");
        };
        bytes.push_back(uint8_t((nibble(value[i]) << 4) | nibble(value[i + 1])));
    }
    return bytes;
}
Hash HashHex(const std::string &value) {
    const auto bytes = Hex(value);
    if (bytes.size() != 32) throw std::runtime_error("hash width");
    Hash result{};
    std::copy(bytes.begin(), bytes.end(), result.begin());
    return result;
}
size_t Number(const char *text) {
    const std::string value(text);
    if (value.empty() || value.find_first_not_of("0123456789") != std::string::npos)
        throw std::runtime_error("decimal integer");
    const auto parsed = std::stoull(value);
    if (parsed > std::numeric_limits<size_t>::max()) throw std::runtime_error("integer overflow");
    return size_t(parsed);
}
struct Amount {
    uint64_t lo = 0, hi = 0;
    void Add(uint64_t value) {
        const uint64_t old = lo;
        lo += value;
        if (lo < old && ++hi == 0) throw std::runtime_error("token amount overflow");
    }
    bool operator>(const Amount &other) const {
        return hi > other.hi || (hi == other.hi && lo > other.lo);
    }
    PositiveDelta Minus(const Amount &other) const {
        if (!(*this > other)) throw std::runtime_error("nonpositive mint delta");
        const uint64_t low = lo - other.lo;
        const uint64_t high = hi - other.hi - (lo < other.lo ? 1 : 0);
        PositiveDelta result{};
        for (size_t i = 0; i < 8; ++i) {
            result[i] = uint8_t(low >> (8 * i));
            result[8 + i] = uint8_t(high >> (8 * i));
        }
        return result;
    }
};
void Require(bool condition, const std::string &reason) {
    if (!condition) throw std::runtime_error(reason);
}
} // namespace

int main(int argc, char **argv) {
    try {
        // wire chain txid txhash coin-count coin-or-dash... signature-count
        // (input-index witness-index argument-index pubkey digest branch-index-or-dash delta-or-dash)...
        Require(argc >= 7, "usage: wire chain txid txhash coin-count coins... signature-count checks...");
        const TxProfile profile{32, 32, 8, 8192, 16, 8192, 64};
        const auto wire = Hex(argv[1]);
        const ChainId chain = HashHex(argv[2]);
        Transaction tx;
        std::string error;
        Require(DecodeTransaction(wire, profile, tx, error), "transaction: " + error);
        IdentityDigests ids;
        Require(ComputeIdentities(tx, profile, chain, ids, error), "identities: " + error);
        if (std::string(argv[3]) != "-") Require(ids.txid == HashHex(argv[3]), "core TxID mismatch");
        if (std::string(argv[4]) != "-") Require(ids.txhash == HashHex(argv[4]), "full TxHash mismatch");
        const size_t coin_count = Number(argv[5]);
        Require(coin_count == tx.inputs.size(), "resolved coin count mismatch");
        Require(size_t(argc) >= 7 + coin_count, "missing resolved coins");
        ResolvedCoins resolved;
        for (size_t i = 0; i < coin_count; ++i) {
            if (std::string(argv[6 + i]) == "-") {
                resolved.push_back(std::nullopt);
            } else {
                Output coin;
                Require(DecodeOutput(Hex(argv[6 + i]), coin, error), "resolved coin: " + error);
                resolved.push_back(coin);
            }
        }
        std::map<Hash, Amount> input_amounts, output_amounts;
        std::map<Hash, size_t> mint_count;
        size_t invocation_count = 0;
        for (size_t i = 0; i < tx.inputs.size(); ++i) {
            const auto &input = tx.inputs[i];
            if (input.flags == 1) {
                Require(resolved[i].has_value() && !resolved[i]->IsBurn(), "spend resolved coin");
                const auto &coin = *resolved[i];
                Require(input.path_index < coin.paths.size(), "spend path index");
                const auto &path = coin.paths[input.path_index];
                Require(path.size() == input.witnesses.size(), "selected path witness count");
                for (size_t j = 0; j < path.size(); ++j) {
                    Require(path[j] < coin.branches.size(), "branch index");
                    const auto &witness = input.witnesses[j];
                    Require(BranchProofRoot(BranchLeaf(witness.script), witness.siblings) == coin.branches[path[j]],
                            "selected branch proof mismatch");
                    ++invocation_count;
                }
                if (coin.HasToken()) input_amounts[coin.token_id].Add(coin.value);
            } else if (input.flags == 3) {
                Require(!resolved[i].has_value(), "mint resolved coin must be null");
                Require(input.witnesses.size() == 1, "mint witness count");
                const auto &witness = input.witnesses[0];
                Require(BranchProofRoot(BranchLeaf(witness.script), witness.siblings) == input.prev_txid,
                        "mint branch proof mismatch");
                ++mint_count[input.prev_txid];
                ++invocation_count;
            } else {
                throw std::runtime_error("unsupported coinbase input");
            }
        }
        for (const auto &output : tx.outputs)
            if (output.HasToken()) output_amounts[output.token_id].Add(output.value);
        std::map<Hash, PositiveDelta> deltas;
        for (const auto &[token, total] : output_amounts)
            if (total > input_amounts[token]) deltas[token] = total.Minus(input_amounts[token]);
        for (const auto &[token, count] : mint_count)
            Require(count == 1 && deltas.contains(token), "mint coverage or duplicate mint");
        Require(deltas.size() == mint_count.size(), "uncovered positive token delta");

        const size_t sig_count_pos = 6 + coin_count;
        const size_t sig_count = Number(argv[sig_count_pos]);
        Require(size_t(argc) == sig_count_pos + 1 + 7 * sig_count, "signature argument count");
        for (size_t n = 0; n < sig_count; ++n) {
            const size_t base = sig_count_pos + 1 + 7 * n;
            const size_t input_index = Number(argv[base]);
            const size_t witness_index = Number(argv[base + 1]);
            const size_t argument_index = Number(argv[base + 2]);
            Require(input_index < tx.inputs.size(), "signature input index");
            const auto &input = tx.inputs[input_index];
            Require(witness_index < input.witnesses.size(), "signature witness index");
            const auto &arguments = input.witnesses[witness_index].arguments;
            Require(argument_index < arguments.size(), "signature argument index");
            const auto &signature = arguments[argument_index];
            const bool mint = input.flags == 3;
            if (mint) {
                Require(std::string(argv[base + 5]) == "-", "mint selector branch index");
                const auto &derived = deltas.at(input.prev_txid);
                Require(Hex(argv[base + 6]) == std::vector<uint8_t>(derived.begin(), derived.end()),
                        "mint positive delta mismatch");
            } else {
                Require(resolved[input_index].has_value(), "signature resolved coin");
                const auto &path = resolved[input_index]->paths.at(input.path_index);
                Require(witness_index < path.size() && Number(argv[base + 5]) == path[witness_index],
                        "spend selector branch index mismatch");
                Require(std::string(argv[base + 6]) == "-", "spend selector positive delta");
            }
            Require(signature.size() == 64, "FULL signature width");
            const uint8_t mode = 0;
            const std::optional<PositiveDelta> delta = mint ? std::optional<PositiveDelta>(deltas.at(input.prev_txid)) : std::nullopt;
            Hash digest;
            Require(SigningMessage(tx, profile, chain, resolved, input_index, witness_index, mode, delta, digest, error),
                    "signing message: " + error);
            Require(digest == HashHex(argv[base + 4]), "FULL signing message mismatch");
            Require(VerifyBip340Signature(Hex(argv[base + 3]), signature, digest, mint) == SignatureStatus::Valid,
                    "BIP340 signature mismatch");
        }
        std::cout << "native token candidate: " << tx.inputs.size() << " inputs, "
                  << invocation_count << " proven branches, " << sig_count
                  << " signatures, " << mint_count.size() << " mint(s)\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
