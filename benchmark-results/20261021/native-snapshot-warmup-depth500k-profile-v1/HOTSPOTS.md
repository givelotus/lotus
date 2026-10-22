# Snapshot-warmup527 depth profiles

One sampled fixed-work run, not a maximum sustainable TPS measurement. Counts are sampled leaf observations, not CPU percentages. Known wait/idle leaves and unresolved symbols are excluded from active candidates. Active ancestor counts are NONADDITIVE.

## Depth 50000

State counts: {'io_or_idle_wait': 1943, 'condition_wait': 31103, 'active_candidate': 1548, 'mutex_wait': 403, 'unresolved': 49}

| Active leaf | Count |
|---|---:|
| `secp256k1_gej_double` | 150 |
| `secp256k1_gej_add_ge_var` | 101 |
| `__psynch_cvbroad` | 61 |
| `secp256k1_gej_add_zinv_var` | 61 |
| `__psynch_cvsignal` | 55 |
| `RadixTree<node::ImmutableMempoolEntry, node::SnapshotEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::remove(Uint256RadixKey const&)` | 47 |
| `_platform_memmove` | 43 |
| `secp256k1_fe_sqrt` | 40 |
| `__psynch_mutexdrop` | 34 |
| `RCUPtr<RadixTree<node::ImmutableMempoolEntry, node::SnapshotEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::RadixNode>::~RCUPtr()` | 31 |
| `lotus::v2::SmtFind(std::shared_ptr<lotus::v2::SmtNode const> const&, lotus::v2::Outpoint const&)` | 30 |
| `operator new(unsigned long)` | 29 |
| `SipHashUint256(unsigned long long, unsigned long long, uint256 const&)` | 28 |
| `_platform_memset` | 27 |
| `secp256k1_fe_impl_mul` | 25 |
| `RCUInfos::runCleanups()` | 24 |
| `MemPoolAccept::AcceptSingleTransaction(std::shared_ptr<CTransaction const> const&, MemPoolAccept::ATMPArgs&, PrecomputedAdmissionChecks const*)` | 23 |
| `mach_continuous_time` | 22 |
| `__gettimeofday` | 21 |
| `blake3_compress_in_place_portable` | 18 |

Active application ancestors (nonadditive):

- 622: `node::BroadcastTransaction(node::NodeContext const&, std::shared_ptr<CTransaction const>, std::basic_string<char>&, Amount, bool, bool, bool, bool)`
- 587: `CScriptCheck::operator()()`
- 583: `CScriptCheck::CheckInput(lotus::v2::DeferredRecords&)`
- 578: `PrecomputeMempoolAdmission(ChainstateManager&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&, CTxMemPool const*)`
- 525: `std::__thread_proxy[abi:nqe210106]<std::tuple<std::unique_ptr<std::__thread_struct>, node::RpcAdmissionDispatcher::Impl::Impl()::'lambda'()>>(void*)`
- 525: `node::RpcAdmissionDispatcher::Impl::Run()`
- 488: `node::AdmitBroadcastLocked(node::NodeContext const&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&, bool, bool, PrecomputedAdmissionChecks const*, std::shared_ptr<std::promise<void>> const&)`
- 471: `lotus::v2::Machine::Execute(unsigned long, unsigned long, unsigned int)`
- 452: `CScriptCheck::CheckInput(lotus::v2::DeferredRecords&)::$_2::__invoke(void*, std::span<unsigned char const, 18446744073709551615ul>, std::span<unsigned char const, 18446744073709551615ul>, std::array<unsigned char, 32ul> const&, bool)`
- 439: `lotus::v2::VerifyBip340Signature(std::span<unsigned char const, 18446744073709551615ul>, std::span<unsigned char const, 18446744073709551615ul>, std::array<unsigned char, 32ul> const&, bool)`
- 353: `MemPoolAccept::AcceptSingleTransaction(std::shared_ptr<CTransaction const> const&, MemPoolAccept::ATMPArgs&, PrecomputedAdmissionChecks const*)`
- 189: `MemPoolAccept::Finalize(MemPoolAccept::ATMPArgs const&, MemPoolAccept::Workspace&, std::vector<ValidationSignals::MempoolAddedBatchItem>*, std::vector<boost::multi_index::detail::hashed_index_iterator<boost::multi_index::detail::hashed_index_node<boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::index_node_base<RCUPtr<CTxMemPoolEntry>, ChunkedSlabAllocator<RCUPtr<CTxMemPoolEntry>, 16384ul>>>>>>, boost::multi_index::detail::bucket_array<ChunkedSlabAllocator<RCUPtr<CTxMemPoolEntry>, 16384ul>>, boost::multi_index::detail::hashed_unique_tag, boost::multi_index::detail::hashed_index_global_iterator_tag>> const*, boost::multi_index::detail::hashed_index_iterator<boost::multi_index::detail::hashed_index_node<boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::index_node_base<RCUPtr<CTxMemPoolEntry>, ChunkedSlabAllocator<RCUPtr<CTxMemPoolEntry>, 16384ul>>>>>>, boost::multi_index::detail::bucket_array<ChunkedSlabAllocator<RCUPtr<CTxMemPoolEntry>, 16384ul>>, boost::multi_index::detail::hashed_unique_tag, boost::multi_index::detail::hashed_index_global_iterator_tag>*)`

