// Actual radix microbenchmark. Build/run commands and raw pair receipts live
// beside this file. Baseline headers are from the full-width equality tip.
#include <arith_uint256.h>
#include <bench/nanobench.h>
#include <crypto/sha256.h>
#include <radix.h>
#include <uint256.h>
#include <uint256radixkey.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

using Clock = std::chrono::steady_clock;
struct Entry {
    Uint256RadixKey key;
    uint64_t ordinal;
    Entry(const arith_uint256 &value, uint64_t index) : key(value), ordinal(index) {}
    const Uint256RadixKey &getId() const { return key; }
    IMPLEMENT_RCU_REFCOUNT(uint32_t);
};

static uint64_t Mix(uint64_t value) {
    value = (value ^ (value >> 30)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31);
}

template <typename Key> static uint32_t Extract(const Key &key, uint32_t level) {
    if constexpr (requires { key.GetNibble(level); }) {
        return key.GetNibble(level);
    } else {
        return static_cast<uint32_t>(size_t((key >> (level * 4)) & 15));
    }
}

struct Corpus {
    std::vector<RCUPtr<Entry>> entries;
    std::vector<Uint256RadixKey> missing;
    std::vector<size_t> order;
    std::string digest;
    uint64_t extraction_sum{0}, hit_sum{0}, lookup_sum{0};
    Corpus(size_t count, const std::string &distribution, uint64_t seed) {
        std::set<arith_uint256> unique;
        for (size_t i = 0; i < count; ++i) {
            const uint64_t low = distribution == "low64" ? 42 : Mix(seed + i);
            const uint64_t high1 = distribution == "prefix" ? Mix(seed + 1) : Mix(seed + i + 1);
            const uint64_t high2 = distribution == "prefix" ? Mix(seed + 2) : Mix(seed + i + 2);
            const uint64_t high3 = distribution == "prefix" ? Mix(seed + 3) : Mix(seed + i + 3);
            const arith_uint256 key = arith_uint256(low) |
                (arith_uint256(high1) << 64) | (arith_uint256(high2) << 128) |
                (arith_uint256(high3) << 192);
            if (!unique.insert(key).second) throw std::runtime_error("nonunique corpus");
            entries.push_back(RCUPtr<Entry>::make(key, i + 1));
        }
        for (const auto &entry : entries) {
            arith_uint256 miss = entry->key.base ^ arith_uint256(1);
            while (unique.contains(miss)) ++miss;
            missing.emplace_back(miss);
        }
        order.resize(count);
        std::iota(order.begin(), order.end(), 0);
        uint64_t state = seed;
        for (size_t i = count; i > 1; --i) {
            state += 0x9e3779b97f4a7c15ULL;
            std::swap(order[i - 1], order[Mix(state) % i]);
        }
        CSHA256 hash;
        for (size_t i = 0; i < count; ++i) {
            const uint256 value = ArithToUint256(entries[i]->key.base);
            hash.Write(value.begin(), 32);
            const uint256 miss = ArithToUint256(missing[i].base);
            hash.Write(miss.begin(), 32);
            // Encode order canonically, independently of host size_t/endian.
            uint8_t encoded[8];
            for (unsigned byte = 0; byte < 8; ++byte) encoded[byte] = static_cast<uint8_t>(uint64_t(order[i]) >> (byte * 8));
            hash.Write(encoded, 8);
        }
        uint8_t result[32];
        hash.Finalize(result);
        constexpr char hex[] = "0123456789abcdef";
        for (uint8_t byte : result) { digest += hex[byte >> 4]; digest += hex[byte & 15]; }
        for (size_t cursor = 0; cursor < count; ++cursor) {
            const auto &entry = entries[order[cursor]];
            const uint32_t level = cursor % 64;
            const auto expected = (entry->key.base >> (4 * level)).GetLow64() & 15;
            if (Extract(entry->key, level) != expected) throw std::runtime_error("extraction oracle mismatch");
            extraction_sum += expected;
            hit_sum += entry->ordinal;
            if (cursor % 2 == 0) lookup_sum += entry->ordinal;
        }
    }
};

