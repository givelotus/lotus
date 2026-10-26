"""Pure prefix transform for MR06, owner recovered-relay-0004/global265.

Input/output are path->bytes or str dictionaries. No writes, Git calls, refs,
cache access or build side effects occur. Payload is immutable alongside module.
"""
from pathlib import Path
import json

PAYLOAD = json.loads((Path(__file__).parent / 'payload.json').read_text())
NET = 'src/net_processing.cpp'
OPTIONS = 'src/net_processing.h'
TXTEST = 'src/test/txrelay_tests.cpp'


def once(text, old, new):
    if old in new and new in text:
        return text
    if old in text:
        if text.count(old) != 1:
            raise ValueError(f'Nonunique anchor: {old[:100]!r}')
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise ValueError(f'Absent old/new anchor: {old[:100]!r}')


def transform(files):
    result = dict(files)
    def read(path):
        value = files[path]
        return value.decode() if isinstance(value, bytes) else value
    def save(path, text):
        result[path] = text.encode() if isinstance(files[path], bytes) else text
    if NET not in files or 'OurTxRelayFeatures() const' not in read(NET):
        return result
    has_push = 'bool txrelay_push_hb{' in read(OPTIONS)
    n = read(NET)
    start = n.index('    uint64_t OurTxRelayFeatures() const {')
    end = n.index('\n    }', start) + len('\n    }')
    old = n[start:end]
    # Continuous reconciliation is added by a later owner. Do not import its
    # options into the earlier short-ID negotiation owner.
    has_recon = 'txrecon_interval' in old
    features = PAYLOAD['features']
    if not has_recon:
        features = features.replace('''            if (m_opts.txrecon_interval > 0ms) {
                features |= txrelay::TXRELAY_RECON;
            }
''', '')
    if not has_push:
        # Before -txrelaypushhb, the existing relay policy pushes bodies by
        # default. Preserve that willingness, but require the remote feature.
        features = features.replace('''        if (!disabled_for_test &&
            (gArgs.GetBoolArg("-highbandwidthtx", false) ||
             m_opts.txrelay_push_hb)) {''', '''        if (!disabled_for_test) {''')
    n = n[:start] + features + n[end:]
    for old, new in PAYLOAD[NET]:
        if 'uint64_t OurTxRelayFeatures() const' in old:
            continue
        if 'const bool is_hb_sealed_peer' in old and 'const bool is_hb_sealed_peer' not in n:
            # Ordinary-announcement sealed relay is added by a native owner.
            continue
        if 'pto->m_bip152_highbandwidth_from.load()' in old:
            # Earlier owners combine the block-only and test-override clauses
            # on one line. Replace only the unsafe remote-capability predicate.
            old = old[old.index('                (pto->'):]
            new = new[new.index('                (peer->'):]
            old = old.rstrip('\n')
            new = new.rstrip('\n')
        n = once(n, old, new)
    save(NET, n)
    for path in ['src/net/txrelay_index.h', 'src/protocol.h', OPTIONS,
                 'src/test/v2_protocol_handler_tests.cpp']:
        if path not in files:
            continue
        text = read(path)
        for old, new in PAYLOAD[path]:
            if path == OPTIONS and not has_push:
                continue
            text = once(text, old, new)
        save(path, text)
    if TXTEST in files:
        text = read(TXTEST)
        if '#include <common/args.h>' not in text:
            text = once(text, '#include <config.h>\n',
                        '#include <config.h>\n#include <common/args.h>\n')
        if has_push:
            marker = 'BOOST_AUTO_TEST_CASE(no_body_push_by_default) {'
            if marker not in text:
                raise ValueError('Push option exists without its original test')
            if 'BOOST_AUTO_TEST_CASE(stock_peer_does_not_support_private_relay)' not in text:
                text = once(text, marker, PAYLOAD['new_cases'] + marker)
            # New tests use only APIs of the already-present RelayHarness and
            # the -txrelaypushhb option. Its default-body test gets real offers.
            for old, new in PAYLOAD[TXTEST]:
                if ('#include <common/args.h>' in new or
                        'stock_peer_does_not_support_private_relay' in new):
                    continue
                text = once(text, old, new)
            old_start = marker + '\n    LOCK(NetEventsInterface::g_msgproc_mutex);\n'
            new_start = old_start + '''    struct ResetArgs {
        ~ResetArgs() { gArgs.ClearForcedArg("-highbandwidthtx"); }
    } reset_args;
    gArgs.ForceSetArg("-highbandwidthtx", "1");
'''
            text = once(text, old_start, new_start)
        save(TXTEST, text)
    return result