Wait callers (wall-thread waits, not CPU cost; background may be idle):

- 27258 condition_wait: `(other/background)`
- 3842 condition_wait: `node::RpcAdmissionDispatcher::Impl::Dispatch(unsigned long, std::function<node::RpcAdmissionOutcome ()>)`
- 1943 io_or_idle_wait: `(other/background)`
- 240 mutex_wait: `PeerManagerImpl::RelayTransaction(TxId const&)`
- 50 mutex_wait: `node::RpcAdmissionDispatcher::Impl::Run()`
- 46 mutex_wait: `(other/background)`

## Depth 250000

State counts: {'io_or_idle_wait': 2027, 'condition_wait': 32865, 'active_candidate': 1601, 'unresolved': 40, 'mutex_wait': 403}

| Active leaf | Count |
|---|---:|
| `secp256k1_gej_double` | 124 |
| `secp256k1_gej_add_ge_var` | 98 |
| `__psynch_cvbroad` | 64 |
| `__psynch_cvsignal` | 64 |
| `secp256k1_gej_add_zinv_var` | 52 |
| `RadixTree<node::ImmutableMempoolEntry, node::SnapshotEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::remove(Uint256RadixKey const&)` | 47 |
| `secp256k1_fe_sqrt` | 45 |
| `RCUPtr<RadixTree<node::ImmutableMempoolEntry, node::SnapshotEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::RadixNode>::~RCUPtr()` | 40 |
| `__psynch_mutexdrop` | 39 |
| `MemPoolAccept::AcceptSingleTransaction(std::shared_ptr<CTransaction const> const&, MemPoolAccept::ATMPArgs&, PrecomputedAdmissionChecks const*)` | 38 |
| `_platform_memmove` | 33 |
| `lotus::v2::SmtFind(std::shared_ptr<lotus::v2::SmtNode const> const&, lotus::v2::Outpoint const&)` | 31 |
| `_platform_memset` | 30 |
| `SipHashUint256(unsigned long long, unsigned long long, uint256 const&)` | 26 |
| `secp256k1_fe_impl_mul` | 25 |
| `mach_continuous_time` | 20 |
| `operator new(unsigned long)` | 20 |
| `secp256k1_ecmult_strauss_wnaf` | 18 |
| `blake3_compress_xof_portable` | 18 |
| `std::basic_string<char>::push_back(char)` | 18 |

Active application ancestors (nonadditive):

