# Isolated generic tree include prerequisite

Candidate01003b36/tree591fb5e7 changes only two header includes from native header.h to existing generic commitment.h. Hash/TxIdentityPair definitions are already available in shared; no algorithm, hash domain, wire format or codec changes. The existing final tree-owner commit at HEAD was amended on an isolated review branch; canonical refs remain on the exact f58 order checkpoint.

Native daemon/core/AVA build516 passed. Full unfiltered native core gate passed1203/1203 cases,31,375,947 assertions in44.38s. Exact diff, source identity, commands and preserved binary/cache/config hashes are adjacent. Generic engine ownership rehome is separate, uses this explicitly changed591 tree as its hard endpoint; it must not be described as an f58-preserving shuffle.
