// SOURCE-ONLY insertion inside v2_protocol_handler_tests before its suite end.
// Reuses that file's real MakeNonCoinbaseTx and ConnmanTestMsg helpers.
// Expected CURRENT behavior: five recovery CHECK_MESSAGE assertions fail.
BOOST_AUTO_TEST_CASE(relay_epoch_balanced_difference_requires_recovery) {
    LOCK(NetEventsInterface::g_msgproc_mutex);
    const auto &config{m_node.chainman->GetConfig()};
    auto connman = std::make_unique<ConnmanTestMsg>(
        config, 0x93, 0x94, *m_node.addrman);
    PeerManager::Options opts;
    auto peerman = PeerManager::make(*connman, *m_node.addrman, nullptr,
        *m_node.chainman, *m_node.mempool, nullptr, opts);
    struct KeyOnly final : TxRelayEpochProvider {
        txrelay::EpochKey key;
        std::optional<std::pair<uint64_t, uint64_t>>
        RelayEpochKey(const uint256 &id) const override {
            if (id != key.epoch_id) return std::nullopt;
            return std::make_pair(key.k0, key.k1);
        }
        uint64_t RelayShortIdMask() const override { return ~uint64_t{0}; }
        std::vector<CTransactionRef> ResolveRelayShortIds(
            const uint256 &, const std::vector<uint64_t> &) const override {
            return {};
        }
        std::optional<std::vector<CTransactionRef>>
        RelayReconSet(const uint256 &) const override { return std::nullopt; }
        bool HaveRelayShortId(const uint256 &, uint64_t) const override {
            return false;
        }
    } provider;
    {
        LOCK(cs_main);
        const auto &tip{*Assert(m_node.chainman->ActiveTip())};
        provider.key = txrelay::MakeEpochKey(tip.GetBlockHash(), tip.nHeight);
    }
    V2PeerProtocolHandler local(*m_node.chainman, *m_node.mempool,
                                *connman, *peerman);
    V2PeerProtocolHandler remote(*m_node.chainman, *m_node.mempool,
                                 *connman, *peerman);
    local.SetTxRelayEpochProvider(&provider);
    remote.SetTxRelayEpochProvider(&provider);
    FastRandomContext rng{uint256{0x93}};
    const auto a{MakeNonCoinbaseTx(rng, 0x59)};
    const auto b{MakeNonCoinbaseTx(rng, 0x59)};
    BOOST_REQUIRE(a && b);
    BOOST_REQUIRE(a->GetId() != b->GetId());
    const auto &key{provider.key};
    BOOST_REQUIRE(ComputeMerklixShortId(key.k0, key.k1, a->GetId()) !=
                  ComputeMerklixShortId(key.k0, key.k1, b->GetId()));
    // Explicit scoped sets make this a stable one-item-per-side counterexample,
    // independent of cap4096, admission age, network timing or transaction policy.
    local.SetScopedTransactions(ReconScope::LIVE_MEMPOOL, key.epoch_id, {b});
    remote.SetScopedTransactions(ReconScope::LIVE_MEMPOOL, key.epoch_id, {a});
    const auto local_summary{local.BuildSyncSummary(
        ReconScope::LIVE_MEMPOOL, key.epoch_id, key.k0, key.k1)};
    const auto remote_summary{remote.BuildSyncSummary(
        ReconScope::LIVE_MEMPOOL, key.epoch_id, key.k0, key.k1)};
    BOOST_REQUIRE(local_summary.candidate_root != remote_summary.candidate_root);
    const auto bucket{GetMerklixBucketIndex(a->GetId())};
    BOOST_REQUIRE_EQUAL(bucket, GetMerklixBucketIndex(b->GetId()));
    BOOST_REQUIRE_EQUAL(local_summary.buckets[bucket].count, 1U);
    BOOST_REQUIRE_EQUAL(remote_summary.buckets[bucket].count, 1U);
    const auto forward{local.DiffSyncSummary(remote_summary)};
    const auto reverse{remote.DiffSyncSummary(local_summary)};
    BOOST_CHECK(!forward.root_matched && !reverse.root_matched);
    BOOST_CHECK_MESSAGE(!forward.single_missing_short_ids.empty() ||
                        forward.mismatched_bucket_mask != 0,
                        "remoteA/localB equal-count root mismatch needs recovery");
    BOOST_CHECK_MESSAGE(!reverse.single_missing_short_ids.empty() ||
                        reverse.mismatched_bucket_mask != 0,
                        "remoteB/localA equal-count root mismatch needs recovery");
    // The same stable balanced difference in a non-relay scope is not suppressed.
    const uint256 control{rng.rand256()};
    local.SetScopedTransactions(ReconScope::BLOCK_RECON, control, {b});
    remote.SetScopedTransactions(ReconScope::BLOCK_RECON, control, {a});
    const auto general{local.DiffSyncSummary(remote.BuildSyncSummary(
        ReconScope::BLOCK_RECON, control))};
    BOOST_CHECK(!general.root_matched);
    BOOST_CHECK(general.mismatched_bucket_mask != 0);
    // Decoder-failure path: both sides have >3 distinct symmetric differences
    // in exactly the same8-bit prefix, with equal or negative count delta.
    std::vector<CTransactionRef> remote_four, local_five;
    for (int i = 0; i < 9; ++i) {
        const auto tx{MakeNonCoinbaseTx(rng, 0x59)};
        BOOST_REQUIRE(tx);
        (i < 4 ? remote_four : local_five).push_back(tx);
    }
    for (size_t local_count : {size_t{4}, size_t{5}}) {
        const std::vector<CTransactionRef> locals(
            local_five.begin(), local_five.begin() + local_count);
        local.SetScopedTransactions(ReconScope::LIVE_MEMPOOL, key.epoch_id, locals);
        remote.SetScopedTransactions(ReconScope::LIVE_MEMPOOL, key.epoch_id, remote_four);
        const auto received{remote.BuildSubBucketSummary(
            ReconScope::LIVE_MEMPOOL, key.epoch_id, key.k0, key.k1, uint8_t{5})};
        const auto ours{local.BuildSubBucketSummary(
            ReconScope::LIVE_MEMPOOL, key.epoch_id, key.k0, key.k1, uint8_t{5})};
        const auto &r{received.sub_buckets[9]}, &l{ours.sub_buckets[9]};
        BOOST_REQUIRE(!RecoverGF64Syndromes(r.s1 ^ l.s1, r.s3 ^ l.s3,
                                            r.s5 ^ l.s5).has_value());
        const auto balanced{local.DiffSubBucketSummary(received)};
        BOOST_CHECK_MESSAGE(!balanced.missing_short_ids.empty() ||
                            !balanced.unresolved_sub_buckets.empty(),
                            "equal/negative relay count must not suppress failed decoder");
        local.SetScopedTransactions(ReconScope::BLOCK_RECON, control, locals);
        remote.SetScopedTransactions(ReconScope::BLOCK_RECON, control, remote_four);
        const auto general_sub{local.DiffSubBucketSummary(remote.BuildSubBucketSummary(
            ReconScope::BLOCK_RECON, control, 0, 0, uint8_t{5}))};
        BOOST_CHECK(!general_sub.unresolved_sub_buckets.empty());
    }
    // Count-consistency failure path: valid two-ID syndromes, forged count.
    local.SetScopedTransactions(ReconScope::LIVE_MEMPOOL, key.epoch_id, {b});
    remote.SetScopedTransactions(ReconScope::LIVE_MEMPOOL, key.epoch_id, {a});
    auto inconsistent{remote.BuildSubBucketSummary(
        ReconScope::LIVE_MEMPOOL, key.epoch_id, key.k0, key.k1, uint8_t{5})};
    BOOST_REQUIRE_EQUAL(inconsistent.sub_buckets[9].count, 1U);
    inconsistent.sub_buckets[9].count = 0;
    const auto mismatch{local.DiffSubBucketSummary(inconsistent)};
    BOOST_CHECK_MESSAGE(!mismatch.unresolved_sub_buckets.empty(),
                        "relay count inconsistency must request drilldown");
    // Budget control: root inequality also exists for a true remote subset.
    // Restoring root fallback deliberately schedules root-bucket checks here,
    // although no remote transaction is missing. Keep this cost visible.
    local.SetScopedTransactions(ReconScope::LIVE_MEMPOOL, key.epoch_id, {a, b});
    remote.SetScopedTransactions(ReconScope::LIVE_MEMPOOL, key.epoch_id, {a});
    const auto extra_only{local.DiffSyncSummary(remote.BuildSyncSummary(
        ReconScope::LIVE_MEMPOOL, key.epoch_id, key.k0, key.k1))};
    BOOST_CHECK(!extra_only.root_matched);
    BOOST_CHECK(extra_only.single_missing_short_ids.empty());
    BOOST_TEST_MESSAGE("extra-only relay root bucket mask=" <<
                        extra_only.mismatched_bucket_mask);

}
