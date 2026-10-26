"""Pure owner266 repair map transform; no source/Git/cache writes."""
import json
from pathlib import Path
PAYLOAD=json.loads((Path(__file__).parent/'payload.json').read_text())
def transform(files):
    result=dict(files)
    path='src/net/v2_protocol_handler.cpp'
    value=result[path];content=value.decode() if isinstance(value,bytes) else value
    for old,new in PAYLOAD['production']:
        if new in content:continue
        if content.count(old)!=1:raise ValueError('Missing/nonunique production anchor '+repr(old[:100]))
        content=content.replace(old,new,1)
    result[path]=content.encode() if isinstance(value,bytes) else content
    path='src/test/v2_protocol_handler_tests.cpp'
    value=result[path];content=value.decode() if isinstance(value,bytes) else value
    if 'BOOST_AUTO_TEST_CASE(relay_epoch_balanced_difference_requires_recovery)' not in content:
        marker=('BOOST_AUTO_TEST_CASE(root_count_one_xor_requires_bucket_proof)'
                if 'BOOST_AUTO_TEST_CASE(root_count_one_xor_requires_bucket_proof)' in content
                else 'BOOST_AUTO_TEST_SUITE_END()')
        if content.count(marker)!=1:raise ValueError('Nonunique test suite endpoint')
        content=content.replace(marker,PAYLOAD['test']+marker)
    result[path]=content.encode() if isinstance(value,bytes) else content
    return result
