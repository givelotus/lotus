"""Restore exact sampled symbol files from the compact committed archive."""
import base64,hashlib,json,zlib
from pathlib import Path
r=Path(__file__).resolve().parent
for name,item in json.loads((r/'RAW-PROFILES.json').read_text()).items():
    data=zlib.decompress(base64.b64decode(item['data']))
    assert len(data)==item['uncompressed_bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
    p=r/name
    assert not p.exists() or p.read_bytes()==data
    if not p.exists():p.write_bytes(data)
