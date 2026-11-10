"""Extend two labelled regression pins after relation completion and follower cleanup.

Keep the original pre-feature witnesses and the previous feature capture intact.
Only the NCAF input follower flags and the CoSiO saved structure may change; this
is serialization regression evidence, never an independent physical expectation.
"""

import hashlib
import json
import tempfile
from pathlib import Path

import edi

from tests.fixtures.c34_t28_baseline import generate_bytes as reference
from tests.fixtures.constraint_expressions.ncaf_follower_bytes import historical_followers

HERE = Path(__file__).resolve().parent
NCAF = 'corpus:ncaf-wish-3bank-s5/project'
COSIO = 'repo:docs/user/cli/pd-neut-cwl_cosio-d20_scan-324f/project'


def main():
    path = HERE / 'byte-pins.json'
    extension = json.loads(path.read_text())
    inputs = reference.inputs()
    with tempfile.TemporaryDirectory() as temporary:
        for index, case in enumerate((NCAF, COSIO)):
            row = extension['cases'][case]
            prior = row.get(
                'before_relation_application',
                {key: row[key] for key in ('after_input_sha256', 'after_saved_sha256')},
            )
            source = inputs[case]
            current = reference.hashes(source)
            if case == NCAF:
                restored = hashlib.sha256(
                    historical_followers(
                        'structures/ncaf.edi', (source / 'structures/ncaf.edi').read_bytes()
                    )
                ).hexdigest()
                if restored != prior['after_input_sha256']['structures/ncaf.edi']:
                    raise ValueError('the NCAF renewal changes only its three y/z free flags')
            saved = reference.observe(source, Path(temporary) / str(index), calculator=True)
            for channel, hashes in (('input', current), ('saved', saved)):
                old = prior[f'after_{channel}_sha256']
                allowed = (
                    {'structures/ncaf.edi'}
                    if (case, channel) == (NCAF, 'input')
                    else {'structures/cosio.edi'}
                    if (case, channel) == (COSIO, 'saved')
                    else set()
                )
                if hashes.keys() != old.keys() or any(
                    hashes[name] != old[name] for name in old if name not in allowed
                ):
                    raise ValueError('the renewal must retain every undeclared byte and file')
            row['before_relation_application'] = prior
            row['after_input_sha256'] = current
            row['after_saved_sha256'] = saved
    extension['relation_application_capture'] = {
        'claim': 'REGRESSION PIN: ADR-0078 section 7 and the declared NCAF follower cleanup.',
        'generator': 'tests/fixtures/constraint_expressions/renew_byte_pins.py',
        'engine_extension_sha256': hashlib.sha256(
            Path(edi._edi.__file__).read_bytes()
        ).hexdigest(),
    }
    path.write_text(json.dumps(extension, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
