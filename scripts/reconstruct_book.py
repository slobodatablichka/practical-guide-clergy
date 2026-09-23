from pathlib import Path
import json,base64,hashlib
root=Path(__file__).resolve().parents[1]
m=json.loads((root/'assets/book/manifest.json').read_text(encoding='utf-8'))
data=b''.join(base64.b64decode((root/p).read_text(encoding='ascii')) for p in m['chunks'])
assert len(data)==m['size'] and hashlib.sha256(data).hexdigest()==m['sha256']
p=root/'assets/book'/m['filename'];p.write_bytes(data);print(p)