- 597: `node::BroadcastTransaction(node::NodeContext const&, std::shared_ptr<CTransaction const>, std::basic_string<char>&, Amount, bool, bool, bool, bool)`
- 573: `CScriptCheck::operator()()`
- 568: `CScriptCheck::CheckInput(lotus::v2::DeferredRecords&)`
- 553: `PrecomputeMempoolAdmission(ChainstateManager&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&, CTxMemPool const*)`
- 546: `std::__thread_proxy[abi:nqe210106]<std::tuple<std::unique_ptr<std::__thread_struct>, node::RpcAdmissionDispatcher::Impl::Impl()::'lambda'()>>(void*)`
- 546: `node::RpcAdmissionDispatcher::Impl::Run()`
- 511: `node::AdmitBroadcastLocked(node::NodeContext const&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&, bool, bool, PrecomputedAdmissionChecks const*, std::shared_ptr<std::promise<void>> const&)`
- 443: `lotus::v2::Machine::Execute(unsigned long, unsigned long, unsigned int)`
- 426: `CScriptCheck::CheckInput(lotus::v2::DeferredRecords&)::$_2::__invoke(void*, std::span<unsigned char const, 18446744073709551615ul>, std::span<unsigned char const, 18446744073709551615ul>, std::array<unsigned char, 32ul> const&, bool)`
- 413: `lotus::v2::VerifyBip340Signature(std::span<unsigned char const, 18446744073709551615ul>, std::span<unsigned char const, 18446744073709551615ul>, std::array<unsigned char, 32ul> const&, bool)`
- 354: `MemPoolAccept::AcceptSingleTransaction(std::shared_ptr<CTransaction const> const&, MemPoolAccept::ATMPArgs&, PrecomputedAdmissionChecks const*)`
- 174: `node::PublishMempoolSnapshot(CTxMemPool const&)`

Wait callers (wall-thread waits, not CPU cost; background may be idle):

- 28734 condition_wait: `(other/background)`
- 4129 condition_wait: `node::RpcAdmissionDispatcher::Impl::Dispatch(unsigned long, std::function<node::RpcAdmissionOutcome ()>)`
- 2027 io_or_idle_wait: `(other/background)`
- 215 mutex_wait: `PeerManagerImpl::RelayTransaction(TxId const&)`
- 54 mutex_wait: `node::RpcAdmissionDispatcher::Impl::Run()`
- 53 mutex_wait: `(other/background)`

## Depth 450000

State counts: {'io_or_idle_wait': 2015, 'condition_wait': 32300, 'active_candidate': 1582, 'unresolved': 43, 'mutex_wait': 456}

| Active leaf | Count |
|---|---:|
| `secp256k1_gej_double` | 158 |
| `secp256k1_gej_add_ge_var` | 99 |
| `secp256k1_gej_add_zinv_var` | 68 |
| `__psynch_cvsignal` | 62 |
| `__psynch_cvbroad` | 52 |
| `secp256k1_fe_sqrt` | 45 |
| `MemPoolAccept::AcceptSingleTransaction(std::shared_ptr<CTransaction const> const&, MemPoolAccept::ATMPArgs&, PrecomputedAdmissionChecks const*)` | 42 |
| `RadixTree<node::ImmutableMempoolEntry, node::SnapshotEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::remove(Uint256RadixKey const&)` | 40 |
| `__psynch_mutexdrop` | 35 |
| `RCUPtr<RadixTree<node::ImmutableMempoolEntry, node::SnapshotEntryAdapter, GlobalConcurrentSlabAllocator<std::byte, 1024ul>>::RadixNode>::~RCUPtr()` | 34 |
| `secp256k1_fe_impl_mul` | 32 |
| `operator new(unsigned long)` | 29 |
| `SipHashUint256(unsigned long long, unsigned long long, uint256 const&)` | 27 |
| `RCUInfos::runCleanups()` | 27 |
| `_platform_memset` | 26 |
| `_platform_memmove` | 26 |
| `secp256k1_ecmult_strauss_wnaf` | 24 |
| `lotus::v2::SmtFind(std::shared_ptr<lotus::v2::SmtNode const> const&, lotus::v2::Outpoint const&)` | 24 |
| `__gettimeofday` | 19 |
| `blake3_compress_xof_portable` | 18 |

