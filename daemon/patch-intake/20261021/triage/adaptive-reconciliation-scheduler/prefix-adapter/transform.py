"""Pure map transform for one new shared scheduling purpose; no source writes."""
import json
from pathlib import Path
PAYLOAD=json.loads((Path(__file__).parent/'payload.json').read_text())

def once(text,old,new):
    if old in new and new in text:return text
    if old in text:
        if text.count(old)!=1:raise ValueError('Nonunique anchor '+repr(old[:100]))
        return text.replace(old,new,1)
    if new in text:return text
    raise ValueError('Absent anchor '+repr(old[:100]))

def transform(files):
    result=dict(files)
    for path,changes in PAYLOAD.items():
        if path=='new_tests':continue
        if isinstance(changes,dict):
            content=changes['new_file']
            if path in result:
                current=result[path].decode() if isinstance(result[path],bytes) else result[path]
                if current!=content:raise ValueError('Conflicting new header')
            else:
                sample=next(iter(files.values()))
                result[path]=content.encode() if isinstance(sample,bytes) else content
            continue
        value=result[path]
        content=value.decode() if isinstance(value,bytes) else value
        for old,new in changes:
            if path=='src/net_processing.cpp' and '      m_mempool(pool)' in old:
                marker='      m_txrelay_index{opts.txrelay_shortid_bits},\n'
                init=new[new.index('      m_recon_scheduler{'):new.index('      m_v2_protocol_handler{')]
                content=once(content,marker,marker+init)
                marker='    m_v2_protocol_handler.SetTxRelayEpochProvider(this);'
                arm=new[new.index('    // Arm quiet discovery'):new.index(marker)]
                content=once(content,marker,arm+marker)
            else:content=once(content,old,new)
        if path=='src/test/txrelay_tests.cpp':
            if 'BOOST_AUTO_TEST_CASE(reconciliation_count_time_and_generation)' not in content:
                content=once(content,'BOOST_AUTO_TEST_SUITE_END()',
                    '\n'+PAYLOAD['new_tests']+'BOOST_AUTO_TEST_SUITE_END()')
        result[path]=content.encode() if isinstance(value,bytes) else content
    return result
