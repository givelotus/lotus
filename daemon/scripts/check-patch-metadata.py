#!/usr/bin/env python3
"""Audit tracked patch mail, rationale, and recovered reference payload hashes."""
import argparse
import email.parser
import email.policy
import hashlib
import json
from pathlib import Path
import re
import subprocess


def inspect_patch(data):
    if not re.search(br'^diff --git ', data, re.MULTILINE):
        if b'PLACEHOLDER' in data or b'NO-OP' in data:
            return 'placeholder'
        raise ValueError('neither a source patch nor an explicit placeholder')
    if not data.startswith(b'From '):
        raise ValueError('source patch lacks git format-patch metadata')
    message = email.parser.BytesParser(policy=email.policy.default).parsebytes(data)
    for header in ('From', 'Date', 'Subject'):
        values = message.get_all(header, [])
        if len(values) != 1 or not str(values[0]).strip() or message[header].defects:
            raise ValueError(f'missing or malformed {header}')
    if message.defects or not message['From'].addresses:
        raise ValueError('malformed patch mail')
    sender = message['From'].addresses[0]
    if not sender.username or not sender.domain:
        raise ValueError('invalid patch author address')
    date = message['Date'].datetime
    if date is None or date.tzinfo is None:
        raise ValueError('invalid patch author date')
    subject = re.sub(r'^\[PATCH[^\]]*\]\s*', '', str(message['Subject']))
    if not subject.strip() or subject.startswith('Apply patch:'):
        raise ValueError('missing meaningful commit subject')
    body = re.split(r'(?m)^---$|^diff --git ', message.get_payload(), maxsplit=1)[0]
    if not body.strip():
        raise ValueError('missing commit rationale')
    return 'mail'


def audit(root):
    names = subprocess.check_output(
        ['git', '-C', str(root), 'ls-files', '-z', '*.patch', '*.diff']
    ).decode().split('\0')
    result = {'mail': 0, 'placeholder': 0}
    for name in filter(None, names):
        try:
            result[inspect_patch((root / name).read_bytes())] += 1
        except ValueError as error:
            raise ValueError(f'{name}: {error}') from error
    provenance = json.loads((root / 'daemon/patches/reference-metadata-provenance.json').read_text())
    for row in provenance['patches']:
        data = (root / row['patch']).read_bytes()
        payload = data[data.index(b'diff --git '):]
        if hashlib.sha256(payload).hexdigest() != row['payload_sha256']:
            raise ValueError(f"{row['patch']}: source payload differs from metadata-only recovery")
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.root), sort_keys=True))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')
