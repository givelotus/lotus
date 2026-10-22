"""Pure source-map transform. No Git calls, source/cache writes, or ref mutations."""
import json
from pathlib import Path
PAYLOAD=json.loads((Path(__file__).parent/'payload.json').read_text())
TEST='src/test/v2_protocol_handler_tests.cpp'
HANDLER='src/net/v2_protocol_handler.cpp'
NET='src/net_processing.cpp'

def once(text,old,new):
    if old in new and new in text:return text
    if old in text:
        if text.count(old)!=1:raise ValueError('Nonunique anchor '+repr(old[:100]))
        return text.replace(old,new,1)
    if new in text:return text
    raise ValueError('Absent anchor '+repr(old[:100]))

def transform(files):
    result=dict(files)
    def read(p):
        x=result[p];return x.decode() if isinstance(x,bytes) else x
    def save(p,s):result[p]=s.encode() if isinstance(files[p],bytes) else s
    if HANDLER not in files:return result
    h=read(HANDLER)
    old='if (it->second.requested_short_ids.erase(sid) > 0) {'
    new='''// Receiving one requested body does not revoke opt-in for
                // the other bodies in the same high-bandwidth response.
                if (it->second.requested_short_ids.erase(sid) > 0 ||
                    high_bandwidth_opt_in) {'''
    if old in h or new in h:h=once(h,old,new)
    save(HANDLER,h)
    has_epoch=NET in files and 'OurTxRelayFeatures() const' in read(NET)
    if has_epoch:
        for p,hs in PAYLOAD.items():
            if p==TEST:continue
            t=read(p)
            for i,(a,b) in enumerate(hs):
                if p==HANDLER and i==2:continue # shared owner above
                if p==NET and i==0:
                    marker='    void ProcessShortTxResponse('
                    addition=b[b.index('    std::vector<CTransactionRef> FilterRequestedShortTxResponse('):b.index(marker)]
                    if addition not in t:t=once(t,marker,addition+marker)
                elif p==NET and i==1:
                    addition=b[len(a):]
                    marker='void PeerManagerImpl::ProcessShortTxResponse('
                    if addition not in t:t=once(t,marker,addition+marker)
                else:t=once(t,a,b)
            save(p,t)
    if TEST in files:
        t=read(TEST)
        for i,(a,b) in enumerate(PAYLOAD[TEST]):
            if i==0:continue
            # Existing generic test controls enter when that test exists.
            if i in (4,5,6):
                if a not in t and b not in t:continue
            elif not has_epoch:continue
            elif i in (1,3):
                if 'TXRELAY_HIGH_BANDWIDTH' not in read('src/net/txrelay_index.h'):continue
                if a not in t and b not in t:continue
            elif i==2:
                # New wire case requires the real index test-mask option and
                # legacy/native funding helpers already present at this prefix.
                if ('txrelay_shortid_bits' not in read('src/net_processing.h') or
                    'void FundTxInputInCoinsTip' not in t or
                    'struct MockRelayTick' not in t):continue
            if i==1:
                start=t.index('BOOST_AUTO_TEST_CASE(bursts_wait_for_the_relay_tick) {')
                end=t.find('BOOST_AUTO_TEST_CASE(',start+1)
                if end<0:end=len(t)
                t=t[:start]+once(t[start:end],a,b)+t[end:]
            else:t=once(t,a,b)
        if 'relay_epoch_responses_use_authoritative_requests' in t:
            t=once(t,*PAYLOAD[TEST][0])
        save(TEST,t)
    return result
