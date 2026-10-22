"""Pure owned-source map adapter; no Git/filesystem mutation."""
PATH = "src/net/txrelay_index.h"
OLD_GETTER = "        Uint256RadixKey getId() const { return txid; }\n"
OLD_ALIAS = "RadixTree<WindowEntry, PassthroughAdapter<WindowEntry>,"
NEW_ALIAS = "RadixTree<WindowEntry, WindowEntryAdapter,"
MARKER = "    using WindowTree =\n"
ADAPTER = """    struct WindowEntryAdapter {
        // Return the numeric key by value. PassthroughAdapter returns auto&&,
        // which would dangle if forwarded from a temporary key conversion.
        Uint256RadixKey getId(const WindowEntry &entry) const {
            return entry.txid;
        }
    };
"""

def transform(files):
    result = dict(files)
    if PATH not in result:
        return result
    original = result[PATH]
    text = original.decode() if isinstance(original, bytes) else original
    if "    struct WindowEntry {" not in text:
        return result  # Purpose has not entered this earlier prefix.
    if ADAPTER in text and NEW_ALIAS in text and OLD_GETTER not in text and OLD_ALIAS not in text:
        return result
    for anchor in (OLD_GETTER, OLD_ALIAS, MARKER):
        if text.count(anchor) != 1:
            raise ValueError("missing/nonunique lifetime repair anchor: " + repr(anchor))
    if ADAPTER in text or NEW_ALIAS in text:
        raise ValueError("partial lifetime repair")
    text = text.replace(OLD_GETTER, "", 1).replace(MARKER, ADAPTER + MARKER, 1)
    text = text.replace(OLD_ALIAS, NEW_ALIAS, 1)
    result[PATH] = text.encode() if isinstance(original, bytes) else text
    return result
