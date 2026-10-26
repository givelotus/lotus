// Temporary diagnostic insertion in txrelay_tests after existing helpers.
// This characterizes the current limitation; it is not a permanent requirement
// that old live transactions MUST disappear from anti-entropy discovery.
BOOST_AUTO_TEST_CASE(recon_age_selection_excludes_available_live_body) {
    LOCK(NetEventsInterface::g_msgproc_mutex);
    auto &chainman{static_cast<TestChainstateManager &>(*m_node.chainman)};
    chainman.JumpOutOfIbd();
    struct ResetState {
        TestChainstateManager &chainman;
        ~ResetState() { SetMockTime(0); chainman.ResetIbd(); }
    } reset{chainman};
    const auto t0{GetTime<std::chrono::seconds>()};
    SetMockTime(t0);
    MockTick clock{12'000'000ms};
    PeerManager::Options opts;
    opts.txrecon_interval = 250ms;
    opts.txrecon_window = 30s;
    RelayHarness h{m_node, opts};
    h.AddPeer();
    h.SendAll();
    txrelay::EpochKey epoch;
    {
        LOCK(cs_main);
        const auto &tip{*Assert(chainman.ActiveTip())};
        epoch = txrelay::MakeEpochKey(tip.GetBlockHash(), tip.nHeight);
    }
    FastRandomContext rng{uint256{0x97}};
    const auto tx{MakeTx(rng)};
    AddToMempool(m_node, tx);
    h.peerman->RelayTransaction(tx->GetId());
    auto *handler{h.peerman->GetV2ProtocolHandler()};
    const auto sid{txrelay::ComputeShortId(epoch.k0, epoch.k1, tx->GetId(), 64)};
    auto summary_count = [&] {
        const auto summary{handler->BuildSyncSummary(
            lotus::v2::net::ReconScope::LIVE_MEMPOOL, epoch.epoch_id,
            epoch.k0, epoch.k1)};
        uint32_t count{0};
        for (const auto &bucket : summary.buckets) count += bucket.count;
        return count;
    };
    SetMockTime(t0 + 1s);
    BOOST_CHECK_EQUAL(summary_count(), 1U);
    SetMockTime(t0 + 31s);
    BOOST_CHECK_EQUAL(summary_count(), 0U);
    BOOST_CHECK(m_node.mempool->exists(tx->GetId()));
    const auto available{handler->ResolveShortIds(
        lotus::v2::net::ReconScope::LIVE_MEMPOOL, epoch.epoch_id,
        epoch.k0, epoch.k1, {sid})};
    BOOST_REQUIRE_EQUAL(available.size(), 1U);
    BOOST_CHECK(available.front()->GetId() == tx->GetId());
}
