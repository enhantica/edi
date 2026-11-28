"""Exercise the local COD tools on independent, byte-pinned sample files."""

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import edi
import pytest

from tools.probes import cod_cif_audit, cod_cif_census

ROOT = Path(__file__).resolve().parents[3]
PROBES = ROOT / 'tools/probes'
FIXTURES = ROOT / 'tests/fixtures/published_cif'
REVISIONS = {'1000003': '208206', '1000007': '282068', '1010067': '176729'}
PUBLISHED_DIGESTS = {
    '1000003': '7d139377aebd5f7d08325fa0005c109aafeb0ded96210eb709ad81d9d29a24f8',
    '1000007': '519dd231c62909eb50349b54a518f454fc5c21d1b005a777ede51ead83ede4e3',
    '1010067': '09e8dc19b330dbe3083b0fb0f6016164fbfe0adc9bf6a4b717bfb5db791bafd7',
}


def _snapshot(cache, output):
    process = subprocess.run(
        [sys.executable, str(PROBES / 'cod_cif_audit.py'), 'snapshot', str(cache), str(output)],
        cwd=ROOT,
        env={
            **os.environ,
            'OMP_NUM_THREADS': '1',
            'OPENBLAS_NUM_THREADS': '1',
        },
        capture_output=True,
        check=False,
        text=True,
        timeout=15,
    )
    assert process.returncode == 0, f'The offline snapshot runs successfully: {process.stderr}'


def _compare(monkeypatch, baseline, candidate, output):
    monkeypatch.setattr(
        sys, 'argv', ['cod_cif_audit.py', 'compare', *map(str, (baseline, candidate, output))]
    )
    cod_cif_audit.main()


def _rows(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return {row['cod_entry_id']: row for row in csv.DictReader(stream)}


def _assert_revisions_and_bytes(rows):
    assert rows.keys() == REVISIONS.keys(), 'Only the selected byte-pinned files are audited'
    for entry, revision in REVISIONS.items():
        payload = (FIXTURES / f'{entry}.cif').read_bytes()
        row = rows[entry]
        assert row['source_url'].endswith(f'/{entry}.cif@{revision}'), (
            'The CSV records the catalogue revision for the audited file'
        )
        assert row['cif_sha256'] == hashlib.sha256(payload).hexdigest(), (
            'The CSV records the SHA-256 of the actual supplied input bytes'
        )


def test_snapshot_and_compare_classify_local_published_inputs(tmp_path, monkeypatch):
    pinned = _rows(PROBES / 'cod-cif-import.csv')
    for entry, digest in PUBLISHED_DIGESTS.items():
        assert pinned[entry]['source_url'].endswith(f'/{entry}.cif@{REVISIONS[entry]}'), (
            'The pinned census retains the selected publication revision'
        )
        assert pinned[entry]['cif_sha256'] == digest, (
            'The census retains the digest of the unmodified upstream publication'
        )

    cache = tmp_path / 'cache'
    shutil.copytree(FIXTURES, cache, ignore=shutil.ignore_patterns('*.py', '__pycache__'))
    baseline, changed = tmp_path / 'baseline.json', tmp_path / 'changed.json'
    output = tmp_path / 'comparison.csv'
    _snapshot(cache, baseline)
    _compare(monkeypatch, baseline, baseline, output)
    rows = _rows(output)
    _assert_revisions_and_bytes(rows)
    expected = {
        '1000003': 'imported',
        '1000007': 'imported with defaults reported',
        '1010067': 'refused',
    }
    assert {entry: row['status_after_fix'] for entry, row in rows.items()} == expected, (
        'The sample distinguishes published values, reported defaults and refusal'
    )
    assert 'occupancy=1 (6 sites)' in rows['1000007']['detail_after_fix'], (
        'The audit identifies which default was reported and how many sites needed it'
    )
    assert '_atom_site_label' in rows['1010067']['detail_after_fix'], (
        'The refusal remains actionable in the CSV'
    )

    edited = json.loads(baseline.read_text(encoding='utf-8'))
    edited['entries']['1000007']['sha256'] = '0' * 64
    changed.write_text(json.dumps(edited), encoding='utf-8')
    rejected = tmp_path / 'invalid.csv'
    with pytest.raises(ValueError, match=r'COD 1000007: snapshot CIF bytes differ'):
        _compare(monkeypatch, baseline, changed, rejected)
    assert not rejected.exists(), 'The audit refuses differing CIF bytes before writing a result'


def test_census_run_and_export_check_revisions_from_a_local_zip(tmp_path):
    archive, ids, revisions, database, output = (
        tmp_path / name
        for name in ('local.zip', 'ids.txt', 'revisions.csv', 'state.sqlite', 'out.csv')
    )
    ids.write_text('\n'.join(REVISIONS) + '\n', encoding='ascii')
    revisions.write_text(
        'file,svnrevision\n'
        + '\n'.join(f'{entry},{revision}' for entry, revision in REVISIONS.items())
        + '\n',
        encoding='ascii',
    )
    with zipfile.ZipFile(archive, 'w') as local:
        for entry in REVISIONS:
            payload = (FIXTURES / f'{entry}.cif').read_bytes()
            if entry == '1000007':
                wrong = payload.replace(b'$Revision: 282068 $', b'$Revision: 100001 $')
                assert wrong != payload, 'The first archive member embeds a different revision'
                local.writestr(f'other/{entry}.cif', wrong)
            local.writestr(f'exact/{entry}.cif', payload)

    extension = Path(edi._edi.__file__).parent
    package = Path(edi.__file__).parents[1]
    run = [
        'run',
        '--database',
        str(database),
        '--ids',
        str(ids),
        '--revisions',
        str(revisions),
        '--before-lib',
        str(package),
        '--after-lib',
        str(package),
        '--before-extension',
        str(extension),
        '--after-extension',
        str(extension),
        '--local-zip',
        str(archive),
        '--jobs',
        '1',
    ]
    assert cod_cif_census.main(run) == 0, 'The census completes an offline run from the local ZIP'
    assert cod_cif_census.main(['export', str(database), str(output)]) == 0, (
        'The census exports the completed audit database through its CLI entry point'
    )
    rows = _rows(output)
    _assert_revisions_and_bytes(rows)
    assert all(
        row['initial_status'] == row['status_after_fix'] and row['initial_status'] != 'pending'
        for row in rows.values()
    ), 'The same runner on both sides yields a completed, identical classification'