Active application ancestors (nonadditive):

- 630: `node::BroadcastTransaction(node::NodeContext const&, std::shared_ptr<CTransaction const>, std::basic_string<char>&, Amount, bool, bool, bool, bool)`
- 619: `CScriptCheck::operator()()`
- 615: `CScriptCheck::CheckInput(lotus::v2::DeferredRecords&)`
- 585: `PrecomputeMempoolAdmission(ChainstateManager&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&, CTxMemPool const*)`
- 526: `std::__thread_proxy[abi:nqe210106]<std::tuple<std::unique_ptr<std::__thread_struct>, node::RpcAdmissionDispatcher::Impl::Impl()::'lambda'()>>(void*)`
- 526: `node::RpcAdmissionDispatcher::Impl::Run()`
- 498: `lotus::v2::Machine::Execute(unsigned long, unsigned long, unsigned int)`
- 496: `node::AdmitBroadcastLocked(node::NodeContext const&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&, bool, bool, PrecomputedAdmissionChecks const*, std::shared_ptr<std::promise<void>> const&)`
- 479: `CScriptCheck::CheckInput(lotus::v2::DeferredRecords&)::$_2::__invoke(void*, std::span<unsigned char const, 18446744073709551615ul>, std::span<unsigned char const, 18446744073709551615ul>, std::array<unsigned char, 32ul> const&, bool)`
- 470: `lotus::v2::VerifyBip340Signature(std::span<unsigned char const, 18446744073709551615ul>, std::span<unsigned char const, 18446744073709551615ul>, std::array<unsigned char, 32ul> const&, bool)`
- 372: `MemPoolAccept::AcceptSingleTransaction(std::shared_ptr<CTransaction const> const&, MemPoolAccept::ATMPArgs&, PrecomputedAdmissionChecks const*)`
- 188: `MemPoolAccept::Finalize(MemPoolAccept::ATMPArgs const&, MemPoolAccept::Workspace&, std::vector<ValidationSignals::MempoolAddedBatchItem>*, std::vector<boost::multi_index::detail::hashed_index_iterator<boost::multi_index::detail::hashed_index_node<boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::index_node_base<RCUPtr<CTxMemPoolEntry>, ChunkedSlabAllocator<RCUPtr<CTxMemPoolEntry>, 16384ul>>>>>>, boost::multi_index::detail::bucket_array<ChunkedSlabAllocator<RCUPtr<CTxMemPoolEntry>, 16384ul>>, boost::multi_index::detail::hashed_unique_tag, boost::multi_index::detail::hashed_index_global_iterator_tag>> const*, boost::multi_index::detail::hashed_index_iterator<boost::multi_index::detail::hashed_index_node<boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::ordered_index_node<boost::multi_index::detail::null_augment_policy, boost::multi_index::detail::index_node_base<RCUPtr<CTxMemPoolEntry>, ChunkedSlabAllocator<RCUPtr<CTxMemPoolEntry>, 16384ul>>>>>>, boost::multi_index::detail::bucket_array<ChunkedSlabAllocator<RCUPtr<CTxMemPoolEntry>, 16384ul>>, boost::multi_index::detail::hashed_unique_tag, boost::multi_index::detail::hashed_index_global_iterator_tag>*)`

Wait callers (wall-thread waits, not CPU cost; background may be idle):

- 28314 condition_wait: `(other/background)`
- 3980 condition_wait: `node::RpcAdmissionDispatcher::Impl::Dispatch(unsigned long, std::function<node::RpcAdmissionOutcome ()>)`
- 2015 io_or_idle_wait: `(other/background)`
- 256 mutex_wait: `PeerManagerImpl::RelayTransaction(TxId const&)`
- 61 mutex_wait: `node::AdmitBroadcastLocked(node::NodeContext const&, std::shared_ptr<CTransaction const> const&, MempoolAdmissionLimits const&, bool, bool, PrecomputedAdmissionChecks const*, std::shared_ptr<std::promise<void>> const&)`
- 58 mutex_wait: `(other/background)`
