// Copyright (c) 2026 The Lotus developers
// Distributed under the MIT software license, see COPYING.
// Benchmark-only overlay: compiled unchanged against both BCHN source revisions.
#include <bench/bench.h>
#include <config.h>
#include <chainparams.h>
#include <consensus/consensus.h>
#include <miner.h>
#include <protocol.h>
#include <script/standard.h>
#include <test/setup_common.h>
#include <test/util.h>
#include <txmempool.h>
#include <validation.h>

#include <algorithm>
#include <chrono>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
const CScript redeem = CScript() << OP_DROP << OP_TRUE;
const CScript pub = GetScriptForDestination(ScriptID(redeem, false));
const CScript sig = CScript() << std::vector<uint8_t>(100, 0xff) << ByteView(redeem);
void require(bool ok) { if (!ok) throw std::runtime_error("Benchmark invariant failed"); }

struct Output { COutPoint out; Amount value; };
struct Fixture {
    CTxMemPool pool;
    std::map<TxId, Amount> fees;
    std::map<TxId, Amount> deltas;
    std::map<TxId, std::vector<TxId>> parents;
    size_t bytes = 0;
    size_t edges = 0;

    std::vector<Output> add(const std::vector<Output> &inputs, size_t outputs, int64_t feeSats) {
        CMutableTransaction tx;
        Amount value = Amount::zero();
        std::vector<TxId> dep;
        for (const auto &input : inputs) {
            tx.vin.emplace_back(input.out, sig);
            value += input.value;
            if (fees.count(input.out.GetTxId())) dep.push_back(input.out.GetTxId());
        }
        const Amount fee = feeSats * SATOSHI;
        require(value > fee);
        const int64_t available = (value - fee) / SATOSHI;
        for (size_t j = 0; j < outputs; ++j) {
            const int64_t each = available / outputs + (j < size_t(available % outputs));
            tx.vout.emplace_back(each * SATOSHI, pub);
        }
        const auto ref = MakeTransactionRef(tx);
        TestMemPoolEntryHelper entry;
        entry.Fee(fee).SigChecks(0);
        {
            LOCK2(cs_main, pool.cs);
            pool.addUnchecked(entry.FromTx(ref));
        }
        fees.emplace(ref->GetId(), fee);
        parents.emplace(ref->GetId(), dep);
        edges += dep.size();
        bytes += ref->GetTotalSize();
        std::vector<Output> result;
        for (size_t j = 0; j < outputs; ++j) result.push_back({COutPoint(ref->GetId(), j), ref->vout[j].nValue});
        return result;
    }
    void delta(const Output &output, int64_t sats) {
        LOCK(pool.cs);
        pool.PrioritiseTransaction(output.out.GetTxId(), sats * SATOSHI);
        deltas[output.out.GetTxId()] = sats * SATOSHI;
    }
};

