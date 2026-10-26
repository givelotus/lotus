"""Pure source-map adapter for a NEW optimization inserted after owner10.
No filesystem/Git mutation; idempotent, supports bytes or str values.
"""
PRODUCTION='src/lotus_v2/commitment.cpp'
TEST='src/test/mempool_overlay_tests.cpp'
OLD='Hash TransactionSubtreeA(const std::vector<const TxIdentityPair *> &entries,\n                         unsigned depth) {\n    if (entries.empty()) return EmptyTxRoot();\n    if (entries.size() == 1) return TxLeaf(*entries[0]);\n    if (depth >= 256) {\n        throw std::invalid_argument("duplicate transaction identifier in subtree");\n    }\n    std::vector<const TxIdentityPair *> left, right;\n    left.reserve(entries.size());\n    right.reserve(entries.size());\n    for (const TxIdentityPair *entry : entries) {\n        (TxKeyBit(entry->tx_id, depth) ? right : left).push_back(entry);\n    }\n    if (depth < 4 && entries.size() >= 64 && !left.empty() && !right.empty()) {\n        auto left_future = std::async(std::launch::async, [&left, depth]() {\n            return TransactionSubtreeA(left, depth + 1);\n        });\n        const Hash right_hash = TransactionSubtreeA(right, depth + 1);\n        return TxNodeAtDepth(depth, left_future.get(), right_hash);\n    }\n    return TxNodeAtDepth(depth, TransactionSubtreeA(left, depth + 1),\n                         TransactionSubtreeA(right, depth + 1));\n}\n'
NEW='Hash TransactionSubtreeA(std::span<const TxIdentityPair *> entries,\n                         unsigned depth) {\n    if (entries.empty()) return EmptyTxRoot();\n    if (entries.size() == 1) return TxLeaf(*entries[0]);\n    if (depth >= 256) {\n        throw std::invalid_argument("duplicate transaction identifier in subtree");\n    }\n    // The public call owns one pointer array. Descendants reorder disjoint\n    // portions of it; transaction identities themselves are immutable. No\n    // recursive left/right vectors or per-level partition allocations.\n    const auto split = std::partition(entries.begin(), entries.end(),\n        [depth](const TxIdentityPair *entry) {\n            return !TxKeyBit(entry->tx_id, depth);\n        });\n    const auto left = entries.first(static_cast<size_t>(split - entries.begin()));\n    const auto right = entries.subspan(left.size());\n    if (depth < 4 && entries.size() >= 64 && !left.empty() && !right.empty()) {\n        auto left_future = std::async(std::launch::async, [left, depth]() {\n            return TransactionSubtreeA(left, depth + 1);\n        });\n        const Hash right_hash = TransactionSubtreeA(right, depth + 1);\n        return TxNodeAtDepth(depth, left_future.get(), right_hash);\n    }\n    return TxNodeAtDepth(depth, TransactionSubtreeA(left, depth + 1),\n                         TransactionSubtreeA(right, depth + 1));\n}\n'
CASE="BOOST_AUTO_TEST_CASE(transaction_subtree_span_partition_matches_arena) {\n    using namespace lotus::v2;\n    std::mt19937 random(0x718391);\n    for (const size_t count : {size_t{0}, size_t{1}, size_t{2}, size_t{63},\n                              size_t{64}, size_t{65}, size_t{255}, size_t{256},\n                              size_t{1000}}) {\n        for (const bool common_prefix : {false, true}) {\n            std::vector<TxIdentityPair> identities(count);\n            TxOverlayArena arena;\n            auto root = TxOverlayArena::kNullIdx;\n            for (size_t i = 0; i < count; ++i) {\n                auto &identity = identities[i];\n                for (auto &byte : identity.tx_id) byte = uint8_t(random());\n                for (auto &byte : identity.tx_hash) byte = uint8_t(random());\n                // Cover long unary chains, including byte/bit ordering, without\n                // relying on finding particular hashed transaction fixtures.\n                if (common_prefix) {\n                    std::fill_n(identity.tx_id.begin(), 20, uint8_t{0x96});\n                    for (unsigned byte = 0; byte < 8; ++byte) {\n                        identity.tx_id[24 + byte] = uint8_t(uint64_t(i) >> (8 * byte));\n                    }\n                }\n                root = arena.InsertTxLeaf(root, identity.tx_id, identity.tx_hash);\n            }\n            const auto saved = identities;\n            const auto expected = arena.SubtreeARoot(root);\n            BOOST_CHECK(BuildTxSubtreeA(identities) == expected);\n            TxIdentityPair coinbase{};\n            coinbase.tx_id.fill(0xff);\n            coinbase.tx_hash.fill(0x73);\n            std::vector<TxIdentityPair> block{coinbase};\n            block.insert(block.end(), identities.begin(), identities.end());\n            lotus::v2::Hash block_root{};\n            BOOST_CHECK(TransactionRoot(block, block_root));\n            BOOST_CHECK(block_root == CombineCoinbaseAndSubtreeA(coinbase, expected));\n            BOOST_CHECK(std::equal(identities.begin(), identities.end(), saved.begin(),\n                [](const auto &a, const auto &b) {\n                    return a.tx_id == b.tx_id && a.tx_hash == b.tx_hash;\n                }));\n            // Multiple calls borrow the same const identities while each owns\n            // a different pointer array. Their internal partitions must never\n            // race with one another or change the caller's order/data.\n            if (count == 65 || count == 1000) {\n                std::vector<std::future<lotus::v2::Hash>> readers;\n                for (unsigned i = 0; i < 4; ++i) {\n                    readers.push_back(std::async(std::launch::async, [&identities] {\n                        return BuildTxSubtreeA(identities);\n                    }));\n                }\n                for (auto &reader : readers) BOOST_CHECK(reader.get() == expected);\n                BOOST_CHECK(std::equal(identities.begin(), identities.end(), saved.begin(),\n                    [](const auto &a, const auto &b) {\n                        return a.tx_id == b.tx_id && a.tx_hash == b.tx_hash;\n                    }));\n            }\n            std::reverse(identities.begin(), identities.end());\n            BOOST_CHECK(BuildTxSubtreeA(identities) == expected);\n            if (!identities.empty()) {\n                auto duplicate = identities;\n                duplicate.push_back(identities.front());\n                duplicate.back().tx_hash[0] ^= 1;\n                BOOST_CHECK_THROW(BuildTxSubtreeA(duplicate), std::invalid_argument);\n                lotus::v2::Hash unchanged{};\n                unchanged.fill(0xa5);\n                block.push_back(identities.front());\n                BOOST_CHECK(!TransactionRoot(block, unchanged));\n                BOOST_CHECK(unchanged[0] == 0xa5);\n                // Duplicate rejection does not corrupt a later valid call.\n                BOOST_CHECK(BuildTxSubtreeA(identities) == expected);\n            }\n        }\n    }\n    TxIdentityPair left{}, right{};\n    right.tx_id[31] = 0x80; // Two keys split at the last canonical bit.\n    right.tx_hash[0] = 1;\n    TxOverlayArena arena;\n    auto root = arena.InsertTxLeaf(TxOverlayArena::kNullIdx, left.tx_id, left.tx_hash);\n    root = arena.InsertTxLeaf(root, right.tx_id, right.tx_hash);\n    BOOST_CHECK(BuildTxSubtreeA(std::vector{left, right}) == arena.SubtreeARoot(root));\n}\n"

