#!/usr/bin/env python3
"""Offline Dart <-> OpenSSL checks; optionally also use daemon libsecp256k1.

Requires the Python cryptography package in a disposable development venv.
Never opens a network connection or reads wallet keys. The test key is integer 1.
"""
import argparse
from collections import Counter
import json
import hashlib
import re
from urllib.parse import unquote, urlparse
import cryptography
from pathlib import Path
import subprocess

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

ROOT = Path(__file__).resolve().parents[1]
ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dart', default='dart')
    parser.add_argument('--native-verifier', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    document = json.loads(subprocess.check_output(
        [args.dart, 'run', 'tool/signature_interop.dart'], cwd=ROOT))
    dart_file = args.output_dir / 'dart-signatures.json'
    dart_file.write_text(json.dumps(document, indent=2) + '\n')
    key = ec.derive_private_key(1, ec.SECP256K1())
    public = key.public_key()
    encoded_public = public.public_bytes(serialization.Encoding.X962,
                                         serialization.PublicFormat.CompressedPoint).hex()
    assert encoded_public == document['publicKey']
    lengths = Counter()
    short, high, low_s = 0, 0, 0
    for row in document['signatures']:
        digest, der = bytes.fromhex(row['digest']), bytes.fromhex(row['der'])
        public.verify(der, digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        r, s = utils.decode_dss_signature(der)
        assert utils.encode_dss_signature(r, s) == der
        assert r == int(row['r'], 16) and s == int(row['s'], 16)
        assert 0 < s <= ORDER // 2
        compact = bytes.fromhex(row['compact'])
        assert len(compact) == 65
        assert int.from_bytes(compact[1:33], 'big') == r
        assert int.from_bytes(compact[33:], 'big') == s
        short += r.bit_length() <= 248 or s.bit_length() <= 248
        high += r.bit_length() == 256
        low_s += 1
        lengths[len(der)] += 1
        if args.native_verifier:
            subprocess.run([str(args.native_verifier.resolve()), row['digest'],
                            encoded_public, row['der']], check=True)
    assert short > 0 and high > 0
    reverse = {'publicKey': encoded_public, 'signatures': []}
    for row in document['signatures'][:32]:
        digest = bytes.fromhex(row['digest'])
        der = key.sign(digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        # Include both low-S and high-S encodings; ECDSA verification permits both.
        r, s = utils.decode_dss_signature(der)
        for scalar in (min(s, ORDER - s), max(s, ORDER - s)):
            reverse['signatures'].append({'digest': row['digest'],
                'der': utils.encode_dss_signature(r, scalar).hex()})
    reverse_file = args.output_dir / 'openssl-signatures.json'
    reverse_file.write_text(json.dumps(reverse, indent=2) + '\n')
    result = subprocess.check_output([args.dart, 'run', 'tool/signature_interop.dart',
                                     'verify', str(reverse_file.resolve())], cwd=ROOT, text=True)
    packages = json.loads((ROOT / '.dart_tool/package_config.json').read_text())['packages']
    package = next(p for p in packages if p['name'] == 'pointycastle')
    package_uri = (ROOT / '.dart_tool/package_config.json').as_uri()
    from urllib.parse import urljoin
    spec = Path(unquote(urlparse(urljoin(package_uri, package['rootUri'])).path)) / 'pubspec.yaml'
    version = re.search(r'^version: (.+)$', spec.read_text(), re.M).group(1)
    summary = {'pointycastle': version,
               'dart': subprocess.check_output([args.dart, '--version'], text=True).strip(),
               'cryptography': cryptography.__version__,
               'native_verifier_sha256': hashlib.sha256(args.native_verifier.read_bytes()).hexdigest() if args.native_verifier else None,
               'openssl': default_backend().openssl_version_text(),
               'dart_to_openssl': len(document['signatures']),
               'dart_to_native_secp256k1': len(document['signatures']) if args.native_verifier else 0,
               'openssl_to_dart': len(reverse['signatures']), 'low_s_signatures': low_s,
               'short_scalar_signatures': short, 'high_bit_r_signatures': high,
               'der_lengths': dict(sorted(lengths.items())), 'reverse_result': result.strip()}
    (args.output_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
