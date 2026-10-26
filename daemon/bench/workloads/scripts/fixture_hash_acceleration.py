"""Optional fixture-only acceleration, preserving the frozen hash byte semantics."""
import hashlib
import importlib
from pathlib import Path
import sys


def install(site):
    site = Path(site).resolve()
    if not site.is_dir():
        raise ValueError('Fixture hash package directory does not exist')
    sys.path.insert(0, str(site))
    backend = importlib.import_module('blake3')
    if backend.__version__ != '1.0.8':
        raise ValueError('Fixture hash backend must be pinned blake3 1.0.8')
    messages = importlib.import_module('test_framework.messages')
    frozen = messages.blake3_single_chunk
    if backend.blake3(b'').hexdigest() != 'af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262':
        raise ValueError('BLAKE3 known-empty vector failed')

    def accelerated(data):
        # Frozen multi-chunk hashing differs from the standard at some lengths.
        # Keep it byte-identical; small signing/leaf hashes are the hot fixture work.
        return backend.blake3(data).digest() if len(data) <= 1024 else frozen(data)

    vectors = []
    for size in (0, 1, 31, 64, 65, 207, 1023, 1024, 1025, 2048, 2049, 4096, 8192):
        payload = bytes(index % 251 for index in range(size))
        expected = frozen(payload)
        if accelerated(payload) != expected:
            raise ValueError('Accelerated fixture hash differs from frozen bytes')
        vectors.append({'bytes': size, 'frozen_digest': expected.hex(),
                        'standard_backend_matches': backend.blake3(payload).digest() == expected})
    messages.blake3_single_chunk = accelerated
    package = Path(backend.__file__).parent
    return {'enabled': True, 'scope': 'fixture preparation only; <=1024 byte hashes',
            'version': backend.__version__, 'site': str(site), 'vectors': vectors,
            'large_payloads': 'unchanged frozen fallback; standard digest mismatch preserved',
            'backend_files_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in package.iterdir() if p.suffix in ('.py', '.so')},
            'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
