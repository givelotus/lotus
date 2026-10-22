# Native523 depth profiles

One sampled fixed-work run, not a maximum sustainable TPS measurement. Counts are sampled leaf observations, not CPU percentages. Known wait/idle leaves and unresolved symbols are excluded from active candidates. Active ancestor counts are NONADDITIVE.

## Depth 50000

State counts: {'io_or_idle_wait': 1931, 'condition_wait': 29663, 'active_candidate': 1170, 'mutex_wait': 1966, 'unresolved': 46}

| Active leaf | Count |
|---|---:|
| `secp256k1_gej_double` | 77 |
| `secp256k1_gej_add_ge_var` | 68 |
| `__psynch_mutexdrop` | 58 |
| `__psynch_cvbroad` | 45 |
| `__psynch_cvsignal` | 37 |
| `_platform_memmove` | 31 |
| `secp256k1_gej_add_zinv_var` | 28 |
| `RadixTree<node::ImmutableMempoolEntry, node::SnapshotEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::remove(Uint256RadixKey const&)` | 28 |
| `secp256k1_fe_sqrt` | 25 |
| `RCUPtr<RadixTree<node::ImmutableMempoolEntry, node::SnapshotEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::RadixNode>::~RCUPtr()` | 24 |
| `SipHashUint256(unsigned long long, unsigned long long, uint256 const&)` | 18 |
| `operator new(unsigned long)` | 17 |
| `sha512::Transform(unsigned long long*, unsigned char const*)` | 16 |
| `_platform_memset` | 16 |
| `MurmurHash3(unsigned int, Span<unsigned char const>)` | 16 |
| `MemPoolAccept::AcceptSingleTransaction(std::shared_ptr<CTransaction const> const&, MemPoolAccept::ATMPArgs&, PrecomputedAdmissionChecks const*)` | 15 |
| `RadixTree<txrelay::TxRelayIndex::WindowEntry, txrelay::TxRelayIndex::WindowEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::forEachLeaf<PeerManagerImpl::RelayReconSet(uint256 const&) const::$_0&>(RadixTree<txrelay::TxRelayIndex::WindowEntry, txrelay::TxRelayIndex::WindowEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::RadixElement, PeerManagerImpl::RelayReconSet(uint256 const&) const::$_0&) const` | 15 |
| `secp256k1_ecmult_strauss_wnaf` | 14 |
| `base_uint<256u>::operator>>=(unsigned int)` | 14 |
| `operator delete(void*)` | 13 |

Active application ancestors (nonadditive):

- 423: `node::BroadcastTransaction(node::NodeContext const&, std::shared_ptr<CTransaction const>, std::basic_string<char>&, Amount, bool, bool, bool, bool)`
- 400: `PrecomputeMempoolAdmission(ChainstateManager&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&)`
- 367: `std::__thread_proxy[abi:nqe210106]<std::tuple<std::unique_ptr<std::__thread_struct>, node::RpcAdmissionDispatcher::Impl::Impl()::'lambda'()>>(void*)`
- 367: `node::RpcAdmissionDispatcher::Impl::Run()`
- 351: `CScriptCheck::operator()()`
- 348: `CScriptCheck::CheckInput(lotus::v2::DeferredRecords&)`
- 330: `node::AdmitBroadcastLocked(node::NodeContext const&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&, bool, bool, PrecomputedAdmissionChecks const*, std::shared_ptr<std::promise<void>> const&)`
- 277: `lotus::v2::Machine::Execute(unsigned long, unsigned long, unsigned int)`
- 264: `CScriptCheck::CheckInput(lotus::v2::DeferredRecords&)::$_2::__invoke(void*, std::span<unsigned char const, 18446744073709551615ul>, std::span<unsigned char const, 18446744073709551615ul>, std::array<unsigned char, 32ul> const&, bool)`
- 255: `lotus::v2::VerifyBip340Signature(std::span<unsigned char const, 18446744073709551615ul>, std::span<unsigned char const, 18446744073709551615ul>, std::array<unsigned char, 32ul> const&, bool)`
- 234: `MemPoolAccept::AcceptSingleTransaction(std::shared_ptr<CTransaction const> const&, MemPoolAccept::ATMPArgs&, PrecomputedAdmissionChecks const*)`
- 130: `node::PublishMempoolSnapshot(CTxMemPool const&)`

Wait callers (wall-thread waits, not CPU cost; background may be idle):

- 27094 condition_wait: `(other/background)`
- 2362 condition_wait: `node::RpcAdmissionDispatcher::Impl::Dispatch(unsigned long, std::function<node::RpcAdmissionOutcome ()>)`
- 1931 io_or_idle_wait: `(other/background)`
- 1583 mutex_wait: `PrecomputeMempoolAdmission(ChainstateManager&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&)`
- 167 mutex_wait: `PeerManagerImpl::RelayTransaction(TxId const&)`
- 143 condition_wait: `node::RpcAdmissionDispatcher::Impl::Run()`

