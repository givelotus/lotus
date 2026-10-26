// Copyright (c) 2026 The Lotus developers
// Distributed under the MIT software license.
// Standalone driver linked to each variant's actual production SMT library.
#include <lotus_v2/mempool_overlay.h>
#include <util/translation.h>

#include <barrier>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

const std::function<std::string(const char *)> G_TRANSLATION_FUN = nullptr;

namespace {
using Clock = std::chrono::steady_clock;
struct Query {
    lotus::v2::Outpoint outpoint;
    uint64_t value;
};
struct alignas(64) Counts {
    uint64_t lookups{0};
    uint64_t checksum{0};
    uint64_t errors{0};
};
std::string Hex(const lotus::v2::Hash &hash) {
    static constexpr char digits[] = "0123456789abcdef";
    std::string result;
    result.reserve(64);
    for (const uint8_t byte : hash) {
        result.push_back(digits[byte >> 4]);
        result.push_back(digits[byte & 15]);
    }
    return result;
}
} // namespace

int main(int argc, char **argv) {
    try {
        if (argc != 6) {
            throw std::runtime_error("usage: lookup COINS QUERIES THREADS SECONDS hit|miss");
        }
        const size_t coin_count = std::stoull(argv[1]);
        const size_t query_count = std::stoull(argv[2]);
        const size_t thread_count = std::stoull(argv[3]);
        const double seconds = std::stod(argv[4]);
        const std::string mode = argv[5];
        const bool hit = mode == "hit";
        if (!coin_count || !query_count || query_count > coin_count ||
            !thread_count || thread_count > 64 || seconds < 1 ||
            (mode != "hit" && mode != "miss")) {
            throw std::runtime_error("invalid benchmark configuration");
        }
        std::vector<lotus::v2::Coin> coins(coin_count);
        for (size_t i = 0; i < coin_count; ++i) {
            auto &coin = coins[i];
            coin.outpoint.tx_id.fill(0xab);
            const uint64_t encoded_index = static_cast<uint64_t>(i);
            for (size_t byte = 0; byte < 8; ++byte) {
                coin.outpoint.tx_id[byte] = static_cast<uint8_t>(encoded_index >> (8 * byte));
            }
            coin.outpoint.index = static_cast<uint32_t>(i & 3);
            coin.output.value = 1000 + i;
            coin.output.legacy_script = std::vector<uint8_t>{0x51};
            coin.creation_height = 1;
            coin.expiration_height = 100001;
        }
        std::shared_ptr<const lotus::v2::SmtNode> root;
        lotus::v2::SmtBatchUpdateParallel(root, {}, coins);
        if (!root || root->count != coin_count) {
            throw std::runtime_error("tree construction count mismatch");
        }
        std::vector<Query> queries;
        queries.reserve(query_count);
        for (size_t i = 0; i < query_count; ++i) {
            const size_t index = (i * size_t{2654435761}) % coin_count;
            auto outpoint = coins[index].outpoint;
            if (!hit) outpoint.index ^= uint32_t{0x80000000};
            queries.push_back({outpoint, coins[index].output.value});
        }
        // Validate and warm exactly the measured query set before the timer.
        for (const auto &query : queries) {
            const auto found = lotus::v2::SmtFind(root, query.outpoint);
            if (bool(found) != hit ||
                (found && (found->outpoint != query.outpoint ||
                           found->output.value != query.value))) {
                throw std::runtime_error("warmup lookup mismatch");
            }
        }
        std::vector<Counts> results(thread_count);
        std::barrier start(static_cast<std::ptrdiff_t>(thread_count + 1));
        Clock::time_point deadline;
        std::vector<std::jthread> readers;
        readers.reserve(thread_count);
        for (size_t tid = 0; tid < thread_count; ++tid) {
            readers.emplace_back([&, owned = root, tid] {
                Counts local;
                size_t index = tid * queries.size() / thread_count;
                start.arrive_and_wait();
                do {
                    // Amortize clock reads; no allocation or random generation
                    // occurs inside the timed query loop.
                    for (size_t batch = 0; batch < 256; ++batch) {
                        const auto &query = queries[index];
                        const auto found = lotus::v2::SmtFind(owned, query.outpoint);
                        if (bool(found) != hit ||
                            (found && found->output.value != query.value)) {
                            ++local.errors;
                        }
                        if (found) local.checksum += found->output.value;
                        ++local.lookups;
                        if (++index == queries.size()) index = 0;
                    }
                } while (Clock::now() < deadline);
                results[tid] = local;
            });
        }
        const auto begun = Clock::now();
        deadline = begun + std::chrono::duration_cast<Clock::duration>(
            std::chrono::duration<double>(seconds));
        start.arrive_and_wait();
        for (auto &reader : readers) reader.join();
        const double elapsed = std::chrono::duration<double>(Clock::now() - begun).count();
        Counts total;
        for (const auto &result : results) {
            total.lookups += result.lookups;
            total.checksum += result.checksum;
            total.errors += result.errors;
        }
        std::cout << std::setprecision(17)
                  << "{\"kind\":\"SMT lookup microbenchmark\",\"coins\":" << coin_count
                  << ",\"queries\":" << query_count << ",\"threads\":" << thread_count
                  << ",\"mode\":\"" << mode << "\",\"root\":\""
                  << Hex(lotus::v2::SmtRoot(root)) << "\",\"lookups\":" << total.lookups
                  << ",\"seconds\":" << elapsed << ",\"lookups_per_second\":"
                  << double(total.lookups) / elapsed << ",\"checksum\":" << total.checksum
                  << ",\"errors\":" << total.errors << "}\n";
        return total.errors ? 2 : 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
