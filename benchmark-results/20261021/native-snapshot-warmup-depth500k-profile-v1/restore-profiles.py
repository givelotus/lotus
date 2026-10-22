import base64,hashlib,json,zlib
from pathlib import Path
r=Path(__file__).resolve().parent
for name,item in json.loads((r/'RAW-PROFILES.json').read_text()).items():
 data=zlib.decompress(base64.b64decode(item['data']))
 assert hashlib.sha256(data).hexdigest()==item['sha256']
 (r/name).write_bytes(data)