## Depth 250000

State counts: {'io_or_idle_wait': 2038, 'condition_wait': 31422, 'active_candidate': 1303, 'mutex_wait': 2050, 'unresolved': 39}

| Active leaf | Count |
|---|---:|
| `secp256k1_gej_double` | 109 |
| `secp256k1_gej_add_ge_var` | 86 |
| `__psynch_mutexdrop` | 69 |
| `_platform_memmove` | 45 |
| `secp256k1_gej_add_zinv_var` | 43 |
| `__psynch_cvbroad` | 41 |
| `__psynch_cvsignal` | 40 |
| `secp256k1_fe_sqrt` | 34 |
| `RadixTree<node::ImmutableMempoolEntry, node::SnapshotEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::remove(Uint256RadixKey const&)` | 33 |
| `MemPoolAccept::AcceptSingleTransaction(std::shared_ptr<CTransaction const> const&, MemPoolAccept::ATMPArgs&, PrecomputedAdmissionChecks const*)` | 31 |
| `_platform_memset` | 25 |
| `blake3_compress_in_place_portable` | 21 |
| `RCUPtr<RadixTree<node::ImmutableMempoolEntry, node::SnapshotEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::RadixNode>::~RCUPtr()` | 20 |
| `SipHashUint256(unsigned long long, unsigned long long, uint256 const&)` | 19 |
| `mach_continuous_time` | 19 |
| `operator new(unsigned long)` | 19 |
| `sha512::Transform(unsigned long long*, unsigned char const*)` | 19 |
| `blake3_compress_xof_portable` | 19 |
| `secp256k1_fe_impl_mul` | 18 |
| `MurmurHash3(unsigned int, Span<unsigned char const>)` | 18 |

Active application ancestors (nonadditive):

- 512: `node::BroadcastTransaction(node::NodeContext const&, std::shared_ptr<CTransaction const>, std::basic_string<char>&, Amount, bool, bool, bool, bool)`
- 480: `PrecomputeMempoolAdmission(ChainstateManager&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&)`
- 447: `CScriptCheck::operator()()`
- 442: `CScriptCheck::CheckInput(lotus::v2::DeferredRecords&)`
- 404: `std::__thread_proxy[abi:nqe210106]<std::tuple<std::unique_ptr<std::__thread_struct>, node::RpcAdmissionDispatcher::Impl::Impl()::'lambda'()>>(void*)`
- 404: `node::RpcAdmissionDispatcher::Impl::Run()`
- 367: `node::AdmitBroadcastLocked(node::NodeContext const&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&, bool, bool, PrecomputedAdmissionChecks const*, std::shared_ptr<std::promise<void>> const&)`
- 347: `lotus::v2::Machine::Execute(unsigned long, unsigned long, unsigned int)`
- 340: `CScriptCheck::CheckInput(lotus::v2::DeferredRecords&)::$_2::__invoke(void*, std::span<unsigned char const, 18446744073709551615ul>, std::span<unsigned char const, 18446744073709551615ul>, std::array<unsigned char, 32ul> const&, bool)`
- 331: `lotus::v2::VerifyBip340Signature(std::span<unsigned char const, 18446744073709551615ul>, std::span<unsigned char const, 18446744073709551615ul>, std::array<unsigned char, 32ul> const&, bool)`
- 265: `MemPoolAccept::AcceptSingleTransaction(std::shared_ptr<CTransaction const> const&, MemPoolAccept::ATMPArgs&, PrecomputedAdmissionChecks const*)`
- 134: `MemPoolAccept::Finalize(MemPoolAccept::ATMPArgs const&, MemPoolAccept::Workspace&, std::vector<ValidationSignals::MempoolAddedBatchItem>*, std::vector<boost::multi_index::detail::hashed_index_iterator<boost::multi_index::detail::hashed_index_node<boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::index_node_base<RCUPtr<CTxMemPoolEntry>, ChunkedSlabAllocator<RCUPtr<CTxMemPoolEntry>, 16384ul>>>>>>, boost::multi_index::detail::bucket_array<ChunkedSlabAllocator<RCUPtr<CTxMemPoolEntry>, 16384ul>>, boost::multi_index::detail::hashed_unique_tag, boost::multi_index::detail::hashed_index_global_iterator_tag>> const*, boost::multi_index::detail::hashed_index_iterator<boost::multi_index::detail::hashed_index_node<boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::index_node_base<RCUPtr<CTxMemPoolEntry>, ChunkedSlabAllocator<RCUPtr<CTxMemPoolEntry>, 16384ul>>>>>>, boost::multi_index::detail::bucket_array<ChunkedSlabAllocator<RCUPtr<CTxMemPoolEntry>, 16384ul>>, boost::multi_index::detail::hashed_unique_tag, boost::multi_index::detail::hashed_index_global_iterator_tag>*)`

