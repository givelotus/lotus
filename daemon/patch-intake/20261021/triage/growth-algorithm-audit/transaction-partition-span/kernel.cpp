#include <lotus_v2/commitment.h>
#include <lotus_v2/tagged_hash.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdio>
#include <future>
#include <stdexcept>
#include <vector>
using namespace lotus::v2;
Hash Reference(std::vector<const TxIdentityPair *> txs, unsigned depth = 0) {
    if (txs.empty()) return TaggedHash(HashDomain::TxRoot, std::array<uint8_t,1>{2});
    if (txs.size()==1) {
        std::array<uint8_t,65> b{};
        std::copy(txs[0]->tx_id.begin(),txs[0]->tx_id.end(),b.begin()+1);
        std::copy(txs[0]->tx_hash.begin(),txs[0]->tx_hash.end(),b.begin()+33);
        return TaggedHash(HashDomain::TxRoot,b);
    }
    if(depth==256) throw std::invalid_argument("duplicate");
    std::vector<const TxIdentityPair *> l,r;
    for(auto *tx:txs) (((tx->tx_id[depth/8]>>(depth%8))&1)?r:l).push_back(tx);
    auto a=Reference(l,depth+1),b=Reference(r,depth+1);
    std::array<uint8_t,67> bytes{};bytes[0]=1;bytes[1]=depth;bytes[2]=depth>>8;
    std::copy(a.begin(),a.end(),bytes.begin()+3);std::copy(b.begin(),b.end(),bytes.begin()+35);
    return TaggedHash(HashDomain::TxRoot,bytes);
}
std::vector<TxIdentityPair> Fixture(size_t n,bool prefix=false) {
    uint64_t s=234567891;
    auto next=[&] {s^=s<<13;s^=s>>7;s^=s<<17;return s;};
    std::vector<TxIdentityPair> out(n);
    for(auto &tx:out) for(size_t i=0;i<32;++i) {tx.tx_id[i]=next();tx.tx_hash[i]=next();}
    if(prefix)for(auto &tx:out)std::fill(tx.tx_id.begin(),tx.tx_id.begin()+16,0);
    return out;
}
int main(int argc,char **argv) {
    if(argc>1) {
        size_t n=std::stoull(argv[1]);auto f=Fixture(n);auto expected=BuildTxSubtreeA(f);
        for (auto byte : expected) std::fprintf(stderr, "%02x", unsigned(byte));
        std::fprintf(stderr, "\n");
        auto start=std::chrono::steady_clock::now();size_t repeats=0;
        do {if(BuildTxSubtreeA(f)!=expected)return 2;++repeats;}
        while(std::chrono::steady_clock::now()-start<std::chrono::seconds(3));
        double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        std::printf("{\"transactions\":%zu,\"roots\":%zu,\"seconds\":%.8f,\"ms_per_root\":%.8f}\n",n,repeats,seconds,seconds*1000/repeats);return 0;
    }
    size_t cases=0;
    for(size_t n:{0,1,2,63,64,65,255,256,1024,4096,65536})for(bool p:{false,true}) {
        if(n==65536 && p)continue;
        auto f=Fixture(n,p);std::vector<const TxIdentityPair*> ptrs;for(auto &tx:f)ptrs.push_back(&tx);
        auto expected=Reference(ptrs);if(BuildTxSubtreeA(f)!=expected)return 3;
        std::reverse(f.begin(),f.end());
        std::vector<std::future<bool>> tasks;
        for(int j=0;j<4;++j)tasks.push_back(std::async(std::launch::async,[&]{for(int k=0;k<8;++k)if(BuildTxSubtreeA(f)!=expected)return false;return true;}));
        for(auto &task:tasks)if(!task.get())return 4;
        ++cases;
    }
    auto duplicate=Fixture(128);duplicate.back().tx_id=duplicate.front().tx_id;
    try{BuildTxSubtreeA(duplicate);return 5;}catch(const std::invalid_argument&){}
    if(BuildTxSubtreeA(Fixture(4096))!=BuildTxSubtreeA(Fixture(4096)))return 6;
    std::printf("{\"status\":\"ok\",\"oracle_cohorts\":%zu,\"concurrent_root_calls\":%zu,\"duplicate_rejection\":true,\"post_error_reuse\":true}\n",cases,cases*32);
}
