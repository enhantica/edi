"""Generate 's three-sigma start from the committed five-bank CLI project."""

import hashlib
import json
import re
import zipfile
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = 'f3ea7afea400639f2a66d6acb8d922163f1ef128'
SOURCE = 'docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project'
NUMBER = re.compile(r'(?<!\S)([+-]?(?:\d+(?:\.\d*)?|\.\d+))\((\d+)\)([eE][+-]?\d+)?(?!\S)')


def shift(match):
    value = Decimal(match[1])
    exponent = int((match[3] or 'e0')[1:])
    uncertainty = Decimal(match[2]).scaleb(value.as_tuple().exponent)
    shifted = value + 3 * uncertainty
    return f'{shifted}({match[2]})' + (f'e{exponent}' if match[3] else '')


def main():
    reference = ROOT / 'tests/fixtures/e04_t12_public_release/history'
    pins = json.loads((reference / 'manifest.json').read_text())['input']
    paths = sorted(name for name in pins if name.startswith(SOURCE + '/'))
    if not paths:
        raise RuntimeError(' source project is absent at ' + BASE)
    inputs, outputs, changes = {}, {}, {}
    for name in paths:
        relative = str(Path(name).relative_to(SOURCE))
        with zipfile.ZipFile(reference / 'input.zip') as archive:
            original = archive.read(name)
        if hashlib.sha256(original).hexdigest() != pins[name]:
            raise ValueError('the retained source project differs from its historical input pin')
        data, count = original, 0
        if name.endswith('.edi'):
            transformed, count = NUMBER.subn(shift, original.decode())
            data = transformed.encode()
        target = HERE / 'project' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        inputs[relative] = hashlib.sha256(original).hexdigest()
        outputs[relative] = hashlib.sha256(data).hexdigest()
        if count:
            changes[relative] = count
    record = {
        'source_commit': BASE,
        'source_project': SOURCE,
        'sigma_offset': 3,
        'input_sha256': inputs,
        'project_sha256': outputs,
        'shifted_tokens': changes,
        'reference': 'three-sigma performance workload; retained historical source input',
    }
    (HERE / 'project-provenance.json').write_text(
        json.dumps(record, indent=2, sort_keys=True) + '\n'
    )


if __name__ == '__main__':
    main()