def transform(files):
    result = dict(files)
    if PRODUCTION not in result:
        return result
    original = result[PRODUCTION]
    text = original.decode() if isinstance(original, bytes) else original
    if "Hash TransactionSubtreeA(" not in text:
        return result
    if NEW not in text:
        if text.count(OLD) != 1:
            raise ValueError("missing/nonunique canonical walker anchor")
        text = text.replace(OLD, NEW, 1)
    if OLD in text:
        raise ValueError("partial walker transform")
    result[PRODUCTION] = text.encode() if isinstance(original, bytes) else text
    if TEST in result:
        original = result[TEST]
        text = original.decode() if isinstance(original, bytes) else original
        if "BOOST_AUTO_TEST_SUITE(mempool_overlay_tests)" not in text and "BOOST_FIXTURE_TEST_SUITE(mempool_overlay_tests" not in text:
            raise ValueError("test fixture unavailable")
        if "transaction_subtree_span_partition_matches_arena" in text:
            if CASE not in text:
                raise ValueError("partial test transform")
        else:
            if text.count("BOOST_AUTO_TEST_SUITE_END()") != 1:
                raise ValueError("nonunique suite ending")
            for header in ("algorithm", "future", "random"):
                include = "#include <" + header + ">\n"
                if include not in text:
                    anchor = "#include <cstring>\n"
                    if text.count(anchor) != 1:
                        raise ValueError("missing include anchor")
                    # Match tested endpoint ordering: algorithm before cstring,
                    # future/random directly after it in that order.
                    if header == "algorithm":
                        text = text.replace(anchor, include + anchor, 1)
                    elif header == "future":
                        text = text.replace(anchor, anchor + include, 1)
                    else:
                        f = "#include <future>\n"
                        text = text.replace(f, f + include, 1)
            text = text.replace("BOOST_AUTO_TEST_SUITE_END()", "\n" + CASE + "\nBOOST_AUTO_TEST_SUITE_END()", 1)
        result[TEST] = text.encode() if isinstance(original, bytes) else text
    return result