Wait callers (wall-thread waits, not CPU cost; background may be idle):

- 28706 condition_wait: `(other/background)`
- 2504 condition_wait: `node::RpcAdmissionDispatcher::Impl::Dispatch(unsigned long, std::function<node::RpcAdmissionOutcome ()>)`
- 2038 io_or_idle_wait: `(other/background)`
- 1626 mutex_wait: `PrecomputeMempoolAdmission(ChainstateManager&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&)`
- 188 mutex_wait: `PeerManagerImpl::RelayTransaction(TxId const&)`
- 150 condition_wait: `node::RpcAdmissionDispatcher::Impl::Run()`

## Depth 450000

State counts: {'io_or_idle_wait': 2056, 'condition_wait': 31631, 'active_candidate': 1208, 'mutex_wait': 2147, 'unresolved': 39}

| Active leaf | Count |
|---|---:|
| `secp256k1_gej_double` | 74 |
| `secp256k1_gej_add_ge_var` | 70 |
| `__psynch_mutexdrop` | 54 |
| `__psynch_cvsignal` | 53 |
| `__psynch_cvbroad` | 51 |
| `MemPoolAccept::AcceptSingleTransaction(std::shared_ptr<CTransaction const> const&, MemPoolAccept::ATMPArgs&, PrecomputedAdmissionChecks const*)` | 39 |
| `secp256k1_gej_add_zinv_var` | 37 |
| `secp256k1_fe_sqrt` | 30 |
| `RadixTree<node::ImmutableMempoolEntry, node::SnapshotEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::remove(Uint256RadixKey const&)` | 30 |
| `RCUPtr<RadixTree<node::ImmutableMempoolEntry, node::SnapshotEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::RadixNode>::~RCUPtr()` | 28 |
| `_platform_memmove` | 26 |
| `SipHashUint256(unsigned long long, unsigned long long, uint256 const&)` | 22 |
| `operator new(unsigned long)` | 18 |
| `secp256k1_ecmult_strauss_wnaf` | 17 |
| `blake3_compress_in_place_portable` | 17 |
| `sha512::Transform(unsigned long long*, unsigned char const*)` | 16 |
| `_platform_memset` | 16 |
| `blake3_compress_xof_portable` | 16 |
| `RCUInfos::runCleanups()` | 15 |
| `secp256k1_fe_impl_mul` | 13 |

Active application ancestors (nonadditive):

- 451: `node::BroadcastTransaction(node::NodeContext const&, std::shared_ptr<CTransaction const>, std::basic_string<char>&, Amount, bool, bool, bool, bool)`
- 410: `PrecomputeMempoolAdmission(ChainstateManager&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&)`
- 396: `std::__thread_proxy[abi:nqe210106]<std::tuple<std::unique_ptr<std::__thread_struct>, node::RpcAdmissionDispatcher::Impl::Impl()::'lambda'()>>(void*)`
- 396: `node::RpcAdmissionDispatcher::Impl::Run()`
- 390: `CScriptCheck::operator()()`
- 388: `CScriptCheck::CheckInput(lotus::v2::DeferredRecords&)`
- 358: `node::AdmitBroadcastLocked(node::NodeContext const&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&, bool, bool, PrecomputedAdmissionChecks const*, std::shared_ptr<std::promise<void>> const&)`
- 296: `lotus::v2::Machine::Execute(unsigned long, unsigned long, unsigned int)`
- 286: `CScriptCheck::CheckInput(lotus::v2::DeferredRecords&)::$_2::__invoke(void*, std::span<unsigned char const, 18446744073709551615ul>, std::span<unsigned char const, 18446744073709551615ul>, std::array<unsigned char, 32ul> const&, bool)`
- 273: `lotus::v2::VerifyBip340Signature(std::span<unsigned char const, 18446744073709551615ul>, std::span<unsigned char const, 18446744073709551615ul>, std::array<unsigned char, 32ul> const&, bool)`
- 266: `MemPoolAccept::AcceptSingleTransaction(std::shared_ptr<CTransaction const> const&, MemPoolAccept::ATMPArgs&, PrecomputedAdmissionChecks const*)`
- 135: `node::PublishMempoolSnapshot(CTxMemPool const&)`

Wait callers (wall-thread waits, not CPU cost; background may be idle):

- 28844 condition_wait: `(other/background)`
- 2574 condition_wait: `node::RpcAdmissionDispatcher::Impl::Dispatch(unsigned long, std::function<node::RpcAdmissionOutcome ()>)`
- 2056 io_or_idle_wait: `(other/background)`
- 1656 mutex_wait: `PrecomputeMempoolAdmission(ChainstateManager&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&)`
- 250 mutex_wait: `PeerManagerImpl::RelayTransaction(TxId const&)`
- 144 condition_wait: `node::RpcAdmissionDispatcher::Impl::Run()`
