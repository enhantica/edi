# SPDX-License-Identifier: BSD-3-Clause
"""Download the pinned Whisper models for voice input and check them (ADR-0107).

The installer's voice component packs the small model; tests use the tiny one. A model is taken
only from the pinned HTTPS source and only with the size and SHA-256 in models.json; a cached copy
is checked again before it is used.
"""

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path

PINS = Path(__file__).with_name('models.json')
ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DESTINATION = ROOT / 'build/voice-models'
MANIFEST = 'voice-model.json'
MANIFEST_SCHEMA = 'edi.voice-model/1'


def pins() -> dict:
    data = json.loads(PINS.read_text(encoding='utf-8'))
    if data.get('schema') != 'edi.voice-models/1':
        raise RuntimeError(f'{PINS.name} has an unknown schema')
    if not data['source'].startswith('https://huggingface.co/'):
        raise RuntimeError('Voice models must come from the pinned HTTPS source')
    return data


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def matches(path: Path, model: dict) -> bool:
    return (
        path.is_file()
        and path.stat().st_size == model['bytes']
        and sha256(path) == model['sha256']
    )


def fetch(name: str, destination: Path = DEFAULT_DESTINATION) -> Path:
    """The checked model `name` ("small" or "tiny") in `destination`, downloaded when needed."""
    data = pins()
    model = data['models'][name]
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / model['file']
    if matches(path, model):
        return path
    partial = path.with_name(path.name + '.part')
    with (
        urllib.request.urlopen(data['source'] + model['file'], timeout=60) as response,  # noqa: S310
        partial.open('wb') as stream,
    ):
        shutil.copyfileobj(response, stream, length=1 << 20)
    if not matches(partial, model):
        partial.unlink()
        raise RuntimeError(f'{model["file"]} differs from its pinned size or SHA-256')
    partial.replace(path)
    return path


def manifest(name: str) -> dict:
    """The voice-model.json the app reads beside the installed model."""
    model = pins()['models'][name]
    return {
        'schema': MANIFEST_SCHEMA,
        'file': model['file'],
        'bytes': model['bytes'],
        'sha256': model['sha256'],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        '--test', action='store_true', help='fetch only the tiny model the tests use'
    )
    parser.add_argument('--destination', type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args()
    for name in ['tiny'] if args.test else ['small', 'tiny']:
        print(fetch(name, args.destination))
    return 0


if __name__ == '__main__':
    sys.exit(main())