void run(benchmark::State &state, const std::string &shape, size_t count, bool constrained, bool validity) {
    const Config &config = GetConfig();
    const auto coin = MineBlock(config, pub);
    for (int i = 0; i <= COINBASE_MATURITY; ++i) MineBlock(config, pub);

    size_t roots = count;
    if (shape == "chains") roots = (count + 99) / 100;
    if (shape == "fanout") roots = (count + 64) / 65;
    if (shape == "wide") roots = 1;
    if (shape == "diamonds") roots = (count + 3) / 4;
    CMutableTransaction funding;
    funding.vin.push_back(coin);
    funding.vin.back().scriptSig = sig;
    // First regtest coinbase is 50 BCH. Leave an exact 1000000 satoshi funding fee.
    const int64_t spendable = (50 * COIN) / SATOSHI - 1000000;
    for (size_t i = 0; i < roots; ++i) {
        funding.vout.emplace_back(int64_t(spendable / roots + (i < size_t(spendable % roots))) * SATOSHI, pub);
    }
    const auto fund = MakeTransactionRef(funding);
    {
        LOCK2(cs_main, g_mempool.cs);
        TestMemPoolEntryHelper entry;
        entry.Fee(1000000 * SATOSHI).SpendsCoinbase(true).SigChecks(0);
        g_mempool.addUnchecked(entry.FromTx(fund));
    }
    MineBlock(config, pub);
    require(g_mempool.size() == 0);
    Fixture f;
    size_t built = 0;
    for (size_t r = 0; r < roots; ++r) {
        const Output root{COutPoint(fund->GetId(), r), fund->vout[r].nValue};
        if (shape == "independent") {
            f.add({root}, 1, 1000 + (r * 7919 % 7000));
            ++built;
        } else if (shape == "chains") {
            Output prev = root;
            for (size_t j = 0; j < 100 && built < count; ++j, ++built) {
                prev = f.add({prev}, 1, 1000 + j * 20)[0];
            }
        } else if (shape == "fanout" || shape == "wide") {
            const size_t width = shape == "wide" ? count - 1 : std::min(size_t(64), count - built - 1);
            const auto children = f.add({root}, width, 2 * (200 + int64_t(32 * width)));
            ++built;
            for (size_t j = 0; j < width; ++j, ++built) {
                const auto child = f.add({children[j]}, 1, 1500 + j * 7919 % 6500)[0];
                // Explicit modified-fee deltas, never counted as actual miner income.
                if (j % 3 == 0) f.delta(child, 4000);
            }
        } else {
            require(shape == "diamonds");
            const auto split = f.add({root}, 2, 1000);
            const auto left = f.add({split[0]}, 1, 3000)[0];
            const auto right = f.add({split[1]}, 1, 5000)[0];
            f.add({left, right}, 1, 8000);
            built += 4;
        }
    }
    require(f.pool.size() == built);
    BlockAssembler::Options opts;
    opts.nConsensusCurrentBlockSizeLimit = 32000000;
    opts.nMaxGeneratedBlockSize = constrained ? 1000000 : 32000000;
    opts.blockMinFeeRate = CFeeRate(1000 * SATOSHI); // BCHN default, no free-parent policy override
    auto assemble = [&](bool validate) { return BlockAssembler(config, f.pool, opts).CreateNewBlock(pub, 0., validate); };
    // Full consensus/script validation before timing, also for the selection-only measurements.
    auto proof = assemble(true);
    Amount actual = Amount::zero(), modified = Amount::zero();
    std::map<TxId, bool> selected;
    for (size_t i = 1; i < proof->block.vtx.size(); ++i) {
        const auto id = proof->block.vtx[i]->GetId();
        require(!selected[id]);
        selected[id] = true;
        actual += f.fees.at(id);
        modified += f.fees.at(id) + f.deltas[id];
        require(proof->entries[i].fees == f.fees.at(id));
    }
    for (const auto &[id, included] : selected) {
        if (included) for (const auto &parent : f.parents.at(id)) require(selected[parent]);
    }
    const size_t selectedCount = proof->block.vtx.size() - 1;
    require(constrained || selectedCount == built);
    require(proof->block.vtx[0]->GetValueOut() == GetBlockSubsidy(ChainActive().Height() + 1, config.GetChainParams().GetConsensus()) + actual);
    require(GetSerializeSize(proof->block, PROTOCOL_VERSION) < opts.nMaxGeneratedBlockSize);
    for (int i = 0; i < 3; ++i) assemble(validity); // warm allocator and validation caches
    std::cout << "# fixture," << state.GetName() << ',' << built << ',' << f.edges << ',' << f.bytes
              << ',' << opts.nMaxGeneratedBlockSize << ',' << selectedCount << ',' << actual / SATOSHI
              << ',' << modified / SATOSHI << ',' << GetSerializeSize(proof->block, PROTOCOL_VERSION) << '\n';
    std::vector<int64_t> samples;
    samples.reserve(state.m_num_iters);
    BENCHMARK_LOOP {
        const auto begin = std::chrono::steady_clock::now();
        {
            const auto block = assemble(validity);
            require(block->block.vtx.size() - 1 == selectedCount);
        }
        samples.push_back(std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now() - begin).count());
    }
    std::cout << "# samples_ns," << state.GetName();
    for (const auto sample : samples) std::cout << ',' << sample;
    std::cout << '\n';
}
} // namespace

#define CASE(NAME, SHAPE, N, CAP, VALID) \
static void NAME(benchmark::State &s) { run(s, SHAPE, N, CAP, VALID); } \
BENCHMARK(NAME, 10);
CASE(ReadyIndependent2000, "independent", 2000, false, false)
CASE(ReadyIndependent20000, "independent", 20000, false, false)
CASE(ReadyChains2000, "chains", 2000, false, false)
CASE(ReadyChains20000, "chains", 20000, false, false)
CASE(ReadyFanout2000, "fanout", 2000, false, false)
CASE(ReadyFanout20000, "fanout", 20000, false, false)
CASE(ReadyDiamonds2000, "diamonds", 2000, false, false)
CASE(ReadyDiamonds20000, "diamonds", 20000, false, false)
CASE(ReadyWide2000, "wide", 2000, false, false)
CASE(ReadyWide20000, "wide", 20000, false, false)
CASE(ReadyFanout20000Cap, "fanout", 20000, true, false)
CASE(ReadyWide20000Cap, "wide", 20000, true, false)
CASE(ReadyFanout20000Validated, "fanout", 20000, false, true)
CASE(ReadyFanout20000CapValidated, "fanout", 20000, true, true)

CASE(ReadyFanout100000, "fanout", 100000, false, false)
CASE(ReadyChains100000, "chains", 100000, false, false)
