"""development hub  unit 11: independently count measured and explicitly unmeasured rows."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def test_inventory_writer_keeps_unmeasured_rows_and_rejects_a_hand_edited_header(
    tmp_path, monkeypatch
):
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        'e09_t74_bank', root / 'tools/checks/per_pr_runtimes.py'
    )
    bank = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bank)
    rows = {'tests/unit/py/test_a.py::test_one': 0.012, 'tests/unit/cpp/test_c.cpp::case': 0.019}
    holes = {'tests/unit/py/test_b.py::test_unmeasured': 'prescribed fixture hole'}
    text = bank.render_manifest(rows, [' independent fixture'], unmeasured=holes)
    for key, value in {'python': 2, 'cpp': 1, 'measured': 2, 'unmeasured': 1}.items():
        assert f'# inventory_{key} = {value}\n' in text, (
            ' unit 11: inventory counts include holes without manufacturing measurements'
        )
    assert (
        'UNMEASURED:prescribed fixture hole\ttests/unit/py/test_b.py::test_unmeasured' in text
    ), ' unit 11: the writer preserves each explicitly unmeasured identity and reason'
    manifest = tmp_path / 'runtimes.tsv'
    manifest.write_text(text)
    bank.load_manifest(manifest)
    manifest.write_text(text.replace('# inventory_measured = 2', '# inventory_measured = 3'))
    with pytest.raises(bank.ManifestError, match='inventory'):
        bank.load_manifest(manifest)

    real_load = bank.load_manifest
    nightly = 'tests/integration/py/test_cif_import_contract.py'
    ordinary = 'tests/unit/py/test_a.py::test_one'
    monkeypatch.setattr(bank, 'load_manifest', lambda: (1.0, {ordinary: 0.012}))
    monkeypatch.setattr(bank, 'load_unmeasured', set)
    monkeypatch.setattr(bank, 'load_module_costs', dict)
    monkeypatch.setattr(bank, 'parse_breach_baseline', set)
    monkeypatch.setattr(bank, '_marker_deselection_errors', list)
    monkeypatch.setattr(
        bank,
        'collect_nodeids',
        lambda excluded: (
            [ordinary] if nightly in excluded else [ordinary, nightly + '::test_witness']
        ),
    )
    assert bank.check() == 0, (
        'PR audit must not require an optional nightly row or collect the CIF matrix'
    )
    monkeypatch.setattr(bank, 'load_manifest', lambda: (1.0, {}))
    assert bank.check() == 1, 'A missing ordinary PR node must still fail the inventory audit'
    retained = {ordinary: 0.012, nightly + '::test_witness': 0.025}
    rendered = bank.render_manifest(retained, ['retained nightly measurements'])
    assert '# inventory_pr_python = 1\n' in rendered, (
        'Declared PR inventory must exclude the nightly cohort while retaining its measured row'
    )
    manifest.write_text(rendered)
    assert real_load(manifest)[1] == retained, (
        'Both PR and optional nightly measurements survive a canonical inventory render'
    )
    assert bank._ratchet_errors({nightly + '::test_witness': 1.1}, set()), (
        'A retained nightly measurement must still obey its unchanged integration tier bound'
    )
