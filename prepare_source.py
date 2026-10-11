"""Restore complete workflow source shipped alongside the core. No business data."""
from pathlib import Path
import hashlib, tarfile
ROOT = Path(__file__).resolve().parent
archive = ROOT/'workflow-source.tar.gz'
EXPECTED = '0c6b4573c69f275897f1bd6df9cf913763ffc031ecaeaccfd17416d033984b8e'
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
