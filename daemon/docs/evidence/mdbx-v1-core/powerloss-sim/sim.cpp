// Power-loss and kill -9 experiment for libmdbx durability settings.
//
//   sim gen <dir> <flags-hex> <pagesize>   write a workload, capture images
//   sim kill-writer <dir> <flags-hex> <pagesize>  write until killed
//   sim verify <dir> <flags-hex> <pagesize>       open, compare with the model
//
// Each transaction applies a deterministic set of changes and records its own
// number under the key "!txn". The verifier reads that number, replays the
// model up to it and compares every key and value, so it detects any state
// that is not exactly a committed prefix of the transaction history. That is
// the property the node's chainstate needs from its database.
#include "mdbx.h"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <string>
#include <unistd.h>

static const int NKEYS = 20000;
static const int CHANGES = 1500;
static const int TXNS_BEFORE_SYNC = 40;
static const int TXNS_AFTER_SYNC = 160;

static uint64_t mix(uint64_t x) {
    x ^= x >> 33; x *= 0xff51afd7ed558ccdULL; x ^= x >> 33;
    x *= 0xc4ceb9fe1a85ec53ULL; x ^= x >> 33; return x;
}
static std::string key_of(uint64_t i) {
    char b[32]; snprintf(b, sizeof(b), "k%016llx", (unsigned long long)mix(i)); return b;
}
static std::string val_of(uint64_t k, uint64_t txn) {
    uint64_t h = mix(k * 1000003 + txn);
    size_t len = 16 + h % 200;
    if (h % 100 == 0) len = 9000; // spills to overflow pages
    std::string s(len, 0);
    for (size_t i = 0; i < len; i++) { if (i % 8 == 0) h = mix(h + i); s[i] = char(h >> (8 * (i % 8))); }
    return s;
}
// A change: set (key, value) or erase. Deterministic in txn number.
template <typename F> static void changes(uint64_t txn, F f) {
    for (int c = 0; c < CHANGES; c++) {
        uint64_t r = mix(txn * 7919 + c);
        uint64_t k = r % NKEYS;
        bool erase = (r >> 40) % 4 == 0 && txn > 1;
        f(k, erase, txn);
    }
}
static void model_apply(std::map<std::string, std::string>& m, uint64_t txn) {
    changes(txn, [&](uint64_t k, bool erase, uint64_t t) {
        if (erase) m.erase(key_of(k)); else m[key_of(k)] = val_of(k, t);
    });
    char b[32]; snprintf(b, sizeof(b), "%llu", (unsigned long long)txn);
    m["!txn"] = b;
}
#define CK(x) do { int _rc = (x); if (_rc != MDBX_SUCCESS && _rc != MDBX_RESULT_TRUE) { \
    fprintf(stderr, "%s: %d %s\n", #x, _rc, mdbx_strerror(_rc)); exit(3); } } while (0)

static MDBX_env* open_env(const char* dir, unsigned flags, int pagesize, MDBX_dbi* dbi) {
    MDBX_env* env;
    CK(mdbx_env_create(&env));
    CK(mdbx_env_set_maxreaders(env, 16));
    CK(mdbx_env_set_geometry(env, 1 << 20, 16 << 20, intptr_t(16) << 30, 64 << 20, 128 << 20, pagesize));
    int rc = mdbx_env_open(env, dir, MDBX_env_flags_t(flags), 0600);
    if (rc != MDBX_SUCCESS) { printf("open-failed rc=%d %s\n", rc, mdbx_strerror(rc)); fflush(stdout); _exit(10); }
    CK(mdbx_env_set_option(env, MDBX_opt_sync_bytes, 0));
    CK(mdbx_env_set_option(env, MDBX_opt_sync_period, 0));
    MDBX_txn* t;
    CK(mdbx_txn_begin(env, nullptr, MDBX_TXN_READWRITE, &t));
    CK(mdbx_dbi_open(t, nullptr, MDBX_CREATE, dbi));
    CK(mdbx_txn_commit(t));
    return env;
}
static void write_txn(MDBX_env* env, MDBX_dbi dbi, uint64_t txn) {
    MDBX_txn* t;
    CK(mdbx_txn_begin(env, nullptr, MDBX_TXN_READWRITE, &t));
    changes(txn, [&](uint64_t k, bool erase, uint64_t tn) {
        std::string ks = key_of(k);
        MDBX_val mk{ks.data(), ks.size()};
        if (erase) {
            int rc = mdbx_del(t, dbi, &mk, nullptr);
            if (rc != MDBX_NOTFOUND) CK(rc);
        } else {
            std::string vs = val_of(k, tn);
            MDBX_val mv{vs.data(), vs.size()};
            CK(mdbx_put(t, dbi, &mk, &mv, MDBX_UPSERT));
        }
    });
    char b[32]; int n = snprintf(b, sizeof(b), "%llu", (unsigned long long)txn);
    MDBX_val mk{(void*)"!txn", 4}, mv{b, size_t(n)};
    CK(mdbx_put(t, dbi, &mk, &mv, MDBX_UPSERT));
    CK(mdbx_txn_commit(t));
}
static void copy_file(const std::string& a, const std::string& b) {
    std::string cmd = "cp '" + a + "' '" + b + "'";
    if (system(cmd.c_str())) exit(4);
}
static void info(MDBX_env* env, const char* tag) {
    MDBX_envinfo i{};
    CK(mdbx_env_info_ex(env, nullptr, &i, sizeof(i)));
    printf("%s recent_txnid=%llu metas: %llu/%llx %llu/%llx %llu/%llx\n", tag,
           (unsigned long long)i.mi_recent_txnid,
           (unsigned long long)i.mi_meta_txnid[0], (unsigned long long)i.mi_meta_sign[0],
           (unsigned long long)i.mi_meta_txnid[1], (unsigned long long)i.mi_meta_sign[1],
           (unsigned long long)i.mi_meta_txnid[2], (unsigned long long)i.mi_meta_sign[2]);
    fflush(stdout);
}

int main(int argc, char** argv) {
    if (argc < 5) return 2;
    std::string mode = argv[1], dir = argv[2];
    unsigned flags = strtoul(argv[3], nullptr, 16);
    int pagesize = atoi(argv[4]);
    mdbx_setup_debug(MDBX_LOG_FATAL, MDBX_DBG_DONTCHANGE, MDBX_LOGGER_DONTCHANGE);
    MDBX_dbi dbi;
    if (mode == "gen") {
        MDBX_env* env = open_env((dir + "/db").c_str(), flags, pagesize, &dbi);
        for (uint64_t t = 1; t <= TXNS_BEFORE_SYNC; t++) write_txn(env, dbi, t);
        CK(mdbx_env_sync_ex(env, true, false));
        info(env, "after-explicit-sync");
        copy_file(dir + "/db/mdbx.dat", dir + "/D0");
        for (uint64_t t = TXNS_BEFORE_SYNC + 1; t <= TXNS_BEFORE_SYNC + TXNS_AFTER_SYNC; t++) write_txn(env, dbi, t);
        info(env, "after-unsynced-commits");
        copy_file(dir + "/db/mdbx.dat", dir + "/D1");
        fflush(stdout);
        _exit(0); // no close, no final sync: the point of the experiment
    }
    if (mode == "kill-writer") {
        MDBX_env* env = open_env((dir + "/db").c_str(), flags, pagesize, &dbi);
        uint64_t t = 1;
        if (argc > 5) t = strtoull(argv[5], nullptr, 10) + 1;
        for (;; t++) {
            write_txn(env, dbi, t);
            if (t % 25 == 0) CK(mdbx_env_sync_ex(env, true, false));
        }
    }
    if (mode == "verify") {
        MDBX_env* env = open_env((dir + "/db").c_str(), flags, pagesize, &dbi);
        MDBX_txn* t;
        CK(mdbx_txn_begin(env, nullptr, MDBX_TXN_RDONLY, &t));
        MDBX_cursor* c;
        CK(mdbx_cursor_open(t, dbi, &c));
        std::map<std::string, std::string> got;
        MDBX_val k{}, v{};
        int rc = mdbx_cursor_get(c, &k, &v, MDBX_FIRST);
        while (rc == MDBX_SUCCESS) {
            got[std::string((char*)k.iov_base, k.iov_len)] = std::string((char*)v.iov_base, v.iov_len);
            rc = mdbx_cursor_get(c, &k, &v, MDBX_NEXT);
        }
        if (rc != MDBX_NOTFOUND) { printf("scan-error rc=%d %s\n", rc, mdbx_strerror(rc)); fflush(stdout); _exit(11); }
        mdbx_cursor_close(c);
        mdbx_txn_abort(t);
        uint64_t marker = 0;
        if (got.count("!txn")) marker = strtoull(got["!txn"].c_str(), nullptr, 10);
        std::map<std::string, std::string> model;
        for (uint64_t i = 1; i <= marker; i++) model_apply(model, i);
        size_t wrong = 0, missing = 0, extra = 0;
        for (auto& [ks, vs] : model) {
            auto it = got.find(ks);
            if (it == got.end()) missing++; else if (it->second != vs) wrong++;
        }
        for (auto& [ks, vs] : got) if (!model.count(ks)) extra++;
        if (wrong || missing || extra) {
            printf("SILENT-WRONG-STATE marker=%llu wrong=%zu missing=%zu extra=%zu\n",
                   (unsigned long long)marker, wrong, missing, extra);
            fflush(stdout);
            _exit(12);
        }
        // Keep going like a node would; a broken free list shows up here.
        write_txn(env, dbi, marker + 1);
        printf("exact-prefix marker=%llu\n", (unsigned long long)marker);
        fflush(stdout);
        _exit(0);
    }
    return 2;
}