enum class Mode { Extraction, Insert, Hit, Miss, Lookup };
struct Result { uint64_t operations{0}, checksum{0}; double active{0}, wall{0}; };
template <Mode mode> static Result Run(const Corpus &data, double seconds) {
    RadixTree<Entry> lookup;
    if constexpr (mode == Mode::Hit || mode == Mode::Miss || mode == Mode::Lookup) {
        for (const auto &entry : data.entries) {
            if (!lookup.insert(entry)) throw std::runtime_error("setup insert failed");
        }
        for (size_t i = 0; i < data.entries.size(); ++i) {
            if (lookup.get(data.entries[i]->key) != data.entries[i] || lookup.get(data.missing[i])) {
                throw std::runtime_error("lookup oracle mismatch");
            }
        }
    }
    Result out;
    const auto wall_start = Clock::now();
    uint64_t rounds = 0;
    while (out.active < seconds) {
        // Entry creation, fresh tree lifetime and reclamation are outside the
        // measured insertion loop; actual node allocation remains inside it.
        {
            RadixTree<Entry> fresh;
            const auto start = Clock::now();
            for (size_t cursor = 0; cursor < data.order.size(); ++cursor) {
                const size_t index = data.order[cursor];
                if constexpr (mode == Mode::Extraction) {
                    const auto &key = data.entries[index]->key;
                    const uint32_t level = cursor % 64;
                    ankerl::nanobench::doNotOptimizeAway(key);
                    ankerl::nanobench::doNotOptimizeAway(level);
                    out.checksum += Extract(key, level);
                } else if constexpr (mode == Mode::Insert) {
                    const bool inserted = fresh.insert(data.entries[index]);
                    ankerl::nanobench::doNotOptimizeAway(inserted);
                    out.checksum += inserted;
                } else {
                    const auto found = lookup.get((mode == Mode::Hit || (mode == Mode::Lookup && cursor % 2 == 0))
                        ? data.entries[index]->key : data.missing[index]);
                    ankerl::nanobench::doNotOptimizeAway(found);
                    out.checksum += found ? found->ordinal : 0;
                }
            }
            out.active += std::chrono::duration<double>(Clock::now() - start).count();
            out.operations += data.order.size();
            ++rounds;
            ankerl::nanobench::doNotOptimizeAway(out.checksum);
            if constexpr (mode == Mode::Insert) {
                // Validate actual retained leaves after timing, before retirement.
                for (const auto &entry : data.entries) {
                    if (fresh.get(entry->key) != entry) throw std::runtime_error("insert oracle mismatch");
                }
            }
        } // Retire the fresh tree before synchronization, outside timing.
        if constexpr (mode == Mode::Insert) RCULock::synchronize();
    }
    RCULock::synchronize();
    out.wall = std::chrono::duration<double>(Clock::now() - wall_start).count();
    const uint64_t expected = rounds * (mode == Mode::Extraction ? data.extraction_sum
        : mode == Mode::Insert ? data.entries.size() : mode == Mode::Hit ? data.hit_sum
        : mode == Mode::Lookup ? data.lookup_sum : 0);
    if (out.checksum != expected) throw std::runtime_error("timed checksum mismatch");
    return out;
}

int main(int argc, char **argv) {
    try {
        if (argc != 7) throw std::runtime_error("usage: bench label workload distribution count seconds seed");
        const std::string label = argv[1], workload = argv[2], distribution = argv[3];
        if (workload != "extraction" && workload != "lookup-hit" && workload != "lookup-miss" && workload != "lookup" && workload != "insert") throw std::runtime_error("unknown workload");
        if (distribution != "uniform" && distribution != "low64" && distribution != "prefix") throw std::runtime_error("unknown distribution");
        const size_t count = std::stoull(argv[4]);
        const double seconds = std::stod(argv[5]);
        const uint64_t seed = std::stoull(argv[6]);
        if (count == 0 || count > 1000000 || seconds < 0.01) throw std::runtime_error("invalid size/duration");
        const Corpus data(count, distribution, seed);
        auto run = [&]<Mode mode>() {
            Run<mode>(data, 0.25);
            RCULock::synchronize();
            return Run<mode>(data, seconds);
        };
        const Result result = workload == "extraction" ? run.template operator()<Mode::Extraction>()
            : workload == "insert" ? run.template operator()<Mode::Insert>()
            : workload == "lookup-hit" ? run.template operator()<Mode::Hit>()
            : workload == "lookup-miss" ? run.template operator()<Mode::Miss>()
            : run.template operator()<Mode::Lookup>();
        RCULock::synchronize();
        std::cout << std::setprecision(12) << "{\"label\":\"" << label
            << "\",\"workload\":\"" << workload << "\",\"distribution\":\"" << distribution
            << "\",\"count\":" << count << ",\"seed\":" << seed
            << ",\"dataset_sha256\":\"" << data.digest << "\",\"requested_seconds\":" << seconds
            << ",\"active_seconds\":" << result.active << ",\"wall_seconds\":" << result.wall
            << ",\"operations\":" << result.operations << ",\"checksum\":" << result.checksum
            << ",\"ns_per_operation\":" << result.active * 1e9 / result.operations << "}\n";
    } catch (const std::exception &error) { std::cerr << error.what() << '\n'; return 1; }
}
