"""Authenticate committed solver retakes before checking the original annotation stage."""

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from tests.fixtures.path_keys import repository_key
from tests.fixtures.stop_defaults import retention

HERE = Path(__file__).parent
ROOT = HERE.resolve().parents[2]
BEFORE = '42491216b12ea0d676a680e2606e513835c8f42d'
INTERMEDIATE = '9d4162bb35cc1f361daf5e1e2fc0860b0def62cd'
AFTER = 'b2c6d9b1547ed6506d2bc36cae5f9a43b748895a'


def previous_bytes(name, data):
    data = retention.composed_bytes(name, data)
    name = repository_key(name)
    rows = json.loads((HERE / 'joined-pin-sources.json').read_text())['files']
    row = rows.get(name)
    if row is None:
        return data
    digest = hashlib.sha256(data).hexdigest()
    if digest == row['before_sha256']:
        return data
    assert digest in {row['after_sha256'], row.get('intermediate_sha256')}, (
        'Pin provenance requires every committed source byte across the solver retake'
    )
    with zipfile.ZipFile(HERE / 'joined-pin-sources.zip') as archive:
        before = archive.read(row['before_sha256'])
    assert hashlib.sha256(before).hexdigest() == row['before_sha256'], (
        'The original annotation witness keeps its complete committed byte identity'
    )
    return before


def generate():
    from tests.fixtures.metadata_transition import (  # noqa: PLC0415 - generator-only inputs
        pin_sources,
        release_pin_bytes,
    )

    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT)

    revision = git('rev-parse', AFTER).decode().strip()
    rows, payloads = {}, {}
    sources = {
        name: {'after_sha256': row['after_sha256']}
        for name, row in release_pin_bytes.rows().items()
    }
    sources.update(pin_sources.rows())
    for name, source in sources.items():
        before, after = (git('show', ref + ':' + name) for ref in (BEFORE, revision))
        assert hashlib.sha256(before).hexdigest() == source['after_sha256'], (
            'Every joined retake starts at the original exact annotation witness'
        )
        if before == after:
            continue
        intermediate = git('show', INTERMEDIATE + ':' + name)
        old, new = json.loads(before), json.loads(after)
        assert release_pin_bytes.references(old) == release_pin_bytes.references(
            json.loads(intermediate)
        ), 'Every retained intermediate stage keeps the same physical references and bounds'
        if 'metadata' in source:
            assert old['source']['pins'] == new['source']['pins'] == source['metadata'], (
                'A retake cannot rewrite the original pin-document attribution'
            )
        assert release_pin_bytes.references(old) == release_pin_bytes.references(new), (
            'Solver retakes cannot rebase independent physical references or their bounds'
        )
        old_hash, new_hash = (hashlib.sha256(raw).hexdigest() for raw in (before, after))
        rows[name] = {'before_sha256': old_hash, 'after_sha256': new_hash}
        if intermediate not in {after, before}:
            rows[name]['intermediate_sha256'] = hashlib.sha256(intermediate).hexdigest()
        payloads[old_hash] = before
    with zipfile.ZipFile(HERE / 'joined-pin-sources.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for digest, raw in sorted(payloads.items()):
            info = zipfile.ZipInfo(digest, (2026, 11, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    (HERE / 'joined-pin-sources.json').write_text(
        json.dumps(
            {
                'claim': 'Committed source-stage receipt only; no numerical fit or recapture',
                'before_revision': BEFORE,
                'intermediate_revision': INTERMEDIATE,
                'after_revision': revision,
                'files': rows,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    generate()
