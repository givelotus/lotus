import json
from pathlib import Path
PAYLOAD=json.loads((Path(__file__).parent/'payload.json').read_text())
def transform(files):
 result=dict(files)
 for path,changes in PAYLOAD.items():
  if path in ('new_test','metric_changes'):continue
  value=result[path];content=value.decode() if isinstance(value,bytes) else value
  for old,new in changes:
   if new in content:continue
   if content.count(old)!=1:raise ValueError('Missing/nonunique anchor '+repr(old[:100]))
   content=content.replace(old,new,1)
  if path.endswith('tests.cpp') and 'metrics.m.merklix_rounds' in content:
   for old,new in PAYLOAD['metric_changes']:
    if new in content:continue
    if content.count(old)!=1:raise ValueError('Missing metric anchor '+repr(old[:100]))
    content=content.replace(old,new,1)
  if path.endswith('tests.cpp') and 'BOOST_AUTO_TEST_CASE(root_count_one_xor_requires_bucket_proof)' not in content:
   marker='BOOST_AUTO_TEST_SUITE_END()'
   if content.count(marker)!=1:raise ValueError('Bad test suite anchor')
   content=content.replace(marker,PAYLOAD['new_test']+marker)
  result[path]=content.encode() if isinstance(value,bytes) else content
 return result
