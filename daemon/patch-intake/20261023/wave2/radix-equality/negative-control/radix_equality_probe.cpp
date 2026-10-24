#include <radix.h>
#include <uint256radixkey.h>
#include <iostream>
struct Entry {
    Uint256RadixKey key;
    explicit Entry(const Uint256RadixKey &value) : key(value) {}
    const Uint256RadixKey &getId() const { return key; }
    IMPLEMENT_RCU_REFCOUNT(uint32_t);
};
int main() {
    const Uint256RadixKey low{arith_uint256(42)};
    const Uint256RadixKey high{arith_uint256(42) | (arith_uint256(1) << 255)};
    RadixTree<Entry> tree;
    const auto first = RCUPtr<Entry>::make(low);
    const auto second = RCUPtr<Entry>::make(high);
    const bool inserted_first = tree.insert(first);
    const bool wrong_lookup = bool(tree.get(high));
    const bool false_equality = low == high;
    const bool inserted_second = tree.insert(second);
    std::cout << "inserted_first=" << inserted_first
              << " false_equality=" << false_equality
              << " absent_key_found=" << wrong_lookup
              << " inserted_distinct_high_key=" << inserted_second << '\n';
    return inserted_first && !false_equality && !wrong_lookup && inserted_second
        ? 0 : 1;
}
