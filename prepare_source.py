"""Restore complete workflow source shipped alongside the core. No business data."""
from pathlib import Path
import hashlib, tarfile
ROOT = Path(__file__).resolve().parent
archive = ROOT/'workflow-source.tar.gz'
EXPECTED = 'b1fa0e66286cd50c867910b10dfb832614ce28eee7221bb7906ac999e2993041'
if hashlib.sha256(archive.read_bytes()).hexdigest() != EXPECTED:
    raise SystemExit('Source archive checksum mismatch')
with tarfile.open(archive) as tar:
    for member in tar.getmembers():
        path = Path(member.name)
        if path.is_absolute() or '..' in path.parts or not member.isfile():
            raise SystemExit('Invalid source archive member')
        if path.parts[0] not in {'modules','migrations','cloudflare','scripts'}:
            raise SystemExit('Unexpected source path')
    tar.extractall(ROOT)
print('Full workflow source restored: quote, procurement, aftersales and migrations')
